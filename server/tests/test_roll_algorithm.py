"""Property and example tests for the roll algorithm (vision §Logic 2).

Hypothesis covers Step A invariants and Step D pairing rules; concrete
tests cover the orchestrator and reroll semantics.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nutriroll.domain.component import (
    ALLOWED_METHODS,
    Category,
    Component,
    CookingMethod,
    CookingMethodSpec,
    Macros,
    Portion,
    PortionUnit,
)
from nutriroll.domain.roll import (
    EmptyCandidatePoolError,
    FeatureWeights,
    RollRequest,
    SlotSpec,
    check_pairing,
    filter_candidates,
    reroll_slot,
    roll,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies for synthesizing components
# ---------------------------------------------------------------------------


def _component_of(
    category: Category,
    *,
    name: str,
    blacklisted: bool = False,
    dietary_tags: tuple[str, ...] = ("vegan", "vegetarian", "gluten-free"),
    allergens: tuple[str, ...] = (),
    flavor_tags: tuple[str, ...] = ("mild",),
    minutes: int = 10,
    component_id: UUID | None = None,
) -> Component:
    method = next(iter(ALLOWED_METHODS[category]))
    return Component(
        id=component_id or uuid4(),
        category=category,
        name=name,
        macros_per_100g=Macros(kcal=100, carbs_g=20, protein_g=4, fat_g=2, fiber_g=2),
        default_portion=Portion(value=80, unit=PortionUnit.GRAM),
        default_cooking_method=method,
        cooking_methods=(CookingMethodSpec(method=method, approx_minutes=minutes),),
        flavor_tags=flavor_tags,
        dietary_tags=dietary_tags,
        allergens=allergens,
        blacklisted=blacklisted,
    )


@st.composite
def _components(draw: st.DrawFn) -> Component:
    category = draw(st.sampled_from(list(Category)))
    minutes = draw(st.integers(min_value=0, max_value=120))
    blacklisted = draw(st.booleans())
    has_dairy = draw(st.booleans())
    flavor = draw(st.sampled_from([("mild",), ("spicy",), ("bold",), ("crunchy",)]))
    return _component_of(
        category,
        name=draw(st.text(min_size=1, max_size=20).filter(lambda s: s.strip())),
        blacklisted=blacklisted,
        dietary_tags=("vegan", "vegetarian"),
        allergens=("dairy",) if has_dairy else (),
        flavor_tags=flavor,
        minutes=minutes,
    )


# ---------------------------------------------------------------------------
# Step A — hard filter invariants
# ---------------------------------------------------------------------------


@given(st.lists(_components(), min_size=1, max_size=15))
@settings(max_examples=50, deadline=None)
def test_blacklisted_components_never_pass_filter(comps: list[Component]) -> None:
    request = RollRequest(slots=(SlotSpec(category=Category.BASE),))
    survivors = filter_candidates(comps, request, Category.BASE)
    assert all(not c.blacklisted for c in survivors)


@given(st.lists(_components(), min_size=1, max_size=15))
@settings(max_examples=50, deadline=None)
def test_allergen_excluded_components_never_pass(comps: list[Component]) -> None:
    request = RollRequest(
        slots=(SlotSpec(category=Category.BASE),),
        allergens_excluded=frozenset({"dairy"}),
    )
    survivors = filter_candidates(comps, request, Category.BASE)
    assert all("dairy" not in c.allergens for c in survivors)


@given(st.lists(_components(), min_size=1, max_size=15), st.integers(min_value=0, max_value=120))
@settings(max_examples=50, deadline=None)
def test_time_budget_eliminates_slow_components(comps: list[Component], budget: int) -> None:
    request = RollRequest(slots=(SlotSpec(category=Category.BASE),), time_budget_min=budget)
    survivors = filter_candidates(comps, request, Category.BASE)
    for c in survivors:
        fastest = min(
            (s.approx_minutes or 0 for s in c.cooking_methods),
            default=0,
        )
        assert fastest <= budget


@given(st.lists(_components(), min_size=1, max_size=15))
@settings(max_examples=50, deadline=None)
def test_filtered_pool_only_contains_requested_category(
    comps: list[Component],
) -> None:
    request = RollRequest(slots=(SlotSpec(category=Category.SAUCE),))
    survivors = filter_candidates(comps, request, Category.SAUCE)
    assert all(c.category is Category.SAUCE for c in survivors)


# ---------------------------------------------------------------------------
# Step D — pairing rules
# ---------------------------------------------------------------------------


def test_check_pairing_flags_too_many_bold() -> None:
    bowl_slots = [
        _component_of(Category.BASE, name="b", flavor_tags=("spicy",)),
        _component_of(Category.SAUCE, name="s", flavor_tags=("bold",)),
    ]
    from nutriroll.domain.roll import ChosenComponent

    chosen = [ChosenComponent(component=c, score=1.0, reasons=()) for c in bowl_slots]
    issues = check_pairing(chosen)
    assert any("bold" in i for i in issues)


def test_check_pairing_flags_topping_without_crunch() -> None:
    from nutriroll.domain.roll import ChosenComponent

    bowl = [
        ChosenComponent(
            component=_component_of(Category.TOPPING, name="t", flavor_tags=("creamy",)),
            score=1.0,
            reasons=(),
        )
    ]
    issues = check_pairing(bowl)
    assert any("crunchy" in i for i in issues)


def test_check_pairing_passes_clean_bowl() -> None:
    from nutriroll.domain.roll import ChosenComponent

    bowl = [
        ChosenComponent(
            component=_component_of(Category.BASE, name="b", flavor_tags=("mild",)),
            score=1.0,
            reasons=(),
        ),
        ChosenComponent(
            component=_component_of(Category.TOPPING, name="t", flavor_tags=("crunchy",)),
            score=1.0,
            reasons=(),
        ),
    ]
    assert check_pairing(bowl) == []


# ---------------------------------------------------------------------------
# Step C / E / F — orchestrator and reroll
# ---------------------------------------------------------------------------


def _sample_pool() -> list[Component]:
    return [
        _component_of(Category.BASE, name="Brown rice", minutes=25),
        _component_of(Category.BASE, name="Quinoa", minutes=15),
        _component_of(Category.VEGETABLE, name="Broccoli", minutes=5),
        _component_of(Category.VEGETABLE, name="Spinach", minutes=3),
        _component_of(Category.SAUCE, name="Tahini", minutes=0),
        _component_of(Category.SAUCE, name="Salsa Verde", minutes=2),
        _component_of(
            Category.TOPPING,
            name="Sesame Seeds",
            flavor_tags=("crunchy",),
            minutes=3,
        ),
    ]


def test_roll_returns_one_per_slot_with_explanations() -> None:
    request = RollRequest(
        slots=(
            SlotSpec(category=Category.BASE),
            SlotSpec(category=Category.VEGETABLE),
            SlotSpec(category=Category.SAUCE),
            SlotSpec(category=Category.TOPPING),
        ),
        time_budget_min=30,
        seed=42,
    )
    bowl = roll(_sample_pool(), request)
    assert len(bowl.slots) == 4
    cats = [s.component.category for s in bowl.slots]
    assert cats == [
        Category.BASE,
        Category.VEGETABLE,
        Category.SAUCE,
        Category.TOPPING,
    ]
    for s in bowl.slots:
        assert s.reasons  # at least one reason per chosen component


def test_roll_is_deterministic_with_seed() -> None:
    request = RollRequest(
        slots=(SlotSpec(category=Category.BASE), SlotSpec(category=Category.VEGETABLE)),
        seed=7,
    )
    a = roll(_sample_pool(), request)
    b = roll(_sample_pool(), request)
    assert [s.component.name for s in a.slots] == [s.component.name for s in b.slots]


def test_roll_raises_when_pool_empty() -> None:
    request = RollRequest(
        slots=(SlotSpec(category=Category.BASE),),
        allergens_excluded=frozenset({"gluten", "dairy", "soy", "nuts"}),
        # Force no candidate by demanding an impossible cooking method.
        forced_methods={Category.BASE: CookingMethod.BLEND_HOT},
    )
    with pytest.raises(EmptyCandidatePoolError):
        roll(_sample_pool(), request)


def test_reroll_slot_changes_only_that_slot() -> None:
    request = RollRequest(
        slots=(
            SlotSpec(category=Category.BASE),
            SlotSpec(category=Category.VEGETABLE),
        ),
        seed=1,
    )
    bowl = roll(_sample_pool(), request)
    rerolled = reroll_slot(_sample_pool(), request, bowl, 0)
    assert rerolled.slots[1].component.id == bowl.slots[1].component.id
    assert rerolled.slots[0].component.id != bowl.slots[0].component.id


def test_score_uses_weights() -> None:
    from nutriroll.domain.roll import score_component

    c = _component_of(Category.BASE, name="x", minutes=5)
    high_novelty = RollRequest(
        slots=(SlotSpec(category=Category.BASE),),
        weights=FeatureWeights(
            taste_match=0,
            novelty=1.0,
            price_fit=0,
            nutrition_fit=0,
            time_fit=0,
            pantry_bonus=0,
        ),
    )
    score, contrib = score_component(c, high_novelty)
    assert contrib["novelty"] == 1.0
    assert score == 1.0


def test_extra_weights_round_trip_and_validation() -> None:
    """M6: forward-compat extra weights validate but do not affect scoring yet."""
    from nutriroll.domain.roll import score_component

    c = _component_of(Category.BASE, name="x", minutes=5)
    req = RollRequest(
        slots=(SlotSpec(category=Category.BASE),),
        weights=FeatureWeights(
            taste_match=0,
            novelty=1.0,
            price_fit=0,
            nutrition_fit=0,
            time_fit=0,
            pantry_bonus=0,
            extra_weights={"seasonal_bonus": 0.5, "eco_score": 0.25},
        ),
    )
    score, contrib = score_component(c, req)
    # Extras are accepted but not yet scored — algorithm result is unchanged.
    assert "seasonal_bonus" not in contrib
    assert score == 1.0

    with pytest.raises(ValueError, match="must be >= 0"):
        FeatureWeights(extra_weights={"foo": -1.0})
    with pytest.raises(ValueError, match="clashes with a well-known field"):
        FeatureWeights(extra_weights={"novelty": 0.1})
    with pytest.raises(ValueError, match="non-empty"):
        FeatureWeights(extra_weights={" ": 0.1})


# ---------------------------------------------------------------------------
# Phase 11 — per-meal macro targets
# ---------------------------------------------------------------------------


def _macro_pool() -> list[Component]:
    """Two BASE components with a clear protein gap. Used to assert that
    targets steer selection toward the higher-protein candidate.
    """
    high = _component_of(Category.BASE, name="HighProtein", minutes=5)
    low = _component_of(Category.BASE, name="LowProtein", minutes=5)
    # Mutate macros via dataclass replace pattern (frozen).
    high = Component(
        id=high.id,
        category=high.category,
        name=high.name,
        macros_per_100g=Macros(kcal=200, carbs_g=5, protein_g=40, fat_g=10, fiber_g=0),
        default_portion=high.default_portion,
        default_cooking_method=high.default_cooking_method,
        cooking_methods=high.cooking_methods,
        flavor_tags=high.flavor_tags,
        dietary_tags=high.dietary_tags,
        allergens=high.allergens,
        blacklisted=high.blacklisted,
    )
    low = Component(
        id=low.id,
        category=low.category,
        name=low.name,
        macros_per_100g=Macros(kcal=120, carbs_g=20, protein_g=5, fat_g=3, fiber_g=2),
        default_portion=low.default_portion,
        default_cooking_method=low.default_cooking_method,
        cooking_methods=low.cooking_methods,
        flavor_tags=low.flavor_tags,
        dietary_tags=low.dietary_tags,
        allergens=low.allergens,
        blacklisted=low.blacklisted,
    )
    return [high, low]


def test_macro_target_min_prefers_higher_protein_component() -> None:
    """A min protein target should rank the high-protein component higher."""
    from nutriroll.domain.roll import MacroTarget, MacroTargets, score_component

    pool = _macro_pool()
    high, low = pool[0], pool[1]
    req = RollRequest(
        slots=(SlotSpec(category=Category.BASE),),
        macro_targets=MacroTargets(protein_g=MacroTarget(value=50, mode="min")),
    )
    high_score, _ = score_component(high, req)
    low_score, _ = score_component(low, req)
    assert high_score > low_score


def test_macro_target_max_penalises_high_fat_component() -> None:
    from nutriroll.domain.roll import MacroTarget, MacroTargets, score_component

    pool = _macro_pool()
    high, low = pool[0], pool[1]  # high has fat=10, low has fat=3
    req = RollRequest(
        slots=(SlotSpec(category=Category.BASE),),
        macro_targets=MacroTargets(fat_g=MacroTarget(value=5, mode="max")),
    )
    high_score, high_contrib = score_component(high, req)
    low_score, low_contrib = score_component(low, req)
    # Low-fat component must score the macro feature at least as well as high-fat.
    assert low_contrib["macro_target_fit"] >= high_contrib["macro_target_fit"]
    assert low_score >= high_score


def test_no_macro_targets_means_neutral_contribution() -> None:
    """Regression guard: omitting macro_targets keeps existing behaviour."""
    from nutriroll.domain.roll import score_component

    c = _macro_pool()[0]
    req = RollRequest(slots=(SlotSpec(category=Category.BASE),))
    _, contrib = score_component(c, req)
    assert contrib["macro_target_fit"] == 0.0


def test_macro_target_validation() -> None:
    from nutriroll.domain.roll import MacroTarget, MacroTargets

    with pytest.raises(ValueError, match="value must be >= 0"):
        MacroTarget(value=-1)
    with pytest.raises(ValueError, match=r"invalid MacroTarget\.mode"):
        MacroTarget(value=10, mode="exact")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="clashes with a well-known field"):
        MacroTargets(extra=(("kcal", MacroTarget(value=1)),))


# ---------------------------------------------------------------------------
# Phase 12 — portions metadata
# ---------------------------------------------------------------------------


def test_portions_default_and_validation() -> None:
    req = RollRequest(slots=(SlotSpec(category=Category.BASE),))
    assert req.portions == 1
    with pytest.raises(ValueError, match=r"portions must be in \[1, 14\]"):
        RollRequest(slots=(SlotSpec(category=Category.BASE),), portions=0)
    with pytest.raises(ValueError, match=r"portions must be in \[1, 14\]"):
        RollRequest(slots=(SlotSpec(category=Category.BASE),), portions=15)


def test_portions_does_not_change_rolled_components() -> None:
    """Phase 12 guarantee: portions is metadata; roll outcome is unchanged."""
    base_req = RollRequest(
        slots=(SlotSpec(category=Category.BASE), SlotSpec(category=Category.VEGETABLE)),
        seed=99,
    )
    prep_req = RollRequest(
        slots=base_req.slots,
        seed=99,
        portions=4,
    )
    a = roll(_sample_pool(), base_req)
    b = roll(_sample_pool(), prep_req)
    assert [s.component.name for s in a.slots] == [s.component.name for s in b.slots]
