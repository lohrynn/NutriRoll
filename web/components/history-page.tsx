"use client";

import { ChefHat, ClipboardList, Flame, Save, Sparkles, Star, Trash2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import type { HistoryEventKind, HistoryEventRead } from "@/lib/history/types";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; items: HistoryEventRead[] }
  | { kind: "error"; message: string };

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

export function HistoryPageView() {
  const t = useTranslations("history");
  const tKind = useTranslations("history.kind");

  const [filter, setFilter] = useState<FilterValue>("all");
  const [status, setStatus] = useState<Status>({ kind: "loading" });

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

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async (id: string) => {
    await apiClient.DELETE("/v1/history/{event_id}", {
      params: { path: { event_id: id } },
    });
    await load();
  };

  return (
    <div className="grid gap-4">
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
          <CardContent>
            <p className="text-sm text-[color:var(--color-muted)]">{t("empty")}</p>
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
