from __future__ import annotations

from typing import override

import pytest

from nutriroll.domain.recipe import RecipeStep
from nutriroll.domain.recipe_step_polish import RecipeStepPolish


def _steps() -> list[RecipeStep]:
    return [
        RecipeStep(text="Cut the vegetables into small pieces.", offset_min=0, duration_min=2),
        RecipeStep(text="Cook the rice for about 20 minutes.", offset_min=0, duration_min=20),
        RecipeStep(text="Mix the sauce and drizzle it over the bowl.", offset_min=18),
    ]


class _StubPolisher(RecipeStepPolish):
    def __init__(self, responses: list[list[str] | None]) -> None:
        super().__init__(
            api_key="test-key",
            model="test-model",
            base_url="https://example.test/v1",
        )
        self._responses = responses
        self.calls = 0

    @override
    async def _request_polished_texts(
        self,
        directions: list[RecipeStep],
        tone: str,
    ) -> list[str] | None:
        self.calls += 1
        assert tone in {"concise", "enthusiastic", "calm", "professional"}
        if not self._responses:
            raise AssertionError("unexpected extra LLM call")
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_recipe_step_polish_happy_path() -> None:
    RecipeStepPolish.clear_cache()
    steps = _steps()
    polisher = _StubPolisher(
        [
            [
                "Dice the vegetables into small pieces.",
                "Cook the rice for about 20 minutes.",
                "Mix the sauce and drizzle it over the bowl.",
            ]
        ]
    )

    polished = await polisher.polish_steps(steps, tone="concise")

    assert len(polished) == 3
    assert polished[0].text == "Dice the vegetables into small pieces."
    assert polished[0].offset_min == steps[0].offset_min
    assert polished[0].duration_min == steps[0].duration_min
    assert polished[1].text == steps[1].text
    assert polisher.last_applied is True


@pytest.mark.asyncio
async def test_recipe_step_polish_invalid_response_falls_back_to_raw_steps() -> None:
    RecipeStepPolish.clear_cache()
    steps = _steps()
    polisher = _StubPolisher([["Only one step"]])

    polished = await polisher.polish_steps(steps, tone="enthusiastic")

    assert [step.text for step in polished] == [step.text for step in steps]
    assert polisher.last_applied is False


@pytest.mark.asyncio
async def test_recipe_step_polish_cache_hit_skips_second_llm_call() -> None:
    RecipeStepPolish.clear_cache()
    steps = _steps()
    polisher = _StubPolisher(
        [
            [
                "Dice the vegetables into small pieces.",
                "Cook the rice for about 20 minutes.",
                "Whisk the sauce, then drizzle it over the bowl.",
            ]
        ]
    )

    first = await polisher.polish_steps(steps, tone="concise")
    second = await polisher.polish_steps(steps, tone="concise")

    assert polisher.calls == 1
    assert [step.text for step in first] == [step.text for step in second]


@pytest.mark.asyncio
async def test_recipe_step_polish_empty_list_returns_empty_list() -> None:
    RecipeStepPolish.clear_cache()
    polisher = _StubPolisher([])

    polished = await polisher.polish_steps([], tone="calm")

    assert polished == []
    assert polisher.calls == 0
