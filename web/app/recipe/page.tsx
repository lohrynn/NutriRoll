import { getTranslations } from "next-intl/server";
import Link from "next/link";

import { PageShell } from "@/components/page-shell";
import { RecipePage } from "@/components/recipe-page";

export default async function RecipeRoute() {
  const t = await getTranslations("recipe");
  return (
    <PageShell
      title={t("title")}
      description={t("subtitle")}
      action={
        <Link
          href="/roll"
          className="text-xs font-medium text-[color:var(--color-muted)] underline-offset-2 hover:underline"
        >
          ← {t("backToRoll")}
        </Link>
      }
    >
      <RecipePage />
    </PageShell>
  );
}
