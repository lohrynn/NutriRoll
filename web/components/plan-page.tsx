"use client";

import { Calendar, ChefHat, ChevronLeft, ChevronRight, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api/client";
import {
  MEAL_SLOTS,
  type MealSlot,
  type PlannedMealRead,
  type PlannedStatus,
} from "@/lib/planning/types";
import {
  parseStoredRolledMeal,
  writeRolledMealToStorage,
} from "@/lib/recipe/storage";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; items: PlannedMealRead[] }
  | { kind: "error"; message: string };

function startOfWeek(d: Date): Date {
  const out = new Date(d);
  out.setHours(0, 0, 0, 0);
  // Monday-based week
  const day = out.getDay();
  const diff = (day + 6) % 7;
  out.setDate(out.getDate() - diff);
  return out;
}

function addDays(d: Date, n: number): Date {
  const out = new Date(d);
  out.setDate(out.getDate() + n);
  return out;
}

function toIsoDate(d: Date): string {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

const STATUS_VARIANT: Record<PlannedStatus, "brand" | "neutral" | "danger"> = {
  planned: "neutral",
  shopped: "brand",
  cooked: "brand",
  skipped: "danger",
};

export function PlanPage() {
  const t = useTranslations("plan");
  const tSlot = useTranslations("plan.slot");
  const tStatus = useTranslations("plan.status");
  const locale = useLocale();
  const router = useRouter();

  const [weekStart, setWeekStart] = useState<Date>(() => startOfWeek(new Date()));
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  );
  const firstDay = days[0] ?? weekStart;
  const lastDay = days[6] ?? weekStart;
  const startIso = toIsoDate(firstDay);
  const endIso = toIsoDate(lastDay);

  const load = useCallback(async () => {
    setStatus({ kind: "loading" });
    const { data, error, response } = await apiClient.GET("/v1/planned", {
      params: { query: { start: startIso, end: endIso } },
    });
    if (error || !data) {
      setStatus({ kind: "error", message: `HTTP ${response.status}` });
      return;
    }
    setStatus({ kind: "ok", items: data.items });
  }, [startIso, endIso]);

  useEffect(() => {
    void load();
  }, [load]);

  const cook = (meal: PlannedMealRead) => {
    const storedMeal = parseStoredRolledMeal(meal.bowl_snapshot);
    if (!storedMeal || storedMeal.bowl.slots.length === 0) return;
    writeRolledMealToStorage(storedMeal);
    router.push("/recipe");
  };

  const setStatusOf = async (id: string, next: PlannedStatus) => {
    await apiClient.PATCH("/v1/planned/{meal_id}", {
      params: { path: { meal_id: id } },
      body: { status: next },
    });
    await load();
  };

  const setSlotOf = async (id: string, slot: MealSlot) => {
    await apiClient.PATCH("/v1/planned/{meal_id}", {
      params: { path: { meal_id: id } },
      body: { slot },
    });
    await load();
  };

  const remove = async (id: string) => {
    await apiClient.DELETE("/v1/planned/{meal_id}", {
      params: { path: { meal_id: id } },
    });
    await load();
  };

  const markEaten = async (id: string) => {
    await apiClient.POST("/v1/planned/{meal_id}/mark-eaten", {
      params: { path: { meal_id: id } },
    });
    await load();
  };

  const itemsByDay = useMemo(() => {
    const map = new Map<string, PlannedMealRead[]>();
    if (status.kind !== "ok") return map;
    for (const item of status.items) {
      const list = map.get(item.planned_for) ?? [];
      list.push(item);
      map.set(item.planned_for, list);
    }
    return map;
  }, [status]);

  return (
    <div className="grid gap-3">
      <Card>
        <CardContent className="flex items-center justify-between gap-2 py-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setWeekStart((d) => addDays(d, -7))}
            aria-label={t("prevWeek")}
          >
            <ChevronLeft aria-hidden size={14} />
          </Button>
          <span className="inline-flex items-center gap-2 text-sm font-medium">
            <Calendar aria-hidden size={14} className="text-[color:var(--color-brand)]" />
            {firstDay.toLocaleDateString(locale)} – {lastDay.toLocaleDateString(locale)}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setWeekStart((d) => addDays(d, 7))}
            aria-label={t("nextWeek")}
          >
            <ChevronRight aria-hidden size={14} />
          </Button>
        </CardContent>
      </Card>

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

      {status.kind === "ok" &&
        days.map((day) => {
          const iso = toIsoDate(day);
          const dayItems = itemsByDay.get(iso) ?? [];
          return (
            <Card key={iso}>
              <CardContent className="grid gap-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold leading-tight">
                    {day.toLocaleDateString(locale, {
                      weekday: "long",
                      month: "short",
                      day: "numeric",
                    })}
                  </p>
                  <Badge>{t("count", { count: dayItems.length })}</Badge>
                </div>
                {dayItems.length === 0 && (
                  <p className="text-xs text-[color:var(--color-muted)]">{t("empty")}</p>
                )}
                {dayItems.map((meal) => {
                  const storedMeal = parseStoredRolledMeal(meal.bowl_snapshot);
                  const preview =
                    storedMeal?.bowl.slots
                      ?.slice(0, 2)
                      .map((s) => s.component.name)
                      .join(" + ") ?? "";
                  return (
                    <div
                      key={meal.id}
                      className="grid gap-2 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] p-3"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Select
                            aria-label={t("changeSlot")}
                            value={meal.slot}
                            onChange={(e) => void setSlotOf(meal.id, e.target.value as MealSlot)}
                            className="text-xs"
                          >
                            {MEAL_SLOTS.map((slot) => (
                              <option key={slot} value={slot}>
                                {tSlot(slot)}
                              </option>
                            ))}
                          </Select>
                          <Badge variant={STATUS_VARIANT[meal.status as PlannedStatus]}>
                            {tStatus(meal.status as PlannedStatus)}
                          </Badge>
                          {meal.portions_total > 1 && (
                            <Badge variant="brand">
                              {t("portions", {
                                remaining: meal.portions_remaining,
                                total: meal.portions_total,
                              })}
                            </Badge>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => cook(meal)}
                            disabled={!storedMeal?.bowl.slots.length}
                          >
                            <ChefHat aria-hidden size={14} />
                            {t("cook")}
                          </Button>
                          {meal.portions_remaining > 0 && (
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => void markEaten(meal.id)}
                            >
                              {t("markEaten")}
                            </Button>
                          )}
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              void setStatusOf(
                                meal.id,
                                meal.status === "cooked" ? "planned" : "cooked",
                              )
                            }
                          >
                            {meal.status === "cooked" ? t("undo") : t("markCooked")}
                          </Button>
                          {meal.status !== "shopped" && meal.status !== "cooked" && (
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => void setStatusOf(meal.id, "shopped")}
                            >
                              {t("markShopped")}
                            </Button>
                          )}
                          {meal.status !== "skipped" && meal.status !== "cooked" && (
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => void setStatusOf(meal.id, "skipped")}
                            >
                              {t("markSkipped")}
                            </Button>
                          )}
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            aria-label={t("delete")}
                            onClick={() => void remove(meal.id)}
                          >
                            <Trash2 aria-hidden size={14} />
                          </Button>
                        </div>
                      </div>
                      {preview && (
                        <p className="text-xs text-[color:var(--color-muted)]">{preview}</p>
                      )}
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          );
        })}

      <Card>
        <CardContent className="text-xs text-[color:var(--color-muted)]">{t("hint")}</CardContent>
      </Card>
    </div>
  );
}
