"""Weekly recap aggregation + optional LLM summary generation."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nutriroll.config import get_settings
from nutriroll.db.models.component import ComponentRow
from nutriroll.db.models.history import HistoryEventRow
from nutriroll.db.models.rating import RatingRow
from nutriroll.db.models.store import StoreRow, SupermarketPriceRow
from nutriroll.db.repositories.profile import UserProfileRepository
from nutriroll.domain.llm_config import (
    KNOWN_FEATURES,
    LLMConfig,
    LLMRuntimeConfig,
    perform_llm_request,
    resolve_runtime_llm_config,
)
from nutriroll.domain.profile import UserProfile
from nutriroll.logging import get_logger

log = get_logger("nutriroll.domain.weekly_recap")


class WeeklyRecapLLMError(RuntimeError):
    """Raised when the optional LLM copy-generation step fails."""


@dataclass(frozen=True, slots=True)
class RecapStats:
    meals_cooked: int
    spent_eur: float
    avg_kcal: float | None
    top_components: tuple[str, ...]
    longest_streak: int
    new_foods_tried: int


@dataclass(frozen=True, slots=True)
class Recap:
    summary_text: str
    stats: RecapStats
    suggestions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _MealEstimate:
    component_ids: tuple[UUID, ...]
    component_names: tuple[str, ...]
    estimated_kcal: float | None
    estimated_cost_eur: float | None
    cooked_on: date


class WeeklyRecapGenerator:
    """Aggregate one week of meal activity and optionally add LLM-written copy."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        runtime_config: LLMRuntimeConfig | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        settings = get_settings()
        self._session = session
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

    async def generate_recap(self, user_id: str, week_start: date) -> Recap:
        """Build a recap for one calendar week.

        `user_id` is currently used for cache/prompt context only. The current
        app branch stores one installation-scoped history/profile, so the DB
        query is not yet user-partitioned.
        """

        self.runtime_config.require_feature("weekly_recaps")
        profile = await UserProfileRepository(self._session).get_or_create()
        week_end = week_start + timedelta(days=7)
        week_events = await self._list_history_events(start=week_start, end=week_end)
        previous_events = await self._list_history_events(end=week_start)
        ratings = await self._list_ratings(start=week_start, end=week_end)

        cooked_events = [event for event in week_events if event.kind == "cooked"]
        cooked_component_ids = self._collect_component_ids(cooked_events)
        prior_component_ids = self._collect_component_ids(previous_events)
        component_rows = await self._load_components(cooked_component_ids)
        price_rows = await self._load_prices(cooked_component_ids)
        meals = [
            self._estimate_meal(event, component_rows=component_rows, price_rows=price_rows)
            for event in cooked_events
        ]

        stats = self._build_stats(meals, prior_component_ids=prior_component_ids)
        fallback_suggestions = self._build_fallback_suggestions(stats)

        if stats.meals_cooked == 0:
            return Recap(
                summary_text=(
                    "No meals were cooked this week yet. Roll one bowl next week and "
                    "your recap will start filling in automatically."
                ),
                stats=stats,
                suggestions=fallback_suggestions,
            )

        try:
            summary_text, suggestions = await self._generate_llm_copy(
                user_id=user_id,
                week_start=week_start,
                week_end=week_end - timedelta(days=1),
                profile=profile,
                stats=stats,
                meals=meals,
                average_rating=self._average_rating(ratings),
            )
            return Recap(
                summary_text=summary_text,
                stats=stats,
                suggestions=suggestions or fallback_suggestions,
            )
        except WeeklyRecapLLMError as exc:
            log.warning("weekly_recap_llm_failed", error=str(exc), model=self.model)
            return Recap(
                summary_text=self._fallback_summary_text(stats, profile),
                stats=stats,
                suggestions=fallback_suggestions,
            )

    async def _list_history_events(
        self, *, start: date | None = None, end: date | None = None
    ) -> list[HistoryEventRow]:
        stmt = select(HistoryEventRow).order_by(HistoryEventRow.created_at.asc())
        if start is not None:
            stmt = stmt.where(HistoryEventRow.created_at >= datetime.combine(start, time.min))
        if end is not None:
            stmt = stmt.where(HistoryEventRow.created_at < datetime.combine(end, time.min))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _list_ratings(self, *, start: date, end: date) -> list[RatingRow]:
        stmt = (
            select(RatingRow)
            .where(RatingRow.created_at >= datetime.combine(start, time.min))
            .where(RatingRow.created_at < datetime.combine(end, time.min))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _load_components(self, component_ids: set[UUID]) -> dict[UUID, ComponentRow]:
        if not component_ids:
            return {}
        result = await self._session.execute(
            select(ComponentRow).where(ComponentRow.id.in_(component_ids))
        )
        return {row.id: row for row in result.scalars().all()}

    async def _load_prices(
        self, component_ids: set[UUID]
    ) -> dict[UUID, tuple[float, bool]]:
        if not component_ids:
            return {}
        store_rows = await self._session.execute(select(StoreRow))
        primary_store_ids = {row.id for row in store_rows.scalars().all() if row.is_primary}
        price_rows = await self._session.execute(
            select(SupermarketPriceRow).where(SupermarketPriceRow.component_id.in_(component_ids))
        )
        chosen: dict[UUID, tuple[float, bool]] = {}
        for row in price_rows.scalars().all():
            if row.pack_size <= 0:
                continue
            price_per_unit = row.pack_price / row.pack_size
            current = chosen.get(row.component_id)
            is_primary = row.store_id in primary_store_ids
            if current is None:
                chosen[row.component_id] = (price_per_unit, is_primary)
                continue
            current_price, current_is_primary = current
            if (is_primary and not current_is_primary) or (
                is_primary == current_is_primary and price_per_unit < current_price
            ):
                chosen[row.component_id] = (price_per_unit, is_primary)
        return chosen

    @staticmethod
    def _collect_component_ids(events: list[HistoryEventRow]) -> set[UUID]:
        component_ids: set[UUID] = set()
        for event in events:
            for item in WeeklyRecapGenerator._payload_components(event.payload):
                component_id = WeeklyRecapGenerator._parse_uuid(item.get("id"))
                if component_id is not None:
                    component_ids.add(component_id)
        return component_ids

    def _estimate_meal(
        self,
        event: HistoryEventRow,
        *,
        component_rows: dict[UUID, ComponentRow],
        price_rows: dict[UUID, tuple[float, bool]],
    ) -> _MealEstimate:
        component_ids: list[UUID] = []
        component_names: list[str] = []
        estimated_kcal = self._coerce_float((event.payload or {}).get("estimated_total_kcal"))
        estimated_cost = self._coerce_float((event.payload or {}).get("estimated_cost_eur"))

        kcal_parts: list[float] = []
        cost_parts: list[float] = []
        for item in self._payload_components(event.payload):
            name = str(item.get("name", "")).strip()
            if name:
                component_names.append(name)
            component_id = self._parse_uuid(item.get("id"))
            if component_id is None:
                continue
            component_ids.append(component_id)
            row = component_rows.get(component_id)
            if row is None:
                continue
            if estimated_kcal is None:
                kcal_piece = self._estimate_component_kcal(row)
                if kcal_piece is not None:
                    kcal_parts.append(kcal_piece)
            if estimated_cost is None:
                price = price_rows.get(component_id)
                if price is not None:
                    cost_parts.append(self._estimate_component_cost(row, price_per_unit=price[0]))

        if estimated_kcal is None and kcal_parts:
            estimated_kcal = sum(kcal_parts)
        if estimated_cost is None and cost_parts:
            estimated_cost = sum(cost_parts)

        created_at = event.created_at or datetime.combine(date.today(), time.min)
        return _MealEstimate(
            component_ids=tuple(component_ids),
            component_names=tuple(component_names),
            estimated_kcal=estimated_kcal,
            estimated_cost_eur=estimated_cost,
            cooked_on=created_at.date(),
        )

    @staticmethod
    def _build_stats(meals: list[_MealEstimate], *, prior_component_ids: set[UUID]) -> RecapStats:
        top_counter: Counter[str] = Counter()
        seen_this_week: set[UUID] = set()
        kcal_values: list[float] = []
        cost_values: list[float] = []
        cooked_days = sorted({meal.cooked_on for meal in meals})

        for meal in meals:
            top_counter.update(name for name in meal.component_names if name)
            seen_this_week.update(meal.component_ids)
            if meal.estimated_kcal is not None:
                kcal_values.append(meal.estimated_kcal)
            if meal.estimated_cost_eur is not None:
                cost_values.append(meal.estimated_cost_eur)

        avg_kcal = round(sum(kcal_values) / len(kcal_values), 1) if kcal_values else None
        spent_eur = round(sum(cost_values), 2) if cost_values else 0.0
        top_components = tuple(name for name, _count in top_counter.most_common(3))
        new_foods_tried = len(seen_this_week - prior_component_ids)

        streak = 0
        longest_streak = 0
        previous_day: date | None = None
        for current_day in cooked_days:
            if previous_day is not None and current_day == previous_day + timedelta(days=1):
                streak += 1
            else:
                streak = 1
            previous_day = current_day
            longest_streak = max(longest_streak, streak)

        return RecapStats(
            meals_cooked=len(meals),
            spent_eur=spent_eur,
            avg_kcal=avg_kcal,
            top_components=top_components,
            longest_streak=longest_streak,
            new_foods_tried=new_foods_tried,
        )

    @staticmethod
    def _estimate_component_kcal(row: ComponentRow) -> float | None:
        if row.default_portion_unit not in {"g", "ml"}:
            return None
        kcal_per_100g = float((row.macros or {}).get("kcal", 0.0))
        return kcal_per_100g * float(row.default_portion_value) / 100.0

    @staticmethod
    def _estimate_component_cost(row: ComponentRow, *, price_per_unit: float) -> float:
        if row.default_portion_unit not in {"g", "ml"}:
            return 0.0
        return price_per_unit * float(row.default_portion_value)

    @staticmethod
    def _payload_components(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
        raw_items = (payload or {}).get("components")
        if not isinstance(raw_items, list):
            return []
        items: list[dict[str, Any]] = []
        for raw in raw_items:
            if isinstance(raw, dict):
                items.append(raw)
        return items

    @staticmethod
    def _parse_uuid(value: Any) -> UUID | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return UUID(value)
        except ValueError:
            return None

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _average_rating(ratings: list[RatingRow]) -> float | None:
        if not ratings:
            return None
        return round(sum(float(row.score) for row in ratings) / len(ratings), 2)

    @staticmethod
    def _build_fallback_suggestions(stats: RecapStats) -> tuple[str, ...]:
        suggestions: list[str] = []
        if stats.meals_cooked == 0:
            suggestions.append("Start with one easy bowl to seed next week's recap.")
        if stats.new_foods_tried == 0 and stats.meals_cooked > 0:
            suggestions.append("Try one new vegetable or topping next week to widen variety.")
        if stats.avg_kcal is not None and stats.avg_kcal > 700:
            suggestions.append("Balance one heavier bowl with a lighter, veg-forward lunch.")
        elif stats.avg_kcal is not None and stats.avg_kcal < 450:
            suggestions.append("Add a sturdier base or extra protein to keep meals more filling.")
        if stats.spent_eur > 0 and stats.meals_cooked > 0:
            per_meal = stats.spent_eur / stats.meals_cooked
            if per_meal > 4.5:
                suggestions.append("Swap one premium topping for a pantry staple to trim cost.")
        if stats.longest_streak >= 3:
            suggestions.append("Keep the streak going with a prep-friendly bowl at the start of the week.")
        if not suggestions:
            suggestions.append("Repeat your best bowl once and tweak one component for variety.")
        return tuple(suggestions[:3])

    @staticmethod
    def _fallback_summary_text(stats: RecapStats, profile: UserProfile) -> str:
        goal = profile.goal.strip()
        goal_suffix = f" while staying aligned with your goal of {goal}" if goal else ""
        kcal_part = (
            f" at an average of {stats.avg_kcal:.0f} kcal per cooked meal"
            if stats.avg_kcal is not None
            else ""
        )
        spend_part = (
            f" and an estimated EUR {stats.spent_eur:.2f} spent" if stats.spent_eur > 0 else ""
        )
        meal_label = "meal" if stats.meals_cooked == 1 else "meals"
        return (
            f"You cooked {stats.meals_cooked} {meal_label} this week"
            f"{kcal_part}{spend_part}{goal_suffix}. "
            f"Your longest cooking streak was {stats.longest_streak} day"
            f"{'' if stats.longest_streak == 1 else 's'}, and you tried {stats.new_foods_tried} new foods."
        )

    async def _generate_llm_copy(
        self,
        *,
        user_id: str,
        week_start: date,
        week_end: date,
        profile: UserProfile,
        stats: RecapStats,
        meals: list[_MealEstimate],
        average_rating: float | None,
    ) -> tuple[str, tuple[str, ...]]:
        if not self.api_key.strip():
            raise WeeklyRecapLLMError("LLM features are not configured on this server.")

        try:
            llm_response = await perform_llm_request(
                self.runtime_config,
                messages=[
                    {"role": "system", "content": self._system_prompt(profile.locale)},
                    {
                        "role": "user",
                        "content": self._user_prompt(
                            user_id=user_id,
                            week_start=week_start,
                            week_end=week_end,
                            profile=profile,
                            stats=stats,
                            meals=meals,
                            average_rating=average_rating,
                        ),
                    },
                ],
                temperature=0.4,
                timeout_seconds=self.timeout_seconds,
                response_format_json=True,
            )
        except httpx.HTTPStatusError as exc:
            raise WeeklyRecapLLMError(self._http_error_message(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise WeeklyRecapLLMError("The AI recap service is unavailable right now.") from exc

        if llm_response.refusal:
            raise WeeklyRecapLLMError("The AI recap service declined this request.")
        parsed = self._parse_llm_payload(llm_response.text)
        summary_text = str(parsed.get("summary_text", "")).strip()
        suggestions = parsed.get("suggestions", [])
        if not summary_text:
            raise WeeklyRecapLLMError("The AI recap service returned malformed recap text.")
        normalized_suggestions = tuple(
            str(item).strip()
            for item in suggestions
            if isinstance(item, str) and str(item).strip()
        )
        return summary_text, normalized_suggestions[:3]

    @staticmethod
    def _system_prompt(locale: str) -> str:
        return (
            "You write weekly meal recaps for a bowl-planning app.\n"
            "Return only valid JSON with this shape:\n"
            '{"summary_text": string, "suggestions": [string, string, string]}\n'
            "Rules:\n"
            "- Keep summary_text to 2-4 sentences and one short paragraph.\n"
            "- Be friendly, concrete, and personalized.\n"
            "- Mention cost, nutrition, streaks, or variety only when data exists.\n"
            "- Suggestions must be specific, practical, and short.\n"
            f"- Write in locale {locale or 'en'}.\n"
            "- Do not use markdown."
        )

    @staticmethod
    def _user_prompt(
        *,
        user_id: str,
        week_start: date,
        week_end: date,
        profile: UserProfile,
        stats: RecapStats,
        meals: list[_MealEstimate],
        average_rating: float | None,
    ) -> str:
        meal_examples = [
            {
                "components": list(meal.component_names),
                "estimated_kcal": meal.estimated_kcal,
                "estimated_cost_eur": meal.estimated_cost_eur,
                "cooked_on": meal.cooked_on.isoformat(),
            }
            for meal in meals[:5]
        ]
        return json.dumps(
            {
                "user_id": user_id,
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "profile": {
                    "goal": profile.goal,
                    "dietary_mode": profile.dietary_mode,
                    "locale": profile.locale,
                },
                "stats": {
                    "meals_cooked": stats.meals_cooked,
                    "spent_eur": stats.spent_eur,
                    "avg_kcal": stats.avg_kcal,
                    "top_components": list(stats.top_components),
                    "longest_streak": stats.longest_streak,
                    "new_foods_tried": stats.new_foods_tried,
                    "avg_rating": average_rating,
                },
                "meal_examples": meal_examples,
            },
            ensure_ascii=True,
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
    def _parse_llm_payload(raw_output: str) -> dict[str, Any]:
        candidate = raw_output.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 3:
                candidate = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise WeeklyRecapLLMError("The AI recap service returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise WeeklyRecapLLMError("The AI recap service returned an invalid payload.")
        return payload

    @staticmethod
    def _http_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()
            detail = payload.get("detail")
            if isinstance(detail, str) and detail.strip():
                return detail.strip()
        return f"The AI recap service returned HTTP {response.status_code}."


__all__ = ["Recap", "RecapStats", "WeeklyRecapGenerator", "WeeklyRecapLLMError"]
