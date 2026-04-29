import { type InputHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, type, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      type={type ?? "text"}
      className={cn(
        "h-10 w-full rounded-xl border border-[color:var(--color-border)]",
        "bg-[color:var(--color-surface)] px-3 text-sm",
        "placeholder:text-[color:var(--color-muted)]",
        "focus:border-[color:var(--color-brand)] focus-visible:outline-none",
        className,
      )}
      {...props}
    />
  );
});
