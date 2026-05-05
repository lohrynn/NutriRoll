"use client";

import { ChefHat, ShoppingBasket, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api/client";
import { readRolledMealFromStorage } from "@/lib/recipe/storage";
import type { RolledBowl } from "@/lib/roll/types";
import type { ShoppingListRead } from "@/lib/shopping/types";
import type { StoreRead } from "@/lib/stores/types";

type Status =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ok"; list: ShoppingListRead }
  | { kind: "error"; message: string };

export function ShopPage() {
  const t = useTranslations("shop");
  const tRow = useTranslations("shop.row");

  const [bowl, setBowl] = useState<RolledBowl | null>(null);
  const [stores, setStores] = useState<StoreRead[]>([]);
  const [storeId, setStoreId] = useState<string>("");
  const [portions, setPortions] = useState<number>(2);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  useEffect(() => {
    const storedMeal = readRolledMealFromStorage();
    if (storedMeal) {
      setBowl(storedMeal.bowl);
      setPortions(storedMeal.portions);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      const { data } = await apiClient.GET("/v1/stores");
      if (data) {
        setStores(data.items);
        const primary = data.items.find((s) => s.is_primary) ?? data.items[0];
        if (primary) setStoreId(primary.id);
      }
    })();
  }, []);

  const componentIds = useMemo(() => {
    if (!bowl) return [] as string[];
    return bowl.slots.map((s) => s.component.id);
  }, [bowl]);

  const handleBuild = useCallback(async () => {
    if (componentIds.length === 0) return;
    setStatus({ kind: "loading" });
    try {
      const { data, error, response } = await apiClient.POST("/v1/shopping-list", {
        body: {
          component_ids: componentIds,
          portions,
          store_id: storeId || null,
          use_pantry: true,
        },
      });
      if (error || !data) {
        setStatus({
          kind: "error",
          message: `HTTP ${response.status}`,
        });
        return;
      }
      setStatus({ kind: "ok", list: data });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "unknown",
      });
    }
  }, [componentIds, portions, storeId]);

  if (!bowl) {
    return (
      <Card>
        <CardContent className="grid gap-3">
          <p className="text-sm text-[color:var(--color-muted)]">{t("noBowl")}</p>
          <Button asChild size="sm">
            <Link href="/roll">
              <ChefHat className="h-4 w-4" aria-hidden="true" />
              {t("goToRoll")}
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShoppingBasket
              className="h-4 w-4 text-[color:var(--color-brand)]"
              aria-hidden="true"
            />
            {bowl.slots.map((s) => s.component.name).join(" + ")}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid grid-cols-2 gap-2">
            <label className="grid gap-1 text-sm">
              <span>{t("portions")}</span>
              <Input
                type="number"
                inputMode="numeric"
                min="1"
                max="20"
                value={portions}
                onChange={(e) => setPortions(Math.max(1, Number(e.target.value) || 1))}
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span>{t("store")}</span>
              <Select value={storeId} onChange={(e) => setStoreId(e.target.value)}>
                <option value="">—</option>
                {stores.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </label>
          </div>
          {stores.length === 0 && (
            <p className="text-xs text-[color:var(--color-muted)]">
              {t.rich("storeMissing", {
                link: (chunks) => (
                  <Link href="/stores" className="text-[color:var(--color-brand)] underline">
                    {chunks}
                  </Link>
                ),
              })}
            </p>
          )}
          <Button
            type="button"
            onClick={() => void handleBuild()}
            disabled={status.kind === "loading"}
          >
            {status.kind === "loading" ? t("building") : t("build")}
          </Button>
        </CardContent>
      </Card>

      {status.kind === "error" && (
        <Card className="border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/5">
          <CardContent>
            <output aria-live="polite" className="text-[color:var(--color-danger)]">
              {t("error", { message: status.message })}
            </output>
          </CardContent>
        </Card>
      )}

      {status.kind === "ok" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-[color:var(--color-brand)]" aria-hidden="true" />
                {t("totalLine", {
                  amount: status.list.total_price.toFixed(2),
                  currency: "EUR",
                })}
              </span>
              <Badge>
                {t("perPortion", {
                  amount: (status.list.total_price / status.list.portions).toFixed(2),
                  currency: "EUR",
                })}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-2">
              {status.list.items.map((item) => (
                <li
                  key={item.component.id}
                  className="grid gap-1 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{item.component.name}</span>
                    {item.line_price == null ? (
                      <Badge variant="warning">{tRow("missingPrice")}</Badge>
                    ) : (
                      <Badge variant="brand" className="tabular-nums">
                        {tRow("lineTotal", {
                          amount: item.line_price.toFixed(2),
                          currency: "EUR",
                        })}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-[color:var(--color-muted)] tabular-nums">
                    {tRow("needsGrams", {
                      grams: Math.round(item.quantity_to_buy),
                    })}
                    {item.pack_size != null && item.packs_to_buy != null && (
                      <>
                        {" · "}
                        {tRow("buyPacks", {
                          packs: item.packs_to_buy,
                          size: item.pack_size,
                        })}
                      </>
                    )}
                  </p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
