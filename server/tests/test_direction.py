"""Tests for `nutriroll.domain.direction`."""

from __future__ import annotations

import pytest

from nutriroll.domain.direction import (
    CUISINE_BOOSTS,
    Direction,
    FlavorAxes,
    translate,
)


def test_empty_direction_translates_to_empty_dict() -> None:
    assert translate(Direction()) == {}


def test_single_cuisine_propagates_its_boosts() -> None:
    out = translate(Direction(cuisines=("asian",)))
    assert set(out) == set(CUISINE_BOOSTS["asian"])
    for tag, boost in CUISINE_BOOSTS["asian"].items():
        assert out[tag] == pytest.approx(boost)  # pyright: ignore[reportUnknownMemberType]


def test_stacking_two_cuisines_sums_overlapping_tags() -> None:
    out = translate(Direction(cuisines=("asian", "mexican")))
    # both boost spicy
    assert out["spicy"] > CUISINE_BOOSTS["asian"]["spicy"]


def test_axis_bold_pulls_bold_tags_up_and_mild_down() -> None:
    out = translate(Direction(axes=FlavorAxes(bold_to_mild=-1.0)))
    assert out["bold"] > 0
    assert out["spicy"] > 0
    assert out["mild"] < 0


def test_axis_light_pulls_creamy_down_and_tangy_up() -> None:
    out = translate(Direction(axes=FlavorAxes(heavy_to_light=1.0)))
    assert out["creamy"] < 0
    assert out["tangy"] > 0


def test_unknown_cuisine_rejected() -> None:
    with pytest.raises(ValueError, match="unknown cuisine"):
        Direction(cuisines=("klingon",))


def test_axis_out_of_range_rejected() -> None:
    with pytest.raises(ValueError, match="bold_to_mild"):
        FlavorAxes(bold_to_mild=2.0)
