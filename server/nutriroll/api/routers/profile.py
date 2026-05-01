"""Singleton profile endpoints, mounted at /v1/me/profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.api.schemas.profile import (
    LLMConfigRead,
    LLMConfigUpdate,
    UserProfileRead,
    UserProfileUpdate,
)
from nutriroll.db.repositories.profile import UserProfileRepository
from nutriroll.db.session import get_session
from nutriroll.domain.llm_config import (
    LLMConfig,
    LLMKeyValidationError,
    StoredLLMConfig,
    encrypt_api_key,
    hash_api_key,
    validate_api_key,
)
from nutriroll.config import get_settings

router = APIRouter(prefix="/v1/me", tags=["profile"])


@router.get("/profile", response_model=UserProfileRead, summary="Get user profile")
async def get_profile(session: AsyncSession = Depends(get_session)) -> UserProfileRead:
    repo = UserProfileRepository(session)
    profile = await repo.get_or_create()
    return UserProfileRead.from_domain(profile)


@router.put("/profile", response_model=UserProfileRead, summary="Update user profile")
async def update_profile(
    payload: UserProfileUpdate, session: AsyncSession = Depends(get_session)
) -> UserProfileRead:
    repo = UserProfileRepository(session)
    saved = await repo.update(payload.to_domain())
    return UserProfileRead.from_domain(saved)


@router.get("/profile/llm", response_model=LLMConfigRead, summary="Get LLM feature settings")
async def get_profile_llm(session: AsyncSession = Depends(get_session)) -> LLMConfigRead:
    repo = UserProfileRepository(session)
    config = await repo.get_llm_config()
    return LLMConfigRead.from_domain(config)


@router.put("/profile/llm", response_model=LLMConfigRead, summary="Update LLM feature settings")
async def update_profile_llm(
    payload: LLMConfigUpdate, session: AsyncSession = Depends(get_session)
) -> LLMConfigRead:
    repo = UserProfileRepository(session)
    current = await repo.get_stored_llm_config()
    merged = _merge_llm_config(current, payload)
    api_key = payload.api_key
    settings = get_settings()
    if api_key is not None:
        candidate = api_key.strip()
        if candidate:
            try:
                await validate_api_key(
                    provider=merged.config.provider,  # type: ignore[arg-type]
                    model=merged.config.model,
                    api_key=candidate,
                    settings=settings,
                    timeout_seconds=5.0,
                )
            except LLMKeyValidationError as exc:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "LLM_KEY_INVALID", "message": str(exc)},
                ) from exc
            merged = StoredLLMConfig(
                config=LLMConfig(
                    enabled_features=list(merged.config.enabled_features),
                    provider=merged.config.provider,
                    model=merged.config.model,
                    api_key_set=True,
                ),
                api_key_hash=hash_api_key(candidate, settings.llm_key_master),
                encrypted_api_key=encrypt_api_key(candidate, settings.llm_key_master),
            )
        else:
            merged = StoredLLMConfig(
                config=LLMConfig(
                    enabled_features=list(merged.config.enabled_features),
                    provider=merged.config.provider,
                    model=merged.config.model,
                    api_key_set=False,
                ),
                api_key_hash=None,
                encrypted_api_key=None,
            )
    saved = await repo.update_llm_config(merged)
    return LLMConfigRead.from_domain(saved)


def _merge_llm_config(current: StoredLLMConfig, payload: LLMConfigUpdate) -> StoredLLMConfig:
    partial = payload.to_partial()
    config = LLMConfig(
        enabled_features=list(partial.get("enabled_features", current.config.enabled_features)),
        provider=str(partial.get("provider", current.config.provider)),
        model=str(partial.get("model", current.config.model) or current.config.model),
        api_key_set=current.config.api_key_set,
    )
    return StoredLLMConfig(
        config=config,
        api_key_hash=current.api_key_hash,
        encrypted_api_key=current.encrypted_api_key,
    )


__all__ = ["router"]
