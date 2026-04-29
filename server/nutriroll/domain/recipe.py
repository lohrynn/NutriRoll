"""Recipe builder — pure functions implementing vision §6 Cooking Recipe View.

Given the chosen components of a rolled bowl, produces a structured Recipe
made of parallel cooking blocks (one per slot category present), each with
a chosen cooking method, total time, and ordered steps.

Framework-free: no FastAPI, no SQLAlchemy. The roll algorithm produces a
``RolledBowl``; this module operates one level lower — on the chosen
``Component`` list — because scores and reasons are roll-time concepts
that have no business in a recipe.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from nutriroll.domain.component import (
    Category,
    Component,
    CookingMethod,
    CookingMethodSpec,
)

# Display order — matches vision §6: base block, vegetable block, sauce
# block, optional topping block.
_CATEGORY_ORDER: tuple[Category, ...] = (
    Category.BASE,
    Category.VEGETABLE,
    Category.SAUCE,
    Category.TOPPING,
)


@dataclass(frozen=True, slots=True)
class RecipeStep:
    """A single instruction inside a block.

    ``offset_min`` is the cumulative offset from the start of the block
    (start at offset 0). It lets the UI render a timeline ("at 0:00 add
    carrots, at 5:00 add broccoli").
    """

    text: str
    offset_min: int = 0
    duration_min: int | None = None

    def __post_init__(self) -> None:
        if self.offset_min < 0:
            raise ValueError("offset_min must be >= 0")
        if self.duration_min is not None and self.duration_min < 0:
            raise ValueError("duration_min must be >= 0")


@dataclass(frozen=True, slots=True)
class RecipeBlock:
    """One parallel cooking block.

    ``components`` is a tuple because vegetables that share a method and
    can cook with others are merged into a single block (vision §6).
    """

    category: Category
    title: str
    method: CookingMethod
    components: tuple[Component, ...]
    total_minutes: int
    can_cook_with_others: bool
    steps: tuple[RecipeStep, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.components:
            raise ValueError("components must be non-empty")
        if self.total_minutes < 0:
            raise ValueError("total_minutes must be >= 0")


@dataclass(frozen=True, slots=True)
class Recipe:
    """The whole recipe. ``blocks`` are sorted longest-first so the UI
    can render them top-to-bottom in the order the user should start
    them — vision §6 "Steps sorted such that the shortest cooking time
    is reached".
    """

    blocks: tuple[RecipeBlock, ...]
    total_minutes: int

    def __post_init__(self) -> None:
        if self.total_minutes < 0:
            raise ValueError("total_minutes must be >= 0")


class IncompatibleForcedMethodError(Exception):
    """Raised when a forced method is not supported by a chosen component."""

    def __init__(self, component: Component, method: CookingMethod) -> None:
        super().__init__(
            f"component {component.name!r} does not support cooking method {method.value}"
        )
        self.component = component
        self.method = method


# ---------------------------------------------------------------------------
# Method selection
# ---------------------------------------------------------------------------


def _spec_for(component: Component, method: CookingMethod) -> CookingMethodSpec:
    for spec in component.cooking_methods:
        if spec.method is method:
            return spec
    raise IncompatibleForcedMethodError(component, method)


def _resolve_method(
    component: Component,
    forced: Mapping[Category, CookingMethod] | None,
) -> CookingMethodSpec:
    if forced is not None and component.category in forced:
        return _spec_for(component, forced[component.category])
    return _spec_for(component, component.default_cooking_method)


# ---------------------------------------------------------------------------
# Block construction
# ---------------------------------------------------------------------------


def _block_title(category: Category, components: Sequence[Component]) -> str:
    label = {
        Category.BASE: "Base",
        Category.VEGETABLE: "Vegetables",
        Category.SAUCE: "Sauce",
        Category.TOPPING: "Topping",
    }[category]
    if len(components) == 1:
        return f"{label}: {components[0].name}"
    names = ", ".join(c.name for c in components)
    return f"{label}: {names}"


def _solo_block(component: Component, spec: CookingMethodSpec) -> RecipeBlock:
    minutes = spec.approx_minutes or 0
    portion = component.default_portion
    step_text = (
        f"{spec.method.value.replace('_', ' ').capitalize()} "
        f"{component.name.lower()} ({portion.value:g}{portion.unit.value} per portion)"
    )
    if minutes:
        step_text += f" for ~{minutes} min."
    else:
        step_text += "."
    return RecipeBlock(
        category=component.category,
        title=_block_title(component.category, (component,)),
        method=spec.method,
        components=(component,),
        total_minutes=minutes,
        can_cook_with_others=spec.can_cook_with_others,
        steps=(RecipeStep(text=step_text, offset_min=0, duration_min=minutes or None),),
    )


def _grouped_vegetable_block(
    pairs: Sequence[tuple[Component, CookingMethodSpec]],
) -> RecipeBlock:
    """Group vegetables that share a method and all can_cook_with_others.

    The longest-cooking vegetable starts first; the rest are added at an
    offset such that they all finish together.
    """
    # Sort longest-first so the slowest one anchors the block.
    sorted_pairs = sorted(pairs, key=lambda p: p[1].approx_minutes or 0, reverse=True)
    longest = sorted_pairs[0][1].approx_minutes or 0
    method = sorted_pairs[0][1].method
    components = tuple(p[0] for p in sorted_pairs)
    steps: list[RecipeStep] = []
    for component, spec in sorted_pairs:
        minutes = spec.approx_minutes or 0
        offset = longest - minutes
        portion = component.default_portion
        verb = method.value.replace("_", " ").capitalize()
        text = (
            f"At {offset:d}:00 add {component.name.lower()} "
            f"({portion.value:g}{portion.unit.value}) — "
            f"{verb.lower()} for ~{minutes} min."
        )
        steps.append(RecipeStep(text=text, offset_min=offset, duration_min=minutes or None))
    return RecipeBlock(
        category=Category.VEGETABLE,
        title=_block_title(Category.VEGETABLE, components),
        method=method,
        components=components,
        total_minutes=longest,
        can_cook_with_others=True,
        steps=tuple(steps),
    )


def _build_category_blocks(
    category: Category,
    components: Sequence[Component],
    forced: Mapping[Category, CookingMethod] | None,
) -> list[RecipeBlock]:
    """Build the blocks for one category. Vegetables may be merged."""
    if not components:
        return []
    pairs = [(c, _resolve_method(c, forced)) for c in components]

    # Only vegetables get grouped, and only when all share the same method
    # and all can cook with others.
    if (
        category is Category.VEGETABLE
        and len(pairs) > 1
        and all(spec.method is pairs[0][1].method for _, spec in pairs)
        and all(spec.can_cook_with_others for _, spec in pairs)
    ):
        return [_grouped_vegetable_block(pairs)]

    return [_solo_block(component, spec) for component, spec in pairs]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_recipe(
    components: Sequence[Component],
    forced_methods: Mapping[Category, CookingMethod] | None = None,
) -> Recipe:
    """Build a Recipe from the chosen components of a rolled bowl.

    Parameters
    ----------
    components:
        The chosen components, in any order. Typically the
        ``c.component for c in bowl.slots`` of a ``RolledBowl``.
    forced_methods:
        Optional per-category cooking-method overrides. Raises
        ``IncompatibleForcedMethodError`` if a forced method is not
        listed in the component's ``cooking_methods``.
    """
    if not components:
        raise ValueError("components must be non-empty")

    by_category: dict[Category, list[Component]] = {}
    for c in components:
        by_category.setdefault(c.category, []).append(c)

    blocks: list[RecipeBlock] = []
    for category in _CATEGORY_ORDER:
        blocks.extend(
            _build_category_blocks(category, by_category.get(category, []), forced_methods)
        )

    # Sort longest-first so the user starts the slowest block first and
    # everything finishes together (vision §6).
    blocks.sort(key=lambda b: b.total_minutes, reverse=True)

    total = max((b.total_minutes for b in blocks), default=0)
    return Recipe(blocks=tuple(blocks), total_minutes=total)


__all__ = [
    "IncompatibleForcedMethodError",
    "Recipe",
    "RecipeBlock",
    "RecipeStep",
    "build_recipe",
]
