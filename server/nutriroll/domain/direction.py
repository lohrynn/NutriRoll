"""Direction → tag-boost translation (vision §1).

Direction chips on the Roll page (Cuisine, Mood, Flavor axis) are soft
influences. Each selection contributes a small additive boost (positive
or negative) to one or more flavor tags. The aggregated boost map is
passed verbatim into `RollRequest.tag_boosts`.

Pure data + a single pure function — framework-free so it can be reused
by future planning code (Roll-a-Week, Settings presets).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

# The boost magnitude for a single picked chip. Capped in `RollRequest`
# at ±1 in aggregate, so combining many chips degrades gracefully.
_CHIP_BOOST: float = 0.35
_AXIS_BOOST: float = 0.5


# Cuisine chip → tag boosts.
CUISINE_BOOSTS: dict[str, dict[str, float]] = {
    "asian": {"umami": _CHIP_BOOST, "savory": _CHIP_BOOST, "spicy": _CHIP_BOOST / 2},
    "mediterranean": {"savory": _CHIP_BOOST, "tangy": _CHIP_BOOST / 2, "herbaceous": _CHIP_BOOST},
    "mexican": {"spicy": _CHIP_BOOST, "smoky": _CHIP_BOOST, "tangy": _CHIP_BOOST / 2},
    "middle_eastern": {"savory": _CHIP_BOOST, "nutty": _CHIP_BOOST, "tangy": _CHIP_BOOST / 2},
    "american": {"savory": _CHIP_BOOST, "smoky": _CHIP_BOOST / 2, "sweet": _CHIP_BOOST / 4},
    "fusion": {"umami": _CHIP_BOOST / 2, "bold": _CHIP_BOOST / 2},
}

# Mood chip → tag boosts. Some moods bias toward time/novelty rather than
# flavor — those are intentionally small (or empty) here because the
# main scoring weights already cover them.
MOOD_BOOSTS: dict[str, dict[str, float]] = {
    "quick_weekday": {},  # handled by time_budget_min, not flavor
    "light_fresh": {
        "tangy": _CHIP_BOOST,
        "herbaceous": _CHIP_BOOST / 2,
        "crunchy": _CHIP_BOOST / 4,
    },
    "comfort": {"savory": _CHIP_BOOST, "creamy": _CHIP_BOOST, "nutty": _CHIP_BOOST / 4},
    "impress": {"bold": _CHIP_BOOST, "umami": _CHIP_BOOST / 2, "smoky": _CHIP_BOOST / 4},
    "use_what_i_have": {},  # handled later by pantry_bonus weight
    "surprise_me": {},  # raises temperature instead — see translate()
}


@dataclass(frozen=True, slots=True)
class FlavorAxes:
    """Two-ended sliders, each in [-1, 1].

    bold_to_mild: -1 = very bold, +1 = very mild
    heavy_to_light: -1 = very heavy, +1 = very light
    """

    bold_to_mild: float = 0.0
    heavy_to_light: float = 0.0

    def __post_init__(self) -> None:
        for label in ("bold_to_mild", "heavy_to_light"):
            v: float = getattr(self, label)
            if v < -1.0 or v > 1.0:
                raise ValueError(f"{label} must be in [-1, 1], got {v}")


@dataclass(frozen=True, slots=True)
class Direction:
    cuisines: tuple[str, ...] = field(default_factory=tuple)
    moods: tuple[str, ...] = field(default_factory=tuple)
    axes: FlavorAxes = field(default_factory=FlavorAxes)

    def __post_init__(self) -> None:
        for c in self.cuisines:
            if c not in CUISINE_BOOSTS:
                raise ValueError(f"unknown cuisine: {c}")
        for m in self.moods:
            if m not in MOOD_BOOSTS:
                raise ValueError(f"unknown mood: {m}")


def translate(direction: Direction) -> dict[str, float]:
    """Reduce a Direction selection into a flat tag → boost map.

    Boosts for the same tag accumulate, so picking Asian + Mexican will
    stack their `spicy` contribution. The roll algorithm clips the per-
    component sum to [-1, 1] anyway, so the effect saturates gracefully.
    """
    out: dict[str, float] = {}
    sources: Iterable[Mapping[str, float]] = (
        *(CUISINE_BOOSTS[c] for c in direction.cuisines),
        *(MOOD_BOOSTS[m] for m in direction.moods),
    )
    for src in sources:
        for tag, boost in src.items():
            out[tag] = out.get(tag, 0.0) + boost

    # Axes: bold_to_mild < 0 boosts bold/spicy/smoky and penalises mild;
    # heavy_to_light < 0 boosts creamy/savory and penalises tangy/crunchy.
    bold = -direction.axes.bold_to_mild  # so negative slider → positive boost
    if bold:
        for tag in ("bold", "spicy", "smoky"):
            out[tag] = out.get(tag, 0.0) + bold * _AXIS_BOOST
        out["mild"] = out.get("mild", 0.0) - bold * _AXIS_BOOST

    heavy = -direction.axes.heavy_to_light
    if heavy:
        for tag in ("creamy", "savory"):
            out[tag] = out.get(tag, 0.0) + heavy * _AXIS_BOOST
        for tag in ("tangy", "crunchy", "herbaceous"):
            out[tag] = out.get(tag, 0.0) - heavy * _AXIS_BOOST

    # Drop near-zero entries to keep payloads tidy.
    return {tag: round(v, 4) for tag, v in out.items() if abs(v) > 1e-3}


__all__ = [
    "CUISINE_BOOSTS",
    "MOOD_BOOSTS",
    "Direction",
    "FlavorAxes",
    "translate",
]
