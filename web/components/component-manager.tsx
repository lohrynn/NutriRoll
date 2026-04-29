"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ComponentForm } from "@/components/component-form";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api/client";
import { CATEGORIES, type Category, type ComponentRead } from "@/lib/components/types";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; items: ComponentRead[] }
  | { kind: "error"; message: string };

const FILTER_OPTIONS: readonly (Category | "all")[] = ["all", ...CATEGORIES];

export function ComponentManager() {
  const t = useTranslations("components");
  const tCategory = useTranslations("components.category");
  const tFilter = useTranslations("components.filter");
  const tRow = useTranslations("components.row");

  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const [filter, setFilter] = useState<Category | "all">("all");

  const load = useCallback(async () => {
    setStatus({ kind: "loading" });
    try {
      const params: { include_blacklisted: boolean; category?: Category } = {
        include_blacklisted: true,
      };
      if (filter !== "all") params.category = filter;
      const { data, error, response } = await apiClient.GET("/v1/components", {
        params: { query: params },
      });
      if (error || !data) {
        setStatus({ kind: "error", message: `HTTP ${response.status}` });
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

  const handleCreated = useCallback((created: ComponentRead) => {
    setStatus((prev) =>
      prev.kind === "ok" ? { kind: "ok", items: [created, ...prev.items] } : prev,
    );
  }, []);

  const items = useMemo(() => (status.kind === "ok" ? status.items : []), [status]);

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="filter-category" className="text-sm font-medium">
          {t("filter.all")}:
        </label>
        <div className="w-40">
          <Select
            id="filter-category"
            value={filter}
            onChange={(e) => setFilter(e.target.value as Category | "all")}
          >
            {FILTER_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {tFilter(opt)}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <section aria-label={t("title")} className="grid gap-2">
        {status.kind === "loading" && (
          <p className="text-sm text-[color:var(--color-muted)]">{t("loading")}</p>
        )}
        {status.kind === "error" && (
          <output
            aria-live="polite"
            className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
          >
            {t("loadError", { message: status.message })}
          </output>
        )}
        {status.kind === "ok" && items.length === 0 && (
          <Card>
            <CardContent>
              <p className="text-sm text-[color:var(--color-muted)]">{t("empty")}</p>
            </CardContent>
          </Card>
        )}
        {status.kind === "ok" && items.length > 0 && (
          <ul className="grid gap-2">
            {items.map((c) => (
              <li key={c.id}>
                <Card>
                  <CardContent className="grid gap-1 p-4">
                    <div className="flex flex-wrap items-baseline gap-2">
                      <strong className="font-semibold">{c.name}</strong>
                      <Badge variant="brand">{tCategory(c.category)}</Badge>
                      {c.blacklisted && <Badge variant="danger">{tRow("blacklisted")}</Badge>}
                    </div>
                    <div className="text-xs text-[color:var(--color-muted)]">
                      {tRow("kcal", { value: c.macros_per_100g.kcal })} ·{" "}
                      {tRow("portion", {
                        value: c.default_portion.value,
                        unit: c.default_portion.unit,
                      })}
                    </div>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>{t("addNew")}</CardTitle>
        </CardHeader>
        <CardContent>
          <ComponentForm onCreated={handleCreated} />
        </CardContent>
      </Card>
    </div>
  );
}
