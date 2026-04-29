import {
  Boxes,
  ChefHat,
  ClipboardList,
  Refrigerator,
  ShoppingBasket,
  Star,
  Store,
} from "lucide-react";
import { getTranslations } from "next-intl/server";
import Link from "next/link";

import { HealthCheck } from "@/components/health-check";
import { PageShell } from "@/components/page-shell";
import { Card, CardContent } from "@/components/ui/card";

const TILES = [
  { href: "/roll", key: "roll", Icon: ChefHat, accent: true },
  { href: "/components", key: "components", Icon: Boxes, accent: false },
  { href: "/pantry", key: "pantry", Icon: Refrigerator, accent: false },
  { href: "/shop", key: "shop", Icon: ShoppingBasket, accent: false },
  { href: "/stores", key: "stores", Icon: Store, accent: false },
  { href: "/cook", key: "cook", Icon: Star, accent: false },
  { href: "/history", key: "history", Icon: ClipboardList, accent: false },
] as const;

export default async function HomePage() {
  const t = await getTranslations("home");
  const tApp = await getTranslations("app");

  return (
    <PageShell title={tApp("title")} description={tApp("tagline")}>
      <Card className="overflow-hidden">
        <div className="relative isolate p-6">
          <div
            aria-hidden
            className="absolute inset-0 -z-10 bg-gradient-to-br from-[color:var(--color-brand)]/15 via-transparent to-[color:var(--color-brand)]/5"
          />
          <div className="grid gap-3">
            <p className="text-xs font-semibold uppercase tracking-widest text-[color:var(--color-brand)]">
              {t("hero.eyebrow")}
            </p>
            <h2 className="text-2xl font-semibold leading-tight">{t("hero.title")}</h2>
            <p className="text-sm text-[color:var(--color-muted)]">{t("hero.subtitle")}</p>
            <Link
              href="/roll"
              className="mt-2 inline-flex h-12 w-fit items-center gap-2 rounded-full bg-[color:var(--color-brand)] px-6 font-medium text-[color:var(--color-brand-fg)] shadow-[var(--shadow-pop)] transition active:scale-[0.98]"
            >
              <ChefHat aria-hidden size={18} strokeWidth={2.4} />
              {t("hero.cta")}
            </Link>
          </div>
        </div>
      </Card>

      <section aria-label={t("explore")} className="grid grid-cols-2 gap-3">
        {TILES.map(({ href, key, Icon, accent }) => (
          <Link
            key={key}
            href={href}
            className="group relative flex flex-col gap-2 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-4 shadow-[var(--shadow-card)] transition hover:-translate-y-0.5 hover:shadow-[var(--shadow-pop)]"
          >
            <span
              className={
                accent
                  ? "inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-[color:var(--color-brand)] text-[color:var(--color-brand-fg)]"
                  : "inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]"
              }
            >
              <Icon aria-hidden size={20} strokeWidth={2} />
            </span>
            <div className="grid gap-0.5">
              <span className="text-sm font-semibold">{t(`tiles.${key}.title`)}</span>
              <span className="text-xs text-[color:var(--color-muted)] leading-snug">
                {t(`tiles.${key}.description`)}
              </span>
            </div>
          </Link>
        ))}
      </section>

      <Card>
        <CardContent>
          <HealthCheck />
        </CardContent>
      </Card>
    </PageShell>
  );
}
