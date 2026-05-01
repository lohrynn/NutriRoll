"""Unified LLM configuration, provider adapters, and BYOK helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Literal, cast

import httpx

from nutriroll.config import Settings, get_settings

LLMProvider = Literal["openai", "anthropic", "google", "ollama", "custom"]
LLMFeature = Literal[
    "component_creation",
    "prompt_rolls",
    "recipe_polish",
    "weekly_recaps",
]

KNOWN_PROVIDERS: tuple[LLMProvider, ...] = (
    "openai",
    "anthropic",
    "google",
    "ollama",
    "custom",
)
KNOWN_FEATURES: tuple[LLMFeature, ...] = (
    "component_creation",
    "prompt_rolls",
    "recipe_polish",
    "weekly_recaps",
)
_ENV_DEFAULT_FEATURES: dict[LLMFeature, str] = {
    "component_creation": "openai_api_key",
    "prompt_rolls": "openai_api_key",
    "recipe_polish": "openai_api_key",
    "weekly_recaps": "openai_api_key",
}
_CUSTOM_BASE_URL_DEFAULT = "https://api.openai.com/v1"
_OPENAI_BASE_URL_DEFAULT = "https://api.openai.com/v1"
_ANTHROPIC_BASE_URL_DEFAULT = "https://api.anthropic.com/v1"
_GOOGLE_BASE_URL_DEFAULT = "https://generativelanguage.googleapis.com/v1beta"
_OLLAMA_BASE_URL_DEFAULT = "http://localhost:11434/v1"


class LLMConfigError(ValueError):
    """Raised when stored/provider config is invalid."""


class LLMFeatureDisabledError(RuntimeError):
    """Raised when an LLM-backed feature is turned off in settings."""

    def __init__(self, feature: LLMFeature) -> None:
        self.feature = feature
        super().__init__(f"LLM feature {feature!r} is disabled.")


class LLMKeyValidationError(RuntimeError):
    """Raised when an API key ping fails."""


@dataclass(frozen=True, slots=True)
class LLMConfig:
    enabled_features: list[str] = field(default_factory=list)
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key_set: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "enabled_features", _normalize_features(self.enabled_features))
        provider = self.provider.strip().lower()
        if provider not in KNOWN_PROVIDERS:
            raise LLMConfigError(f"unknown LLM provider: {self.provider!r}")
        object.__setattr__(self, "provider", provider)
        model = self.model.strip() or "gpt-4o-mini"
        object.__setattr__(self, "model", model)

    def is_enabled(self, feature: LLMFeature) -> bool:
        return feature in self.enabled_features

    def require_feature(self, feature: LLMFeature) -> None:
        if not self.is_enabled(feature):
            raise LLMFeatureDisabledError(feature)


@dataclass(frozen=True, slots=True)
class LLMRuntimeConfig:
    public: LLMConfig
    provider: LLMProvider
    model: str
    api_key: str
    base_url: str

    def require_feature(self, feature: LLMFeature) -> None:
        self.public.require_feature(feature)


@dataclass(frozen=True, slots=True)
class StoredLLMConfig:
    config: LLMConfig
    api_key_hash: str | None = None
    encrypted_api_key: str | None = None


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    refusal: str | None = None
    raw_payload: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None


def default_llm_config() -> LLMConfig:
    return LLMConfig()


def env_default_llm_config(settings: Settings | None = None) -> LLMConfig:
    current = settings or get_settings()
    enabled = [
        feature
        for feature, attr in _ENV_DEFAULT_FEATURES.items()
        if getattr(current, attr).strip()
    ]
    return LLMConfig(
        enabled_features=enabled,
        provider=current.llm_provider,
        model=current.llm_model,
        api_key_set=bool(_provider_api_key(current, current.llm_provider).strip()),
    )


def stored_llm_config_from_payload(
    payload: dict[str, Any] | None,
    *,
    settings: Settings | None = None,
    legacy_weekly_recap_enabled: bool = False,
) -> StoredLLMConfig:
    current = settings or get_settings()
    raw = dict(payload or {})
    base = env_default_llm_config(current)
    if not raw:
        enabled = list(base.enabled_features)
        if legacy_weekly_recap_enabled and "weekly_recaps" not in enabled:
            enabled.append("weekly_recaps")
        config = LLMConfig(
            enabled_features=enabled,
            provider=base.provider,
            model=base.model,
            api_key_set=base.api_key_set,
        )
        return StoredLLMConfig(config=config)

    raw_enabled = raw.get("enabled_features")
    enabled_features = (
        _normalize_features(raw_enabled)
        if isinstance(raw_enabled, list)
        else list(base.enabled_features)
    )
    if legacy_weekly_recap_enabled and "weekly_recaps" not in enabled_features:
        enabled_features.append("weekly_recaps")

    provider = str(raw.get("provider", base.provider) or base.provider).strip().lower()
    model = str(raw.get("model", base.model) or base.model).strip() or base.model
    api_key_hash = _optional_clean_str(raw.get("api_key_hash"))
    encrypted_api_key = _optional_clean_str(raw.get("encrypted_api_key"))
    api_key_set = bool(api_key_hash or encrypted_api_key or _provider_api_key(current, provider).strip())
    config = LLMConfig(
        enabled_features=enabled_features,
        provider=provider,
        model=model,
        api_key_set=api_key_set,
    )
    return StoredLLMConfig(
        config=config,
        api_key_hash=api_key_hash,
        encrypted_api_key=encrypted_api_key,
    )


def serialize_stored_llm_config(stored: StoredLLMConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "enabled_features": list(stored.config.enabled_features),
        "provider": stored.config.provider,
        "model": stored.config.model,
    }
    if stored.api_key_hash:
        payload["api_key_hash"] = stored.api_key_hash
    if stored.encrypted_api_key:
        payload["encrypted_api_key"] = stored.encrypted_api_key
    return payload


def resolve_runtime_llm_config(
    stored: StoredLLMConfig | None = None,
    *,
    settings: Settings | None = None,
) -> LLMRuntimeConfig:
    current = settings or get_settings()
    active = stored or StoredLLMConfig(config=env_default_llm_config(current))
    provider = cast(LLMProvider, active.config.provider)
    encrypted = active.encrypted_api_key
    api_key = _provider_api_key(current, provider)
    if encrypted:
        api_key = decrypt_api_key(encrypted, current.llm_key_master)
    return LLMRuntimeConfig(
        public=LLMConfig(
            enabled_features=list(active.config.enabled_features),
            provider=provider,
            model=active.config.model,
            api_key_set=bool(api_key.strip()),
        ),
        provider=provider,
        model=active.config.model,
        api_key=api_key,
        base_url=_provider_base_url(provider, current),
    )


def hash_api_key(api_key: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), api_key.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def encrypt_api_key(api_key: str, secret: str) -> str:
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    nonce = secrets.token_bytes(16)
    plaintext = api_key.encode("utf-8")
    ciphertext = _xor_stream(plaintext, key=key, nonce=nonce)
    tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + ciphertext + tag).decode("ascii")


def decrypt_api_key(ciphertext: str, secret: str) -> str:
    raw = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
    if len(raw) < 48:
        raise LLMConfigError("stored API key payload is truncated")
    nonce = raw[:16]
    tag = raw[-32:]
    encrypted = raw[16:-32]
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    expected = hmac.new(key, nonce + encrypted, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, tag):
        raise LLMConfigError("stored API key payload failed integrity check")
    plaintext = _xor_stream(encrypted, key=key, nonce=nonce)
    return plaintext.decode("utf-8")


async def validate_api_key(
    *,
    provider: LLMProvider,
    model: str,
    api_key: str,
    settings: Settings | None = None,
    timeout_seconds: float = 5.0,
) -> None:
    trimmed = api_key.strip()
    if provider != "ollama" and not trimmed:
        raise LLMKeyValidationError("API key cannot be empty.")
    runtime = LLMRuntimeConfig(
        public=LLMConfig(
            enabled_features=[],
            provider=provider,
            model=model,
            api_key_set=bool(trimmed),
        ),
        provider=provider,
        model=model.strip() or "gpt-4o-mini",
        api_key=trimmed,
        base_url=_provider_base_url(provider, settings or get_settings()),
    )
    try:
        response = await perform_llm_request(
            runtime,
            messages=[{"role": "user", "content": 'Reply with exactly {"ok":true}.'}],
            temperature=0.0,
            timeout_seconds=timeout_seconds,
            response_format_json=True,
            max_tokens=1,
        )
    except httpx.HTTPStatusError as exc:
        raise LLMKeyValidationError(_provider_ping_error(provider, exc.response)) from exc
    except httpx.TimeoutException as exc:
        raise LLMKeyValidationError("The provider did not respond within 5 seconds.") from exc
    except httpx.HTTPError as exc:
        raise LLMKeyValidationError("The provider could not be reached.") from exc
    if not response.text.strip():
        raise LLMKeyValidationError("The provider returned an empty response.")


async def perform_llm_request(
    runtime: LLMRuntimeConfig,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    timeout_seconds: float,
    response_format_json: bool = False,
    max_tokens: int | None = None,
) -> LLMResponse:
    provider = runtime.provider
    if provider in {"openai", "custom", "ollama"}:
        return await _perform_openai_compatible_request(
            runtime,
            messages=messages,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            response_format_json=response_format_json,
            max_tokens=max_tokens,
        )
    if provider == "anthropic":
        return await _perform_anthropic_request(
            runtime,
            messages=messages,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )
    return await _perform_google_request(
        runtime,
        messages=messages,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
    )


def perform_llm_request_sync(
    runtime: LLMRuntimeConfig,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    timeout_seconds: float,
    response_format_json: bool = False,
    max_tokens: int | None = None,
) -> LLMResponse:
    provider = runtime.provider
    if provider in {"openai", "custom", "ollama"}:
        return _perform_openai_compatible_request_sync(
            runtime,
            messages=messages,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            response_format_json=response_format_json,
            max_tokens=max_tokens,
        )
    if provider == "anthropic":
        return _perform_anthropic_request_sync(
            runtime,
            messages=messages,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )
    return _perform_google_request_sync(
        runtime,
        messages=messages,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
    )


def feature_display_name(feature: LLMFeature) -> str:
    return feature.replace("_", " ")


def _normalize_features(features: list[str] | tuple[str, ...] | Any) -> list[str]:
    if not isinstance(features, list | tuple):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in features:
        feature = str(raw).strip().lower()
        if feature not in KNOWN_FEATURES or feature in seen:
            continue
        seen.add(feature)
        normalized.append(feature)
    return normalized


def _optional_clean_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _provider_api_key(settings: Settings, provider: str) -> str:
    if provider == "openai":
        return settings.openai_api_key
    if provider == "anthropic":
        return settings.anthropic_api_key
    if provider == "google":
        return settings.google_api_key
    if provider == "ollama":
        return settings.ollama_api_key
    return settings.custom_llm_api_key or settings.openai_api_key


def _provider_base_url(provider: LLMProvider, settings: Settings) -> str:
    if provider == "openai":
        return (settings.openai_base_url or settings.llm_base_url or _OPENAI_BASE_URL_DEFAULT).rstrip(
            "/"
        )
    if provider == "anthropic":
        return (settings.anthropic_base_url or _ANTHROPIC_BASE_URL_DEFAULT).rstrip("/")
    if provider == "google":
        return (settings.google_base_url or _GOOGLE_BASE_URL_DEFAULT).rstrip("/")
    if provider == "ollama":
        return (settings.ollama_base_url or _OLLAMA_BASE_URL_DEFAULT).rstrip("/")
    return (settings.custom_llm_base_url or settings.llm_base_url or _CUSTOM_BASE_URL_DEFAULT).rstrip(
        "/"
    )


def _xor_stream(payload: bytes, *, key: bytes, nonce: bytes) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < len(payload):
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        output.extend(block)
        counter += 1
    return bytes(a ^ b for a, b in zip(payload, output, strict=False))


async def _perform_openai_compatible_request(
    runtime: LLMRuntimeConfig,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    timeout_seconds: float,
    response_format_json: bool,
    max_tokens: int | None,
) -> LLMResponse:
    headers = {"Content-Type": "application/json"}
    if runtime.api_key.strip():
        headers["Authorization"] = f"Bearer {runtime.api_key}"
    body: dict[str, Any] = {
        "model": runtime.model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format_json:
        body["response_format"] = {"type": "json_object"}
    if max_tokens is not None:
        body["max_tokens"] = max_tokens

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(
            f"{runtime.base_url}/chat/completions",
            headers=headers,
            json=body,
        )
        response.raise_for_status()

    payload = cast(dict[str, Any], response.json())
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return LLMResponse(text="", raw_payload=payload)
    first = choices[0]
    message = first.get("message") if isinstance(first, dict) else None
    refusal = message.get("refusal") if isinstance(message, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return LLMResponse(
        text=_coerce_message_text(content),
        refusal=str(refusal) if isinstance(refusal, str) and refusal.strip() else None,
        raw_payload=payload,
        usage=cast(dict[str, Any] | None, payload.get("usage")),
    )


def _perform_openai_compatible_request_sync(
    runtime: LLMRuntimeConfig,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    timeout_seconds: float,
    response_format_json: bool,
    max_tokens: int | None,
) -> LLMResponse:
    headers = {"Content-Type": "application/json"}
    if runtime.api_key.strip():
        headers["Authorization"] = f"Bearer {runtime.api_key}"
    body: dict[str, Any] = {
        "model": runtime.model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format_json:
        body["response_format"] = {"type": "json_object"}
    if max_tokens is not None:
        body["max_tokens"] = max_tokens

    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(
            f"{runtime.base_url}/chat/completions",
            headers=headers,
            json=body,
        )
        response.raise_for_status()

    payload = cast(dict[str, Any], response.json())
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return LLMResponse(text="", raw_payload=payload)
    first = choices[0]
    message = first.get("message") if isinstance(first, dict) else None
    refusal = message.get("refusal") if isinstance(message, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return LLMResponse(
        text=_coerce_message_text(content),
        refusal=str(refusal) if isinstance(refusal, str) and refusal.strip() else None,
        raw_payload=payload,
        usage=cast(dict[str, Any] | None, payload.get("usage")),
    )


async def _perform_anthropic_request(
    runtime: LLMRuntimeConfig,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    timeout_seconds: float,
    max_tokens: int | None,
) -> LLMResponse:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": runtime.api_key,
        "anthropic-version": "2023-06-01",
    }
    system_parts = [message["content"] for message in messages if message.get("role") == "system"]
    converted = [
        {"role": "assistant" if m.get("role") == "assistant" else "user", "content": m["content"]}
        for m in messages
        if m.get("role") != "system"
    ]
    body: dict[str, Any] = {
        "model": runtime.model,
        "messages": converted,
        "temperature": temperature,
        "max_tokens": max_tokens or 256,
    }
    if system_parts:
        body["system"] = "\n\n".join(system_parts)

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(f"{runtime.base_url}/messages", headers=headers, json=body)
        response.raise_for_status()

    payload = cast(dict[str, Any], response.json())
    content = payload.get("content")
    texts: list[str] = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    texts.append(text)
    return LLMResponse(text="".join(texts), raw_payload=payload)


def _perform_anthropic_request_sync(
    runtime: LLMRuntimeConfig,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    timeout_seconds: float,
    max_tokens: int | None,
) -> LLMResponse:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": runtime.api_key,
        "anthropic-version": "2023-06-01",
    }
    system_parts = [message["content"] for message in messages if message.get("role") == "system"]
    converted = [
        {"role": "assistant" if m.get("role") == "assistant" else "user", "content": m["content"]}
        for m in messages
        if m.get("role") != "system"
    ]
    body: dict[str, Any] = {
        "model": runtime.model,
        "messages": converted,
        "temperature": temperature,
        "max_tokens": max_tokens or 256,
    }
    if system_parts:
        body["system"] = "\n\n".join(system_parts)

    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(f"{runtime.base_url}/messages", headers=headers, json=body)
        response.raise_for_status()

    payload = cast(dict[str, Any], response.json())
    content = payload.get("content")
    texts: list[str] = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    texts.append(text)
    return LLMResponse(text="".join(texts), raw_payload=payload)


async def _perform_google_request(
    runtime: LLMRuntimeConfig,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    timeout_seconds: float,
    max_tokens: int | None,
) -> LLMResponse:
    headers = {"Content-Type": "application/json"}
    if runtime.api_key.strip():
        headers["x-goog-api-key"] = runtime.api_key
    system_parts = [message["content"] for message in messages if message.get("role") == "system"]
    prompt_parts = [
        f"{message.get('role', 'user').upper()}: {message.get('content', '')}"
        for message in messages
        if message.get("role") != "system"
    ]
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": "\n\n".join(prompt_parts)}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens or 256,
        },
    }
    if system_parts:
        body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

    url = f"{runtime.base_url}/models/{runtime.model}:generateContent"
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()

    payload = cast(dict[str, Any], response.json())
    candidates = payload.get("candidates")
    texts: list[str] = []
    if isinstance(candidates, list) and candidates:
        first = candidates[0]
        content = first.get("content") if isinstance(first, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if isinstance(parts, list):
            for item in parts:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        texts.append(text)
    return LLMResponse(text="".join(texts), raw_payload=payload)


def _perform_google_request_sync(
    runtime: LLMRuntimeConfig,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    timeout_seconds: float,
    max_tokens: int | None,
) -> LLMResponse:
    headers = {"Content-Type": "application/json"}
    if runtime.api_key.strip():
        headers["x-goog-api-key"] = runtime.api_key
    system_parts = [message["content"] for message in messages if message.get("role") == "system"]
    prompt_parts = [
        f"{message.get('role', 'user').upper()}: {message.get('content', '')}"
        for message in messages
        if message.get("role") != "system"
    ]
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": "\n\n".join(prompt_parts)}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens or 256,
        },
    }
    if system_parts:
        body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

    url = f"{runtime.base_url}/models/{runtime.model}:generateContent"
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(url, headers=headers, json=body)
        response.raise_for_status()

    payload = cast(dict[str, Any], response.json())
    candidates = payload.get("candidates")
    texts: list[str] = []
    if isinstance(candidates, list) and candidates:
        first = candidates[0]
        content = first.get("content") if isinstance(first, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if isinstance(parts, list):
            for item in parts:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        texts.append(text)
    return LLMResponse(text="".join(texts), raw_payload=payload)


def _coerce_message_text(content: Any) -> str:
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


def _provider_ping_error(provider: LLMProvider, response: httpx.Response) -> str:
    if response.status_code in {401, 403}:
        return f"The {provider} API key was rejected."
    if response.status_code == 429:
        return f"The {provider} API is rate-limiting requests right now."
    if response.status_code >= 500:
        return f"The {provider} API is unavailable right now."
    return f"The {provider} API rejected the validation request."


__all__ = [
    "KNOWN_FEATURES",
    "KNOWN_PROVIDERS",
    "LLMConfig",
    "LLMConfigError",
    "LLMFeature",
    "LLMFeatureDisabledError",
    "LLMKeyValidationError",
    "LLMProvider",
    "LLMResponse",
    "LLMRuntimeConfig",
    "StoredLLMConfig",
    "default_llm_config",
    "decrypt_api_key",
    "encrypt_api_key",
    "env_default_llm_config",
    "feature_display_name",
    "hash_api_key",
    "perform_llm_request",
    "perform_llm_request_sync",
    "resolve_runtime_llm_config",
    "serialize_stored_llm_config",
    "stored_llm_config_from_payload",
    "validate_api_key",
]
