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

const INITIAL_CONTROLS: RollControls = {
  timeBudgetMin: 30,
  dietaryMode: "",
  allergensCsv: "",
  forceBaseMethod: "",
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
  const tCategory = useTranslations("components.category");
  const router = useRouter();

  const [controls, setControls] = useState<RollControls>(INITIAL_CONTROLS);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const buildRequestBody = useCallback(() => {
    const forced: Partial<Record<Category, CookingMethod>> = {};
    if (controls.forceBaseMethod !== "") {
      forced.base = controls.forceBaseMethod;
    }
    return {
      slots: [...DEFAULT_SLOTS],
      time_budget_min: controls.timeBudgetMin === "" ? null : Number(controls.timeBudgetMin),
      dietary_mode: controls.dietaryMode === "" ? null : controls.dietaryMode,
      allergens_excluded: parseCsv(controls.allergensCsv),
      forced_methods: forced as Record<Category, CookingMethod>,
      temperature: 0.5,
    };
  }, [controls]);

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
