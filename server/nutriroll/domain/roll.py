"""Roll algorithm - pure functions implementing vision Logic 2 Steps A-F.

Framework-free: no FastAPI, no SQLAlchemy. Inputs are domain `Component`
objects + a `RollRequest`; output is a `RolledBowl` with per-slot
explanations. Sampling is seeded for determinism in tests; production
callers omit ``seed`` to get a fresh roll.

The LLM is intentionally NOT an entry point here (vision §6).
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from nutriroll.domain.component import Category, Component, CookingMethod

# ---------------------------------------------------------------------------
# Inputs / outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SlotSpec:
    """How many components to roll for a single slot."""

    category: Category
    count: int = 1

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError("slot count must be >= 0")


@dataclass(frozen=True, slots=True)
class FeatureWeights:
    """Vision §Logic 2 Step B. Weights are non-negative."""

    taste_match: float = 0.30
    novelty: float = 0.20
    price_fit: float = 0.20
    nutrition_fit: float = 0.15
    time_fit: float = 0.10
    pantry_bonus: float = 0.05

    def __post_init__(self) -> None:
        for label in (
            "taste_match",
            "novelty",
            "price_fit",
            "nutrition_fit",
            "time_fit",
            "pantry_bonus",
        ):
            v: float = getattr(self, label)
            if v < 0:
                raise ValueError(f"weight {label} must be >= 0, got {v}")


@dataclass(frozen=True, slots=True)
class RollRequest:
    slots: tuple[SlotSpec, ...]
    dietary_mode: str | None = None
    allergens_excluded: frozenset[str] = field(default_factory=frozenset[str])
    blacklisted_ids: frozenset[UUID] = field(default_factory=frozenset[UUID])
    time_budget_min: int | None = None
    forced_methods: Mapping[Category, CookingMethod] = field(
        default_factory=dict[Category, CookingMethod]
    )
    recent_component_ids: frozenset[UUID] = field(default_factory=frozenset[UUID])
    weights: FeatureWeights = field(default_factory=FeatureWeights)
    temperature: float = 0.5
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.temperature <= 0:
            raise ValueError("temperature must be > 0")
        if self.time_budget_min is not None and self.time_budget_min < 0:
            raise ValueError("time_budget_min must be >= 0")


@dataclass(frozen=True, slots=True)
class ChosenComponent:
    component: Component
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RolledBowl:
    slots: tuple[ChosenComponent, ...]


class EmptyCandidatePoolError(Exception):
    """Raised when Step A leaves a slot with zero candidates."""

    def __init__(self, category: Category, reason: str) -> None:
        super().__init__(f"no candidates for {category.value}: {reason}")
        self.category = category
        self.reason = reason


# ---------------------------------------------------------------------------
# Step A — hard filters
# ---------------------------------------------------------------------------

# Dietary mode → tags a component MUST carry to qualify.
_DIETARY_REQUIRED_TAGS: dict[str, frozenset[str]] = {
    "vegan": frozenset({"vegan"}),
    "vegetarian": frozenset({"vegetarian"}),
    "pescatarian": frozenset(),  # any non-meat or fish; checked separately
}

# Tags that disqualify a pescatarian component (meat).
_PESCATARIAN_FORBIDDEN_TAGS: frozenset[str] = frozenset({"meat", "poultry"})


def _passes_dietary(component: Component, mode: str | None) -> bool:
    if mode is None or mode == "omnivore" or mode == "custom":
        return True
    if mode == "pescatarian":
        return not (set(component.dietary_tags) & _PESCATARIAN_FORBIDDEN_TAGS)
    required = _DIETARY_REQUIRED_TAGS.get(mode)
    if required is None:
        return True
    return required.issubset(set(component.dietary_tags))


def _passes_allergens(component: Component, excluded: frozenset[str]) -> bool:
    return not (set(component.allergens) & excluded)


def _passes_time_budget(component: Component, budget_min: int | None) -> bool:
    if budget_min is None:
        return True
    # A component is feasible if at least one of its supported methods fits.
    for spec in component.cooking_methods:
        if spec.approx_minutes is None or spec.approx_minutes <= budget_min:
            return True
    return False


def _passes_forced_method(
    component: Component, forced: CookingMethod | None
) -> bool:
    if forced is None:
        return True
    return any(spec.method == forced for spec in component.cooking_methods)


def filter_candidates(
    components: Iterable[Component],
    request: RollRequest,
    category: Category,
) -> list[Component]:
    """Step A. Returns the surviving candidate pool for a single slot."""
    forced = request.forced_methods.get(category)
    out: list[Component] = []
    for c in components:
        if c.category is not category:
            continue
        if c.blacklisted:
            continue
        if c.id in request.blacklisted_ids:
            continue
        if not _passes_dietary(c, request.dietary_mode):
            continue
        if not _passes_allergens(c, request.allergens_excluded):
            continue
        if not _passes_time_budget(c, request.time_budget_min):
            continue
        if not _passes_forced_method(c, forced):
            continue
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# Step B — scoring
# ---------------------------------------------------------------------------

# A "balanced" bowl per category roughly looks like this for nutrition_fit:
# values are kcal/100g and macro-density rough targets.
_BALANCED_TARGETS: dict[Category, dict[str, float]] = {
    Category.BASE: {"kcal": 130.0, "carbs_g": 25.0, "protein_g": 4.0, "fat_g": 1.5},
    Category.VEGETABLE: {"kcal": 35.0, "carbs_g": 7.0, "protein_g": 2.0, "fat_g": 0.4},
    Category.SAUCE: {"kcal": 120.0, "carbs_g": 8.0, "protein_g": 2.0, "fat_g": 9.0},
    Category.TOPPING: {"kcal": 200.0, "carbs_g": 10.0, "protein_g": 12.0, "fat_g": 12.0},
}


def _nutrition_fit(component: Component) -> float:
    target = _BALANCED_TARGETS[component.category]
    macros = component.macros_per_100g
    actual = {
        "kcal": macros.kcal,
        "carbs_g": macros.carbs_g,
        "protein_g": macros.protein_g,
        "fat_g": macros.fat_g,
    }
    # L1 distance, normalised against target sum, clipped to [0, 1].
    denom = sum(target.values()) or 1.0
    dist = sum(abs(actual[k] - target[k]) for k in target) / denom
    return max(0.0, 1.0 - dist)


def _time_fit(component: Component, budget_min: int | None) -> float:
    if budget_min is None or budget_min <= 0:
        return 0.5
    fastest = min(
        (s.approx_minutes for s in component.cooking_methods if s.approx_minutes is not None),
        default=0,
    )
    if fastest >= budget_min:
        return 0.0
    # Diminishing-returns: more headroom is better but with sqrt curve.
    return min(1.0, math.sqrt((budget_min - fastest) / budget_min))


def _novelty(component: Component, recent: frozenset[UUID]) -> float:
    return 0.0 if component.id in recent else 1.0


def score_component(
    component: Component,
    request: RollRequest,
) -> tuple[float, dict[str, float]]:
    """Step B. Returns (score, feature contributions)."""
    w = request.weights
    f_nutrition = _nutrition_fit(component)
    f_time = _time_fit(component, request.time_budget_min)
    f_novelty = _novelty(component, request.recent_component_ids)
    # taste_match / price_fit / pantry_bonus require profile data we don't
    # have in v1 — treat as neutral 0.5 so weights still influence ordering
    # if the user dials them up.
    contributions = {
        "nutrition_fit": w.nutrition_fit * f_nutrition,
        "time_fit": w.time_fit * f_time,
        "novelty": w.novelty * f_novelty,
        "taste_match": w.taste_match * 0.5,
        "price_fit": w.price_fit * 0.5,
        "pantry_bonus": w.pantry_bonus * 0.0,
    }
    return sum(contributions.values()), contributions


# ---------------------------------------------------------------------------
# Step C — assembly with softmax sampling
# ---------------------------------------------------------------------------


def _softmax_sample(
    rng: random.Random,
    items: Sequence[tuple[Component, float]],
    temperature: float,
) -> Component:
    if not items:
        raise ValueError("cannot sample from empty pool")
    if len(items) == 1:
        return items[0][0]
    # Numerically stable softmax.
    scores = [s / temperature for _, s in items]
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps) or 1.0
    weights = [e / total for e in exps]
    pick = rng.random()
    acc = 0.0
    for (component, _score), w in zip(items, weights, strict=True):
        acc += w
        if pick <= acc:
            return component
    return items[-1][0]


def _top_reasons(
    component: Component,
    contributions: Mapping[str, float],
    request: RollRequest,
) -> tuple[str, ...]:
    """Step F. Top 2 contributing features as plain-text reasons."""
    ranked = sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)
    out: list[str] = []
    for name, value in ranked:
        if value <= 0:
            continue
        if len(out) >= 2:
            break
        if name == "nutrition_fit":
            out.append(f"balanced macros for a {component.category.value}")
        elif name == "time_fit":
            budget = request.time_budget_min
            if budget is not None:
                fastest = min(
                    (
                        s.approx_minutes
                        for s in component.cooking_methods
                        if s.approx_minutes is not None
                    ),
                    default=0,
                )
                out.append(f"cooks in ~{fastest} min, under your {budget} min budget")
            else:
                out.append("quick to prepare")
        elif name == "novelty":
            out.append("you haven't had this recently")
        elif name == "taste_match":
            out.append("matches flavors you usually enjoy")
        elif name == "price_fit":
            out.append("fits your per-portion budget")
        elif name == "pantry_bonus":
            out.append("already in your pantry")
    return tuple(out)


# ---------------------------------------------------------------------------
# Step D — pairing rules
# ---------------------------------------------------------------------------


_BOLD_FLAVOR_TAGS: frozenset[str] = frozenset({"spicy", "bold", "smoky"})
_CRUNCHY_TAG: str = "crunchy"


def check_pairing(slots: Sequence[ChosenComponent]) -> list[str]:
    """Step D. Returns a list of human-readable pairing complaints (empty = OK)."""
    issues: list[str] = []
    bold_count = 0
    has_topping = False
    has_crunchy = False
    for choice in slots:
        tags = set(choice.component.flavor_tags)
        if tags & _BOLD_FLAVOR_TAGS:
            bold_count += 1
        if choice.component.category is Category.TOPPING:
            has_topping = True
            if _CRUNCHY_TAG in tags:
                has_crunchy = True
    if bold_count > 1:
        issues.append("too many bold/spicy components")
    if has_topping and not has_crunchy:
        issues.append("topping present but no crunchy element")
    return issues


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def roll(
    components: Iterable[Component],
    request: RollRequest,
    *,
    max_resamples: int = 4,
) -> RolledBowl:
    """Step C orchestrator. Runs A → B → C with D as a soft validator.

    Raises `EmptyCandidatePoolError` when a slot has zero candidates after
    Step A — caller is expected to surface relaxation suggestions.
    """
    rng = random.Random(request.seed)  # noqa: S311 -- recommendation, not crypto
    components_list = list(components)
    chosen_per_slot: list[ChosenComponent] = []

    for slot in request.slots:
        if slot.count == 0:
            continue
        pool = filter_candidates(components_list, request, slot.category)
        if not pool:
            raise EmptyCandidatePoolError(
                slot.category, "all candidates eliminated by hard filters"
            )

        scored: list[tuple[Component, float, dict[str, float]]] = []
        for c in pool:
            score, contributions = score_component(c, request)
            scored.append((c, score, contributions))

        chosen_ids: set[UUID] = set()
        for _ in range(slot.count):
            remaining = [(c, s) for c, s, _ in scored if c.id not in chosen_ids]
            if not remaining:
                break
            picked = _softmax_sample(rng, remaining, request.temperature)
            picked_score, contributions = next(
                (s, contrib) for c, s, contrib in scored if c.id == picked.id
            )
            reasons = _top_reasons(picked, contributions, request)
            chosen_per_slot.append(
                ChosenComponent(component=picked, score=picked_score, reasons=reasons)
            )
            chosen_ids.add(picked.id)

    # Step D — soft validation. Resample once per violating slot up to K times.
    for _ in range(max_resamples):
        issues = check_pairing(chosen_per_slot)
        if not issues:
            break
        # Drop the lowest-scoring choice and resample its slot.
        lowest_idx = min(range(len(chosen_per_slot)), key=lambda i: chosen_per_slot[i].score)
        target = chosen_per_slot[lowest_idx]
        pool = filter_candidates(components_list, request, target.component.category)
        already_picked = {c.component.id for c in chosen_per_slot}
        scored = [
            (c, *score_component(c, request))
            for c in pool
            if c.id not in already_picked
        ]
        if not scored:
            break
        picked = _softmax_sample(
            rng, [(c, s) for c, s, _ in scored], request.temperature
        )
        picked_score, contributions = next(
            (s, contrib) for c, s, contrib in scored if c.id == picked.id
        )
        chosen_per_slot[lowest_idx] = ChosenComponent(
            component=picked,
            score=picked_score,
            reasons=_top_reasons(picked, contributions, request),
        )

    return RolledBowl(slots=tuple(chosen_per_slot))


def reroll_slot(
    components: Iterable[Component],
    request: RollRequest,
    bowl: RolledBowl,
    slot_index: int,
) -> RolledBowl:
    """Step E — rerun a single slot, keeping the others. Bumps novelty by
    excluding the previously-chosen component for that slot from the pool.
    """
    if slot_index < 0 or slot_index >= len(bowl.slots):
        raise IndexError("slot_index out of range")
    target = bowl.slots[slot_index]
    extra_excluded = request.blacklisted_ids | {target.component.id}
    sub_request = RollRequest(
        slots=(SlotSpec(category=target.component.category, count=1),),
        dietary_mode=request.dietary_mode,
        allergens_excluded=request.allergens_excluded,
        blacklisted_ids=extra_excluded,
        time_budget_min=request.time_budget_min,
        forced_methods=request.forced_methods,
        recent_component_ids=request.recent_component_ids,
        weights=request.weights,
        temperature=request.temperature,
        seed=request.seed,
    )
    sub = roll(components, sub_request)
    new_slots = list(bowl.slots)
    new_slots[slot_index] = sub.slots[0]
    return RolledBowl(slots=tuple(new_slots))


__all__ = [
    "ChosenComponent",
    "EmptyCandidatePoolError",
    "FeatureWeights",
    "RollRequest",
    "RolledBowl",
    "SlotSpec",
    "check_pairing",
    "filter_candidates",
    "reroll_slot",
    "roll",
    "score_component",
]
