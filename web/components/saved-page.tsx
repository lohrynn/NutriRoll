"use client";

import { CalendarPlus, ChefHat, Heart, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import type { SavedMealRead } from "@/lib/planning/types";
import { ROLLED_BOWL_STORAGE_KEY } from "@/lib/recipe/storage";
import type { RolledBowl } from "@/lib/roll/types";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; items: SavedMealRead[] }
  | { kind: "error"; message: string };

export function SavedPage() {
  const t = useTranslations("saved");
  const router = useRouter();
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  const load = useCallback(async () => {
    setStatus({ kind: "loading" });
    const result = await apiClient.GET("/v1/saved");
    if (!result.data) {
      setStatus({ kind: "error", message: `HTTP ${result.response.status}` });
      return;
    }
    setStatus({ kind: "ok", items: result.data.items });
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const cookSaved = (meal: SavedMealRead) => {
    const snapshot = meal.bowl_snapshot as unknown as RolledBowl | null;
    if (!snapshot || !Array.isArray(snapshot.slots)) return;
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(ROLLED_BOWL_STORAGE_KEY, JSON.stringify(snapshot));
    }
    router.push("/recipe");
  };

  const deleteSaved = async (id: string) => {
    await apiClient.DELETE("/v1/saved/{meal_id}", {
      params: { path: { meal_id: id } },
    });
    await load();
  };

  return (
    <div className="grid gap-3">
      {status.kind === "loading" && (
        <output aria-live="polite" className="text-sm text-[color:var(--color-muted)]">
          {t("loading")}
        </output>
      )}
      {status.kind === "error" && (
        <output
          aria-live="polite"
          className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
        >
          {t("error", { message: status.message })}
        </output>
      )}
      {status.kind === "ok" && status.items.length === 0 && (
        <Card>
          <CardContent className="grid place-items-center gap-2 py-8 text-center text-sm text-[color:var(--color-muted)]">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
              <Heart aria-hidden size={22} strokeWidth={2} />
            </span>
            <p>{t("empty")}</p>
          </CardContent>
        </Card>
      )}
      {status.kind === "ok" &&
        status.items.map((meal) => {
          const snap = meal.bowl_snapshot as unknown as RolledBowl | null;
          const slotCount = snap?.slots?.length ?? 0;
          const previewNames =
            snap?.slots
              ?.slice(0, 3)
              .map((s) => s.component.name)
              .join(" + ") ?? "";
          return (
            <Card key={meal.id}>
              <CardContent className="grid gap-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="grid gap-1">
                    <p className="font-semibold leading-tight">{meal.name}</p>
                    <Badge>{t("slots", { count: slotCount })}</Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => cookSaved(meal)}
                      disabled={slotCount === 0}
                    >
                      <ChefHat aria-hidden size={14} strokeWidth={2.4} />
                      {t("cook")}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      aria-label={t("delete")}
                      onClick={() => void deleteSaved(meal.id)}
                    >
                      <Trash2 aria-hidden size={14} />
                    </Button>
                  </div>
                </div>
                {previewNames && (
                  <p className="text-xs text-[color:var(--color-muted)]">{previewNames}</p>
                )}
                {meal.notes && (
                  <p className="text-xs italic text-[color:var(--color-muted)]">{meal.notes}</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      <Card>
        <CardContent className="grid gap-2 text-sm text-[color:var(--color-muted)]">
          <span className="inline-flex items-center gap-2 font-medium text-[color:var(--color-fg)]">
            <CalendarPlus aria-hidden size={16} />
            {t("hintTitle")}
          </span>
          <p>{t("hintBody")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
