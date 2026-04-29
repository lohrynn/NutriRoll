"use client";

import { Boxes, ChefHat, ClipboardList, ShoppingBasket, User } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

interface Tab {
  href: string;
  /** Top-level tab key in messages.nav. */
  key: "roll" | "plan" | "shop" | "cook" | "me";
  Icon: typeof ChefHat;
  /** Other route prefixes that should highlight this tab. */
  matches?: readonly string[];
}

const TABS: readonly Tab[] = [
  { href: "/roll", key: "roll", Icon: ChefHat, matches: ["/roll", "/recipe"] },
  { href: "/history", key: "plan", Icon: ClipboardList, matches: ["/history"] },
  { href: "/shop", key: "shop", Icon: ShoppingBasket, matches: ["/shop", "/stores"] },
  { href: "/cook", key: "cook", Icon: Boxes, matches: ["/cook"] },
  { href: "/me", key: "me", Icon: User, matches: ["/me", "/components", "/pantry"] },
];

export function BottomNav() {
  const t = useTranslations("nav");
  const pathname = usePathname() ?? "/";

  return (
    <nav
      aria-label={t("primary")}
      className={cn(
        "fixed inset-x-0 bottom-0 z-40 border-t border-[color:var(--color-border)]",
        "bg-[color:var(--color-surface)]/85 backdrop-blur-xl",
        "pb-[var(--safe-bottom)]",
      )}
    >
      <ul className="mx-auto grid max-w-xl grid-cols-5 px-2">
        {TABS.map(({ href, key, Icon, matches }) => {
          const active = (matches ?? [href]).some(
            (m) => pathname === m || pathname.startsWith(`${m}/`),
          );
          return (
            <li key={key}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center gap-0.5 px-2 py-2.5 text-[11px]",
                  "transition-colors",
                  active
                    ? "text-[color:var(--color-brand)]"
                    : "text-[color:var(--color-muted)] hover:text-[color:var(--color-fg)]",
                )}
              >
                <Icon aria-hidden size={22} strokeWidth={active ? 2.4 : 1.8} className="shrink-0" />
                <span className={cn("font-medium", active && "font-semibold")}>{t(key)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
