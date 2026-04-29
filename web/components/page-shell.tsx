import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Standard scaffold every page sits in: a vertical stack with consistent
 * page padding, a hero header, and a content area below. The fixed
 * bottom nav lives outside this component (in the root layout).
 */
export function PageShell({
  title,
  description,
  action,
  children,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <main
      className={cn(
        "mx-auto w-full max-w-xl px-4 pt-[max(env(safe-area-inset-top),1rem)]",
        "pb-[calc(var(--safe-bottom)+5.5rem)]",
        className,
      )}
    >
      <header className="mb-6 mt-2 grid gap-2">
        <div className="flex items-start justify-between gap-3">
          <div className="grid gap-1">
            <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
            {description && (
              <p className="text-sm text-[color:var(--color-muted)] leading-relaxed">
                {description}
              </p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      </header>
      <div className="grid gap-4">{children}</div>
    </main>
  );
}
