"""Tests for ``domain/category_meta.py`` env-var override (M4 / M8)."""

from __future__ import annotations

import importlib

import pytest


def test_env_override_merges_partial_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "NUTRIROLL_BALANCED_TARGETS_JSON",
        '{"base": {"kcal": 999.0, "fiber_g": 7.0}}',
    )
    from nutriroll.domain import category_meta

    reloaded = importlib.reload(category_meta)
    try:
        targets = reloaded.BALANCED_TARGETS
        base = targets[reloaded.Category.BASE]
        assert base["kcal"] == 999.0
        assert base["fiber_g"] == 7.0
        assert base["protein_g"] == 4.0
        veg = targets[reloaded.Category.VEGETABLE]
        assert veg["kcal"] == 35.0
    finally:
        # Restore defaults. We deliberately do NOT reload `roll`: doing so
        # creates a fresh `EmptyCandidatePoolError` class and breaks
        # `pytest.raises` checks in other test modules.
        monkeypatch.delenv("NUTRIROLL_BALANCED_TARGETS_JSON")
        importlib.reload(category_meta)


def test_env_override_invalid_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NUTRIROLL_BALANCED_TARGETS_JSON", "{not json")
    from nutriroll.domain import category_meta

    try:
        with pytest.raises(ValueError, match="not valid JSON"):
            importlib.reload(category_meta)
    finally:
        monkeypatch.delenv("NUTRIROLL_BALANCED_TARGETS_JSON")
        importlib.reload(category_meta)
