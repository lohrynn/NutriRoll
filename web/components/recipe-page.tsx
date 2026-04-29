"use client";

import { Clock, Flame, Salad, Sparkles, Utensils } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import type { Category } from "@/lib/components/types";
import { ROLLED_BOWL_STORAGE_KEY } from "@/lib/recipe/storage";
import type { Recipe } from "@/lib/recipe/types";
import type { RolledBowl } from "@/lib/roll/types";

type Status =
  | { kind: "loading" }
  | { kind: "missing" }
  | { kind: "building" }
  | { kind: "ok"; recipe: Recipe }
  | { kind: "error"; message: string };

const CATEGORY_ICON: Record<Category, typeof Salad> = {
  base: Utensils,
  vegetable: Salad,
  sauce: Flame,
  topping: Sparkles,
};

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
  const tMethod = useTranslations("components.method");
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
    <div className="grid gap-4">
      {(status.kind === "loading" || status.kind === "building") && (
        <output
          aria-live="polite"
          className="rounded-xl bg-[color:var(--color-surface-2)] p-3 text-sm text-[color:var(--color-muted)]"
        >
          {t("loading")}
        </output>
      )}

      {status.kind === "missing" && (
        <Card>
          <CardContent className="grid gap-3">
            <p className="text-sm">{t("missing")}</p>
            <Link
              href="/roll"
              className="text-sm font-medium text-[color:var(--color-brand)] underline-offset-2 hover:underline"
            >
              {t("backToRoll")} →
            </Link>
          </CardContent>
        </Card>
      )}

      {status.kind === "error" && (
        <output
          aria-live="polite"
          className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
        >
          {t("error", { message: status.message })}
        </output>
      )}

      {status.kind === "ok" && (
        <section aria-label={t("blocks")} className="grid gap-3">
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
                <Clock aria-hidden size={20} />
              </span>
              <div>
                <div className="text-xs uppercase tracking-wide text-[color:var(--color-muted)]">
                  {t("blocks")}
                </div>
                <div className="font-semibold">
                  {t("totalMinutes", { minutes: status.recipe.total_minutes })}
                </div>
              </div>
            </CardContent>
          </Card>

          <ol className="grid gap-3">
            {status.recipe.blocks.map((block) => {
              const Icon = CATEGORY_ICON[block.category];
              return (
                <li key={`${block.category}-${block.method}-${block.title}`}>
                  <Card>
                    <CardContent className="grid gap-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
                            <Icon aria-hidden size={18} />
                          </span>
                          <div className="grid gap-1">
                            <div className="font-semibold leading-tight">{block.title}</div>
                            <div className="flex flex-wrap gap-1.5">
                              <Badge variant="brand">{tCategory(block.category)}</Badge>
                              <Badge variant="neutral">{tMethod(block.method)}</Badge>
                            </div>
                          </div>
                        </div>
                        <span className="shrink-0 rounded-full bg-[color:var(--color-surface-2)] px-2.5 py-1 text-xs font-medium tabular-nums">
                          {t("minutes", { minutes: block.total_minutes })}
                        </span>
                      </div>
                      {block.steps.length > 0 && (
                        <ol className="grid gap-1 border-l-2 border-[color:var(--color-border)] pl-3 text-sm">
                          {block.steps.map((step, idx) => (
                            <li key={`${step.text}-${idx}`} className="flex gap-2">
                              <span className="shrink-0 text-xs tabular-nums text-[color:var(--color-muted)]">
                                {String(step.offset_min).padStart(2, "0")}:00
                              </span>
                              <span>{step.text}</span>
                            </li>
                          ))}
                        </ol>
                      )}
                    </CardContent>
                  </Card>
                </li>
              );
            })}
          </ol>
        </section>
      )}
    </div>
  );
}
