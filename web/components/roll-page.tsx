"use client";

import { ChefHat, Dice5, Flame, Salad, Sparkles, Utensils } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api/client";
import type { Category, CookingMethod } from "@/lib/components/types";
import { ROLLED_BOWL_STORAGE_KEY } from "@/lib/recipe/storage";
import { DEFAULT_SLOTS, type RolledBowl, type RolledSlot } from "@/lib/roll/types";

type Status =
  | { kind: "idle" }
  | { kind: "rolling" }
  | { kind: "ok"; bowl: RolledBowl }
  | { kind: "error"; message: string };

interface RollControls {
  timeBudgetMin: number | "";
  dietaryMode: string;
  allergensCsv: string;
  forceBaseMethod: CookingMethod | "";
}

interface DirectionState {
  cuisines: Set<string>;
  moods: Set<string>;
  boldToMild: number;
  heavyToLight: number;
}

const CUISINES = [
  "asian",
  "mediterranean",
  "mexican",
  "middle_eastern",
  "american",
  "fusion",
] as const;
const MOODS = [
  "quick_weekday",
  "light_fresh",
  "comfort",
  "impress",
  "use_what_i_have",
  "surprise_me",
] as const;

const INITIAL_CONTROLS: RollControls = {
  timeBudgetMin: 30,
  dietaryMode: "",
  allergensCsv: "",
  forceBaseMethod: "",
};

const INITIAL_DIRECTION: DirectionState = {
  cuisines: new Set<string>(),
  moods: new Set<string>(),
  boldToMild: 0,
  heavyToLight: 0,
};

const CATEGORY_ICON: Record<Category, typeof Salad> = {
  base: Utensils,
  vegetable: Salad,
  sauce: Flame,
  topping: Sparkles,
};

