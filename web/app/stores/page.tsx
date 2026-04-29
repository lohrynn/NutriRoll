import { getTranslations } from "next-intl/server";

import { PageShell } from "@/components/page-shell";
import { StoresPage } from "@/components/stores-page";

export default async function StoresRoute() {
  const t = await getTranslations("stores");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <StoresPage />
    </PageShell>
  );
}
