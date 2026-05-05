import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CookPage } from "@/components/cook-page";
import { ROLLED_BOWL_STORAGE_KEY } from "@/lib/recipe/storage";
import enMessages from "@/messages/en.json";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
    POST: (...args: unknown[]) => postMock(...args),
  },
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

function wrap(node: ReactNode) {
  return (
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {node}
    </NextIntlClientProvider>
  );
}

const SAMPLE_COMPONENT = {
  id: "11111111-1111-1111-1111-111111111111",
  category: "base",
  name: "Brown rice",
  image_url: null,
  default_portion: { value: 80, unit: "g" },
  macros_per_100g: { kcal: 123, carbs_g: 25, protein_g: 3, fat_g: 1, fiber_g: 2 },
  default_cooking_method: "boil",
  cooking_methods: [
    { method: "boil", approx_minutes: 25, can_cook_with_others: true, notes: null },
  ],
  flavor_tags: [],
  dietary_tags: [],
  allergens: [],
  shelf_life_days: null,
  blacklisted: false,
};

const SAMPLE_BOWL = {
  slots: [
    {
      component: SAMPLE_COMPONENT,
      score: 0.42,
      reasons: [],
    },
  ],
};

const SAMPLE_RECIPE = {
  total_minutes: 25,
  blocks: [
    {
      category: "base",
      title: "Base: Brown rice",
      method: "boil",
      total_minutes: 25,
      can_cook_with_others: true,
      components: [SAMPLE_COMPONENT],
      steps: [{ text: "Boil brown rice for 25 minutes.", offset_min: 0, duration_min: 25 }],
    },
  ],
};

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  getMock.mockResolvedValue({ data: undefined, error: undefined, response: { status: 200 } });
  window.sessionStorage.clear();
});

afterEach(() => {
  cleanup();
});

describe("CookPage", () => {
  it("shows the fallback when no rolled meal is available", async () => {
    render(wrap(<CookPage />));

    await waitFor(() => {
      expect(screen.getByText(enMessages.cook.noBowl)).toBeInTheDocument();
    });
  });

  it("renders the cooking view when a rolled meal is available", async () => {
    window.sessionStorage.setItem(
      ROLLED_BOWL_STORAGE_KEY,
      JSON.stringify({ bowl: SAMPLE_BOWL, portions: 2 }),
    );
    postMock.mockResolvedValueOnce({
      data: SAMPLE_RECIPE,
      error: undefined,
      response: { status: 200 },
    });

    render(wrap(<CookPage />));

    expect(await screen.findByText("Base: Brown rice")).toBeInTheDocument();
    expect(screen.getByText("Boil brown rice for 25 minutes.")).toBeInTheDocument();
    expect(screen.queryByText(enMessages.cook.noBowl)).not.toBeInTheDocument();
  });
});
