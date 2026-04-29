"""User profile domain — vision §0 / §X.

Single-user app: there is exactly one profile per installation. The
``onboarded`` flag drives the first-run flow; once it's true, subsequent
visits skip onboarding by default. The profile feeds Roll defaults
(dietary mode + allergens) and is the canonical source for Settings.
"""

from __future__ import annotations

from dataclasses import dataclass

from nutriroll.domain.roll import MacroMode, MacroTarget, MacroTargets


@dataclass(frozen=True, slots=True)
class UserProfile:
    dietary_mode: str = ""
    """Empty string = "any". Other values: vegan, vegetarian, pescatarian."""

    allergens: tuple[str, ...] = ()
    """Lower-case tag names; rolled bowls exclude any component carrying one."""

    default_time_budget_min: int | None = None
    """Optional default for Roll constraints. None = no preference."""

    goal: str = ""
    """Free-text user goal e.g. "more protein", "use what I have"."""

    locale: str = "en"

    onboarded: bool = False

    roll_weights: tuple[tuple[str, float], ...] = ()
    """Per-user overrides for the roll scoring weights. Stored as a tuple of
    (name, value) pairs so the frozen dataclass can hash it. Empty = use defaults
    from :class:`~nutriroll.domain.roll.FeatureWeights`.
    Keys must be non-empty and non-negative; any key not matching a known
    `FeatureWeights` field is stored in `extra_weights` (forward-compat).
    """

    default_macro_targets: tuple[tuple[str, float, MacroMode], ...] = ()
    """Phase 11 — the user's typical per-portion macro targets (e.g. always
    >=50 g protein). Stored as a tuple of ``(macro_name, value, mode)`` triples
    so the frozen dataclass stays hashable. Empty = no defaults; the Roll page
    seeds this into its form so the user doesn't retype targets every session.
    """

    def __post_init__(self) -> None:
        if self.dietary_mode not in ("", "vegan", "vegetarian", "pescatarian"):
            raise ValueError(f"unknown dietary_mode: {self.dietary_mode!r}")
        if self.default_time_budget_min is not None and self.default_time_budget_min <= 0:
            raise ValueError("default_time_budget_min must be > 0")
        for a in self.allergens:
            if not a or not a.strip():
                raise ValueError("allergens must be non-empty strings")
        for key, value in self.roll_weights:
            if not key or not key.strip():
                raise ValueError("roll_weights keys must be non-empty strings")
            if value < 0:
                raise ValueError(f"roll_weights[{key!r}] must be >= 0")
        seen: set[str] = set()
        for name, value, mode in self.default_macro_targets:
            if not name or not name.strip():
                raise ValueError("default_macro_targets keys must be non-empty")
            if name in seen:
                raise ValueError(f"duplicate default_macro_targets entry {name!r}")
            seen.add(name)
            if value < 0:
                raise ValueError(f"default_macro_targets[{name!r}] value must be >= 0")
            if mode not in ("target", "min", "max"):
                raise ValueError(
                    f"default_macro_targets[{name!r}] mode must be target/min/max, got {mode!r}"
                )

    def macro_targets(self) -> MacroTargets | None:
        """Helper: build a :class:`MacroTargets` from the stored defaults."""
        if not self.default_macro_targets:
            return None
        mapping = {
            name: MacroTarget(value=value, mode=mode)
            for name, value, mode in self.default_macro_targets
        }
        return MacroTargets.from_mapping(mapping)