function parseCsv(input: string): string[] {
  return input
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export function RollPage() {
  const t = useTranslations("roll");
  const tDirection = useTranslations("roll.direction");
  const tNutrition = useTranslations("roll.nutrition");
  const tCategory = useTranslations("components.category");
  const router = useRouter();

  const [controls, setControls] = useState<RollControls>(INITIAL_CONTROLS);
  const [direction, setDirection] = useState<DirectionState>(INITIAL_DIRECTION);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const toggleSetMember = (which: "cuisines" | "moods", value: string) => {
    setDirection((d) => {
      const next = new Set(d[which]);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return { ...d, [which]: next };
    });
  };

  const buildRequestBody = useCallback(() => {
    const forced: Partial<Record<Category, CookingMethod>> = {};
    if (controls.forceBaseMethod !== "") {
      forced.base = controls.forceBaseMethod;
    }
    // Surprise me bumps softmax temperature to flatten the distribution.
    const surpriseBump = direction.moods.has("surprise_me") ? 0.5 : 0;
    return {
      slots: [...DEFAULT_SLOTS],
      time_budget_min: controls.timeBudgetMin === "" ? null : Number(controls.timeBudgetMin),
      dietary_mode: controls.dietaryMode === "" ? null : controls.dietaryMode,
      allergens_excluded: parseCsv(controls.allergensCsv),
      forced_methods: forced as Record<Category, CookingMethod>,
      direction: {
        cuisines: [...direction.cuisines],
        moods: [...direction.moods],
        axes: {
          bold_to_mild: direction.boldToMild,
          heavy_to_light: direction.heavyToLight,
        },
      },
      temperature: 0.5 + surpriseBump,
    };
  }, [controls, direction]);

  const rollAll = useCallback(async () => {
    setStatus({ kind: "rolling" });
    try {
      const { data, error, response } = await apiClient.POST("/v1/roll", {
        body: buildRequestBody(),
      });
      if (error || !data) {
        const message =
          typeof error === "object" && error && "detail" in error
            ? JSON.stringify(error.detail)
            : `HTTP ${response.status}`;
        setStatus({ kind: "error", message });
        return;
      }
      setStatus({ kind: "ok", bowl: data });
      void apiClient.POST("/v1/history", {
        body: {
          kind: "rolled",
          bowl_id: null,
          payload: {
            components: data.slots.map((s) => ({
              id: s.component.id,
              name: s.component.name,
              category: s.component.category,
            })),
          },
        },
      });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "unknown",
      });
    }
  }, [buildRequestBody]);

  const rerollSlot = useCallback(
    async (index: number, slot: RolledSlot) => {
      if (status.kind !== "ok") return;
      const previousBowl = status.bowl;
      try {
        const { data, error, response } = await apiClient.POST("/v1/roll/slot", {
          body: {
            request: buildRequestBody(),
            slot_category: slot.component.category,
            exclude_component_ids: [slot.component.id],
          },
        });
        if (error || !data) {
          const message =
            typeof error === "object" && error && "detail" in error
              ? JSON.stringify(error.detail)
              : `HTTP ${response.status}`;
          setStatus({ kind: "error", message });
          return;
        }
        const nextSlots = [...previousBowl.slots];
        nextSlots[index] = data;
        setStatus({ kind: "ok", bowl: { slots: nextSlots } });
      } catch (err) {
        setStatus({
          kind: "error",
          message: err instanceof Error ? err.message : "unknown",
        });
      }
    },
    [buildRequestBody, status],
  );

  const goCook = useCallback(() => {
    if (status.kind !== "ok") return;
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(ROLLED_BOWL_STORAGE_KEY, JSON.stringify(status.bowl));
    }
    void apiClient.POST("/v1/history", {
      body: {
        kind: "cooked",
        bowl_id: null,
        payload: {
          components: status.bowl.slots.map((s) => ({
            id: s.component.id,
            name: s.component.name,
            category: s.component.category,
          })),
        },
      },
    });
    router.push("/recipe");
  }, [router, status]);

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>{t("constraints")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="grid gap-1.5 text-sm">
              <span className="font-medium">{t("timeBudget")}</span>
              <Input
                type="number"
                min={0}
                max={600}
                value={controls.timeBudgetMin}
                onChange={(e) =>
                  setControls((c) => ({
                    ...c,
                    timeBudgetMin: e.target.value === "" ? "" : Number(e.target.value),
                  }))
                }
              />
            </label>

            <label className="grid gap-1.5 text-sm">
              <span className="font-medium">{t("dietaryMode")}</span>
              <Select
                value={controls.dietaryMode}
                onChange={(e) => setControls((c) => ({ ...c, dietaryMode: e.target.value }))}
              >
                <option value="">{t("dietary.any")}</option>
                <option value="vegan">{t("dietary.vegan")}</option>
                <option value="vegetarian">{t("dietary.vegetarian")}</option>
                <option value="pescatarian">{t("dietary.pescatarian")}</option>
              </Select>
            </label>

            <label className="grid gap-1.5 text-sm sm:col-span-2">
              <span className="font-medium">{t("allergens")}</span>
              <Input
                type="text"
                value={controls.allergensCsv}
                onChange={(e) => setControls((c) => ({ ...c, allergensCsv: e.target.value }))}
                placeholder={t("allergensPlaceholder")}
              />
            </label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2">
            <span>{t("direction.title")}</span>
            {(direction.cuisines.size > 0 ||
              direction.moods.size > 0 ||
              direction.boldToMild !== 0 ||
              direction.heavyToLight !== 0) && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setDirection(INITIAL_DIRECTION)}
              >
                {t("direction.clear")}
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <p className="text-xs text-[color:var(--color-muted)]">{t("direction.subtitle")}</p>
          <div className="grid gap-2">
            <p className="text-sm font-medium">{t("direction.cuisine")}</p>
            <div className="flex flex-wrap gap-2">
              {CUISINES.map((c) => {
                const active = direction.cuisines.has(c);
                return (
                  <button
                    key={c}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleSetMember("cuisines", c)}
                    className={
                      active
                        ? "rounded-full bg-[color:var(--color-brand)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-brand-fg)] shadow-[var(--shadow-pop)] transition active:scale-95"
                        : "rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-fg)] transition hover:border-[color:var(--color-brand)] active:scale-95"
                    }
                  >
                    {tDirection(`cuisines.${c}`)}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="grid gap-2">
            <p className="text-sm font-medium">{t("direction.mood")}</p>
            <div className="flex flex-wrap gap-2">
              {MOODS.map((m) => {
                const active = direction.moods.has(m);
                return (
                  <button
                    key={m}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleSetMember("moods", m)}
                    className={
                      active
                        ? "rounded-full bg-[color:var(--color-brand)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-brand-fg)] shadow-[var(--shadow-pop)] transition active:scale-95"
                        : "rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-fg)] transition hover:border-[color:var(--color-brand)] active:scale-95"
                    }
                  >
                    {tDirection(`moods.${m}`)}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="grid gap-3">
            <p className="text-sm font-medium">{t("direction.axes")}</p>
            <label className="grid gap-1 text-xs">
              <span className="text-[color:var(--color-muted)]">
                {t("direction.axisBoldToMild")}
              </span>
              <input
                type="range"
                min={-1}
                max={1}
                step={0.1}
                value={direction.boldToMild}
                onChange={(e) =>
                  setDirection((d) => ({ ...d, boldToMild: Number(e.target.value) }))
                }
                className="w-full accent-[color:var(--color-brand)]"
              />
            </label>
            <label className="grid gap-1 text-xs">
              <span className="text-[color:var(--color-muted)]">
                {t("direction.axisHeavyToLight")}
              </span>
              <input
                type="range"
                min={-1}
                max={1}
                step={0.1}
                value={direction.heavyToLight}
                onChange={(e) =>
                  setDirection((d) => ({ ...d, heavyToLight: Number(e.target.value) }))
                }
                className="w-full accent-[color:var(--color-brand)]"
              />
            </label>
          </div>
        </CardContent>
      </Card>

      <Button
        type="button"
        size="lg"
        onClick={() => void rollAll()}
        disabled={status.kind === "rolling"}
        className="w-full"
      >
        <Dice5 aria-hidden size={18} strokeWidth={2.4} />
        {status.kind === "rolling" ? t("rolling") : t("rollButton")}
      </Button>

      {status.kind === "error" && (
        <output
          aria-live="polite"
          className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
        >
          {t("error", { message: status.message })}
        </output>
      )}

      {status.kind === "ok" && (
        <section aria-label={t("results")} className="grid gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold tracking-tight">{t("results")}</h2>
            <Button type="button" size="sm" onClick={goCook}>
              <ChefHat aria-hidden size={14} strokeWidth={2.4} />
              {t("cookNow")}
            </Button>
          </div>
          <Card>
            <CardContent className="grid gap-2">
              <p className="text-xs uppercase tracking-wide text-[color:var(--color-muted)]">
                {tNutrition("title")}
              </p>
              {(() => {
                const totals = status.bowl.slots.reduce(
                  (acc, s) => {
                    const m = s.component.macros_per_100g;
                    const portionG =
                      s.component.default_portion.unit === "g"
                        ? s.component.default_portion.value
                        : 0;
                    const factor = portionG / 100;
                    return {
                      kcal: acc.kcal + m.kcal * factor,
                      carbs: acc.carbs + m.carbs_g * factor,
                      protein: acc.protein + m.protein_g * factor,
                      fat: acc.fat + m.fat_g * factor,
                      fiber: acc.fiber + m.fiber_g * factor,
                    };
                  },
                  { kcal: 0, carbs: 0, protein: 0, fat: 0, fiber: 0 },
                );
                return (
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="brand" className="tabular-nums">
                      {tNutrition("kcal", { value: Math.round(totals.kcal) })}
                    </Badge>
                    <Badge className="tabular-nums">
                      {tNutrition("carbs", { value: Math.round(totals.carbs) })}
                    </Badge>
                    <Badge className="tabular-nums">
                      {tNutrition("protein", { value: Math.round(totals.protein) })}
                    </Badge>
                    <Badge className="tabular-nums">
                      {tNutrition("fat", { value: Math.round(totals.fat) })}
                    </Badge>
                    <Badge className="tabular-nums">
                      {tNutrition("fiber", { value: Math.round(totals.fiber) })}
                    </Badge>
                  </div>
                );
              })()}
            </CardContent>
          </Card>
          <ul className="grid gap-3">
            {status.bowl.slots.map((slot, idx) => {
              const Icon = CATEGORY_ICON[slot.component.category];
              return (
                <li key={`${slot.component.id}-${idx}`}>
                  <Card>
                    <CardContent className="grid gap-2 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
                            <Icon aria-hidden size={18} strokeWidth={2} />
                          </span>
                          <div className="grid gap-1">
                            <div className="font-semibold leading-tight">{slot.component.name}</div>
                            <Badge variant="brand">{tCategory(slot.component.category)}</Badge>
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => void rerollSlot(idx, slot)}
                        >
                          <Dice5 aria-hidden size={14} />
                          {t("rerollSlot")}
                        </Button>
                      </div>
                      {slot.reasons.length > 0 && (
                        <ul className="grid gap-0.5 text-xs text-[color:var(--color-muted)]">
                          {slot.reasons.map((reason) => (
                            <li key={reason} className="flex gap-1.5">
                              <span aria-hidden>•</span>
                              <span>{reason}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </CardContent>
                  </Card>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
