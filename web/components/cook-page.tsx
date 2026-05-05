"use client";

import { ChefHat } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { Component, type ReactNode, useEffect, useState } from "react";

import { RecipePage } from "@/components/recipe-page";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { readRolledMealFromStorage } from "@/lib/recipe/storage";

type PageState = "loading" | "missing" | "ready";

interface CookEBState {
  hasError: boolean;
}

class CookErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  CookEBState
> {
  constructor(props: { children: ReactNode; fallback: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(_error: unknown): CookEBState {
    return { hasError: true };
  }

  override render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}

function CookErrorFallback() {
  const t = useTranslations("cook");
  return (
    <Card>
      <CardContent className="grid gap-3 animate-fade-in-up">
        <p className="text-sm font-medium">{t("errorFallback.title")}</p>
        <Button type="button" size="sm" onClick={() => window.location.reload()}>
          {t("errorFallback.retry")}
        </Button>
      </CardContent>
    </Card>
  );
}

export function CookPage() {
  const t = useTranslations("cook");
  const [pageState, setPageState] = useState<PageState>("loading");

  useEffect(() => {
    const storedMeal = readRolledMealFromStorage();
    if (storedMeal && storedMeal.bowl.slots.length > 0) {
      setPageState("ready");
      return;
    }
    setPageState("missing");
  }, []);

  if (pageState === "loading") {
    return (
      <Card>
        <CardContent className="grid gap-3 animate-fade-in-up">
          <p className="text-sm text-[color:var(--color-muted)] animate-soft-pulse">{t("loading")}</p>
          <div className="grid gap-3">
            <Skeleton className="h-12 w-full rounded-2xl" />
            <Skeleton className="h-32 w-full rounded-[var(--radius-card)]" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (pageState === "missing") {
    return (
      <Card>
        <CardContent className="grid gap-3 animate-fade-in-up">
          <p className="text-sm text-[color:var(--color-muted)]">{t("noBowl")}</p>
          <Button asChild size="sm">
            <Link href="/roll">
              <ChefHat className="h-4 w-4" aria-hidden="true" />
              {t("goToRoll")}
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <CookErrorBoundary fallback={<CookErrorFallback />}>
      <div className="animate-fade-in-up">
        <RecipePage />
      </div>
    </CookErrorBoundary>
  );
}
