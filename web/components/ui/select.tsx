import { type SelectHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      className={cn(
        "h-10 w-full rounded-xl border border-[color:var(--color-border)]",
        "bg-[color:var(--color-surface)] px-3 text-sm appearance-none",
        "bg-[url('data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2210%22%20height%3D%226%22%20viewBox%3D%220%200%2010%206%22%3E%3Cpath%20fill%3D%22%23999%22%20d%3D%22M0%200l5%206%205-6z%22%2F%3E%3C%2Fsvg%3E')]",
        "bg-no-repeat bg-[right_0.75rem_center] pr-9",
        "focus:border-[color:var(--color-brand)] focus-visible:outline-none",
        className,
      )}
      {...props}
    />
  );
});
