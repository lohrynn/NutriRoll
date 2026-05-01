"""Optional LLM-based recipe-step phrasing polish."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, replace
from json import JSONDecodeError
from time import monotonic
from typing import Any, ClassVar, Final, Literal, cast

import httpx

from nutriroll.config import get_settings
from nutriroll.domain.llm_config import (
    KNOWN_FEATURES,
    LLMConfig,
    LLMRuntimeConfig,
    perform_llm_request,
    resolve_runtime_llm_config,
)
from nutriroll.domain.recipe import RecipeStep

PolishTone = Literal["concise", "enthusiastic", "calm", "professional"]

_ALLOWED_TONES: Final[frozenset[str]] = frozenset(
    {"concise", "enthusiastic", "calm", "professional"}
)
_CACHE_TTL_SECONDS: Final[float] = 24 * 60 * 60


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    texts: tuple[str, ...]
    expires_at: float


class RecipeStepPolish:
    """Rephrase recipe steps while preserving technique and timing."""

    _cache: ClassVar[dict[tuple[str, str], _CacheEntry]] = {}
    _locks: ClassVar[dict[tuple[str, str], asyncio.Lock]] = {}

    def __init__(
        self,
        *,
        runtime_config: LLMRuntimeConfig | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 12.0,
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
        self.last_applied = False

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
        cls._locks.clear()

    async def polish_steps(
        self, directions: list[RecipeStep], tone: str = "concise"
    ) -> list[RecipeStep]:
        validated_tone = self._validate_tone(tone)
        self.last_applied = False
        if not directions:
            return []
        self.runtime_config.require_feature("recipe_polish")
        if not self.api_key.strip():
            return list(directions)

        cache_key = (self._directions_hash(directions), validated_tone)
        cached = self._cache.get(cache_key)
        now = monotonic()
        if cached is not None and cached.expires_at > now:
            self.last_applied = True
            return self._apply_texts(directions, cached.texts)

        lock = self._locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached = self._cache.get(cache_key)
            now = monotonic()
            if cached is not None and cached.expires_at > now:
                self.last_applied = True
                return self._apply_texts(directions, cached.texts)

            texts = await self._request_polished_texts(directions, validated_tone)
            if texts is None or len(texts) != len(directions):
                return list(directions)

            normalized = tuple(text.strip() for text in texts)
            if any(not text for text in normalized):
                return list(directions)

            self._cache[cache_key] = _CacheEntry(
                texts=normalized,
                expires_at=monotonic() + _CACHE_TTL_SECONDS,
            )
            self.last_applied = True
            return self._apply_texts(directions, normalized)

    @staticmethod
    def _validate_tone(tone: str) -> PolishTone:
        if tone not in _ALLOWED_TONES:
            raise ValueError(f"unsupported polish tone: {tone!r}")
        return tone  # type: ignore[return-value]

    @staticmethod
    def _directions_hash(directions: list[RecipeStep]) -> str:
        payload = [
            {
                "text": step.text,
                "offset_min": step.offset_min,
                "duration_min": step.duration_min,
            }
            for step in directions
        ]
        encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _apply_texts(
        directions: list[RecipeStep],
        texts: tuple[str, ...] | list[str],
    ) -> list[RecipeStep]:
        return [replace(step, text=text) for step, text in zip(directions, texts, strict=True)]

    async def _request_polished_texts(
        self,
        directions: list[RecipeStep],
        tone: PolishTone,
    ) -> list[str] | None:
        try:
            response = await perform_llm_request(
                self.runtime_config,
                messages=[
                    {"role": "system", "content": self._system_prompt(tone)},
                    {"role": "user", "content": self._user_prompt(directions)},
                ],
                temperature=0.2,
                timeout_seconds=self.timeout_seconds,
            )
        except httpx.HTTPError:
            return None

        payload = response.raw_payload or {}
        if not isinstance(payload, dict):
            return None
        return self._parse_response(cast(dict[str, Any], payload), expected_count=len(directions))

    @staticmethod
    def _system_prompt(tone: PolishTone) -> str:
        return (
            "You rewrite recipe steps for a bowl-cooking app.\n"
            "Return only a JSON array of strings with the same number of items as the input.\n"
            f"Use this tone: {tone}.\n"
            "Rules:\n"
            "- Keep the same cooking meaning.\n"
            "- Do not change techniques, ingredients, quantities, temperatures, or timing.\n"
            "- Use imperative mood and active voice.\n"
            "- Keep each step clear, brief, and consistent in style.\n"
            "- Do not add numbering, markdown, or commentary."
        )

    @staticmethod
    def _user_prompt(directions: list[RecipeStep]) -> str:
        payload = [
            {
                "text": step.text,
                "duration_minutes": step.duration_min,
            }
            for step in directions
        ]
        return (
            "Rewrite these recipe steps.\n"
            f"Input steps: {json.dumps(payload, ensure_ascii=True)}"
        )

    @classmethod
    def _parse_response(
        cls,
        payload: dict[str, Any],
        *,
        expected_count: int,
    ) -> list[str] | None:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first_choice = cast(object, choices[0])
        if not isinstance(first_choice, dict):
            return None
        first_choice_dict = cast(dict[str, Any], first_choice)
        message = first_choice_dict.get("message")
        if not isinstance(message, dict):
            return None
        message_dict = cast(dict[str, Any], message)
        refusal = message_dict.get("refusal")
        if refusal:
            return None
        content = message_dict.get("content")
        raw_output = cls._coerce_message_content(content).strip()
        if not raw_output:
            return None
        try:
            parsed = cls._extract_json_array(raw_output)
        except JSONDecodeError:
            return None
        if len(parsed) != expected_count or any(not isinstance(item, str) for item in parsed):
            return None
        return [item for item in parsed if isinstance(item, str)]

    @staticmethod
    def _coerce_message_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in cast(list[object], content):
                if isinstance(item, dict):
                    item_dict = cast(dict[str, Any], item)
                    text = item_dict.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""

    @staticmethod
    def _extract_json_array(raw_output: str) -> list[Any]:
        candidate = raw_output.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 3:
                candidate = "\n".join(lines[1:-1]).strip()
        parsed = json.loads(candidate)
        if not isinstance(parsed, list):
            return []
        return cast(list[Any], parsed)


__all__ = ["PolishTone", "RecipeStepPolish"]
