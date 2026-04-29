import { getTranslations } from "next-intl/server";

import { HistoryPageView } from "@/components/history-page";
import { PageShell } from "@/components/page-shell";

export default async function HistoryRoute() {
  const t = await getTranslations("history");
  return (
    <PageShell title={t("title")} description={t("subtitle")}>
      <HistoryPageView />
    </PageShell>
  );
}
