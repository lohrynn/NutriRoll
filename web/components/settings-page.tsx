"use client";

import { Download, Monitor, Moon, RotateCcw, Save, Sun } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api/client";
import { useDefaultEquipment, useEquipment } from "@/lib/components/meta";
import type { ComponentRead, Equipment } from "@/lib/components/types";
import {
  COMMON_ALLERGENS,
  DIETARY_MODES,
  type DietaryMode,
  LLM_FEATURES,
  LLM_PROVIDERS,
  type LLMConfigRead,
  type LLMConfigUpdate,
  type LLMFeature,
  type LLMProvider,
  type UserProfileRead,
  type UserProfileUpdate,
} from "@/lib/profile/types";
import {
  DEFAULT_WEIGHTS,
  WEIGHT_KEYS,
  type WeightKey,
  clearWeights,
  loadWeights,
  saveWeights,
} from "@/lib/settings/weights";

type MacroMode = "target" | "min" | "max";
const MACRO_KEYS = ["kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"] as const;
type MacroKey = (typeof MACRO_KEYS)[number];
type MacroTargetsState = Partial<Record<MacroKey, { value: number; mode: MacroMode }>>;

type ThemeMode = "system" | "light" | "dark";
const DEFAULT_LLM_MODEL = "gpt-4o-mini";
const LLM_FEATURE_LABELS: Record<LLMFeature, string> = {
  component_creation: "Component creation",
  prompt_rolls: "Prompt rolls",
  recipe_polish: "Recipe polish",
  weekly_recaps: "Weekly recaps",
};
const LLM_PROVIDER_LABELS: Record<LLMProvider, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google",
  ollama: "Ollama",
  custom: "Custom",
};

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
  const tMacro = useTranslations("roll.nutritionTargets.macros");
  const tEquipment = useTranslations("settings.equipment");
  const equipmentVocab = useEquipment();
  const defaultEquipmentVocab = useDefaultEquipment();

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
  const [defaultTargets, setDefaultTargets] = useState<MacroTargetsState>({});
  const [targetsSavedAt, setTargetsSavedAt] = useState<number | null>(null);
  const [equipment, setEquipment] = useState<Set<Equipment>>(() => new Set());
  const [equipmentTouched, setEquipmentTouched] = useState(false);
  const [equipmentSavedAt, setEquipmentSavedAt] = useState<number | null>(null);
  const [llmConfig, setLlmConfig] = useState<LLMConfigRead | null>(null);
  const [llmEnabledFeatures, setLlmEnabledFeatures] = useState<Set<LLMFeature>>(() => new Set());
  const [llmProvider, setLlmProvider] = useState<LLMProvider>("openai");
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL);
  const [llmApiKey, setLlmApiKey] = useState("");
  const [llmApiKeySet, setLlmApiKeySet] = useState(false);
  const [llmSaving, setLlmSaving] = useState(false);
  const [llmTesting, setLlmTesting] = useState(false);
  const [llmError, setLlmError] = useState<string | null>(null);
  const [llmSavedAt, setLlmSavedAt] = useState<number | null>(null);
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
      const [profileResult, llmResult] = await Promise.all([
        apiClient.GET("/v1/me/profile"),
        apiClient.GET("/v1/me/profile/llm"),
      ]);
      if (cancelled || !profileResult.data || !llmResult.data) return;
      const p = profileResult.data;
      const llm = llmResult.data;
      setProfile(p);
      setDietaryMode(p.dietary_mode);
      setAllergens(new Set(p.allergens));
      setTimeBudget(p.default_time_budget_min?.toString() ?? "");
      setGoal(p.goal);
      // Seed weights from profile if present; fall back to localStorage.
      const profileWeights = p.roll_weights ?? {};
      const merged = { ...loadWeights(), ...profileWeights } as Record<WeightKey, number>;
      setWeights({ ...DEFAULT_WEIGHTS, ...merged });
      // Seed default macro targets from profile.
      const seed: MacroTargetsState = {};
      const dt = p.default_macro_targets ?? {};
      for (const key of MACRO_KEYS) {
        const t = dt[key];
        if (t) seed[key] = { value: t.value, mode: (t.mode ?? "target") as MacroMode };
      }
      setDefaultTargets(seed);
      // Phase 13. Empty stored equipment = back-compat "all available".
      setEquipment(new Set(p.equipment ?? []));
      setLlmConfig(llm);
      setLlmEnabledFeatures(new Set(llm.enabled_features ?? []));
      setLlmProvider(llm.provider ?? "openai");
      setLlmModel(llm.model || DEFAULT_LLM_MODEL);
      setLlmApiKeySet(llm.api_key_set ?? false);
    })();
    return () => {
      cancelled = true;
    };
  }, [loadBlacklist]);

  const buildProfileBody = useCallback(
    (overrides: Partial<UserProfileUpdate> = {}): UserProfileUpdate | null => {
      if (!profile) return null;
      return {
        dietary_mode: dietaryMode,
        allergens: [...allergens],
        default_time_budget_min: timeBudget.trim() === "" ? null : Number.parseInt(timeBudget, 10),
        goal: goal.trim(),
        locale: profile.locale,
        onboarded: profile.onboarded || true,
        roll_weights: weights,
        default_macro_targets: defaultTargets as Record<string, { value: number; mode: MacroMode }>,
        equipment: [...equipment],
        llm_weekly_recap_enabled: llmEnabledFeatures.has("weekly_recaps"),
        ...overrides,
      };
    },
    [allergens, defaultTargets, dietaryMode, equipment, goal, llmEnabledFeatures, profile, timeBudget, weights],
  );

  const updateWeight = (key: WeightKey, value: number) => {
    const next = { ...weights, [key]: value };
    setWeights(next);
    saveWeights(next); // keep localStorage in sync for offline / roll page
    if (profile) {
      const body = buildProfileBody({ roll_weights: next });
      if (!body) return;
      // Fire-and-forget persist to profile — ignore transient failures.
      void apiClient.PUT("/v1/me/profile", { body });
    }
  };

  const resetWeights = () => {
    clearWeights();
    setWeights({ ...DEFAULT_WEIGHTS });
    if (profile) {
      const body = buildProfileBody({ roll_weights: {} });
      if (!body) return;
      void apiClient.PUT("/v1/me/profile", { body });
    }
  };

  const saveDefaultTargets = async () => {
    const body = buildProfileBody();
    if (!body) return;
    const result = await apiClient.PUT("/v1/me/profile", { body });
    if (result.data) {
      setProfile(result.data);
      setTargetsSavedAt(Date.now());
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

  const toggleEquipment = (e: Equipment) => {
    setEquipmentTouched(true);
    setEquipment((prev) => {
      const next = new Set(prev);
      if (next.has(e)) next.delete(e);
      else next.add(e);
      return next;
    });
  };

  // Phase 13. New profiles arrive with `equipment: []` (back-compat = "all
  // available"). Once meta loads we seed the chips with the recommended
  // defaults (oven + stovetop + microwave) so the user starts from a
  // realistic baseline. We only seed when the user hasn't touched the chips
  // yet to avoid stomping an explicit empty selection.
  useEffect(() => {
    if (!profile) return;
    if (equipmentTouched) return;
    if ((profile.equipment ?? []).length > 0) return;
    if (defaultEquipmentVocab.length === 0) return;
    setEquipment(new Set(defaultEquipmentVocab));
  }, [profile, equipmentTouched, defaultEquipmentVocab]);

  const saveEquipment = async () => {
    const body = buildProfileBody();
    if (!body) return;
    const result = await apiClient.PUT("/v1/me/profile", { body });
    if (result.data) {
      setProfile(result.data);
      setEquipmentSavedAt(Date.now());
    }
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
    const body = buildProfileBody({ default_time_budget_min: tbNum });
    if (!body) {
      setSaving(false);
      return;
    }
    const result = await apiClient.PUT("/v1/me/profile", { body });
    setSaving(false);
    if (!result.data) {
      setError(`HTTP ${result.response.status}`);
      return;
    }
    setProfile(result.data);
    setSavedAt(Date.now());
  };

  const toggleLlmFeature = (feature: LLMFeature) => {
    setLlmEnabledFeatures((prev) => {
      const next = new Set(prev);
      if (next.has(feature)) next.delete(feature);
      else next.add(feature);
      return next;
    });
  };

  const toggleAllLlmFeatures = () => {
    setLlmEnabledFeatures((prev) =>
      prev.size > 0 ? new Set<LLMFeature>() : new Set<LLMFeature>(LLM_FEATURES),
    );
  };

  const saveLlmSettings = async (options?: { includeApiKey?: boolean }) => {
    const includeApiKey = options?.includeApiKey === true;
    if (!llmConfig) return;
    if (includeApiKey) setLlmTesting(true);
    else setLlmSaving(true);
    setLlmError(null);
    const body: LLMConfigUpdate = {
      enabled_features: [...llmEnabledFeatures],
      provider: llmProvider,
      model: llmModel.trim() || DEFAULT_LLM_MODEL,
      ...(includeApiKey ? { api_key: llmApiKey } : {}),
    };
    const result = await apiClient.PUT("/v1/me/profile/llm", { body });
    if (includeApiKey) setLlmTesting(false);
    else setLlmSaving(false);
    if (!result.data) {
      const detail =
        typeof result.error === "object" &&
        result.error !== null &&
        "detail" in result.error &&
        typeof result.error.detail === "object" &&
        result.error.detail !== null &&
        "message" in result.error.detail
          ? String(result.error.detail.message)
          : `HTTP ${result.response.status}`;
      setLlmError(detail);
      return;
    }
    setLlmConfig(result.data);
    setLlmEnabledFeatures(new Set(result.data.enabled_features ?? []));
    setLlmProvider(result.data.provider ?? "openai");
    setLlmModel(result.data.model || DEFAULT_LLM_MODEL);
    setLlmApiKeySet(result.data.api_key_set ?? false);
    if (includeApiKey) setLlmApiKey("");
    setLlmSavedAt(Date.now());
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

      {/* Default nutrition targets */}
      <Card>
        <CardHeader>
          <CardTitle>{t("defaultNutritionTargets.title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <p className="text-sm text-[color:var(--color-muted)]">
            {t("defaultNutritionTargets.body")}
          </p>
          {MACRO_KEYS.map((key) => {
            const current = defaultTargets[key];
            return (
              <div key={key} className="flex items-center gap-2">
                <span className="flex-1 text-sm">{tMacro(key)}</span>
                <Select
                  aria-label={`${key} mode`}
                  className="h-8 w-14 text-sm"
                  value={current?.mode ?? "target"}
                  onChange={(e) => {
                    const mode = e.target.value as MacroMode;
                    setDefaultTargets((m) => {
                      const existing = m[key];
                      if (!existing) return m;
                      return { ...m, [key]: { ...existing, mode } };
                    });
                  }}
                  disabled={!current}
                >
                  <option value="target">=</option>
                  <option value="min">≥</option>
                  <option value="max">≤</option>
                </Select>
                <Input
                  type="number"
                  min={0}
                  className="h-8 w-24 text-sm"
                  value={current?.value ?? ""}
                  onChange={(e) => {
                    const raw = e.target.value;
                    setDefaultTargets((m) => {
                      if (raw === "") {
                        const next = { ...m };
                        delete next[key];
                        return next;
                      }
                      const value = Math.max(0, Number(raw));
                      return {
                        ...m,
                        [key]: { value, mode: m[key]?.mode ?? "target" },
                      };
                    });
                  }}
                />
              </div>
            );
          })}
          <div className="flex items-center justify-between">
            <output aria-live="polite" className="text-xs text-[color:var(--color-muted)]">
              {targetsSavedAt ? t("defaultNutritionTargets.saved") : ""}
            </output>
            <Button type="button" size="sm" onClick={() => void saveDefaultTargets()}>
              {t("defaultNutritionTargets.save")}
              <Save aria-hidden size={14} />
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("llm.title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <p className="rounded-2xl border border-[color:var(--color-brand)]/20 bg-[color:var(--color-brand-soft)] px-4 py-3 text-sm text-[color:var(--color-brand)]">
            {t("llm.byokBanner")}
          </p>

          <button
            type="button"
            aria-pressed={llmEnabledFeatures.size > 0}
            onClick={toggleAllLlmFeatures}
            className={
              llmEnabledFeatures.size > 0
                ? "flex items-center justify-between rounded-2xl border-2 border-[color:var(--color-brand)] bg-[color:var(--color-brand-soft)] p-3 text-left"
                : "flex items-center justify-between rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] p-3 text-left transition hover:border-[color:var(--color-brand)]"
            }
          >
            <span className="text-sm font-medium">{t("llm.masterToggle")}</span>
            <span className="text-xs font-medium">
              {llmEnabledFeatures.size > 0 ? t("llm.on") : t("llm.off")}
            </span>
          </button>

          <div className="grid gap-2">
            {LLM_FEATURES.map((feature) => {
              const active = llmEnabledFeatures.has(feature);
              return (
                <button
                  key={feature}
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleLlmFeature(feature)}
                  className={
                    active
                      ? "flex items-center justify-between rounded-2xl border-2 border-[color:var(--color-brand)] bg-[color:var(--color-brand-soft)] p-3 text-left"
                      : "flex items-center justify-between rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] p-3 text-left transition hover:border-[color:var(--color-brand)]"
                  }
                >
                  <span className="text-sm font-medium">{LLM_FEATURE_LABELS[feature]}</span>
                  <span className="text-xs font-medium">{active ? t("llm.on") : t("llm.off")}</span>
                </button>
              );
            })}
          </div>

          <label className="grid gap-1.5 text-sm font-medium">
            {t("llm.provider")}
            <Select value={llmProvider} onChange={(e) => setLlmProvider(e.target.value as LLMProvider)}>
              {LLM_PROVIDERS.map((provider) => (
                <option key={provider} value={provider}>
                  {LLM_PROVIDER_LABELS[provider]}
                </option>
              ))}
            </Select>
          </label>

          <label className="grid gap-1.5 text-sm font-medium">
            {t("llm.model")}
            <Input
              type="text"
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              placeholder={DEFAULT_LLM_MODEL}
            />
          </label>

          <label className="grid gap-1.5 text-sm font-medium">
            {t("llm.apiKey")}
            <div className="flex gap-2">
              <Input
                type="password"
                value={llmApiKey}
                onChange={(e) => setLlmApiKey(e.target.value)}
                placeholder={t("llm.apiKeyPlaceholder")}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => void saveLlmSettings({ includeApiKey: true })}
                disabled={llmTesting || llmApiKey.trim() === ""}
              >
                {llmTesting ? t("llm.testing") : t("llm.testConnection")}
              </Button>
            </div>
          </label>

          {llmEnabledFeatures.size > 0 && !llmApiKeySet && (
            <output
              aria-live="polite"
              className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
            >
              {t("llm.apiKeyWarning")}
            </output>
          )}

          {llmError && (
            <output
              aria-live="polite"
              className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
            >
              {llmError}
            </output>
          )}

          <div className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] p-4">
            <div className="text-sm font-medium">{t("llm.disclosureTitle")}</div>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[color:var(--color-muted)]">
              <li>{t("llm.disclosure.componentDescriptions")}</li>
              <li>{t("llm.disclosure.recipeSteps")}</li>
              <li>{t("llm.disclosure.weeklyMealCounts")}</li>
              <li>{t("llm.disclosure.noPersonalInfo")}</li>
            </ul>
          </div>

          <div className="flex items-center justify-between">
            <output aria-live="polite" className="text-xs text-[color:var(--color-muted)]">
              {llmSavedAt ? t("llm.saved") : ""}
            </output>
            <Button
              type="button"
              size="sm"
              onClick={() => void saveLlmSettings()}
              disabled={!llmConfig || llmSaving}
            >
              {llmSaving ? t("profile.saving") : t("llm.save")}
              <Save aria-hidden size={14} />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Equipment (Phase 13) */}
      <Card>
        <CardHeader>
          <CardTitle>{tEquipment("title")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <p className="text-sm text-[color:var(--color-muted)]">{tEquipment("body")}</p>
          {equipmentVocab.length === 0 ? (
            <output aria-live="polite" className="text-sm text-[color:var(--color-muted)]">
              {tEquipment("loading")}
            </output>
          ) : (
            <div className="flex flex-wrap gap-2">
              {equipmentVocab.map((piece) => {
                const active = equipment.has(piece);
                return (
                  <button
                    key={piece}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleEquipment(piece)}
                    className={
                      active
                        ? "rounded-full bg-[color:var(--color-brand)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-brand-fg)] transition active:scale-95"
                        : "rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-1.5 text-xs font-medium transition hover:border-[color:var(--color-brand)] active:scale-95"
                    }
                  >
                    {tEquipment(`pieces.${piece}`)}
                  </button>
                );
              })}
            </div>
          )}
          <div className="flex items-center justify-between">
            <output aria-live="polite" className="text-xs text-[color:var(--color-muted)]">
              {equipmentSavedAt ? tEquipment("saved") : ""}
            </output>
            <Button
              type="button"
              size="sm"
              onClick={() => void saveEquipment()}
              disabled={!profile || equipmentVocab.length === 0}
            >
              {tEquipment("save")}
              <Save aria-hidden size={14} />
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
