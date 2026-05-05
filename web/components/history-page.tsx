"use client";

import { ChefHat, ClipboardList, Flame, Save, Sparkles, Star, Trash2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import type {
  HistoryEventKind,
  HistoryEventRead,
  HistoryRecapResponse,
} from "@/lib/history/types";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; items: HistoryEventRead[] }
  | { kind: "error"; message: string };

type RecapStatus =
  | { kind: "loading"; recap: HistoryRecapResponse["recap"] | null }
  | { kind: "disabled"; recap: null }
  | { kind: "idle"; recap: null }
  | { kind: "ready"; recap: NonNullable<HistoryRecapResponse["recap"]>; cached: boolean }
  | { kind: "error"; recap: HistoryRecapResponse["recap"] | null; message: string };

type FilterValue = "all" | HistoryEventKind;
const FILTERS: readonly FilterValue[] = ["all", "rolled", "cooked", "rated"];

const KIND_ICON: Record<HistoryEventKind, typeof ChefHat> = {
  rolled: ChefHat,
  cooked: Flame,
  rated: Star,
  saved: Save,
  discarded: X,
};

function formatDate(iso?: string | null): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function currentWeekStartIso(): string {
  const today = new Date();
  const day = today.getDay();
  const offset = day === 0 ? 6 : day - 1;
  const monday = new Date(today);
  monday.setDate(today.getDate() - offset);
  const year = monday.getFullYear();
  const month = String(monday.getMonth() + 1).padStart(2, "0");
  const date = String(monday.getDate()).padStart(2, "0");
  return `${year}-${month}-${date}`;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(amount);
}

