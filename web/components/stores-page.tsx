"use client";

import { Plus, Star, Store, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api/client";
import type { ComponentRead } from "@/lib/components/types";
import type { PriceRead, StoreRead } from "@/lib/stores/types";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; items: StoreRead[] }
  | { kind: "error"; message: string };

interface StoreDraft {
  name: string;
  location: string;
  isPrimary: boolean;
}

interface PriceDraft {
  componentId: string;
  packSize: string;
  packPrice: string;
}

const INITIAL_STORE_DRAFT: StoreDraft = { name: "", location: "", isPrimary: false };
const INITIAL_PRICE_DRAFT: PriceDraft = {
  componentId: "",
  packSize: "",
  packPrice: "",
};

export function StoresPage() {
  const t = useTranslations("stores");
  const tForm = useTranslations("stores.form");
  const tPrices = useTranslations("stores.prices");

  const [status, setStatus] = useState<Status>({ kind: "loading" });
  const [components, setComponents] = useState<ComponentRead[]>([]);
  const [pricesByStore, setPricesByStore] = useState<Record<string, PriceRead[]>>({});
  const [draft, setDraft] = useState<StoreDraft>(INITIAL_STORE_DRAFT);
  const [priceDrafts, setPriceDrafts] = useState<Record<string, PriceDraft>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const componentsById = useMemo(() => new Map(components.map((c) => [c.id, c])), [components]);

  const loadPricesFor = useCallback(async (storeId: string) => {
    const { data } = await apiClient.GET("/v1/stores/{store_id}/prices", {
      params: { path: { store_id: storeId } },
    });
    if (data) {
      setPricesByStore((prev) => ({ ...prev, [storeId]: data.items }));
    }
  }, []);

  const load = useCallback(async () => {
    setStatus({ kind: "loading" });
    try {
      const [storesRes, componentsRes] = await Promise.all([
        apiClient.GET("/v1/stores"),
        apiClient.GET("/v1/components", {
          params: { query: { include_blacklisted: false } },
        }),
      ]);
      if (storesRes.error || !storesRes.data) {
        setStatus({ kind: "error", message: "loadFailed" });
        return;
      }
      if (componentsRes.data) setComponents(componentsRes.data.items);
      setStatus({ kind: "ok", items: storesRes.data.items });
      await Promise.all(storesRes.data.items.map((s) => loadPricesFor(s.id)));
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "unknown",
      });
    }
  }, [loadPricesFor]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleAddStore = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setError(null);
      if (!draft.name.trim()) return;
      setSubmitting(true);
      try {
        const {
          data,
          error: err,
          response,
        } = await apiClient.POST("/v1/stores", {
          body: {
            name: draft.name.trim(),
            location: draft.location.trim() || null,
            is_primary: draft.isPrimary,
          },
        });
        if (err || !data) {
          setError(tForm("saveFailed", { message: `HTTP ${response.status}` }));
          return;
        }
        // Reload to apply primary toggling consistently
        setDraft(INITIAL_STORE_DRAFT);
        await load();
      } catch (err) {
        setError(
          tForm("saveFailed", {
            message: err instanceof Error ? err.message : "unknown",
          }),
        );
      } finally {
        setSubmitting(false);
      }
    },
    [draft, load, tForm],
  );

  const handleDeleteStore = useCallback(
    async (id: string) => {
      if (!window.confirm(t("removeConfirm"))) return;
      const { error: err } = await apiClient.DELETE("/v1/stores/{store_id}", {
        params: { path: { store_id: id } },
      });
      if (!err) await load();
    },
    [load, t],
  );

  const updatePriceDraft = (storeId: string, patch: Partial<PriceDraft>) => {
    setPriceDrafts((prev) => ({
      ...prev,
      [storeId]: { ...(prev[storeId] ?? INITIAL_PRICE_DRAFT), ...patch },
    }));
  };

  const handleAddPrice = useCallback(
    async (storeId: string, event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const d = priceDrafts[storeId] ?? INITIAL_PRICE_DRAFT;
      const packSize = Number(d.packSize);
      const packPrice = Number(d.packPrice);
      if (
        !d.componentId ||
        !Number.isFinite(packSize) ||
        packSize <= 0 ||
        !Number.isFinite(packPrice) ||
        packPrice < 0
      ) {
        setError(tPrices("saveFailed", { message: "invalid input" }));
        return;
      }
      const { error: err, response } = await apiClient.PUT("/v1/stores/{store_id}/prices", {
        params: { path: { store_id: storeId } },
        body: {
          component_id: d.componentId,
          pack_size: packSize,
          pack_price: packPrice,
        },
      });
      if (err) {
        setError(tPrices("saveFailed", { message: `HTTP ${response.status}` }));
        return;
      }
      setPriceDrafts((prev) => ({ ...prev, [storeId]: INITIAL_PRICE_DRAFT }));
      await loadPricesFor(storeId);
    },
    [loadPricesFor, priceDrafts, tPrices],
  );

  const handleRemovePrice = useCallback(
    async (storeId: string, priceId: string) => {
      await apiClient.DELETE("/v1/stores/{store_id}/prices/{price_id}", {
        params: { path: { store_id: storeId, price_id: priceId } },
      });
      await loadPricesFor(storeId);
    },
    [loadPricesFor],
  );

  return (
    <div className="grid gap-4">
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
        status.items.map((store) => {
          const prices = pricesByStore[store.id] ?? [];
          const draftP = priceDrafts[store.id] ?? INITIAL_PRICE_DRAFT;
          return (
            <Card key={store.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="grid h-10 w-10 place-items-center rounded-xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
                      <Store className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <div className="grid">
                      <CardTitle className="flex items-center gap-2">
                        {store.name}
                        {store.is_primary && (
                          <Badge variant="brand">
                            <Star className="mr-1 h-3 w-3" aria-hidden="true" />
                            {t("primary")}
                          </Badge>
                        )}
                      </CardTitle>
                      {store.location && (
                        <p className="text-sm text-[color:var(--color-muted)]">{store.location}</p>
                      )}
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={t("remove")}
                    onClick={() => void handleDeleteStore(store.id)}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="grid gap-3">
                <div className="grid gap-2">
                  <p className="text-sm font-medium">{tPrices("title")}</p>
                  {prices.length === 0 ? (
                    <p className="text-sm text-[color:var(--color-muted)]">{tPrices("empty")}</p>
                  ) : (
                    <ul className="grid gap-2">
                      {prices.map((p) => {
                        const c = componentsById.get(p.component_id);
                        return (
                          <li
                            key={p.id}
                            className="flex items-center justify-between gap-2 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-2 text-sm"
                          >
                            <span className="font-medium">{c?.name ?? p.component_id}</span>
                            <span className="flex items-center gap-2 tabular-nums">
                              <Badge>{p.pack_size} g</Badge>
                              <Badge variant="brand">
                                {p.pack_price.toFixed(2)} {tPrices("currency")}
                              </Badge>
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                aria-label={tPrices("remove")}
                                onClick={() => void handleRemovePrice(store.id, p.id)}
                              >
                                <Trash2 className="h-4 w-4" aria-hidden="true" />
                              </Button>
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                <form
                  className="grid gap-2 border-t border-[color:var(--color-border)] pt-3"
                  onSubmit={(e) => void handleAddPrice(store.id, e)}
                >
                  <label className="grid gap-1 text-sm">
                    <span>{tPrices("component")}</span>
                    <Select
                      value={draftP.componentId}
                      onChange={(e) => updatePriceDraft(store.id, { componentId: e.target.value })}
                      required
                    >
                      <option value="" disabled>
                        —
                      </option>
                      {components.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <label className="grid gap-1 text-sm">
                      <span>{tPrices("packSize")} (g)</span>
                      <Input
                        type="number"
                        inputMode="decimal"
                        step="any"
                        min="0"
                        value={draftP.packSize}
                        onChange={(e) => updatePriceDraft(store.id, { packSize: e.target.value })}
                        required
                      />
                    </label>
                    <label className="grid gap-1 text-sm">
                      <span>
                        {tPrices("packPrice")} ({tPrices("currency")})
                      </span>
                      <Input
                        type="number"
                        inputMode="decimal"
                        step="0.01"
                        min="0"
                        value={draftP.packPrice}
                        onChange={(e) => updatePriceDraft(store.id, { packPrice: e.target.value })}
                        required
                      />
                    </label>
                  </div>
                  <Button type="submit" size="sm">
                    {tPrices("addNew")}
                  </Button>
                </form>
              </CardContent>
            </Card>
          );
        })}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t("addNew")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleAddStore(e)} className="grid gap-3">
            <label className="grid gap-1 text-sm">
              <span>{tForm("name")}</span>
              <Input
                value={draft.name}
                onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
                placeholder={tForm("namePlaceholder")}
                required
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span>{tForm("location")}</span>
              <Input
                value={draft.location}
                onChange={(e) => setDraft((d) => ({ ...d, location: e.target.value }))}
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={draft.isPrimary}
                onChange={(e) => setDraft((d) => ({ ...d, isPrimary: e.target.checked }))}
              />
              <span>{tForm("isPrimary")}</span>
            </label>
            {error && (
              <output aria-live="polite" className="text-sm text-[color:var(--color-danger)]">
                {error}
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
