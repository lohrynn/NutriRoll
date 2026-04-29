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
from typing import ClassVar, Literal
from uuid import UUID

from nutriroll.domain.category_meta import BALANCED_TARGETS
from nutriroll.domain.component import Category, Component, CookingMethod, PortionUnit
from nutriroll.domain.equipment import Equipment, component_is_equipment_feasible

MacroMode = Literal["target", "min", "max"]

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
    """Vision §Logic 2 Step B. Weights are non-negative.

    The seven well-known weights map 1:1 to the features computed by
    ``score_component()``. ``extra_weights`` is a forward-compat bucket
    for new scoring signals (e.g. ``seasonal_bonus``, ``eco_score``)
    that can be persisted and round-tripped through the API before the
    algorithm gains a feature for them — see modularity-audit M6.
    Unknown keys are silently ignored by ``score_component()`` until a
    matching feature lands.
    """

    taste_match: float = 0.30
    novelty: float = 0.20
    price_fit: float = 0.20
    nutrition_fit: float = 0.15
    time_fit: float = 0.10
    pantry_bonus: float = 0.05
    direction_match: float = 0.25
    macro_target_fit: float = 0.5
    extra_weights: Mapping[str, float] = field(default_factory=dict[str, float])

    WELL_KNOWN_KEYS: ClassVar[tuple[str, ...]] = (
        "taste_match",
        "novelty",
        "price_fit",
        "nutrition_fit",
        "time_fit",
        "pantry_bonus",
        "direction_match",
        "macro_target_fit",
    )

    def __post_init__(self) -> None:
        for label in self.WELL_KNOWN_KEYS:
            v: float = getattr(self, label)
            if v < 0:
                raise ValueError(f"weight {label} must be >= 0, got {v}")
        for key, value in self.extra_weights.items():
            if not key or not key.strip():
                raise ValueError("extra_weights keys must be non-empty")
            if key in self.WELL_KNOWN_KEYS:
                raise ValueError(
                    f"extra_weights {key!r} clashes with a well-known field; "
                    "set it as a regular argument instead"
                )
            if value < 0:
                raise ValueError(f"extra_weights[{key!r}] must be >= 0, got {value}")


@dataclass(frozen=True, slots=True)
class MacroTarget:
    """A single per-portion macro constraint (Phase 11).

    ``mode`` controls how the algorithm scores deviation:
      * ``"target"`` — closest to ``value`` wins (triangular penalty).
      * ``"min"``    — only penalise *below* ``value`` (e.g. >=50 g protein).
      * ``"max"``    — only penalise *above* ``value`` (e.g. <=30 g fat).
    """

    value: float
    mode: MacroMode = "target"

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"MacroTarget.value must be >= 0, got {self.value}")
        if self.mode not in ("target", "min", "max"):
            raise ValueError(f"invalid MacroTarget.mode: {self.mode!r}")