export function HistoryPageView() {
  const t = useTranslations("history");
  const tKind = useTranslations("history.kind");

  const [filter, setFilter] = useState<FilterValue>("all");
  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const [recapStatus, setRecapStatus] = useState<RecapStatus>({ kind: "loading", recap: null });
  const weekStart = currentWeekStartIso();

  const load = useCallback(async () => {
    setStatus({ kind: "loading" });
    try {
      const params: { kind?: HistoryEventKind; limit: number } = { limit: 100 };
      if (filter !== "all") params.kind = filter;
      const { data, error, response } = await apiClient.GET("/v1/history", {
        params: { query: params },
      });
      if (error || !data) {
        setStatus({
          kind: "error",
          message: `HTTP ${response.status}`,
        });
        return;
      }
      setStatus({ kind: "ok", items: data.items });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "unknown",
      });
    }
  }, [filter]);

  const loadRecap = useCallback(
    async (generate: boolean) => {
      setRecapStatus((current) => ({
        kind: "loading",
        recap: current.kind === "ready" ? current.recap : null,
      }));
      try {
        const llmResult = await apiClient.GET("/v1/me/profile/llm");
        if (!llmResult.data) {
          setRecapStatus({ kind: "error", recap: null, message: `HTTP ${llmResult.response.status}` });
          return;
        }
        if (!(llmResult.data.enabled_features ?? []).includes("weekly_recaps")) {
          setRecapStatus({ kind: "disabled", recap: null });
          return;
        }

        const { data, error, response } = await apiClient.GET("/v1/history/recap", {
          params: {
            query: {
              week_start: weekStart,
              generate,
            },
          },
        });
        if (error || !data) {
          const featureDisabled =
            typeof error === "object" &&
            error !== null &&
            "detail" in error &&
            typeof error.detail === "object" &&
            error.detail !== null &&
            "code" in error.detail &&
            error.detail.code === "LLM_FEATURE_DISABLED";
          if (featureDisabled) {
            setRecapStatus({ kind: "disabled", recap: null });
            return;
          }
          setRecapStatus({
            kind: "error",
            recap: null,
            message: `HTTP ${response.status}`,
          });
          return;
        }
        if (!data.recap) {
          setRecapStatus({ kind: "idle", recap: null });
          return;
        }
        setRecapStatus({ kind: "ready", recap: data.recap, cached: data.cached });
      } catch (err) {
        setRecapStatus({
          kind: "error",
          recap: null,
          message: err instanceof Error ? err.message : "unknown",
        });
      }
    },
    [weekStart],
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadRecap(false);
  }, [loadRecap]);

  const handleDelete = async (id: string) => {
    await apiClient.DELETE("/v1/history/{event_id}", {
      params: { path: { event_id: id } },
    });
    await load();
  };

  return (
    <div className="grid gap-4">
      <Card className="overflow-hidden border-[color:var(--color-brand)]/15 bg-[linear-gradient(135deg,var(--color-brand-soft),transparent_70%)]">
        <CardContent className="grid gap-3">
          <div className="flex items-start justify-between gap-3">
            <div className="grid gap-1">
              <div className="flex items-center gap-2">
                <span className="grid h-10 w-10 place-items-center rounded-2xl bg-[color:var(--color-brand)] text-[color:var(--color-brand-fg)]">
                  <Sparkles className="h-5 w-5" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-sm font-semibold">{t("recap.title")}</p>
                  <p className="text-xs text-[color:var(--color-muted)]">{t("recap.subtitle")}</p>
                </div>
              </div>
            </div>
            {recapStatus.kind === "ready" && recapStatus.cached && (
              <Badge variant="brand">{t("recap.cached")}</Badge>
            )}
          </div>

          {recapStatus.kind === "disabled" && (
            <p className="text-sm text-[color:var(--color-muted)]">{t("recap.disabled")}</p>
          )}

          {recapStatus.kind === "loading" && (
            <output aria-live="polite" className="text-sm text-[color:var(--color-muted)]">
              {t("recap.loading")}
            </output>
          )}

          {recapStatus.kind === "idle" && (
            <div className="grid gap-3">
              <p className="text-sm text-[color:var(--color-muted)]">{t("recap.empty")}</p>
              <div>
                <Button type="button" variant="secondary" size="sm" onClick={() => void loadRecap(true)}>
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                  {t("recap.generate")}
                </Button>
              </div>
            </div>
          )}

          {recapStatus.kind === "error" && (
            <div className="grid gap-3">
              <p className="text-sm text-[color:var(--color-danger)]">
                {t("recap.error", { message: recapStatus.message })}
              </p>
              <div>
                <Button type="button" variant="secondary" size="sm" onClick={() => void loadRecap(true)}>
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                  {t("recap.generate")}
                </Button>
              </div>
            </div>
          )}

          {recapStatus.kind === "ready" && (
            <div className="grid gap-3">
              <p className="text-sm leading-6">{recapStatus.recap.summary_text}</p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="brand">
                  {t("recap.chips.meals", {
                    count: recapStatus.recap.stats.meals_cooked,
                  })}
                </Badge>
                <Badge>{t("recap.chips.spend", { amount: formatCurrency(recapStatus.recap.stats.spent_eur) })}</Badge>
                <Badge>
                  {t("recap.chips.kcal", {
                    amount:
                      recapStatus.recap.stats.avg_kcal == null
                        ? "—"
                        : Math.round(recapStatus.recap.stats.avg_kcal),
                  })}
                </Badge>
              </div>
              {recapStatus.recap.suggestions.length > 0 && (
                <ul className="grid gap-1 text-sm text-[color:var(--color-muted)]">
                  {recapStatus.recap.suggestions.map((suggestion) => (
                    <li key={suggestion}>{suggestion}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => {
          const active = filter === f;
          const labelKey =
            f === "all"
              ? "filterAll"
              : f === "rolled"
                ? "filterRolled"
                : f === "cooked"
                  ? "filterCooked"
                  : "filterRated";
          return (
            <Button
              key={f}
              type="button"
              size="sm"
              variant={active ? "primary" : "outline"}
              onClick={() => setFilter(f)}
            >
              {t(labelKey)}
            </Button>
          );
        })}
      </div>

      {status.kind === "loading" && (
        <Card>
          <CardContent>
            <output aria-live="polite">{t("loading")}</output>
          </CardContent>
        </Card>
      )}

      {status.kind === "error" && (
        <Card className="border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/5">
          <CardContent>
            <output aria-live="polite" className="text-[color:var(--color-danger)]">
              {t("loadError", { message: status.message })}
            </output>
          </CardContent>
        </Card>
      )}

      {status.kind === "ok" && status.items.length === 0 && (
        <Card>
          <CardContent className="grid place-items-center gap-3 py-8 text-center animate-fade-in-up">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
              <ChefHat className="h-6 w-6" aria-hidden="true" />
            </span>
            <div className="grid gap-1">
              <p className="font-semibold">{t("emptyState.title")}</p>
              <p className="text-sm text-[color:var(--color-muted)]">{t("emptyState.body")}</p>
            </div>
            <Button asChild>
              <Link href="/roll">{t("emptyState.cta")}</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {status.kind === "ok" &&
        status.items.map((event) => {
          const Icon = KIND_ICON[event.kind] ?? ClipboardList;
          const components =
            (event.payload?.components as Array<{ id: string; name: string }> | undefined) ?? [];
          const overall = event.payload?.overall as number | undefined;
          return (
            <Card key={event.id}>
              <CardContent className="flex items-start gap-3">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <div className="grid flex-1 gap-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="brand">{tKind(event.kind)}</Badge>
                      {typeof overall === "number" && (
                        <Badge>
                          <Star className="mr-1 h-3 w-3 fill-current" aria-hidden="true" />
                          {t("rating", { value: overall })}
                        </Badge>
                      )}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={t("remove")}
                      onClick={() => void handleDelete(event.id)}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                  {components.length > 0 && (
                    <p className="text-sm">{components.map((c) => c.name).join(" + ")}</p>
                  )}
                  <p className="text-xs text-[color:var(--color-muted)] tabular-nums">
                    {formatDate(event.created_at)}
                  </p>
                </div>
              </CardContent>
            </Card>
          );
        })}
    </div>
  );
}
