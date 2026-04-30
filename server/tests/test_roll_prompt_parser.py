from __future__ import annotations

from types import SimpleNamespace

import pytest

from nutriroll.domain.roll_prompt_parser import (
    PromptParseError,
    RollPromptParser,
)


def _stub_llm(raw_output: str):
    return lambda self, prompt, profile: SimpleNamespace(raw_output=raw_output)


def test_parse_prompt_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        RollPromptParser,
        "_request_constraints_json",
        _stub_llm(
            """
            {
              "hard_exclusions": [],
              "cuisine_weights": {"asian": 0.8},
              "flavor_boosts": {"spicy": 0.9, "vegan": 0.5},
              "macro_bounds": {"min_protein": 25, "max_kcal": null, "min_fiber": null, "max_sodium": null},
              "cooking_method_constraint": null,
              "time_budget_minutes": null,
              "pantry_only": false
            }
            """
        ),
    )
    parser = RollPromptParser(api_key="test-key", base_url="https://example.com")

    constraints = parser.parse_prompt("spicy vegan bowl", profile=None)

    assert constraints.cuisine_weights == {"asian": 0.8}
    assert constraints.flavor_boosts["spicy"] == pytest.approx(0.9)
    assert constraints.flavor_boosts["vegan"] == pytest.approx(0.5)
    assert constraints.macro_bounds is not None
    assert constraints.macro_bounds.min_protein == pytest.approx(25)


def test_parse_prompt_empty_prompt_returns_no_constraints() -> None:
    parser = RollPromptParser(api_key="", base_url="https://example.com")

    constraints = parser.parse_prompt("   ", profile=None)

    assert constraints.is_empty()


def test_parse_prompt_malformed_llm_response_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        RollPromptParser,
        "_request_constraints_json",
        _stub_llm('{"unknown_key": true}'),
    )
    parser = RollPromptParser(api_key="test-key", base_url="https://example.com")

    with pytest.raises(PromptParseError, match="couldn't safely apply|couldn't read"):
        parser.parse_prompt("something spicy under 500 kcal", profile=None)