@dataclass(frozen=True, slots=True)
class MacroTargets:
    """Per-portion macro targets for a single rolled bowl (Phase 11).

    Each well-known field is optional — ``None`` means "no preference" for
    that macro and the algorithm ignores it. Unknown macro keys round-trip
    through ``extra`` so a forward-compat target like ``sodium_mg`` flows
    end-to-end without schema changes (mirrors :class:`Macros`).
    """

    kcal: MacroTarget | None = None
    protein_g: MacroTarget | None = None
    carbs_g: MacroTarget | None = None
    fat_g: MacroTarget | None = None
    fiber_g: MacroTarget | None = None
    extra: tuple[tuple[str, MacroTarget], ...] = ()

    WELL_KNOWN_KEYS: ClassVar[tuple[str, ...]] = (
        "kcal",
        "protein_g",
        "carbs_g",
        "fat_g",
        "fiber_g",
    )

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for key, _ in self.extra:
            if not key or not key.strip():
                raise ValueError("extra macro target keys must be non-empty")
            if key in self.WELL_KNOWN_KEYS:
                raise ValueError(f"extra macro target {key!r} clashes with a well-known field")
            if key in seen:
                raise ValueError(f"duplicate extra macro target {key!r}")
            seen.add(key)

    def as_mapping(self) -> dict[str, MacroTarget]:
        """Flat name → MacroTarget mapping for *set* targets only."""
        out: dict[str, MacroTarget] = {}
        for key in self.WELL_KNOWN_KEYS:
            v: MacroTarget | None = getattr(self, key)
            if v is not None:
                out[key] = v
        for key, v in self.extra:
            out[key] = v
        return out

    @classmethod
    def from_mapping(cls, data: Mapping[str, MacroTarget]) -> MacroTargets:
        kwargs: dict[str, MacroTarget | None] = {k: None for k in cls.WELL_KNOWN_KEYS}
        extras: list[tuple[str, MacroTarget]] = []
        for key, v in data.items():
            if key in cls.WELL_KNOWN_KEYS:
                kwargs[key] = v
            else:
                extras.append((key, v))
        return cls(**kwargs, extra=tuple(extras))

    def is_empty(self) -> bool:
        return not self.as_mapping()


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
    tag_boosts: Mapping[str, float] = field(default_factory=dict[str, float])
    macro_targets: MacroTargets | None = None
    """Phase 11. Per-portion macro constraints. ``None`` = no preference;
    the algorithm falls back to the generic ``BALANCED_TARGETS``-based
    ``nutrition_fit`` feature only."""
    portions: int = 1
    """Phase 12 — meal-prep batch size. Does not change which components are
    rolled (targets stay per-portion); used by the recipe / shopping / planner
    surfaces to scale grams and track remaining portions."""
    available_equipment: frozenset[Equipment] = field(
        default_factory=lambda: frozenset()
    )
    """Phase 13 — the user's owned hardware. Empty = "all available"
    (back-compat). When non-empty, components without at least one
    equipment-feasible cooking method are dropped in Step A."""
    # IDs of components currently in the user's pantry. Boosts ``pantry_bonus``.
    pantry_component_ids: frozenset[UUID] = field(default_factory=frozenset[UUID])
    # Subset of ``pantry_component_ids`` that are about to expire (within
    # ``EXPIRY_WARNING_DAYS`` server-side). Receives a stronger boost so the
    # roller surfaces ingredients the user should use up.
    expiring_component_ids: frozenset[UUID] = field(default_factory=frozenset[UUID])
    temperature: float = 0.5
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.temperature <= 0:
            raise ValueError("temperature must be > 0")
        if self.time_budget_min is not None and self.time_budget_min < 0:
            raise ValueError("time_budget_min must be >= 0")
        for tag, boost in self.tag_boosts.items():
            if not tag.strip():
                raise ValueError("tag_boosts keys must be non-empty")
            if boost < -1.0 or boost > 1.0:
                raise ValueError(f"tag_boosts[{tag!r}] must be in [-1, 1], got {boost}")
        if not self.expiring_component_ids.issubset(self.pantry_component_ids):
            raise ValueError("expiring_component_ids must be a subset of pantry_component_ids")
        if self.portions < 1 or self.portions > 14:
            raise ValueError(f"portions must be in [1, 14], got {self.portions}")


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


def _passes_forced_method(component: Component, forced: CookingMethod | None) -> bool:
    if forced is None:
        return True
    return any(spec.method == forced for spec in component.cooking_methods)


def _passes_equipment(component: Component, available: frozenset[Equipment]) -> bool:
    """Step A. Drop components when none of their methods are equipment-feasible.

    Empty ``available`` is treated as "all available" (back-compat for users
    who never declared equipment). See :mod:`nutriroll.domain.equipment`.
    """
    return component_is_equipment_feasible(component, available)


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
        if not _passes_equipment(c, request.available_equipment):
            continue
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# Step B — scoring
# ---------------------------------------------------------------------------


