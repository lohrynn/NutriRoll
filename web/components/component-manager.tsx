"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ComponentForm } from "@/components/component-form";
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
    <div className="grid gap-6">
      <header className="grid gap-1">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-sm opacity-70">{t("subtitle")}</p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="filter-category" className="text-sm">
          {t("filter.all")}:
        </label>
        <select
          id="filter-category"
          value={filter}
          onChange={(e) => setFilter(e.target.value as Category | "all")}
          className="rounded border border-current/30 bg-transparent px-3 py-1 text-sm"
        >
          {FILTER_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {tFilter(opt)}
            </option>
          ))}
        </select>
      </div>

      <section aria-label={t("title")} className="grid gap-2">
        {status.kind === "loading" && <p className="text-sm opacity-70">{t("loading")}</p>}
        {status.kind === "error" && (
          <output aria-live="polite" className="text-sm text-red-600">
            {t("loadError", { message: status.message })}
          </output>
        )}
        {status.kind === "ok" && items.length === 0 && (
          <p className="text-sm opacity-70">{t("empty")}</p>
        )}
        {status.kind === "ok" && items.length > 0 && (
          <ul className="grid gap-2">
            {items.map((c) => (
              <li key={c.id} className="rounded border border-current/20 px-3 py-2 text-sm">
                <div className="flex flex-wrap items-baseline gap-2">
                  <strong>{c.name}</strong>
                  <span className="text-xs opacity-70">{tCategory(c.category)}</span>
                  {c.blacklisted && (
                    <span className="text-xs uppercase tracking-wide text-red-600">
                      {tRow("blacklisted")}
                    </span>
                  )}
                </div>
                <div className="text-xs opacity-70">
                  {tRow("kcal", { value: c.macros_per_100g.kcal })} ·{" "}
                  {tRow("portion", {
                    value: c.default_portion.value,
                    unit: c.default_portion.unit,
                  })}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label={t("addNew")} className="grid gap-3">
        <h2 className="text-lg font-medium">{t("addNew")}</h2>
        <ComponentForm onCreated={handleCreated} />
      </section>
    </div>
  );
}
