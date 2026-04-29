"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ComponentForm } from "@/components/component-form";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api/client";
import { useCategories } from "@/lib/components/meta";
import type { Category, ComponentRead } from "@/lib/components/types";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; items: ComponentRead[] }
  | { kind: "error"; message: string };

export function ComponentManager() {
  const t = useTranslations("components");
  const tCategory = useTranslations("components.category");
  const tFilter = useTranslations("components.filter");
  const tRow = useTranslations("components.row");

  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const [filter, setFilter] = useState<Category | "all">("all");
  const [editing, setEditing] = useState<ComponentRead | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const categories = useCategories();
  const filterOptions = useMemo<readonly (Category | "all")[]>(
    () => ["all", ...categories],
    [categories],
  );

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

  const handleUpdated = useCallback((updated: ComponentRead) => {
    setEditing(null);
    setStatus((prev) =>
      prev.kind === "ok"
        ? { kind: "ok", items: prev.items.map((i) => (i.id === updated.id ? updated : i)) }
        : prev,
    );
  }, []);

  const handleDelete = useCallback(async (id: string) => {
    setConfirmDeleteId(null);
    await apiClient.DELETE("/v1/components/{component_id}", {
      params: { path: { component_id: id } },
    });
    setStatus((prev) =>
      prev.kind === "ok" ? { kind: "ok", items: prev.items.filter((i) => i.id !== id) } : prev,
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
            {filterOptions.map((opt) => (
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
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-baseline gap-2">
                        <strong className="font-semibold">{c.name}</strong>
                        <Badge variant="brand">{tCategory(c.category)}</Badge>
                        {c.blacklisted && <Badge variant="danger">{tRow("blacklisted")}</Badge>}
                      </div>
                      {confirmDeleteId === c.id ? (
                        <div className="flex gap-1">
                          <button
                            type="button"
                            onClick={() => void handleDelete(c.id)}
                            className="rounded border border-[color:var(--color-danger)]/60 px-2 py-1 text-xs text-[color:var(--color-danger)]"
                          >
                            {tRow("confirmDelete")}
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmDeleteId(null)}
                            className="rounded border border-current/30 px-2 py-1 text-xs"
                          >
                            {tRow("cancelDelete")}
                          </button>
                        </div>
                      ) : (
                        <div className="flex gap-1">
                          <button
                            type="button"
                            aria-label={tRow("edit")}
                            onClick={() => {
                              setEditing(c);
                              setConfirmDeleteId(null);
                            }}
                            className="rounded border border-current/30 px-2 py-1 text-xs"
                          >
                            <Pencil aria-hidden size={12} />
                          </button>
                          <button
                            type="button"
                            aria-label={tRow("delete")}
                            onClick={() => {
                              setConfirmDeleteId(c.id);
                              setEditing(null);
                            }}
                            className="rounded border border-current/30 px-2 py-1 text-xs text-[color:var(--color-danger)]"
                          >
                            <Trash2 aria-hidden size={12} />
                          </button>
                        </div>
                      )}
                    </div>
                    <div className="text-xs text-[color:var(--color-muted)]">
                      {tRow("kcal", { value: c.macros_per_100g.kcal })} ·{" "}
                      {tRow("portion", {
                        value: c.default_portion.value,
                        unit: c.default_portion.unit,
                      })}
                    </div>
                  </CardContent>
                  {editing?.id === c.id && (
                    <CardContent className="border-t border-[color:var(--color-border)] pt-4">
                      <ComponentForm
                        key={c.id}
                        editId={c.id}
                        initialValues={editing}
                        onUpdated={handleUpdated}
                        onCancel={() => setEditing(null)}
                      />
                    </CardContent>
                  )}
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
