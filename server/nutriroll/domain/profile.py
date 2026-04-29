"""User profile domain — vision §0 / §X.

Single-user app: there is exactly one profile per installation. The
``onboarded`` flag drives the first-run flow; once it's true, subsequent
visits skip onboarding by default. The profile feeds Roll defaults
(dietary mode + allergens) and is the canonical source for Settings.
"""

from __future__ import annotations

from dataclasses import dataclass


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

    def __post_init__(self) -> None:
        if self.dietary_mode not in ("", "vegan", "vegetarian", "pescatarian"):
            raise ValueError(f"unknown dietary_mode: {self.dietary_mode!r}")
        if self.default_time_budget_min is not None and self.default_time_budget_min <= 0:
            raise ValueError("default_time_budget_min must be > 0")
        for a in self.allergens:
            if not a or not a.strip():
                raise ValueError("allergens must be non-empty strings")
