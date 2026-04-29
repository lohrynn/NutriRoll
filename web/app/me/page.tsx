import { Boxes, Carrot, ChevronRight, Store as StoreIcon, User } from "lucide-react";
import { getTranslations } from "next-intl/server";
import Link from "next/link";

import { PageShell } from "@/components/page-shell";
import { Card, CardContent } from "@/components/ui/card";

const TILES = [
  { href: "/components", icon: Carrot, key: "components" as const },
  { href: "/pantry", icon: Boxes, key: "pantry" as const },
  { href: "/stores", icon: StoreIcon, key: "stores" as const },
] as const;

export default async function MeRoute() {
  const t = await getTranslations("home.tiles");
  const tNav = await getTranslations("nav");
  return (
    <PageShell
      title={tNav("me")}
      description={
        <span className="inline-flex items-center gap-2">
          <User className="h-4 w-4" aria-hidden="true" />
          {tNav("primary")}
        </span>
      }
    >
      <div className="grid gap-3">
        {TILES.map(({ href, icon: Icon, key }) => (
          <Link key={href} href={href}>
            <Card className="transition hover:-translate-y-0.5 hover:shadow-[var(--shadow-pop)]">
              <CardContent className="flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[color:var(--color-brand-soft)] text-[color:var(--color-brand)]">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <div className="flex-1 grid">
                  <p className="font-semibold">{t(`${key}.title`)}</p>
                  <p className="text-sm text-[color:var(--color-muted)]">
                    {t(`${key}.description`)}
                  </p>
                </div>
                <ChevronRight
                  className="h-5 w-5 text-[color:var(--color-muted)]"
                  aria-hidden="true"
                />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </PageShell>
  );
}
