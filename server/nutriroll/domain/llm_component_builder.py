"""Prompt-based component generation service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any
from uuid import uuid4

import httpx

from nutriroll.config import get_settings
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
from nutriroll.domain.llm_config import (
    KNOWN_FEATURES,
    LLMConfig,
    LLMRuntimeConfig,
    perform_llm_request_sync,
    resolve_runtime_llm_config,
)
from nutriroll.domain.profile import UserProfile


class LLMBuildError(RuntimeError):
    """Raised when a prompt cannot be converted into a valid component."""


@dataclass(frozen=True, slots=True)
class LLMGeneratedComponent:
    component: Component
    raw_llm_output: str
    confidence: float


@dataclass(frozen=True, slots=True)
class _LLMResponse:
    raw_output: str
    confidence: float | None


class LLMComponentBuilder:
    """Generate Component domain objects from a natural-language prompt."""

    def __init__(
        self,
        *,
        runtime_config: LLMRuntimeConfig | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        settings = get_settings()
        resolved = resolve_runtime_llm_config(settings=settings)
        enabled_features = (
            list(KNOWN_FEATURES)
            if runtime_config is None and any(value is not None for value in (model, api_key, base_url))
            else list(resolved.public.enabled_features)
        )
        self.runtime_config = (
            runtime_config
            if runtime_config is not None
            else LLMRuntimeConfig(
                public=LLMConfig(
                    enabled_features=enabled_features,
                    provider=resolved.public.provider,
                    model=model or resolved.model,
                    api_key_set=bool(
                        (api_key if api_key is not None else resolved.api_key).strip()
                    ),
                ),
                provider=resolved.provider,
                model=model or resolved.model,
                api_key=api_key if api_key is not None else resolved.api_key,
                base_url=(base_url or resolved.base_url).rstrip("/"),
            )
        )
        self.model = self.runtime_config.model
        self.api_key = self.runtime_config.api_key
        self.base_url = self.runtime_config.base_url
        self.timeout_seconds = timeout_seconds

    def generate_from_prompt(self, prompt: str, profile: UserProfile | None = None) -> Component:
        return self.build_from_prompt(prompt, profile).component

    def build_from_prompt(
        self, prompt: str, profile: UserProfile | None = None
    ) -> LLMGeneratedComponent:
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise LLMBuildError("Enter a short description before generating a component.")
        self.runtime_config.require_feature("component_creation")
        if not self.api_key.strip():
            raise LLMBuildError("LLM features are not configured on this server.")

        llm_response = self._request_component_json(normalized_prompt, profile)
        try:
            payload = self._extract_json_payload(llm_response.raw_output)
            component = self._component_from_payload(payload)
        except LLMBuildError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMBuildError(
                "The AI response was incomplete or invalid. Please try a more specific prompt."
            ) from exc

        confidence = llm_response.confidence
        if confidence is None:
            confidence = 0.72

        return LLMGeneratedComponent(
            component=component,
            raw_llm_output=llm_response.raw_output,
            confidence=max(0.0, min(1.0, float(confidence))),
        )

    def _request_component_json(
        self, prompt: str, profile: UserProfile | None
    ) -> _LLMResponse:
        try:
            llm_response = perform_llm_request_sync(
                self.runtime_config,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": self._user_prompt(prompt, profile)},
                ],
                temperature=0.2,
                timeout_seconds=self.timeout_seconds,
                response_format_json=True,
            )
        except httpx.HTTPStatusError as exc:
            detail = self._http_error_message(exc.response)
            raise LLMBuildError(detail) from exc
        except httpx.HTTPError as exc:
            raise LLMBuildError("The AI service is unavailable right now. Please try again.") from exc

        data = llm_response.raw_payload or {}
        if llm_response.refusal:
            raise LLMBuildError("The AI could not generate a component from that request.")
        raw_output = llm_response.text
        if raw_output.strip() == "":
            raise LLMBuildError("The AI service returned an empty response.")
        confidence = self._extract_confidence(data, raw_output)
        return _LLMResponse(raw_output=raw_output, confidence=confidence)

    def _system_prompt(self) -> str:
        categories = ", ".join(category.value for category in Category)
        portion_units = ", ".join(unit.value for unit in PortionUnit)
        method_lines = "\n".join(
            f"- {category.value}: {', '.join(method.value for method in sorted(methods, key=lambda item: item.value))}"
            for category, methods in ALLOWED_METHODS.items()
        )
        return (
            "You generate structured meal components for a bowl-recommendation app.\n"
            "Return only valid JSON with no markdown fences.\n"
            "Choose the best category and provide realistic nutrition, portioning, and prep details.\n"
            f"Allowed categories: {categories}.\n"
            f"Allowed portion units: {portion_units}.\n"
            "Allowed cooking methods by category:\n"
            f"{method_lines}\n"
            "JSON schema:\n"
            "{"
            '"category": string, '
            '"name": string, '
            '"image_url": string|null, '
            '"macros_per_100g": {"kcal": number, "carbs_g": number, "protein_g": number, "fat_g": number, "fiber_g": number}, '
            '"default_portion": {"value": number, "unit": string}, '
            '"default_cooking_method": string, '
            '"cooking_methods": [{"method": string, "approx_minutes": integer|null, "can_cook_with_others": boolean, "notes": string|null}], '
            '"flavor_tags": [string], '
            '"dietary_tags": [string], '
            '"allergens": [string], '
            '"shelf_life_days": integer|null, '
            '"seasonal_availability": string|null, '
            '"blacklisted": boolean, '
            '"confidence": number'
            "}\n"
            "Rules:\n"
            "- confidence must be between 0 and 1.\n"
            "- Use null instead of inventing unknown values.\n"
            "- cooking_methods must be non-empty and include default_cooking_method.\n"
            "- Reject impossible values such as negative macros, zero portion, or invalid methods.\n"
            "- If the prompt is unsafe or impossible, return JSON with an \"error\" string instead."
        )

    def _user_prompt(self, prompt: str, profile: UserProfile | None) -> str:
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
            "Generate one component proposal.\n"
            f"User profile: {profile_block}\n"
            f"Prompt: {prompt}"
        )

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
    def _extract_confidence(data: dict[str, Any], raw_output: str) -> float | None:
        parsed = None
        try:
            parsed = LLMComponentBuilder._extract_json_payload(raw_output)
        except LLMBuildError:
            parsed = None
        if isinstance(parsed, dict):
            confidence = parsed.get("confidence")
            if isinstance(confidence, (int, float)):
                return float(confidence)
        usage = data.get("usage")
        if isinstance(usage, dict):
            completion_tokens = usage.get("completion_tokens")
            if isinstance(completion_tokens, (int, float)) and completion_tokens > 0:
                return 0.72
        return None

    @staticmethod
    def _extract_json_payload(raw_output: str) -> dict[str, Any]:
        candidate = raw_output.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 3:
                candidate = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(candidate)
        except JSONDecodeError as exc:
            raise LLMBuildError(
                "The AI response could not be parsed. Please try a more specific description."
            ) from exc
        if not isinstance(payload, dict):
            raise LLMBuildError("The AI response was not a JSON object.")
        error = payload.get("error")
        if isinstance(error, str) and error.strip():
            raise LLMBuildError(error.strip())
        return payload

    @staticmethod
    def _component_from_payload(payload: dict[str, Any]) -> Component:
        try:
            category = Category(str(payload["category"]))
            name = str(payload["name"]).strip()
            image_url = LLMComponentBuilder._optional_str(payload.get("image_url"))
            macros_data = LLMComponentBuilder._require_mapping(payload, "macros_per_100g")
            default_portion_data = LLMComponentBuilder._require_mapping(payload, "default_portion")
            cooking_methods_data = payload["cooking_methods"]
            default_method = CookingMethod(str(payload["default_cooking_method"]))
        except KeyError as exc:
            missing = exc.args[0]
            raise LLMBuildError(f"The AI response was missing '{missing}'.") from exc
        except ValueError as exc:
            raise LLMBuildError(f"The AI returned an invalid enum value: {exc!s}") from exc

        if not isinstance(cooking_methods_data, list) or not cooking_methods_data:
            raise LLMBuildError("The AI response must include at least one cooking method.")

        macros = Macros(
            kcal=float(macros_data["kcal"]),
            carbs_g=float(macros_data["carbs_g"]),
            protein_g=float(macros_data["protein_g"]),
            fat_g=float(macros_data["fat_g"]),
            fiber_g=float(macros_data["fiber_g"]),
        )
        portion = Portion(
            value=float(default_portion_data["value"]),
            unit=PortionUnit(str(default_portion_data["unit"])),
        )
        cooking_method_specs: list[CookingMethodSpec] = []
        for item in cooking_methods_data:
            method_payload = LLMComponentBuilder._ensure_mapping(item, "cooking_methods item")
            cooking_method_specs.append(
                CookingMethodSpec(
                    method=CookingMethod(str(method_payload["method"])),
                    approx_minutes=LLMComponentBuilder._optional_int(
                        method_payload.get("approx_minutes")
                    ),
                    can_cook_with_others=bool(
                        method_payload.get("can_cook_with_others", True)
                    ),
                    notes=LLMComponentBuilder._optional_str(method_payload.get("notes")),
                )
            )
        cooking_methods = tuple(cooking_method_specs)

        return Component(
            id=uuid4(),
            category=category,
            name=name,
            image_url=image_url,
            macros_per_100g=macros,
            default_portion=portion,
            default_cooking_method=default_method,
            cooking_methods=cooking_methods,
            flavor_tags=tuple(LLMComponentBuilder._string_list(payload.get("flavor_tags"))),
            dietary_tags=tuple(LLMComponentBuilder._string_list(payload.get("dietary_tags"))),
            allergens=tuple(LLMComponentBuilder._string_list(payload.get("allergens"))),
            shelf_life_days=LLMComponentBuilder._optional_int(payload.get("shelf_life_days")),
            seasonal_availability=LLMComponentBuilder._optional_str(
                payload.get("seasonal_availability")
            ),
            blacklisted=bool(payload.get("blacklisted", False)),
        )

    @staticmethod
    def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
        value = payload[key]
        if not isinstance(value, dict):
            raise LLMBuildError(f"The AI response field '{key}' must be an object.")
        return value

    @staticmethod
    def _ensure_mapping(value: Any, label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise LLMBuildError(f"The AI response field '{label}' must be an object.")
        return value

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None:
            return None
        return int(value)

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise LLMBuildError("The AI response contains invalid tag fields.")
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _http_error_message(response: httpx.Response) -> str:
        if response.status_code in {401, 403}:
            return "LLM features are not configured on this server."
        if response.status_code == 429:
            return "The AI service is busy right now. Please wait a few seconds and try again."
        detail = ""
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str):
                    detail = message.strip()
            elif isinstance(error, str):
                detail = error.strip()
        if detail:
            return detail
        return "The AI service could not generate a component right now."


__all__ = ["LLMBuildError", "LLMComponentBuilder", "LLMGeneratedComponent"]
