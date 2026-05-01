"""Singleton user profile repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.db.models.profile import UserProfileRow
from nutriroll.domain.equipment import Equipment
from nutriroll.domain.profile import UserProfile
from nutriroll.domain.roll import MacroMode

PROFILE_ID = 1
_WEEKLY_RECAP_FLAG_KEY = "__llm_weekly_recap_enabled"


def _to_domain(row: UserProfileRow) -> UserProfile:
    raw_allergens = row.allergens or []
    raw_weights_payload = dict(row.roll_weights or {})
    raw_recap_flag = raw_weights_payload.pop(_WEEKLY_RECAP_FLAG_KEY, 0.0)
    try:
        recap_enabled = bool(float(raw_recap_flag))
    except (TypeError, ValueError):
        recap_enabled = bool(raw_recap_flag)
    raw_weights: dict[str, float] = {k: float(v) for k, v in raw_weights_payload.items()}
    raw_targets = row.default_macro_targets or {}
    target_triples: list[tuple[str, float, MacroMode]] = []
    for name, payload in raw_targets.items():
        if not isinstance(payload, dict):
            continue
        payload_dict: dict[str, Any] = dict(payload)  # type: ignore[arg-type]
        value = float(payload_dict.get("value", 0.0))
        raw_mode = str(payload_dict.get("mode", "target"))
        mode: MacroMode = (
            raw_mode  # type: ignore[assignment]
            if raw_mode in ("target", "min", "max")
            else "target"
        )
        target_triples.append((str(name), value, mode))
    raw_equipment = row.equipment or []
    equipment_tuple: tuple[Equipment, ...] = ()
    if raw_equipment:
        seen: set[Equipment] = set()
        accepted: list[Equipment] = []
        for value in raw_equipment:
            try:
                e = Equipment(str(value))
            except ValueError:
                # Forward-compat: silently drop unknown equipment values
                # rather than blowing up an existing profile load.
                continue
            if e in seen:
                continue
            seen.add(e)
            accepted.append(e)
        equipment_tuple = tuple(accepted)
    return UserProfile(
        dietary_mode=row.dietary_mode,
        allergens=tuple(str(a) for a in raw_allergens),
        default_time_budget_min=row.default_time_budget_min,
        goal=row.goal,
        locale=row.locale,
        onboarded=row.onboarded,
        roll_weights=tuple(raw_weights.items()),
        default_macro_targets=tuple(target_triples),
        equipment=equipment_tuple,
        llm_weekly_recap_enabled=recap_enabled,
    )


class UserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> UserProfile:
        row = await self._session.get(UserProfileRow, PROFILE_ID)
        if row is None:
            row = UserProfileRow(id=PROFILE_ID, allergens=[])
            self._session.add(row)
            await self._session.commit()
            await self._session.refresh(row)
        return _to_domain(row)

    async def update(self, profile: UserProfile) -> UserProfile:
        weights_json: dict[str, float] = dict(profile.roll_weights)
        if profile.llm_weekly_recap_enabled:
            weights_json[_WEEKLY_RECAP_FLAG_KEY] = 1.0
        targets_json: dict[str, dict[str, str | float]] | None = (
            {
                name: {"value": value, "mode": mode}
                for name, value, mode in profile.default_macro_targets
            }
            if profile.default_macro_targets
            else None
        )
        equipment_json: list[str] | None = (
            [e.value for e in profile.equipment] if profile.equipment else None
        )
        row = await self._session.get(UserProfileRow, PROFILE_ID)
        if row is None:
            row = UserProfileRow(id=PROFILE_ID)
            self._session.add(row)
        row.dietary_mode = profile.dietary_mode
        row.allergens = list(profile.allergens)
        row.default_time_budget_min = profile.default_time_budget_min
        row.goal = profile.goal
        row.locale = profile.locale
        row.onboarded = profile.onboarded
        row.roll_weights = weights_json or None
        row.default_macro_targets = targets_json
        row.equipment = equipment_json
        await self._session.commit()
        await self._session.refresh(row)
        return _to_domain(row)
