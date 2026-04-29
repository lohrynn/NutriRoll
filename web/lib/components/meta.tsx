"use client";

import { type ReactNode, createContext, useContext, useEffect, useState } from "react";

import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { DEFAULT_EXPIRY_WARNING_DAYS } from "@/lib/pantry/freshness";
import type { Category, CookingMethod, Equipment } from "./types";

export type ComponentMeta = components["schemas"]["ComponentMeta"];

let cachedPromise: Promise<ComponentMeta> | null = null;

export function fetchComponentMeta(): Promise<ComponentMeta> {
  if (cachedPromise) return cachedPromise;
  cachedPromise = apiClient.GET("/v1/meta/components").then(({ data, error }) => {
    if (error || !data) {
      cachedPromise = null;
      throw new Error("Failed to fetch component meta");
    }
    return data;
  });
  return cachedPromise;
}

const Ctx = createContext<ComponentMeta | null>(null);

export function ComponentMetaProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<ComponentMeta | null>(null);
  useEffect(() => {
    let alive = true;
    fetchComponentMeta()
      .then((m) => {
        if (alive) setMeta(m);
      })
      .catch(() => {
        // Provider stays null; consumers render a loading state.
      });
    return () => {
      alive = false;
    };
  }, []);
  return <Ctx.Provider value={meta}>{children}</Ctx.Provider>;
}

/** Returns the loaded component meta, or `null` while it is still loading. */
export function useComponentMeta(): ComponentMeta | null {
  return useContext(Ctx);
}

/** Returns the allowed cooking methods for a category, or an empty list while loading. */
export function useAllowedMethods(category: Category): readonly CookingMethod[] {
  const meta = useComponentMeta();
  return meta?.allowed_methods[category] ?? [];
}

/** Returns the list of categories, or an empty list while loading. */
export function useCategories(): readonly Category[] {
  const meta = useComponentMeta();
  return meta?.categories ?? [];
}

/**
 * Returns the expiry warning window (days) from the server, falling back to
 * `DEFAULT_EXPIRY_WARNING_DAYS` while the meta is still loading (M9).
 */
export function useExpiryWarningDays(): number {
  const meta = useComponentMeta();
  return meta?.expiry_warning_days ?? DEFAULT_EXPIRY_WARNING_DAYS;
}

/**
 * Returns the human-readable display label for a category, falling back to
 * the raw enum value if meta hasn't loaded yet (M4).
 *
 * The label is derived server-side from the enum value (title-cased with
 * underscores replaced by spaces), so any new category added to the Python
 * `Category` enum is rendered correctly without requiring a frontend code change.
 */
export function useCategoryLabel(category: Category): string {
  const meta = useComponentMeta();
  return (
    meta?.category_labels?.[category] ??
    category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

/** Phase 13. Returns the equipment vocabulary, or `[]` while loading. */
export function useEquipment(): readonly Equipment[] {
  const meta = useComponentMeta();
  return meta?.equipment ?? [];
}

/** Phase 13. Sensible defaults for new users (oven + stovetop + microwave). */
export function useDefaultEquipment(): readonly Equipment[] {
  const meta = useComponentMeta();
  return meta?.default_equipment ?? [];
}

/**
 * Phase 13. Returns the equipment required by a given cooking method, or `[]`
 * if the method has no requirements (e.g. raw / no_prep / custom). Used by the
 * Roll page to render a per-bowl equipment icon strip without duplicating the
 * algorithm's hard-filter rules.
 */
export function useMethodRequirements(): Readonly<Record<CookingMethod, readonly Equipment[]>> {
  const meta = useComponentMeta();
  return (meta?.method_requirements ?? {}) as unknown as Readonly<
    Record<CookingMethod, readonly Equipment[]>
  >;
}
