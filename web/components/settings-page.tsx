"use client";

import { Download, Monitor, Moon, RotateCcw, Save, Sun } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api/client";
import type { ComponentRead } from "@/lib/components/types";
import {
  COMMON_ALLERGENS,
  DIETARY_MODES,
  type DietaryMode,
  type UserProfileRead,
} from "@/lib/profile/types";
import {
  DEFAULT_WEIGHTS,
  WEIGHT_KEYS,
  type WeightKey,
  clearWeights,
  loadWeights,
  saveWeights,
} from "@/lib/settings/weights";

type ThemeMode = "system" | "light" | "dark";

const THEME_KEY = "nutriroll.theme";

function readTheme(): ThemeMode {
  if (typeof window === "undefined") return "system";
  const v = window.localStorage.getItem(THEME_KEY);
  return v === "light" || v === "dark" ? v : "system";
}

function applyTheme(mode: ThemeMode): void {
  if (typeof document === "undefined") return;
  if (mode === "system") {
    document.documentElement.removeAttribute("data-theme");
    window.localStorage.removeItem(THEME_KEY);
  } else {
    document.documentElement.setAttribute("data-theme", mode);
    window.localStorage.setItem(THEME_KEY, mode);
  }
}

export function SettingsPage() {
  const t = useTranslations("settings");
  const tDietary = useTranslations("roll.dietary");

  const [profile, setProfile] = useState<UserProfileRead | null>(null);
  const [dietaryMode, setDietaryMode] = useState<DietaryMode>("");
  const [allergens, setAllergens] = useState<Set<string>>(() => new Set());
  const [timeBudget, setTimeBudget] = useState<string>("");
  const [goal, setGoal] = useState<string>("");
  const [theme, setTheme] = useState<ThemeMode>("system");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [weights, setWeights] = useState<Record<WeightKey, number>>(() => ({
    ...DEFAULT_WEIGHTS,
  }));
  const [blacklisted, setBlacklisted] = useState<ComponentRead[]>([]);
  const [blacklistLoading, setBlacklistLoading] = useState<boolean>(true);

  const loadBlacklist = useCallback(async () => {
    setBlacklistLoading(true);
    const result = await apiClient.GET("/v1/components", {
      params: { query: { include_blacklisted: true, limit: 1000, offset: 0 } },
    });
    if (result.data) {
      setBlacklisted(result.data.items.filter((c) => c.blacklisted));
    }
    setBlacklistLoading(false);
  }, []);

  useEffect(() => {
    setTheme(readTheme());
    void loadBlacklist();
    let cancelled = false;
    void (async () => {
      const result = await apiClient.GET("/v1/me/profile");
      if (cancelled || !result.data) return;
      const p = result.data;
      setProfile(p);
      setDietaryMode(p.dietary_mode);
      setAllergens(new Set(p.allergens));
      setTimeBudget(p.default_time_budget_min?.toString() ?? "");
      setGoal(p.goal);
      // Seed weights from profile if present; fall back to localStorage.
      const profileWeights = p.roll_weights ?? {};
      const merged = { ...loadWeights(), ...profileWeights } as Record<WeightKey, number>;
      setWeights({ ...DEFAULT_WEIGHTS, ...merged });
    })();
    return () => {
      cancelled = true;
    };
  }, [loadBlacklist]);

  const updateWeight = (key: WeightKey, value: number) => {
    const next = { ...weights, [key]: value };
    setWeights(next);
    saveWeights(next); // keep localStorage in sync for offline / roll page
    if (profile) {
      // Fire-and-forget persist to profile — ignore transient failures.
      void apiClient.PUT("/v1/me/profile", {
        body: {
          dietary_mode: dietaryMode,
          allergens: [...allergens],
          default_time_budget_min:
            timeBudget.trim() === "" ? null : Number.parseInt(timeBudget, 10),
          goal: goal.trim(),
          locale: profile.locale,
          onboarded: profile.onboarded || true,
          roll_weights: next,
        },
      });
    }
  };

  const resetWeights = () => {
    clearWeights();
    setWeights({ ...DEFAULT_WEIGHTS });
    if (profile) {
      void apiClient.PUT("/v1/me/profile", {
        body: {
          dietary_mode: dietaryMode,
          allergens: [...allergens],
          default_time_budget_min:
            timeBudget.trim() === "" ? null : Number.parseInt(timeBudget, 10),
          goal: goal.trim(),
          locale: profile.locale,
          onboarded: profile.onboarded || true,
          roll_weights: {},
        },
      });
    }
  };

  const restoreFromBlacklist = async (component: ComponentRead) => {
    // Component endpoints are PUT-replace, not PATCH — rebuild full payload.
    const result = await apiClient.PUT("/v1/components/{component_id}", {
      params: { path: { component_id: component.id } },
      body: {
        category: component.category,
        name: component.name,
        image_url: component.image_url ?? null,
        default_portion: component.default_portion,
        macros_per_100g: component.macros_per_100g,
        default_cooking_method: component.default_cooking_method,
        cooking_methods: component.cooking_methods,
        flavor_tags: component.flavor_tags ?? [],
        dietary_tags: component.dietary_tags ?? [],
        allergens: component.allergens ?? [],
        shelf_life_days: component.shelf_life_days ?? null,
        seasonal_availability: component.seasonal_availability ?? null,
        blacklisted: false,
      },
    });
    if (result.data) {
      setBlacklisted((prev) => prev.filter((c) => c.id !== component.id));
    }
  };

  const onThemeChange = (next: ThemeMode) => {
    setTheme(next);
    applyTheme(next);
  };

  const toggleAllergen = (a: string) => {
    setAllergens((prev) => {
      const next = new Set(prev);
      if (next.has(a)) next.delete(a);
      else next.add(a);
      return next;
    });
  };

  const saveProfile = async () => {
    if (!profile) return;
    setSaving(true);
    setError(null);
    const tb = timeBudget.trim();
    const tbNum = tb === "" ? null : Number.parseInt(tb, 10);
    if (tb !== "" && (Number.isNaN(tbNum) || (tbNum ?? 0) <= 0)) {
      setError(t("errors.timeBudget"));
      setSaving(false);
      return;
    }
    const result = await apiClient.PUT("/v1/me/profile", {
      body: {
        dietary_mode: dietaryMode,
        allergens: [...allergens],
        default_time_budget_min: tbNum,
        goal: goal.trim(),
        locale: profile.locale,
        onboarded: profile.onboarded || true,
        roll_weights: weights,
      },
    });
    setSaving(false);
    if (!result.data) {
      setError(`HTTP ${result.response.status}`);
      return;
    }
    setProfile(result.data);
    setSavedAt(Date.now());
  };

  const exportData = async () => {
    setExporting(true);
    const [profileR, componentsR, savedR, plannedR, historyR] = await Promise.all([
      apiClient.GET("/v1/me/profile"),
      apiClient.GET("/v1/components"),
      apiClient.GET("/v1/saved"),
      apiClient.GET("/v1/planned"),
      apiClient.GET("/v1/history"),
    ]);
    const bundle = {
      exported_at: new Date().toISOString(),
      app: "nutriroll",
      version: 1,
      profile: profileR.data ?? null,
      components: componentsR.data ?? null,
      saved: savedR.data ?? null,
      planned: plannedR.data ?? null,
      history: historyR.data ?? null,
    };
    const blob = new Blob([JSON.stringify(bundle, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `nutriroll-export-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setExporting(false);
  };

  return (
    <div className="grid gap-4">
      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle>{t("profile.title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <label className="grid gap-1.5 text-sm font-medium">
            {t("profile.dietary")}
            <Select
              value={dietaryMode}
              onChange={(e) => setDietaryMode(e.target.value as DietaryMode)}
            >
              {DIETARY_MODES.map((m) => (
                <option key={m || "any"} value={m}>
                  {tDietary(m === "" ? "any" : (m as Exclude<DietaryMode, "">))}
                </option>
              ))}
            </Select>
          </label>

          <fieldset className="grid gap-2">
            <legend className="text-sm font-medium">{t("profile.allergens")}</legend>
            <div className="flex flex-wrap gap-2">
              {COMMON_ALLERGENS.map((a) => {
                const active = allergens.has(a);
                return (
                  <button
                    key={a}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleAllergen(a)}
                    className={
                      active
                        ? "rounded-full bg-[color:var(--color-brand)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-brand-fg)] transition active:scale-95"
                        : "rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-1.5 text-xs font-medium transition hover:border-[color:var(--color-brand)] active:scale-95"
                    }
                  >
                    {a}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <label className="grid gap-1.5 text-sm font-medium">
            {t("profile.timeBudget")}
            <Input
              type="number"
              inputMode="numeric"
              min={1}
              value={timeBudget}
              onChange={(e) => setTimeBudget(e.target.value)}
              placeholder={t("profile.timeBudgetPlaceholder")}
            />
          </label>

          <label className="grid gap-1.5 text-sm font-medium">
            {t("profile.goal")}
            <Input
              type="text"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder={t("profile.goalPlaceholder")}
            />
          </label>

          {error && (
            <output
              aria-live="polite"
              className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
            >
              {error}
            </output>
          )}

          <div className="flex items-center justify-between">
            <output aria-live="polite" className="text-xs text-[color:var(--color-muted)]">
              {savedAt ? t("profile.saved") : ""}
            </output>
            <Button type="button" onClick={() => void saveProfile()} disabled={saving || !profile}>
              {saving ? t("profile.saving") : t("profile.save")}
              <Save aria-hidden size={14} />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle>{t("appearance.title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <p className="text-sm text-[color:var(--color-muted)]">{t("appearance.body")}</p>
          <div className="grid grid-cols-3 gap-2">
            {(
              [
                ["system", Monitor],
                ["light", Sun],
                ["dark", Moon],
              ] as const
            ).map(([mode, Icon]) => {
              const active = theme === mode;
              return (
                <button
                  key={mode}
                  type="button"
                  aria-pressed={active}
                  onClick={() => onThemeChange(mode)}
                  className={
                    active
                      ? "flex flex-col items-center gap-1 rounded-2xl border-2 border-[color:var(--color-brand)] bg-[color:var(--color-brand-soft)] p-3 text-xs font-medium"
                      : "flex flex-col items-center gap-1 rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] p-3 text-xs transition hover:border-[color:var(--color-brand)]"
                  }
                >
                  <Icon aria-hidden size={18} />
                  {t(`appearance.${mode}`)}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>{t("recommendations.title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <p className="text-sm text-[color:var(--color-muted)]">{t("recommendations.body")}</p>
          <div className="grid gap-3">
            {WEIGHT_KEYS.map((key) => (
              <label key={key} className="grid gap-1.5 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{t(`recommendations.weights.${key}`)}</span>
                  <span className="tabular-nums text-xs text-[color:var(--color-muted)]">
                    {weights[key].toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={weights[key]}
                  onChange={(e) => updateWeight(key, Number.parseFloat(e.target.value))}
                  className="w-full"
                />
              </label>
            ))}
          </div>
          <div className="flex justify-end">
            <Button type="button" variant="outline" size="sm" onClick={resetWeights}>
              {t("recommendations.reset")}
              <RotateCcw aria-hidden size={14} />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Blacklist */}
      <Card>
        <CardHeader>
          <CardTitle>{t("blacklist.title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <p className="text-sm text-[color:var(--color-muted)]">{t("blacklist.body")}</p>
          {blacklistLoading ? (
            <output aria-live="polite" className="text-sm text-[color:var(--color-muted)]">
              {t("blacklist.loading")}
            </output>
          ) : blacklisted.length === 0 ? (
            <p className="text-sm text-[color:var(--color-muted)]">{t("blacklist.empty")}</p>
          ) : (
            <ul className="grid gap-2">
              {blacklisted.map((c) => (
                <li
                  key={c.id}
                  className="flex items-center justify-between gap-2 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-2"
                >
                  <span className="text-sm">{c.name}</span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => void restoreFromBlacklist(c)}
                  >
                    {t("blacklist.restore")}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Data */}
      <Card>
        <CardHeader>
          <CardTitle>{t("data.title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <p className="text-sm text-[color:var(--color-muted)]">{t("data.body")}</p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => void exportData()}
              disabled={exporting}
            >
              {exporting ? t("data.exporting") : t("data.export")}
              <Download aria-hidden size={14} />
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                if (typeof window !== "undefined") {
                  window.localStorage.removeItem(THEME_KEY);
                  document.documentElement.removeAttribute("data-theme");
                  setTheme("system");
                }
              }}
            >
              {t("data.resetLocal")}
              <RotateCcw aria-hidden size={14} />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* About */}
      <Card>
        <CardHeader>
          <CardTitle>{t("about.title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-1 text-sm text-[color:var(--color-muted)]">
          <p>{t("about.version", { version: "0.10.0" })}</p>
          <p>{t("about.tagline")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
