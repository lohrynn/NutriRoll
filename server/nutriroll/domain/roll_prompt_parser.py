"""Natural-language prompt → structured roll constraints."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from nutriroll.config import get_settings
from nutriroll.domain.component import CookingMethod
from nutriroll.domain.direction import CUISINE_BOOSTS
from nutriroll.domain.profile import UserProfile


class PromptParseError(RuntimeError):
    """Raised when a natural-language roll prompt cannot be converted safely."""


class _MacroBoundsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_protein: float | None = Field(default=None, ge=0)
    max_kcal: float | None = Field(default=None, ge=0)
    min_fiber: float | None = Field(default=None, ge=0)
    max_sodium: float | None = Field(default=None, ge=0)


class _PromptPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hard_exclusions: list[str] = Field(default_factory=list, max_length=32)
    cuisine_weights: dict[str, float] = Field(default_factory=dict)
    flavor_boosts: dict[str, float] = Field(default_factory=dict)
    macro_bounds: _MacroBoundsPayload | None = None
    cooking_method_constraint: CookingMethod | None = None
    time_budget_minutes: int | None = Field(default=None, ge=0, le=600)
    pantry_only: bool = False

    @field_validator("hard_exclusions")
    @classmethod
    def _validate_hard_exclusions(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            normalized = item.strip()
            if not normalized:
                raise ValueError("hard exclusions must be non-empty strings")
            cleaned.append(normalized)
        return cleaned

    @field_validator("cuisine_weights")
    @classmethod
    def _validate_cuisine_weights(cls, value: dict[str, float]) -> dict[str, float]:
        cleaned: dict[str, float] = {}
        for cuisine, weight in value.items():
            if cuisine not in CUISINE_BOOSTS:
                raise ValueError(f"unknown cuisine {cuisine!r}")
            numeric = float(weight)
            if numeric < 0 or numeric > 1:
                raise ValueError(f"cuisine weight for {cuisine!r} must be in [0, 1]")
            cleaned[cuisine] = numeric
        return cleaned

    @field_validator("flavor_boosts")
    @classmethod
    def _validate_flavor_boosts(cls, value: dict[str, float]) -> dict[str, float]:
        cleaned: dict[str, float] = {}
        for tag, boost in value.items():
            normalized = tag.strip()
            if not normalized:
                raise ValueError("flavor boost keys must be non-empty strings")
            numeric = float(boost)
            if numeric < -1 or numeric > 1:
                raise ValueError(f"flavor boost for {normalized!r} must be in [-1, 1]")
            cleaned[normalized] = numeric
        return cleaned


@dataclass(frozen=True, slots=True)
class MacroBounds:
    min_protein: float | None = None
    max_kcal: float | None = None
    min_fiber: float | None = None
    max_sodium: float | None = None

    def is_empty(self) -> bool:
        return (
            self.min_protein is None
            and self.max_kcal is None
            and self.min_fiber is None
            and self.max_sodium is None
        )


@dataclass(frozen=True, slots=True)
class RollConstraints:
    hard_exclusion_ids: frozenset[UUID] = field(default_factory=frozenset[UUID])
    allergen_exclusions: frozenset[str] = field(default_factory=frozenset[str])
    cuisine_weights: dict[str, float] = field(default_factory=dict[str, float])
    flavor_boosts: dict[str, float] = field(default_factory=dict[str, float])
    macro_bounds: MacroBounds | None = None
    cooking_method_constraint: CookingMethod | None = None
    time_budget_minutes: int | None = None
    pantry_only: bool = False

    def is_empty(self) -> bool:
        return (
            not self.hard_exclusion_ids
            and not self.allergen_exclusions
            and not self.cuisine_weights
            and not self.flavor_boosts
            and (self.macro_bounds is None or self.macro_bounds.is_empty())
            and self.cooking_method_constraint is None
            and self.time_budget_minutes is None
            and not self.pantry_only
        )


@dataclass(frozen=True, slots=True)
class _LLMResponse:
    raw_output: str


class RollPromptParser:
    """Translate a natural-language prompt into structured roll constraints."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.llm_model
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def parse_prompt(self, prompt: str, profile: UserProfile | None = None) -> RollConstraints:
        normalized_prompt = prompt.strip()
        if normalized_prompt == "":
            return RollConstraints()
        if not self.api_key.strip():
            raise PromptParseError("Prompt-based rolling is not configured right now.")

        llm_response = self._request_constraints_json(normalized_prompt, profile)
        try:
            payload = self._extract_json_payload(llm_response.raw_output)
            parsed = _PromptPayload.model_validate(payload)
        except PromptParseError:
            raise
        except ValidationError as exc:
            raise PromptParseError(
                "I couldn't safely apply that description. Try a simpler prompt like "
                '"spicy vegan under 600 kcal".'
            ) from exc

        macro_bounds = None
        if parsed.macro_bounds is not None:
            macro_bounds = MacroBounds(
                min_protein=parsed.macro_bounds.min_protein,
                max_kcal=parsed.macro_bounds.max_kcal,
                min_fiber=parsed.macro_bounds.min_fiber,
                max_sodium=parsed.macro_bounds.max_sodium,
            )
            if macro_bounds.is_empty():
                macro_bounds = None

        hard_exclusion_ids: set[UUID] = set()
        allergen_exclusions: set[str] = set()
        for item in parsed.hard_exclusions:
            try:
                hard_exclusion_ids.add(UUID(item))
            except ValueError:
                allergen_exclusions.add(item.lower())

        constraints = RollConstraints(
            hard_exclusion_ids=frozenset(hard_exclusion_ids),
            allergen_exclusions=frozenset(allergen_exclusions),
            cuisine_weights=dict(parsed.cuisine_weights),
            flavor_boosts=dict(parsed.flavor_boosts),
            macro_bounds=macro_bounds,
            cooking_method_constraint=parsed.cooking_method_constraint,
            time_budget_minutes=parsed.time_budget_minutes,
            pantry_only=parsed.pantry_only,
        )
        if constraints.is_empty():
            raise PromptParseError(
                "I couldn't find any usable roll constraints in that description. "
                "Try naming a flavor, cuisine, time limit, nutrition target, or exclusion."
            )
        return constraints

    def _request_constraints_json(
        self, prompt: str, profile: UserProfile | None
    ) -> _LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._user_prompt(prompt, profile)},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PromptParseError(self._http_error_message(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise PromptParseError(
                "The AI parser is unavailable right now. Please try again in a moment."
            ) from exc

        data = response.json()
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise PromptParseError("The AI parser returned an empty response.")
        first_choice = choices[0]
        message = first_choice.get("message") if isinstance(first_choice, dict) else None
        refusal = message.get("refusal") if isinstance(message, dict) else None
        if refusal:
            raise PromptParseError(
                "I couldn't turn that description into roll constraints. Try being more specific."
            )
        content = message.get("content") if isinstance(message, dict) else None
        raw_output = self._coerce_message_content(content)
        if raw_output.strip() == "":
            raise PromptParseError("The AI parser returned an empty response.")
        return _LLMResponse(raw_output=raw_output)

    @staticmethod
    def _coerce_message_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""

    @staticmethod
    def _extract_json_payload(raw_output: str) -> dict[str, Any]:
        candidate = raw_output.strip()
        if candidate == "PARSE_ERROR":
            raise PromptParseError(
                "I couldn't understand that request. Try naming one or two specifics like "
                "cuisine, protein, calories, time, or exclusions."
            )
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 3:
                candidate = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(candidate)
        except JSONDecodeError as exc:
            raise PromptParseError(
                "I couldn't read the AI response for that prompt. Please try again."
            ) from exc
        if not isinstance(payload, dict):
            raise PromptParseError("The AI response for that prompt was not a JSON object.")
        return payload

    def _system_prompt(self) -> str:
        cuisines = ", ".join(sorted(CUISINE_BOOSTS))
        methods = ", ".join(method.value for method in CookingMethod)
        return (
            "You translate meal-desire prompts into structured roll constraints for a bowl app.\n"
            "Return JSON only, with no markdown fences.\n"
            "If the prompt is gibberish, too vague to constrain, or unsafe to infer, return the exact text PARSE_ERROR.\n"
            "Resolve contradictions by keeping the strongest / most specific constraint.\n"
            "Use allergen-style strings like nuts, dairy, soy, sesame in hard_exclusions unless the user supplied a literal component UUID.\n"
            f"Allowed cuisines: {cuisines}.\n"
            f"Allowed cooking methods: {methods}.\n"
            "Valid JSON schema (no extra keys):\n"
            "{"
            '"hard_exclusions": [string], '
            '"cuisine_weights": {string: number}, '
            '"flavor_boosts": {string: number}, '
            '"macro_bounds": {"min_protein": number|null, "max_kcal": number|null, "min_fiber": number|null, "max_sodium": number|null}|null, '
            '"cooking_method_constraint": string|null, '
            '"time_budget_minutes": integer|null, '
            '"pantry_only": boolean'
            "}\n"
            "Rules:\n"
            "- hard_exclusions may contain allergen flags or literal component UUIDs.\n"
            "- cuisine_weights values must be in [0, 1].\n"
            "- flavor_boosts values must be in [-1, 1].\n"
            "- Use empty arrays/objects and nulls when a field is not implied.\n"
            '- "high protein" should usually map to macro_bounds.min_protein and may also add a protein-oriented flavor or dietary tag when justified.\n'
            '- "use what I have", "pantry only", or similar should set pantry_only to true.\n'
            "- Never invent unsupported keys."
        )

    @staticmethod
    def _user_prompt(prompt: str, profile: UserProfile | None) -> str:
        profile_block = "No profile provided."
        if profile is not None:
            profile_block = json.dumps(
                {
                    "dietary_mode": profile.dietary_mode,
                    "allergens": list(profile.allergens),
                    "default_time_budget_min": profile.default_time_budget_min,
                    "goal": profile.goal,
                    "locale": profile.locale,
                },
                ensure_ascii=True,
            )
        return (
            "Translate this request into roll constraints.\n"
            f"User profile: {profile_block}\n"
            f"Prompt: {prompt}"
        )

    @staticmethod
    def _http_error_message(response: httpx.Response) -> str:
        if response.status_code == 401:
            return "Prompt-based rolling is not configured right now."
        if response.status_code == 429:
            return "The AI parser is busy right now. Please try again in a moment."
        if response.status_code >= 500:
            return "The AI parser is unavailable right now. Please try again in a moment."
        return "The AI parser could not understand that request. Please try a simpler prompt."


__all__ = [
    "MacroBounds",
    "PromptParseError",
    "RollConstraints",
    "RollPromptParser",
]
