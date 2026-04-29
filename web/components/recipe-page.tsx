"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiClient } from "@/lib/api/client";
import { ROLLED_BOWL_STORAGE_KEY } from "@/lib/recipe/storage";
import type { Recipe } from "@/lib/recipe/types";
import type { RolledBowl } from "@/lib/roll/types";

type Status =
  | { kind: "loading" }
  | { kind: "missing" }
  | { kind: "building" }
  | { kind: "ok"; recipe: Recipe }
  | { kind: "error"; message: string };

function readBowlFromStorage(): RolledBowl | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(ROLLED_BOWL_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as RolledBowl;
  } catch {
    return null;
  }
}

export function RecipePage() {
  const t = useTranslations("recipe");
  const tCategory = useTranslations("components.category");
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  const buildRecipe = useCallback(async (bowl: RolledBowl) => {
    setStatus({ kind: "building" });
    try {
      const { data, error, response } = await apiClient.POST("/v1/recipe", {
        body: {
          component_ids: bowl.slots.map((s) => s.component.id),
          forced_methods: {},
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
      setStatus({ kind: "ok", recipe: data });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "unknown",
      });
    }
  }, []);

  useEffect(() => {
    const bowl = readBowlFromStorage();
    if (!bowl) {
      setStatus({ kind: "missing" });
      return;
    }
    void buildRecipe(bowl);
  }, [buildRecipe]);

  return (
    <div className="grid gap-6">
      <header className="grid gap-1">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-sm opacity-70">{t("subtitle")}</p>
      </header>

      {(status.kind === "loading" || status.kind === "building") && (
        <output aria-live="polite" className="text-sm opacity-70">
          {t("loading")}
        </output>
      )}

      {status.kind === "missing" && (
        <output aria-live="polite" className="grid gap-2 text-sm">
          <span>{t("missing")}</span>
          <Link href="/roll" className="underline">
            {t("backToRoll")}
          </Link>
        </output>
      )}

      {status.kind === "error" && (
        <output aria-live="polite" className="text-sm text-red-600">
          {t("error", { message: status.message })}
        </output>
      )}

      {status.kind === "ok" && (
        <section aria-label={t("blocks")} className="grid gap-4">
          <p className="text-sm opacity-80">
            {t("totalMinutes", { minutes: status.recipe.total_minutes })}
          </p>
          <ol className="grid gap-3">
            {status.recipe.blocks.map((block) => (
              <li
                key={`${block.category}-${block.method}-${block.title}`}
                className="rounded border border-current/20 p-3 text-sm"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <strong>{block.title}</strong>
                  <span className="text-xs opacity-70">
                    {tCategory(block.category)} · {block.method} ·{" "}
                    {t("minutes", { minutes: block.total_minutes })}
                  </span>
                </div>
                {block.steps.length > 0 && (
                  <ol className="mt-2 grid gap-1 pl-4 text-xs opacity-90">
                    {block.steps.map((step) => (
                      <li key={step.text}>{step.text}</li>
                    ))}
                  </ol>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
