"use client";

import { ArrowRight, Check, ChefHat, Dice5, Leaf, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { COMMON_ALLERGENS, DIETARY_MODES, type DietaryMode } from "@/lib/profile/types";

type Step = 0 | 1 | 2;

export function OnboardingPage() {
  const t = useTranslations("onboarding");
  const tDietary = useTranslations("roll.dietary");
  const router = useRouter();

  const [step, setStep] = useState<Step>(0);
  const [dietaryMode, setDietaryMode] = useState<DietaryMode>("");
  const [allergens, setAllergens] = useState<Set<string>>(() => new Set());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleAllergen = (a: string) => {
    setAllergens((prev) => {
      const next = new Set(prev);
      if (next.has(a)) next.delete(a);
      else next.add(a);
      return next;
    });
  };

  const finish = async () => {
    setSaving(true);
    setError(null);
    const result = await apiClient.PUT("/v1/me/profile", {
      body: {
        dietary_mode: dietaryMode,
        allergens: [...allergens],
        default_time_budget_min: null,
        goal: "",
        locale: "en",
        onboarded: true,
        llm_weekly_recap_enabled: false,
      },
    });
    setSaving(false);
    if (!result.data) {
      setError(`HTTP ${result.response.status}`);
      return;
    }
    if (typeof window !== "undefined") {
      window.localStorage.setItem("nutriroll.onboarded", "1");
      // Cookie powers the middleware redirect — value is read but never trusted
      // for server-side decisions (the profile endpoint remains source of truth).
      document.cookie = "nutriroll-onboarded=1; path=/; max-age=31536000; samesite=lax";
    }
    router.push("/roll");
  };

  return (
    <div className="grid gap-4">
      <div
        className="grid grid-cols-3 gap-1.5"
        role="progressbar"
        aria-label={t("progress")}
        aria-valuemin={1}
        aria-valuemax={3}
        aria-valuenow={step + 1}
        tabIndex={-1}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className={
              i <= step
                ? "h-1.5 rounded-full bg-[color:var(--color-brand)]"
                : "h-1.5 rounded-full bg-[color:var(--color-border)]"
            }
          />
        ))}
      </div>

      {step === 0 && (
        <Card>
          <CardContent className="grid gap-4">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
              <ChefHat aria-hidden size={22} strokeWidth={2} />
            </span>
            <h2 className="text-xl font-semibold leading-tight">{t("welcome.title")}</h2>
            <p className="text-sm text-[color:var(--color-muted)]">{t("welcome.body")}</p>
            <ul className="grid gap-2 text-sm">
              <li className="flex items-center gap-2">
                <Dice5 aria-hidden size={16} className="text-[color:var(--color-brand)]" />
                {t("welcome.bullet1")}
              </li>
              <li className="flex items-center gap-2">
                <Leaf aria-hidden size={16} className="text-[color:var(--color-brand)]" />
                {t("welcome.bullet2")}
              </li>
              <li className="flex items-center gap-2">
                <Sparkles aria-hidden size={16} className="text-[color:var(--color-brand)]" />
                {t("welcome.bullet3")}
              </li>
            </ul>
            <div className="flex justify-between gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  if (typeof document !== "undefined") {
                    document.cookie =
                      "nutriroll-onboarded=1; path=/; max-age=31536000; samesite=lax";
                  }
                  router.push("/roll");
                }}
              >
                {t("skip")}
              </Button>
              <Button type="button" onClick={() => setStep(1)}>
                {t("next")}
                <ArrowRight aria-hidden size={14} />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <CardContent className="grid gap-4">
            <h2 className="text-xl font-semibold leading-tight">{t("dietary.title")}</h2>
            <p className="text-sm text-[color:var(--color-muted)]">{t("dietary.body")}</p>
            <div className="grid gap-2">
              {DIETARY_MODES.map((mode) => {
                const active = dietaryMode === mode;
                const labelKey = mode === "" ? "any" : (mode as Exclude<DietaryMode, "">);
                return (
                  <button
                    key={mode || "any"}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setDietaryMode(mode)}
                    className={
                      active
                        ? "flex items-center justify-between rounded-2xl border-2 border-[color:var(--color-brand)] bg-[color:var(--color-brand-soft)] p-3 text-left text-sm font-medium"
                        : "flex items-center justify-between rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] p-3 text-left text-sm transition hover:border-[color:var(--color-brand)]"
                    }
                  >
                    <span>{tDietary(labelKey)}</span>
                    {active && (
                      <Check aria-hidden size={16} className="text-[color:var(--color-brand)]" />
                    )}
                  </button>
                );
              })}
            </div>
            <div className="flex justify-between gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setStep(0)}>
                {t("back")}
              </Button>
              <Button type="button" onClick={() => setStep(2)}>
                {t("next")}
                <ArrowRight aria-hidden size={14} />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <CardContent className="grid gap-4">
            <h2 className="text-xl font-semibold leading-tight">{t("allergens.title")}</h2>
            <p className="text-sm text-[color:var(--color-muted)]">{t("allergens.body")}</p>
            <div className="flex flex-wrap gap-2">
              {COMMON_ALLERGENS.map((a) => {
                const active = allergens.has(a);
                return (
                  <button
                    key={a}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleAllergen(a)}
                    className={
                      active
                        ? "rounded-full bg-[color:var(--color-brand)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-brand-fg)] shadow-[var(--shadow-pop)] transition active:scale-95"
                        : "rounded-full border border-[color:var(--color-border)] bg-[color:var(--color-surface-2)] px-3 py-1.5 text-xs font-medium text-[color:var(--color-fg)] transition hover:border-[color:var(--color-brand)] active:scale-95"
                    }
                  >
                    {t(`allergens.tag.${a}`)}
                  </button>
                );
              })}
            </div>
            {error && (
              <output
                aria-live="polite"
                className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
              >
                {t("error", { message: error })}
              </output>
            )}
            <div className="flex justify-between gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setStep(1)}>
                {t("back")}
              </Button>
              <Button type="button" onClick={() => void finish()} disabled={saving}>
                {saving ? t("saving") : t("finish")}
                <ChefHat aria-hidden size={14} />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
