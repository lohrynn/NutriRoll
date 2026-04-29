import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { COOK_TIMERS_STORAGE_KEY, useCookTimer } from "@/lib/cook/timers";

describe("useCookTimer", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  const baseOpts = {
    key: "block:0",
    durationSec: 60,
    notificationTitle: "done",
    notificationBody: "step",
  };

  it("starts idle with full duration and persists nothing until start", () => {
    const { result } = renderHook(() => useCookTimer(baseOpts));
    expect(result.current.remainingSec).toBe(60);
    expect(result.current.running).toBe(false);
    expect(result.current.done).toBe(false);
    expect(window.sessionStorage.getItem(COOK_TIMERS_STORAGE_KEY)).toBeNull();
  });

  it("counts down and persists endsAt in sessionStorage when started", () => {
    const { result } = renderHook(() => useCookTimer(baseOpts));
    act(() => {
      result.current.start();
    });
    expect(result.current.running).toBe(true);
    const stored = JSON.parse(window.sessionStorage.getItem(COOK_TIMERS_STORAGE_KEY) ?? "{}");
    expect(stored["block:0"].endsAt).toBeTypeOf("number");
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.remainingSec).toBeLessThan(60);
  });

  it("fires fallback and marks done when the countdown reaches zero", () => {
    const onExpireFallback = vi.fn();
    const { result } = renderHook(() =>
      useCookTimer({ ...baseOpts, durationSec: 1, onExpireFallback }),
    );
    act(() => {
      result.current.start();
    });
    act(() => {
      vi.advanceTimersByTime(1500);
    });
    expect(result.current.done).toBe(true);
    expect(result.current.remainingSec).toBe(0);
    expect(onExpireFallback).toHaveBeenCalledTimes(1);
  });

  it("reset clears storage and returns to idle state", () => {
    const { result } = renderHook(() => useCookTimer(baseOpts));
    act(() => {
      result.current.start();
    });
    act(() => {
      result.current.reset();
    });
    expect(result.current.running).toBe(false);
    expect(result.current.done).toBe(false);
    expect(result.current.remainingSec).toBe(60);
    const stored = JSON.parse(window.sessionStorage.getItem(COOK_TIMERS_STORAGE_KEY) ?? "{}");
    expect(stored["block:0"]).toBeUndefined();
  });
});
