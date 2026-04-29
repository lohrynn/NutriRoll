import { getTranslations } from "next-intl/server";

import { CookPage } from "@/components/cook-page";
import { PageShell } from "@/components/page-shell";

export default async function CookRoute() {
  const t = await getTranslations("cook");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <CookPage />
    </PageShell>
  );
}
