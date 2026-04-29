/**
 * Phase 14 — persisted cooking timers.
 *
 * The recipe page renders a per-step countdown next to every step. State is
 * mirrored to ``sessionStorage`` so a tab refresh mid-cook resumes the
 * countdown instead of resetting it. We deliberately use a different
 * sessionStorage key from the rolled bowl so the two storages cannot
 * collide (workflow rule "sessionStorage key ownership").
 *
 * The hook is intentionally tiny — no global registry or context — because
 * each timer is independent and identified by a stable string key.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export const COOK_TIMERS_STORAGE_KEY = "nutriroll.cookTimers";
const NOTIFICATION_TAG_PREFIX = "nutriroll-cook-";

type StoredTimer = {
  /** Wall-clock ms when the countdown reaches zero. Null = paused/idle. */
  endsAt: number | null;
  /** Remaining seconds when paused. Null = not paused. */
  pausedRemaining: number | null;
  /** Original duration in seconds, used by Reset. */
  durationSec: number;
};

type Registry = Record<string, StoredTimer>;

function readRegistry(): Registry {
  if (typeof window === "undefined") return {};
  const raw = window.sessionStorage.getItem(COOK_TIMERS_STORAGE_KEY);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === "object") return parsed as Registry;
  } catch {
    /* ignore corrupted storage */
  }
  return {};
}

function writeRegistry(next: Registry): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(COOK_TIMERS_STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* quota exceeded — non-fatal */
  }
}

function patchRegistry(key: string, value: StoredTimer | null): void {
  const reg = readRegistry();
  if (value === null) {
    delete reg[key];
  } else {
    reg[key] = value;
  }
  writeRegistry(reg);
}

/**
 * Request notification permission lazily on first user gesture.
 * Returns the resulting permission state (or "denied" when unsupported).
 */
export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (typeof window === "undefined" || !("Notification" in window)) return "denied";
  if (Notification.permission === "granted" || Notification.permission === "denied") {
    return Notification.permission;
  }
  try {
    return await Notification.requestPermission();
  } catch {
    return "denied";
  }
}

function fireNotification(key: string, title: string, body: string): boolean {
  if (typeof window === "undefined" || !("Notification" in window)) return false;
  if (Notification.permission !== "granted") return false;
  try {
    new Notification(title, {
      body,
      tag: `${NOTIFICATION_TAG_PREFIX}${key}`,
      // ``renotify`` is intentionally omitted: the tag dedupes across pages
      // so the user never sees stacked alerts for the same step.
    });
    return true;
  } catch {
    return false;
  }
}

export type CookTimerState = {
  /** ``true`` once the user has tapped Start at least once. */
  active: boolean;
  /** ``true`` while the countdown is decrementing. */
  running: boolean;
  /** Seconds left; equals ``durationSec`` while idle, ``0`` once expired. */
  remainingSec: number;
  /** ``true`` after expiry; cleared by ``reset()``. */
  done: boolean;
};

export type CookTimerControls = CookTimerState & {
  start: () => void;
  pause: () => void;
  reset: () => void;
};

export type UseCookTimerOptions = {
  /** Stable key identifying the step (e.g. ``"block-2:step-3"``). */
  key: string;
  durationSec: number;
  /** Title shown on the OS notification when the timer expires. */
  notificationTitle: string;
  /** Body text shown on the notification. */
  notificationBody: string;
  /** Optional fallback that fires when notifications are unavailable. */
  onExpireFallback?: () => void;
};

/**
 * Persisted countdown for a single recipe step. The hook is the single
 * source of truth: components render a button row + ``mm:ss`` label.
 */
export function useCookTimer(options: UseCookTimerOptions): CookTimerControls {
  const { key, durationSec, notificationTitle, notificationBody, onExpireFallback } = options;

  // We only seed the initial state from sessionStorage once on mount so
  // that durationSec changes (e.g. recipe re-fetched with new timings)
  // don't accidentally wipe a running timer.
  const initialState = useRef<CookTimerState>({
    active: false,
    running: false,
    remainingSec: durationSec,
    done: false,
  });
  if (!initialState.current.active) {
    const stored = readRegistry()[key];
    if (stored) {
      const now = Date.now();
      if (stored.endsAt !== null) {
        const remaining = Math.max(0, Math.round((stored.endsAt - now) / 1000));
        initialState.current = {
          active: true,
          running: remaining > 0,
          remainingSec: remaining,
          done: remaining === 0,
        };
      } else if (stored.pausedRemaining !== null) {
        initialState.current = {
          active: true,
          running: false,
          remainingSec: stored.pausedRemaining,
          done: false,
        };
      }
    }
  }

  const [state, setState] = useState<CookTimerState>(initialState.current);
  const expireFiredRef = useRef<boolean>(state.done);

  // Tick loop: when running, recompute remaining from the persisted endsAt
  // so wall-clock drift (background tab throttling) self-corrects.
  useEffect(() => {
    if (!state.running) return;
    const stored = readRegistry()[key];
    const endsAt = stored?.endsAt ?? null;
    if (endsAt === null) return;
    const tick = () => {
      const remaining = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
      setState((prev) => {
        if (!prev.running) return prev;
        if (remaining <= 0) {
          if (!expireFiredRef.current) {
            expireFiredRef.current = true;
            const ok = fireNotification(key, notificationTitle, notificationBody);
            if (!ok) onExpireFallback?.();
          }
          return { active: true, running: false, remainingSec: 0, done: true };
        }
        return { ...prev, remainingSec: remaining };
      });
    };
    tick();
    const handle = window.setInterval(tick, 1000);
    return () => {
      window.clearInterval(handle);
    };
  }, [state.running, key, notificationTitle, notificationBody, onExpireFallback]);

  const start = useCallback(() => {
    expireFiredRef.current = false;
    const remaining = state.remainingSec > 0 ? state.remainingSec : durationSec;
    const endsAt = Date.now() + remaining * 1000;
    patchRegistry(key, { endsAt, pausedRemaining: null, durationSec });
    setState({ active: true, running: true, remainingSec: remaining, done: false });
  }, [state.remainingSec, durationSec, key]);

  const pause = useCallback(() => {
    setState((prev) => {
      if (!prev.running) return prev;
      patchRegistry(key, {
        endsAt: null,
        pausedRemaining: prev.remainingSec,
        durationSec,
      });
      return { ...prev, running: false };
    });
  }, [key, durationSec]);

  const reset = useCallback(() => {
    expireFiredRef.current = false;
    patchRegistry(key, null);
    setState({ active: false, running: false, remainingSec: durationSec, done: false });
  }, [key, durationSec]);

  return { ...state, start, pause, reset };
}
