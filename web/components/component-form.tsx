"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { apiClient } from "@/lib/api/client";
import { useAllowedMethods, useCategories, useComponentMeta } from "@/lib/components/meta";
import {
  type Category,
  type ComponentCreate,
  type ComponentRead,
  type CookingMethod,
  MACRO_KEYS,
  type MacroKey,
  PORTION_UNITS,
  type PortionUnit,
  parseCsvList,
} from "@/lib/components/types";

interface MethodRow {
  method: CookingMethod;
  approxMinutes: string;
  canCookWithOthers: boolean;
  notes: string;
}

interface Props {
  onCreated?: (component: ComponentRead) => void;
  editId?: string;
  onUpdated?: (component: ComponentRead) => void;
  onCancel?: () => void;
  initialValues?: ComponentRead;
}

export function ComponentForm({ onCreated, editId, onUpdated, onCancel, initialValues }: Props) {
  const t = useTranslations("components.form");
  const tMethod = useTranslations("components.method");

  const [category, setCategory] = useState<Category>(() => initialValues?.category ?? "base");
  const [name, setName] = useState(() => initialValues?.name ?? "");
  const [imageUrl, setImageUrl] = useState(() => initialValues?.image_url ?? "");
  const [portionValue, setPortionValue] = useState(() =>
    initialValues?.default_portion.value != null
      ? String(initialValues.default_portion.value)
      : "80",
  );
  const [portionUnit, setPortionUnit] = useState<PortionUnit>(
    () => initialValues?.default_portion.unit ?? "g",
  );
  const [macros, setMacros] = useState<Record<MacroKey, string>>(() => {
    const initial = initialValues?.macros_per_100g;
    return Object.fromEntries(
      MACRO_KEYS.map((key) => {
        const v = initial?.[key];
        return [key, typeof v === "number" ? String(v) : "0"];
      }),
    ) as Record<MacroKey, string>;
  });
  const [flavorTags, setFlavorTags] = useState(() => initialValues?.flavor_tags?.join(", ") ?? "");
  const [dietaryTags, setDietaryTags] = useState(
    () => initialValues?.dietary_tags?.join(", ") ?? "",
  );
  const [allergens, setAllergens] = useState(() => initialValues?.allergens?.join(", ") ?? "");
  const [shelfLifeDays, setShelfLifeDays] = useState(() =>
    initialValues?.shelf_life_days != null ? String(initialValues.shelf_life_days) : "",
  );
  const [blacklisted, setBlacklisted] = useState(() => initialValues?.blacklisted ?? false);
  const [methods, setMethods] = useState<MethodRow[]>(() =>
    initialValues
      ? initialValues.cooking_methods.map((m) => ({
          method: m.method,
          approxMinutes: m.approx_minutes != null ? String(m.approx_minutes) : "",
          canCookWithOthers: m.can_cook_with_others,
          notes: m.notes ?? "",
        }))
      : [{ method: "boil", approxMinutes: "", canCookWithOthers: true, notes: "" }],
  );
  const [defaultMethod, setDefaultMethod] = useState<CookingMethod>(
    () => initialValues?.default_cooking_method ?? "boil",
  );
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const allowed = useAllowedMethods(category);
  const categories = useCategories();
  const meta = useComponentMeta();

  function changeCategory(next: Category) {
    setCategory(next);
    const allowedNext = meta?.allowed_methods[next] ?? [];
    setMethods((prev) => prev.filter((m) => allowedNext.includes(m.method)));
    const fallback = allowedNext[0];
    if (fallback === undefined) return;
    setMethods((prev) =>
      prev.length === 0
        ? [{ method: fallback, approxMinutes: "", canCookWithOthers: true, notes: "" }]
        : prev,
    );
    setDefaultMethod((current) => (allowedNext.includes(current) ? current : fallback));
  }

  function updateMethod(index: number, patch: Partial<MethodRow>): void {
    setMethods((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function addMethodRow(): void {
    const remaining = allowed.filter((m) => !methods.some((row) => row.method === m));
    const next = remaining[0];
    if (next === undefined) return;
    setMethods((prev) => [
      ...prev,
      { method: next, approxMinutes: "", canCookWithOthers: true, notes: "" },
    ]);
  }

  function removeMethodRow(index: number): void {
    setMethods((prev) => {
      if (prev.length <= 1) return prev;
      const next = prev.filter((_, i) => i !== index);
      const removed = prev[index];
      if (removed && removed.method === defaultMethod) {
        const fallback = next[0];
        if (fallback) setDefaultMethod(fallback.method);
      }
      return next;
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);

    const payload: ComponentCreate = {
      category,
      name: name.trim(),
      image_url: imageUrl.trim() === "" ? null : imageUrl.trim(),
      default_portion: { value: Number(portionValue), unit: portionUnit },
      macros_per_100g: {
        kcal: Number(macros.kcal),
        carbs_g: Number(macros.carbs_g),
        protein_g: Number(macros.protein_g),
        fat_g: Number(macros.fat_g),
        fiber_g: Number(macros.fiber_g),
      },
      default_cooking_method: defaultMethod,
      cooking_methods: methods.map((row) => ({
        method: row.method,
        approx_minutes: row.approxMinutes === "" ? null : Number(row.approxMinutes),
        can_cook_with_others: row.canCookWithOthers,
        notes: row.notes.trim() === "" ? null : row.notes.trim(),
      })),
      flavor_tags: parseCsvList(flavorTags),
      dietary_tags: parseCsvList(dietaryTags),
      allergens: parseCsvList(allergens),
      shelf_life_days: shelfLifeDays === "" ? null : Number(shelfLifeDays),
      blacklisted,
    };

    try {
      const apiCall =
        editId !== undefined
          ? apiClient.PUT("/v1/components/{component_id}", {
              params: { path: { component_id: editId } },
              body: payload,
            })
          : apiClient.POST("/v1/components", { body: payload });
      const { data, error, response } = await apiCall;
      if (error || !data) {
        setErrorMessage(
          t("errors.submitFailed", {
            message:
              typeof error === "object" && error !== null && "detail" in error
                ? String((error as { detail: unknown }).detail)
                : `HTTP ${response.status}`,
          }),
        );
        return;
      }
      if (editId !== undefined) {
        onUpdated?.(data);
      } else {
        onCreated?.(data);
        setName("");
        setImageUrl("");
        setFlavorTags("");
        setDietaryTags("");
        setAllergens("");
      }
    } catch (err) {
      setErrorMessage(
        t("errors.submitFailed", {
          message: err instanceof Error ? err.message : "unknown",
        }),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4">
      <div className="grid gap-2">
        <label htmlFor="cmp-name" className="text-sm font-medium">
          {t("name")}
        </label>
        <input
          id="cmp-name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded border border-current/30 bg-transparent px-3 py-2"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="grid gap-2">
          <label htmlFor="cmp-category" className="text-sm font-medium">
            {t("category")}
          </label>
          <select
            id="cmp-category"
            value={category}
            onChange={(e) => changeCategory(e.target.value as Category)}
            className="rounded border border-current/30 bg-transparent px-3 py-2"
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-2">
          <label htmlFor="cmp-image" className="text-sm font-medium">
            {t("image_url")}
          </label>
          <input
            id="cmp-image"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            className="rounded border border-current/30 bg-transparent px-3 py-2"
          />
        </div>
      </div>

      <fieldset className="grid gap-2 rounded border border-current/20 p-3">
        <legend className="px-1 text-sm font-medium">{t("default_portion_value")}</legend>
        <div className="grid grid-cols-2 gap-3">
          <input
            aria-label={t("default_portion_value")}
            type="number"
            min={0.1}
            step={0.1}
            required
            value={portionValue}
            onChange={(e) => setPortionValue(e.target.value)}
            className="rounded border border-current/30 bg-transparent px-3 py-2"
          />
          <select
            aria-label={t("default_portion_unit")}
            value={portionUnit}
            onChange={(e) => setPortionUnit(e.target.value as PortionUnit)}
            className="rounded border border-current/30 bg-transparent px-3 py-2"
          >
            {PORTION_UNITS.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </select>
        </div>
      </fieldset>

      <fieldset className="grid gap-2 rounded border border-current/20 p-3">
        <legend className="px-1 text-sm font-medium">{t("macros")}</legend>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {MACRO_KEYS.map((field) => (
            <label key={field} className="grid gap-1 text-xs">
              <span>{t(field)}</span>
              <input
                type="number"
                min={0}
                step={0.1}
                value={macros[field]}
                onChange={(e) => setMacros((prev) => ({ ...prev, [field]: e.target.value }))}
                className="rounded border border-current/30 bg-transparent px-2 py-1"
              />
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="grid gap-3 rounded border border-current/20 p-3">
        <legend className="px-1 text-sm font-medium">{t("cooking_methods")}</legend>
        {methods.map((row, index) => (
          <div
            key={`${row.method}-${index}`}
            className="grid gap-2 border-t border-current/10 pt-2 first:border-t-0 first:pt-0"
          >
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <select
                aria-label={t("cooking_methods")}
                value={row.method}
                onChange={(e) => updateMethod(index, { method: e.target.value as CookingMethod })}
                className="rounded border border-current/30 bg-transparent px-2 py-1"
              >
                {allowed.map((m) => (
                  <option key={m} value={m}>
                    {tMethod(m)}
                  </option>
                ))}
              </select>
              <input
                aria-label={t("approx_minutes")}
                placeholder={t("approx_minutes")}
                type="number"
                min={0}
                value={row.approxMinutes}
                onChange={(e) => updateMethod(index, { approxMinutes: e.target.value })}
                className="rounded border border-current/30 bg-transparent px-2 py-1"
              />
              <label className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={row.canCookWithOthers}
                  onChange={(e) => updateMethod(index, { canCookWithOthers: e.target.checked })}
                />
                {t("can_cook_with_others")}
              </label>
              <button
                type="button"
                onClick={() => removeMethodRow(index)}
                disabled={methods.length <= 1}
                className="rounded border border-current/30 px-2 py-1 text-xs disabled:opacity-50"
              >
                {t("removeMethod")}
              </button>
            </div>
            <input
              aria-label={t("notes")}
              placeholder={t("notes")}
              value={row.notes}
              onChange={(e) => updateMethod(index, { notes: e.target.value })}
              className="rounded border border-current/30 bg-transparent px-2 py-1 text-xs"
            />
          </div>
        ))}
        <button
          type="button"
          onClick={addMethodRow}
          disabled={methods.length >= allowed.length}
          className="self-start rounded border border-current/30 px-3 py-1 text-xs disabled:opacity-50"
        >
          {t("addMethod")}
        </button>
        <div className="grid gap-1">
          <label htmlFor="cmp-default-method" className="text-xs">
            {t("default_cooking_method")}
          </label>
          <select
            id="cmp-default-method"
            value={defaultMethod}
            onChange={(e) => setDefaultMethod(e.target.value as CookingMethod)}
            className="rounded border border-current/30 bg-transparent px-2 py-1"
          >
            {methods.map((row) => (
              <option key={row.method} value={row.method}>
                {tMethod(row.method)}
              </option>
            ))}
          </select>
        </div>
      </fieldset>

      <div className="grid gap-2">
        <label htmlFor="cmp-flavor" className="text-sm font-medium">
          {t("flavor_tags")}
        </label>
        <input
          id="cmp-flavor"
          value={flavorTags}
          onChange={(e) => setFlavorTags(e.target.value)}
          className="rounded border border-current/30 bg-transparent px-3 py-2"
        />
      </div>
      <div className="grid gap-2">
        <label htmlFor="cmp-dietary" className="text-sm font-medium">
          {t("dietary_tags")}
        </label>
        <input
          id="cmp-dietary"
          value={dietaryTags}
          onChange={(e) => setDietaryTags(e.target.value)}
          className="rounded border border-current/30 bg-transparent px-3 py-2"
        />
      </div>
      <div className="grid gap-2">
        <label htmlFor="cmp-allergens" className="text-sm font-medium">
          {t("allergens")}
        </label>
        <input
          id="cmp-allergens"
          value={allergens}
          onChange={(e) => setAllergens(e.target.value)}
          className="rounded border border-current/30 bg-transparent px-3 py-2"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="grid gap-2">
          <label htmlFor="cmp-shelf" className="text-sm font-medium">
            {t("shelf_life_days")}
          </label>
          <input
            id="cmp-shelf"
            type="number"
            min={0}
            value={shelfLifeDays}
            onChange={(e) => setShelfLifeDays(e.target.value)}
            className="rounded border border-current/30 bg-transparent px-3 py-2"
          />
        </div>
        <label className="flex items-end gap-2 pb-2 text-sm">
          <input
            type="checkbox"
            checked={blacklisted}
            onChange={(e) => setBlacklisted(e.target.checked)}
          />
          {t("blacklisted")}
        </label>
      </div>

      {errorMessage !== null ? (
        <output aria-live="polite" className="text-sm text-red-600">
          {errorMessage}
        </output>
      ) : null}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="self-start rounded border border-current/40 px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {submitting ? t("submitting") : t("submit")}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="self-start rounded border border-current/30 px-4 py-2 text-sm font-medium"
          >
            {t("cancel")}
          </button>
        )}
      </div>
    </form>
  );
}
