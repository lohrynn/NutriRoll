import { getTranslations } from "next-intl/server";

import { PageShell } from "@/components/page-shell";
import { PantryPage } from "@/components/pantry-page";

export default async function PantryRoute() {
  const t = await getTranslations("pantry");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <PantryPage />
    </PageShell>
  );
}
