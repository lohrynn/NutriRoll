"use client";

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
      style={{
        display: "block",
        padding: "0.75rem 1rem",
        borderRadius: "0.5rem",
        border: "1px solid currentColor",
        opacity: 0.85,
      }}
    >
      {status.kind === "loading" && <span>Checking API…</span>}
      {status.kind === "ok" && <span>API OK — server v{status.version}</span>}
      {status.kind === "error" && <span>API error: {status.message}</span>}
    </output>
  );
}
