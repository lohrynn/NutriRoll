"use client";

import { Boxes, Pencil, Plus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api/client";
import { useExpiryWarningDays } from "@/lib/components/meta";
import type { ComponentRead, PortionUnit } from "@/lib/components/types";
import { PORTION_UNITS } from "@/lib/components/types";
import { daysUntilExpiry, isExpiringSoon } from "@/lib/pantry/freshness";
import type { PantryItemRead } from "@/lib/pantry/types";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; items: PantryItemRead[] }
  | { kind: "error"; message: string };

interface DraftItem {
  componentId: string;
  quantity: string;
  unit: PortionUnit;
  opened: boolean;
  expiresAt: string;
}

const INITIAL_DRAFT: DraftItem = {
  componentId: "",
  quantity: "",
  unit: "g",
  opened: false,
  expiresAt: "",
};

function fromItem(item: PantryItemRead): DraftItem {
  return {
    componentId: item.component_id,
    quantity: String(item.quantity),
    unit: item.unit,
    opened: item.opened,
    expiresAt: item.expires_at ?? "",
  };
}

export function PantryPage() {
  const t = useTranslations("pantry");
  const tForm = useTranslations("pantry.form");
  const tRow = useTranslations("pantry.row");
  const tUnit = useTranslations("components.unit");

  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const [components, setComponents] = useState<ComponentRead[]>([]);
  const [draft, setDraft] = useState<DraftItem>(INITIAL_DRAFT);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<DraftItem>(INITIAL_DRAFT);
  const [editError, setEditError] = useState<string | null>(null);
  const expiryWarningDays = useExpiryWarningDays();

  const componentsById = useMemo(() => new Map(components.map((c) => [c.id, c])), [components]);

  const load = useCallback(async () => {
    setStatus({ kind: "loading" });
    try {
      const [pantryRes, componentsRes] = await Promise.all([
        apiClient.GET("/v1/pantry"),
        apiClient.GET("/v1/components", {
          params: { query: { include_blacklisted: false } },
        }),
      ]);
      if (pantryRes.error || !pantryRes.data) {
        setStatus({ kind: "error", message: "loadFailed" });
        return;
      }
      if (componentsRes.data) {
        setComponents(componentsRes.data.items);
      }
      setStatus({ kind: "ok", items: pantryRes.data.items });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "unknown",
      });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleAdd = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setSubmitError(null);
      const quantity = Number(draft.quantity);
      if (!draft.componentId || !Number.isFinite(quantity) || quantity < 0) {
        setSubmitError(tForm("saveFailed", { message: "invalid input" }));
        return;
      }
      setSubmitting(true);
      try {
        const { data, error, response } = await apiClient.POST("/v1/pantry", {
          body: {
            component_id: draft.componentId,
            quantity,
            unit: draft.unit,
            opened: draft.opened,
            expires_at: draft.expiresAt || null,
          },
        });
        if (error || !data) {
          setSubmitError(tForm("saveFailed", { message: `HTTP ${response.status}` }));
          return;
        }
        setStatus((prev) =>
          prev.kind === "ok" ? { kind: "ok", items: [data, ...prev.items] } : prev,
        );
        setDraft(INITIAL_DRAFT);
      } catch (err) {
        setSubmitError(
          tForm("saveFailed", {
            message: err instanceof Error ? err.message : "unknown",
          }),
        );
      } finally {
        setSubmitting(false);
      }
    },
    [draft, tForm],
  );

  const startEdit = useCallback((item: PantryItemRead) => {
    setEditingId(item.id);
    setEditDraft(fromItem(item));
    setEditError(null);
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingId(null);
    setEditError(null);
  }, []);

  const saveEdit = useCallback(
    async (item: PantryItemRead) => {
      const quantity = Number(editDraft.quantity);
      if (!editDraft.componentId || !Number.isFinite(quantity) || quantity < 0) {
        setEditError(tForm("saveFailed", { message: "invalid input" }));
        return;
      }
      const { data, error, response } = await apiClient.PUT("/v1/pantry/{item_id}", {
        params: { path: { item_id: item.id } },
        body: {
          component_id: editDraft.componentId,
          quantity,
          unit: editDraft.unit,
          opened: editDraft.opened,
          expires_at: editDraft.expiresAt || null,
        },
      });
      if (error || !data) {
        setEditError(tForm("saveFailed", { message: `HTTP ${response.status}` }));
        return;
      }
      setStatus((prev) =>
        prev.kind === "ok"
          ? { kind: "ok", items: prev.items.map((i) => (i.id === item.id ? data : i)) }
          : prev,
      );
      setEditingId(null);
    },
    [editDraft, tForm],
  );

  const handleRemove = useCallback(
    async (id: string) => {
      try {
        const { error, response } = await apiClient.DELETE("/v1/pantry/{item_id}", {
          params: { path: { item_id: id } },
        });
        if (error) {
          setSubmitError(tForm("removeFailed", { message: `HTTP ${response.status}` }));
          return;
        }
        setStatus((prev) =>
          prev.kind === "ok" ? { kind: "ok", items: prev.items.filter((i) => i.id !== id) } : prev,
        );
      } catch (err) {
        setSubmitError(
          tForm("removeFailed", {
            message: err instanceof Error ? err.message : "unknown",
          }),
        );
      }
    },
    [tForm],
  );

  const expiringCount = useMemo(() => {
    if (status.kind !== "ok") return 0;
    return status.items.filter((i) => isExpiringSoon(i.expires_at, expiryWarningDays)).length;
  }, [status, expiryWarningDays]);

  return (
    <div className="grid gap-4">
      {expiringCount > 0 && (
        <Card className="border-[color:var(--color-warning)]/40 bg-[color:var(--color-warning)]/10">
          <CardContent className="text-sm">
            {t("expiryAlert", { count: expiringCount, days: expiryWarningDays })}
          </CardContent>
        </Card>
      )}
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

      {status.kind === "ok" && status.items.length > 0 && (
        <div className="grid gap-3">
          {status.items.map((item) => {
            const component = componentsById.get(item.component_id);
            const expiringSoon = isExpiringSoon(item.expires_at, expiryWarningDays);
            const remainingDays = daysUntilExpiry(item.expires_at);
            const isEditing = editingId === item.id;
            return (
              <Card key={item.id}>
                <CardContent className="flex items-start gap-3">
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
                    <Boxes className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div className="grid flex-1 gap-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{component?.name ?? item.component_id}</p>
                      <div className="flex gap-1">
                        {!isEditing && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => startEdit(item)}
                            aria-label={tRow("edit")}
                          >
                            <Pencil className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        )}
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => void handleRemove(item.id)}
                          aria-label={tRow("remove")}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </div>
                    </div>
                    {!isEditing && (
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="brand">
                          {tRow("quantity", {
                            value: item.quantity,
                            unit: tUnit(item.unit),
                          })}
                        </Badge>
                        {item.opened && <Badge>{tRow("opened")}</Badge>}
                        {item.expires_at && !expiringSoon && (
                          <Badge variant="warning">
                            {tRow("expires", { date: item.expires_at })}
                          </Badge>
                        )}
                        {item.expires_at && expiringSoon && (
                          <Badge variant="danger">
                            {remainingDays !== null && remainingDays < 0
                              ? tRow("expired")
                              : tRow("expiringSoon", {
                                  days: remainingDays ?? expiryWarningDays,
                                })}
                          </Badge>
                        )}
                      </div>
                    )}
                    {isEditing && (
                      <div className="grid gap-2">
                        <div className="grid grid-cols-[1fr_auto] gap-2">
                          <label className="grid gap-1 text-sm">
                            <span>{tForm("quantity")}</span>
                            <Input
                              type="number"
                              inputMode="decimal"
                              step="any"
                              min="0"
                              value={editDraft.quantity}
                              onChange={(e) =>
                                setEditDraft((d) => ({ ...d, quantity: e.target.value }))
                              }
                            />
                          </label>
                          <label className="grid gap-1 text-sm">
                            <span>{tForm("unit")}</span>
                            <Select
                              value={editDraft.unit}
                              onChange={(e) =>
                                setEditDraft((d) => ({
                                  ...d,
                                  unit: e.target.value as PortionUnit,
                                }))
                              }
                            >
                              {PORTION_UNITS.map((u) => (
                                <option key={u} value={u}>
                                  {tUnit(u)}
                                </option>
                              ))}
                            </Select>
                          </label>
                        </div>
                        <label className="grid gap-1 text-sm">
                          <span>{tForm("expires")}</span>
                          <Input
                            type="date"
                            value={editDraft.expiresAt}
                            onChange={(e) =>
                              setEditDraft((d) => ({ ...d, expiresAt: e.target.value }))
                            }
                          />
                        </label>
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={editDraft.opened}
                            onChange={(e) =>
                              setEditDraft((d) => ({ ...d, opened: e.target.checked }))
                            }
                          />
                          <span>{tForm("opened")}</span>
                        </label>
                        {editError && (
                          <output
                            aria-live="polite"
                            className="text-sm text-[color:var(--color-danger)]"
                          >
                            {editError}
                          </output>
                        )}
                        <div className="flex gap-2">
                          <Button type="button" size="sm" onClick={() => void saveEdit(item)}>
                            {tForm("saveEdit")}
                          </Button>
                          <Button type="button" size="sm" variant="outline" onClick={cancelEdit}>
                            {tForm("cancelEdit")}
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t("addNew")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleAdd(e)} className="grid gap-3">
            <label className="grid gap-1 text-sm">
              <span>{tForm("component")}</span>
              <Select
                value={draft.componentId}
                onChange={(e) => setDraft((d) => ({ ...d, componentId: e.target.value }))}
                required
              >
                <option value="" disabled>
                  {tForm("componentPlaceholder")}
                </option>
                {components.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </label>
            <div className="grid grid-cols-[1fr_auto] gap-2">
              <label className="grid gap-1 text-sm">
                <span>{tForm("quantity")}</span>
                <Input
                  type="number"
                  inputMode="decimal"
                  step="any"
                  min="0"
                  value={draft.quantity}
                  onChange={(e) => setDraft((d) => ({ ...d, quantity: e.target.value }))}
                  required
                />
              </label>
              <label className="grid gap-1 text-sm">
                <span>{tForm("unit")}</span>
                <Select
                  value={draft.unit}
                  onChange={(e) =>
                    setDraft((d) => ({
                      ...d,
                      unit: e.target.value as PortionUnit,
                    }))
                  }
                >
                  {PORTION_UNITS.map((u) => (
                    <option key={u} value={u}>
                      {tUnit(u)}
                    </option>
                  ))}
                </Select>
              </label>
            </div>
            <label className="grid gap-1 text-sm">
              <span>{tForm("expires")}</span>
              <Input
                type="date"
                value={draft.expiresAt}
                onChange={(e) => setDraft((d) => ({ ...d, expiresAt: e.target.value }))}
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={draft.opened}
                onChange={(e) => setDraft((d) => ({ ...d, opened: e.target.checked }))}
              />
              <span>{tForm("opened")}</span>
            </label>
            {submitError && (
              <output aria-live="polite" className="text-sm text-[color:var(--color-danger)]">
                {submitError}
              </output>
            )}
            <Button type="submit" disabled={submitting}>
              {submitting ? tForm("submitting") : tForm("submit")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
