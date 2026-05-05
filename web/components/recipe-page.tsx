"use client";

import { Clock, Flame, Pause, Play, RotateCcw, Salad, Sparkles, Utensils } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api/client";
import type { Category } from "@/lib/components/types";
import { requestNotificationPermission, useCookTimer } from "@/lib/cook/timers";
import { readRolledMealFromStorage } from "@/lib/recipe/storage";
import type { Recipe } from "@/lib/recipe/types";
import type { RolledBowl } from "@/lib/roll/types";

type PageState = "loading" | "missing" | "ready" | "error";
type PolishMode = "off" | "concise" | "enthusiastic";

const CATEGORY_ICON: Record<Category, typeof Salad> = {
  base: Utensils,
  vegetable: Salad,
  sauce: Flame,
  topping: Sparkles,
};

function readBowlFromStorage(): RolledBowl | null {
  return readRolledMealFromStorage()?.bowl ?? null;
}

function formatMmSs(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const mm = String(Math.floor(safe / 60)).padStart(2, "0");
  const ss = String(safe % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

/**
 * Plays a short beep without bundling an audio asset. Falls back to a
 * no-op if the browser blocks AudioContext (e.g. iOS without prior gesture).
 */
function playDoneTone(): void {
  if (typeof window === "undefined") return;
  const Ctor =
    window.AudioContext ??
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return;
  try {
    const ctx = new Ctor();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = 880;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.55);
    oscillator.connect(gain).connect(ctx.destination);
    oscillator.start();
    oscillator.stop(ctx.currentTime + 0.6);
    oscillator.onended = () => {
      void ctx.close();
    };
  } catch {
    // ignore — autoplay policy
  }
}

interface BlockTimerProps {
  totalMinutes: number;
}

function BlockTimer({ totalMinutes }: BlockTimerProps) {
  const t = useTranslations("recipe.timer");
  const totalSeconds = Math.max(0, Math.floor(totalMinutes * 60));
  const [remaining, setRemaining] = useState<number>(totalSeconds);
  const [running, setRunning] = useState<boolean>(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const firedRef = useRef<boolean>(false);

  const stop = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setRunning(false);
  }, []);

  useEffect(() => {
    if (!running) return;
    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          if (!firedRef.current) {
            firedRef.current = true;
            playDoneTone();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [running]);

  useEffect(() => {
    if (remaining === 0 && running) {
      stop();
    }
  }, [remaining, running, stop]);

  const reset = () => {
    stop();
    firedRef.current = false;
    setRemaining(totalSeconds);
  };

  if (totalSeconds === 0) return null;

  const done = remaining === 0;

  return (
    <div className="flex items-center gap-2">
      <output
        aria-live="polite"
        className={`tabular-nums text-sm font-semibold ${
          done ? "text-[color:var(--color-danger)]" : "text-[color:var(--color-fg)]"
        }`}
      >
        {formatMmSs(remaining)}
      </output>
      {!running && !done && (
        <Button
          type="button"
          size="icon"
          variant="ghost"
          aria-label={t("start")}
          onClick={() => setRunning(true)}
          className="h-11 w-11"
        >
          <Play aria-hidden size={14} />
        </Button>
      )}
      {running && (
        <Button
          type="button"
          size="icon"
          variant="ghost"
          aria-label={t("pause")}
          onClick={stop}
          className="h-11 w-11"
        >
          <Pause aria-hidden size={14} />
        </Button>
      )}
      {(done || remaining < totalSeconds) && (
        <Button
          type="button"
          size="icon"
          variant="ghost"
          aria-label={t("reset")}
          onClick={reset}
          className="h-11 w-11"
        >
          <RotateCcw aria-hidden size={14} />
        </Button>
      )}
    </div>
  );
}

interface StepTimerProps {
  stepKey: string;
  durationSec: number;
  blockTitle: string;
  stepText: string;
}

/** Phase 14. Per-step countdown with sessionStorage persistence and PWA
 * notifications. Falls back to the existing in-page beep when notifications
 * are denied or unsupported. */
function StepTimer({ stepKey, durationSec, blockTitle, stepText }: StepTimerProps) {
  const t = useTranslations("recipe.timer");
  const timer = useCookTimer({
    key: stepKey,
    durationSec,
    notificationTitle: t("notify.title", { block: blockTitle }),
    notificationBody: stepText,
    onExpireFallback: playDoneTone,
  });

  if (durationSec === 0) return null;

  return (
    <div className="flex items-center gap-1">
      <output
        aria-live="polite"
        className={`tabular-nums text-xs font-semibold ${
          timer.done ? "text-[color:var(--color-danger)]" : "text-[color:var(--color-fg)]"
        }`}
      >
        {formatMmSs(timer.remainingSec)}
      </output>
      {!timer.running && !timer.done && (
        <Button
          type="button"
          size="icon"
          variant="ghost"
          aria-label={t("start")}
          onClick={() => {
            void requestNotificationPermission();
            timer.start();
          }}
          className="h-11 w-11"
        >
          <Play aria-hidden size={12} />
        </Button>
      )}
      {timer.running && (
        <Button
          type="button"
          size="icon"
          variant="ghost"
          aria-label={t("pause")}
          onClick={timer.pause}
          className="h-11 w-11"
        >
          <Pause aria-hidden size={12} />
        </Button>
      )}
      {(timer.done || (timer.active && !timer.running && timer.remainingSec < durationSec)) && (
        <Button
          type="button"
          size="icon"
          variant="ghost"
          aria-label={t("reset")}
          onClick={timer.reset}
          className="h-11 w-11"
        >
          <RotateCcw aria-hidden size={12} />
        </Button>
      )}
    </div>
  );
}

export function RecipePage() {
  const t = useTranslations("recipe");
  const tCategory = useTranslations("components.category");
  const tMethod = useTranslations("components.method");
  const [pageState, setPageState] = useState<PageState>("loading");
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [bowl, setBowl] = useState<RolledBowl | null>(null);
  const [isRefreshingSteps, setIsRefreshingSteps] = useState(false);
  const [polishMode, setPolishMode] = useState<PolishMode>("off");
  const [recipePolishEnabled, setRecipePolishEnabled] = useState(false);

  const buildRecipe = useCallback(
    async (rolledBowl: RolledBowl, polish: PolishMode, keepRecipeVisible = false) => {
      const componentIds = rolledBowl.slots
        .map((slot) => slot.component.id)
        .filter((id) => typeof id === "string" && id.length > 0);
      if (componentIds.length === 0) {
        setErrorMessage(null);
        setPageState("missing");
        return;
      }
      if (keepRecipeVisible) {
        setIsRefreshingSteps(true);
      } else {
        setPageState("loading");
      }
      setErrorMessage(null);

      const request =
        polish === "off"
          ? {
              body: {
                component_ids: componentIds,
                forced_methods: {},
              },
            }
          : {
              params: { query: { polish } },
              body: {
                component_ids: componentIds,
                forced_methods: {},
              },
            };

      try {
        const { data, error, response } = await apiClient.POST("/v1/recipe", request);
        if (error || !data) {
          const message =
            typeof error === "object" && error && "detail" in error
              ? JSON.stringify(error.detail)
              : `HTTP ${response.status}`;
          setErrorMessage(message);
          if (!keepRecipeVisible) setPageState("error");
          return;
        }
        setRecipe(data);
        setPageState("ready");
      } catch (err) {
        setErrorMessage(err instanceof Error ? err.message : "unknown");
        if (!keepRecipeVisible) setPageState("error");
      } finally {
        setIsRefreshingSteps(false);
      }
    },
    [],
  );

  useEffect(() => {
    const storedBowl = readBowlFromStorage();
    if (!storedBowl || storedBowl.slots.length === 0) {
      setPageState("missing");
      return;
    }
    setBowl(storedBowl);
    void buildRecipe(storedBowl, "off");
  }, [buildRecipe]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const result = await apiClient.GET("/v1/me/profile/llm");
      if (cancelled || !result.data) return;
      setRecipePolishEnabled((result.data.enabled_features ?? []).includes("recipe_polish"));
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onPolishModeChange = (nextMode: PolishMode) => {
    if (nextMode === polishMode || bowl === null) return;
    setPolishMode(nextMode);
    void buildRecipe(bowl, nextMode, recipe !== null);
  };

  const showPolishToggle = recipePolishEnabled && recipe !== null;

  const renderStepSkeleton = (count: number) => (
    <div aria-hidden className="grid gap-2">
      {Array.from({ length: Math.max(1, count) }, (_, idx) => (
        <div key={`step-skeleton-${count}-${idx}`} className="grid gap-2">
          <Skeleton className="h-3 w-12 rounded-md" />
          <Skeleton className={idx % 2 === 0 ? "h-4 w-full rounded-md" : "h-4 w-4/5 rounded-md"} />
        </div>
      ))}
    </div>
  );

  const renderRecipeSkeleton = () => (
    <section aria-label={t("blocks")} className="grid gap-3 animate-fade-in-up">
      <Card>
        <CardContent className="flex items-center gap-3 p-4">
          <Skeleton className="h-10 w-10 rounded-xl" />
          <div className="grid flex-1 gap-2">
            <Skeleton className="h-3 w-24 rounded-md" />
            <Skeleton className="h-6 w-36 rounded-md" />
          </div>
        </CardContent>
      </Card>
      <ol className="grid gap-3">
        {Array.from({ length: 3 }, (_, idx) => (
          <li key={`recipe-skeleton-${idx}`}>
            <Card>
              <CardContent className="grid gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <Skeleton className="h-10 w-10 rounded-xl" />
                    <div className="grid gap-2">
                      <Skeleton className="h-5 w-40 rounded-md" />
                      <div className="flex gap-2">
                        <Skeleton className="h-6 w-20 rounded-full" />
                        <Skeleton className="h-6 w-20 rounded-full" />
                      </div>
                    </div>
                  </div>
                  <Skeleton className="h-8 w-24 rounded-full" />
                </div>
                {renderStepSkeleton(3)}
              </CardContent>
            </Card>
          </li>
        ))}
      </ol>
    </section>
  );

  return (
    <div className="grid gap-4">
      {pageState === "loading" && recipe === null && (
        <>
          <output aria-live="polite" className="text-sm text-[color:var(--color-muted)] animate-soft-pulse">
            {t("loading")}
          </output>
          {renderRecipeSkeleton()}
        </>
      )}

      {pageState === "missing" && (
        <Card>
          <CardContent className="grid gap-3">
            <p className="text-sm">{t("missing")}</p>
            <Link
              href="/roll"
              className="inline-flex min-h-11 items-center text-sm font-medium text-[color:var(--color-brand)] underline-offset-2 transition-colors hover:underline"
            >
              {t("backToRoll")} →
            </Link>
          </CardContent>
        </Card>
      )}

      {errorMessage !== null && (
        <output
          aria-live="polite"
          className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
        >
          {t("error", { message: errorMessage })}
        </output>
      )}

      {recipe !== null && pageState === "ready" && (
        <section aria-label={t("blocks")} className="grid gap-3 animate-fade-in-up">
          <Card>
            <CardContent className="flex items-center gap-3 p-4">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
                <Clock aria-hidden size={20} />
              </span>
              <div>
                <div className="text-xs uppercase tracking-wide text-[color:var(--color-muted)]">
                  {t("blocks")}
                </div>
                <div className="font-semibold">
                  {t("totalMinutes", { minutes: recipe.total_minutes })}
                </div>
              </div>
            </CardContent>
          </Card>

          {showPolishToggle && (
            <Card>
              <CardContent className="flex items-center justify-between gap-3 p-4">
                <div className="grid gap-1">
                  <div className="text-sm font-medium">{t("polish.label")}</div>
                  <div className="text-xs text-[color:var(--color-muted)]">
                    {isRefreshingSteps ? t("polish.loading") : t("polish.help")}
                  </div>
                </div>
                <div
                  role="group"
                  aria-label={t("polish.label")}
                  className="flex items-center gap-1 rounded-full bg-[color:var(--color-surface-2)] p-1"
                >
                  {(["off", "concise", "enthusiastic"] as const).map((option) => (
                    <Button
                      key={option}
                      type="button"
                      size="sm"
                      variant={polishMode === option ? "secondary" : "ghost"}
                      aria-pressed={polishMode === option}
                      onClick={() => onPolishModeChange(option)}
                      disabled={isRefreshingSteps}
                      className="min-h-11 rounded-full px-4 transition-all duration-300"
                    >
                      {t(`polish.${option}`)}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <ol className="grid gap-3">
            {recipe.blocks.map((block) => {
              const Icon = CATEGORY_ICON[block.category];
              return (
                <li key={`${block.category}-${block.method}-${block.title}`}>
                  <Card>
                    <CardContent className="grid gap-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
                            <Icon aria-hidden size={18} />
                          </span>
                          <div className="grid gap-1">
                            <div className="font-semibold leading-tight">{block.title}</div>
                            <div className="flex flex-wrap gap-1.5">
                              <Badge variant="brand">{tCategory(block.category)}</Badge>
                              <Badge variant="neutral">{tMethod(block.method)}</Badge>
                            </div>
                          </div>
                        </div>
                        <span className="flex shrink-0 items-center gap-2">
                          <span className="rounded-full bg-[color:var(--color-surface-2)] px-2.5 py-1 text-xs font-medium tabular-nums">
                            {t("minutes", { minutes: block.total_minutes })}
                          </span>
                          <BlockTimer totalMinutes={block.total_minutes} />
                        </span>
                      </div>
                      {block.steps.length > 0 &&
                        (isRefreshingSteps ? (
                          renderStepSkeleton(block.steps.length)
                        ) : (
                          <ol className="grid gap-1 border-l-2 border-[color:var(--color-border)] pl-3 text-sm">
                            {block.steps.map((step, idx) => {
                              const next = block.steps[idx + 1];
                              const stepDurationMin =
                                next !== undefined
                                  ? Math.max(0, next.offset_min - step.offset_min)
                                  : Math.max(0, block.total_minutes - step.offset_min);
                              const stepKey = `${block.category}:${block.method}:${block.title}:${idx}`;
                              return (
                                <li key={`${step.text}-${idx}`} className="flex items-center gap-2">
                                  <span className="shrink-0 text-xs tabular-nums text-[color:var(--color-muted)]">
                                    {String(step.offset_min).padStart(2, "0")}:00
                                  </span>
                                  <span className="flex-1">{step.text}</span>
                                  <StepTimer
                                    stepKey={stepKey}
                                    durationSec={Math.round(stepDurationMin * 60)}
                                    blockTitle={block.title}
                                    stepText={step.text}
                                  />
                                </li>
                              );
                            })}
                          </ol>
                        ))}
                    </CardContent>
                  </Card>
                </li>
              );
            })}
          </ol>
        </section>
      )}
    </div>
  );
}
