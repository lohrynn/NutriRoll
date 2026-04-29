"use client";

import { Clock, Flame, Pause, Play, RotateCcw, Salad, Sparkles, Utensils } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import type { Category } from "@/lib/components/types";
import { ROLLED_BOWL_STORAGE_KEY } from "@/lib/recipe/storage";
import type { Recipe } from "@/lib/recipe/types";
import type { RolledBowl } from "@/lib/roll/types";

type Status =
  | { kind: "loading" }
  | { kind: "missing" }
  | { kind: "building" }
  | { kind: "ok"; recipe: Recipe }
  | { kind: "error"; message: string };

const CATEGORY_ICON: Record<Category, typeof Salad> = {
  base: Utensils,
  vegetable: Salad,
  sauce: Flame,
  topping: Sparkles,
};

function readBowlFromStorage(): RolledBowl | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(ROLLED_BOWL_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as RolledBowl;
  } catch {
    return null;
  }
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
        >
          <Play aria-hidden size={14} />
        </Button>
      )}
      {running && (
        <Button type="button" size="icon" variant="ghost" aria-label={t("pause")} onClick={stop}>
          <Pause aria-hidden size={14} />
        </Button>
      )}
      {(done || remaining < totalSeconds) && (
        <Button type="button" size="icon" variant="ghost" aria-label={t("reset")} onClick={reset}>
          <RotateCcw aria-hidden size={14} />
        </Button>
      )}
    </div>
  );
}

export function RecipePage() {
  const t = useTranslations("recipe");
  const tCategory = useTranslations("components.category");
  const tMethod = useTranslations("components.method");
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  const buildRecipe = useCallback(async (bowl: RolledBowl) => {
    setStatus({ kind: "building" });
    try {
      const { data, error, response } = await apiClient.POST("/v1/recipe", {
        body: {
          component_ids: bowl.slots.map((s) => s.component.id),
          forced_methods: {},
        },
      });
      if (error || !data) {
        const message =
          typeof error === "object" && error && "detail" in error
            ? JSON.stringify(error.detail)
            : `HTTP ${response.status}`;
        setStatus({ kind: "error", message });
        return;
      }
      setStatus({ kind: "ok", recipe: data });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "unknown",
      });
    }
  }, []);

  useEffect(() => {
    const bowl = readBowlFromStorage();
    if (!bowl) {
      setStatus({ kind: "missing" });
      return;
    }
    void buildRecipe(bowl);
  }, [buildRecipe]);

  return (
    <div className="grid gap-4">
      {(status.kind === "loading" || status.kind === "building") && (
        <output
          aria-live="polite"
          className="rounded-xl bg-[color:var(--color-surface-2)] p-3 text-sm text-[color:var(--color-muted)]"
        >
          {t("loading")}
        </output>
      )}

      {status.kind === "missing" && (
        <Card>
          <CardContent className="grid gap-3">
            <p className="text-sm">{t("missing")}</p>
            <Link
              href="/roll"
              className="text-sm font-medium text-[color:var(--color-brand)] underline-offset-2 hover:underline"
            >
              {t("backToRoll")} →
            </Link>
          </CardContent>
        </Card>
      )}

      {status.kind === "error" && (
        <output
          aria-live="polite"
          className="rounded-xl border border-[color:var(--color-danger)]/30 bg-[color:var(--color-danger)]/10 p-3 text-sm text-[color:var(--color-danger)]"
        >
          {t("error", { message: status.message })}
        </output>
      )}

      {status.kind === "ok" && (
        <section aria-label={t("blocks")} className="grid gap-3">
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
                  {t("totalMinutes", { minutes: status.recipe.total_minutes })}
                </div>
              </div>
            </CardContent>
          </Card>

          <ol className="grid gap-3">
            {status.recipe.blocks.map((block) => {
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
                      {block.steps.length > 0 && (
                        <ol className="grid gap-1 border-l-2 border-[color:var(--color-border)] pl-3 text-sm">
                          {block.steps.map((step, idx) => (
                            <li key={`${step.text}-${idx}`} className="flex gap-2">
                              <span className="shrink-0 text-xs tabular-nums text-[color:var(--color-muted)]">
                                {String(step.offset_min).padStart(2, "0")}:00
                              </span>
                              <span>{step.text}</span>
                            </li>
                          ))}
                        </ol>
                      )}
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
