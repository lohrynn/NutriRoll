import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import enMessages from "@/messages/en.json";

const postMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    POST: (...args: unknown[]) => postMock(...args),
  },
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import { RecipePage } from "@/components/recipe-page";
import { ROLLED_BOWL_STORAGE_KEY } from "@/lib/recipe/storage";

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
    { method: "boil", approx_minutes: 25, can_cook_with_others: false, notes: null },
  ],
  flavor_tags: [],
  dietary_tags: [],
  allergens: [],
  shelf_life_days: null,
  blacklisted: false,
};

const SAMPLE_BOWL = {
  slots: [{ component: SAMPLE_COMPONENT, score: 0.42, reasons: [] }],
};

const SAMPLE_RECIPE = {
  total_minutes: 25,
  blocks: [
    {
      category: "base",
      title: "Base: Brown rice",
      method: "boil",
      total_minutes: 25,
      can_cook_with_others: false,
      components: [SAMPLE_COMPONENT],
      steps: [
        { text: "Boil brown rice (80g per portion) for ~25 min.", offset_min: 0, duration_min: 25 },
      ],
    },
  ],
};

beforeEach(() => {
  postMock.mockReset();
  window.sessionStorage.clear();
});

afterEach(() => {
  cleanup();
});

describe("RecipePage", () => {
  it("shows a missing-bowl message when sessionStorage is empty", async () => {
    render(wrap(<RecipePage />));
    await waitFor(() => {
      expect(screen.getByText(/no bowl found/i)).toBeInTheDocument();
    });
    expect(postMock).not.toHaveBeenCalled();
  });

  it("builds a recipe from the stashed bowl and renders blocks", async () => {
    window.sessionStorage.setItem(ROLLED_BOWL_STORAGE_KEY, JSON.stringify(SAMPLE_BOWL));
    postMock.mockResolvedValueOnce({
      data: SAMPLE_RECIPE,
      error: undefined,
      response: { status: 200 },
    });

    render(wrap(<RecipePage />));

    expect(await screen.findByText("Base: Brown rice")).toBeInTheDocument();
    expect(screen.getByText("Boil brown rice (80g per portion) for ~25 min.")).toBeInTheDocument();
    expect(postMock).toHaveBeenCalledWith(
      "/v1/recipe",
      expect.objectContaining({
        body: expect.objectContaining({
          component_ids: ["11111111-1111-1111-1111-111111111111"],
        }),
      }),
    );
  });

  it("surfaces an error when the recipe endpoint fails", async () => {
    window.sessionStorage.setItem(ROLLED_BOWL_STORAGE_KEY, JSON.stringify(SAMPLE_BOWL));
    postMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: { code: "incompatible_forced_method" } },
      response: { status: 422 },
    });

    render(wrap(<RecipePage />));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/incompatible_forced_method/);
    });
  });
});
