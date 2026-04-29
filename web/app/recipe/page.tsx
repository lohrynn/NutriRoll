import { getTranslations } from "next-intl/server";

import { RecipePage } from "@/components/recipe-page";

export default async function RecipeRoute() {
  const t = await getTranslations("recipe");
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-6">
      <nav className="text-sm opacity-70">
        <a href="/roll">← {t("backToRoll")}</a>
      </nav>
      <h1 className="sr-only">{t("title")}</h1>
      <RecipePage />
    </main>
  );
}
