import { getTranslations } from "next-intl/server";

import { PageShell } from "@/components/page-shell";
import { PlanPage } from "@/components/plan-page";

export default async function PlanRoute() {
  const t = await getTranslations("plan");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <PlanPage />
    </PageShell>
  );
}