def _nutrition_fit(component: Component) -> float:
    target = BALANCED_TARGETS[component.category]
    macros = component.macros_per_100g
    actual = {
        "kcal": macros.kcal,
        "carbs_g": macros.carbs_g,
        "protein_g": macros.protein_g,
        "fat_g": macros.fat_g,
        "fiber_g": macros.fiber_g,
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


def _direction_match(component: Component, boosts: Mapping[str, float]) -> float:
    """Sum the boosts whose tag the component carries; clip to [-1, 1].

    Negative boosts soft-penalise (used by axis sliders pulling the other
    direction). A component with no overlapping tags scores 0 and is
    therefore neutral with respect to direction selection.
    """
    if not boosts:
        return 0.0
    tags = set(component.flavor_tags) | set(component.dietary_tags)
    total = 0.0
    for tag, boost in boosts.items():
        if tag in tags:
            total += boost
    return max(-1.0, min(1.0, total))


def _portion_grams(component: Component) -> float:
    """Component portion expressed in grams, or 0 if unit is not gram-based."""
    if component.default_portion.unit is PortionUnit.GRAM:
        return component.default_portion.value
    return 0.0


def _macro_target_fit(
    component: Component,
    targets: MacroTargets | None,
    n_slots: int,
) -> float:
    """Phase 11. Per-portion fit of *this* component vs the user's targets.

    The component contributes ``macros_per_100g * portion_g / 100`` to the
    bowl per portion. We compare that single-slot contribution against the
    *fair share* of each target, ``target / n_slots``, so that the algorithm
    rewards components that pull the bowl toward the target.

    Returns 0.0 (neutral) when ``targets`` is None / empty so the existing
    behaviour is preserved when the user sets no preference.
    """
    if targets is None or n_slots <= 0:
        return 0.0
    mapping = targets.as_mapping()
    if not mapping:
        return 0.0
    factor = _portion_grams(component) / 100.0
    macros = component.macros_per_100g.as_dict()
    total = 0.0
    count = 0
    for name, target in mapping.items():
        actual = macros.get(name, 0.0) * factor
        share = target.value / n_slots
        if share <= 0:
            # User asked for 0 of something — only "max"/"target" make sense.
            fit = 1.0 if target.mode == "min" or actual <= 0 else 0.0
        elif target.mode == "target":
            dist = abs(actual - share) / share
            fit = max(0.0, 1.0 - dist)
        elif target.mode == "min":
            fit = min(1.0, actual / share)
        else:  # "max"
            over = max(0.0, actual - share)
            fit = max(0.0, 1.0 - over / share)
        total += fit
        count += 1
    return total / count if count else 0.0


def score_component(
    component: Component,
    request: RollRequest,
) -> tuple[float, dict[str, float]]:
    """Step B. Returns (score, feature contributions)."""
    w = request.weights
    f_nutrition = _nutrition_fit(component)
    f_time = _time_fit(component, request.time_budget_min)
    f_novelty = _novelty(component, request.recent_component_ids)
    f_direction = _direction_match(component, request.tag_boosts)
    n_slots = sum(s.count for s in request.slots) or 1
    f_macro = _macro_target_fit(component, request.macro_targets, n_slots)
    # taste_match / price_fit require profile data we don't have in v1 —
    # treat as neutral 0.5 so weights still influence ordering if dialed up.
    if component.id in request.expiring_component_ids:
        f_pantry = 1.0
    elif component.id in request.pantry_component_ids:
        f_pantry = 0.5
    else:
        f_pantry = 0.0
    contributions = {
        "nutrition_fit": w.nutrition_fit * f_nutrition,
        "time_fit": w.time_fit * f_time,
        "novelty": w.novelty * f_novelty,
        "taste_match": w.taste_match * 0.5,
        "price_fit": w.price_fit * 0.5,
        "pantry_bonus": w.pantry_bonus * f_pantry,
        "direction_match": w.direction_match * f_direction,
        "macro_target_fit": w.macro_target_fit * f_macro,
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
            if component.id in request.expiring_component_ids:
                out.append("about to expire in your pantry — use it up")
            else:
                out.append("already in your pantry")
        elif name == "direction_match":
            matched = sorted(
                tag
                for tag, boost in request.tag_boosts.items()
                if boost > 0 and tag in set(component.flavor_tags) | set(component.dietary_tags)
            )
            if matched:
                out.append(f"matches your direction ({', '.join(matched[:2])})")
            else:
                out.append("matches the direction you picked")
        elif name == "macro_target_fit":
            out.append("helps hit your nutrition targets")
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
        scored = [(c, *score_component(c, request)) for c in pool if c.id not in already_picked]
        if not scored:
            break
        picked = _softmax_sample(rng, [(c, s) for c, s, _ in scored], request.temperature)
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
        tag_boosts=request.tag_boosts,
        macro_targets=request.macro_targets,
        portions=request.portions,
        available_equipment=request.available_equipment,
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
    "MacroMode",
    "MacroTarget",
    "MacroTargets",
    "RollRequest",
    "RolledBowl",
    "SlotSpec",
    "check_pairing",
    "filter_candidates",
    "reroll_slot",
    "roll",
    "score_component",
]
