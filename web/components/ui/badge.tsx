import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant = "neutral",
  ...props
}: HTMLAttributes<HTMLSpanElement> & {
  variant?: "neutral" | "brand" | "success" | "danger" | "warning";
}) {
  const palette: Record<string, string> = {
    neutral: "bg-[color:var(--color-surface-2)] text-[color:var(--color-muted)]",
    brand: "bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]",
    success: "bg-[color:var(--color-success)]/15 text-[color:var(--color-success)]",
    danger: "bg-[color:var(--color-danger)]/12 text-[color:var(--color-danger)]",
    warning: "bg-[color:var(--color-warning)]/18 text-[color:var(--color-fg)]",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase",
        palette[variant],
        className,
      )}
      {...props}
    />
  );
}
