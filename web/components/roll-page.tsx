"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

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

  return (
    <div className="grid gap-6">
      <header className="grid gap-1">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-sm opacity-70">{t("subtitle")}</p>
      </header>

      <fieldset className="grid gap-3 rounded border border-current/20 p-4">
        <legend className="px-2 text-sm font-medium">{t("constraints")}</legend>

        <div className="grid gap-2 sm:grid-cols-2">
          <label className="grid gap-1 text-sm">
            <span>{t("timeBudget")}</span>
            <input
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
              className="rounded border border-current/30 bg-transparent px-2 py-1"
            />
          </label>

          <label className="grid gap-1 text-sm">
            <span>{t("dietaryMode")}</span>
            <select
              value={controls.dietaryMode}
              onChange={(e) => setControls((c) => ({ ...c, dietaryMode: e.target.value }))}
              className="rounded border border-current/30 bg-transparent px-2 py-1"
            >
              <option value="">{t("dietary.any")}</option>
              <option value="vegan">{t("dietary.vegan")}</option>
              <option value="vegetarian">{t("dietary.vegetarian")}</option>
              <option value="pescatarian">{t("dietary.pescatarian")}</option>
            </select>
          </label>

          <label className="grid gap-1 text-sm sm:col-span-2">
            <span>{t("allergens")}</span>
            <input
              type="text"
              value={controls.allergensCsv}
              onChange={(e) => setControls((c) => ({ ...c, allergensCsv: e.target.value }))}
              placeholder={t("allergensPlaceholder")}
              className="rounded border border-current/30 bg-transparent px-2 py-1"
            />
          </label>
        </div>
      </fieldset>

      <button
        type="button"
        onClick={() => void rollAll()}
        disabled={status.kind === "rolling"}
        className="rounded bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-50"
      >
        {status.kind === "rolling" ? t("rolling") : t("rollButton")}
      </button>

      {status.kind === "error" && (
        <output aria-live="polite" className="text-sm text-red-600">
          {t("error", { message: status.message })}
        </output>
      )}

      {status.kind === "ok" && (
        <section aria-label={t("results")} className="grid gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-medium">{t("results")}</h2>
            <button
              type="button"
              onClick={() => {
                if (status.kind !== "ok") return;
                if (typeof window !== "undefined") {
                  window.sessionStorage.setItem(
                    ROLLED_BOWL_STORAGE_KEY,
                    JSON.stringify(status.bowl),
                  );
                }
                router.push("/recipe");
              }}
              className="rounded bg-foreground px-3 py-1.5 text-xs font-medium text-background"
            >
              {t("cookNow")}
            </button>
          </div>
          <ul className="grid gap-2">
            {status.bowl.slots.map((slot, idx) => (
              <li
                key={`${slot.component.id}-${idx}`}
                className="rounded border border-current/20 p-3 text-sm"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <strong>{slot.component.name}</strong>{" "}
                    <span className="text-xs opacity-70">{tCategory(slot.component.category)}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void rerollSlot(idx, slot)}
                    className="rounded border border-current/30 px-2 py-1 text-xs"
                  >
                    {t("rerollSlot")}
                  </button>
                </div>
                {slot.reasons.length > 0 && (
                  <ul className="mt-1 list-disc pl-4 text-xs opacity-80">
                    {slot.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
