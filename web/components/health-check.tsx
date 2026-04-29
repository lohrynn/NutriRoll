"use client";

import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { apiClient } from "@/lib/api/client";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; version: string }
  | { kind: "error"; message: string };

export function HealthCheck() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data, error } = await apiClient.GET("/healthz");
        if (cancelled) return;
        if (error || !data) {
          setStatus({ kind: "error", message: "API unreachable" });
          return;
        }
        setStatus({ kind: "ok", version: data.version });
      } catch (err) {
        if (cancelled) return;
        setStatus({
          kind: "error",
          message: err instanceof Error ? err.message : "unknown error",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <output
      aria-live="polite"
      className="flex items-center gap-2.5 text-sm text-[color:var(--color-muted)]"
    >
      {status.kind === "loading" && (
        <>
          <Loader2 aria-hidden size={16} className="animate-spin" />
          <span>Checking API…</span>
        </>
      )}
      {status.kind === "ok" && (
        <>
          <CheckCircle2 aria-hidden size={16} className="text-[color:var(--color-success)]" />
          <span>API OK · v{status.version}</span>
        </>
      )}
      {status.kind === "error" && (
        <>
          <XCircle aria-hidden size={16} className="text-[color:var(--color-danger)]" />
          <span>API error: {status.message}</span>
        </>
      )}
    </output>
  );
}
