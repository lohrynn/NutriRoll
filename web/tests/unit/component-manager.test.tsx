import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import enMessages from "@/messages/en.json";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
    POST: (...args: unknown[]) => postMock(...args),
  },
}));

import { ComponentManager } from "@/components/component-manager";

function wrap(node: ReactNode) {
  return (
    <NextIntlClientProvider locale="en" messages={enMessages}>
      {node}
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("ComponentManager", () => {
  it("renders empty state when API returns no items", async () => {
    getMock.mockResolvedValue({
      data: { items: [], total: 0 },
      error: undefined,
      response: { status: 200 },
    });

    render(wrap(<ComponentManager />));

    expect(await screen.findByText(enMessages.components.empty)).toBeInTheDocument();
  });

  it("renders fetched components", async () => {
    getMock.mockResolvedValue({
      data: {
        items: [
          {
            id: "11111111-1111-1111-1111-111111111111",
            category: "base",
            name: "Brown rice",
            image_url: null,
            default_portion: { value: 80, unit: "g" },
            macros_per_100g: {
              kcal: 123,
              carbs_g: 25,
              protein_g: 3,
              fat_g: 1,
              fiber_g: 2,
            },
            default_cooking_method: "boil",
            cooking_methods: [
              { method: "boil", approx_minutes: 25, can_cook_with_others: true, notes: null },
            ],
            flavor_tags: [],
            dietary_tags: [],
            allergens: [],
            shelf_life_days: null,
            blacklisted: false,
          },
        ],
        total: 1,
      },
      error: undefined,
      response: { status: 200 },
    });

    render(wrap(<ComponentManager />));

    expect(await screen.findByText("Brown rice")).toBeInTheDocument();
  });

  it("shows an error when the API fails", async () => {
    getMock.mockResolvedValue({
      data: undefined,
      error: { detail: "boom" },
      response: { status: 500 },
    });

    render(wrap(<ComponentManager />));

    const output = await screen.findByText(/Could not load components/i);
    expect(output).toBeInTheDocument();
  });

  it("submits a new component via the form", async () => {
    getMock.mockResolvedValue({
      data: { items: [], total: 0 },
      error: undefined,
      response: { status: 200 },
    });
    postMock.mockResolvedValue({
      data: {
        id: "22222222-2222-2222-2222-222222222222",
        category: "base",
        name: "Quinoa",
        image_url: null,
        default_portion: { value: 80, unit: "g" },
        macros_per_100g: { kcal: 120, carbs_g: 21, protein_g: 4, fat_g: 2, fiber_g: 3 },
        default_cooking_method: "boil",
        cooking_methods: [
          { method: "boil", approx_minutes: null, can_cook_with_others: true, notes: null },
        ],
        flavor_tags: [],
        dietary_tags: [],
        allergens: [],
        shelf_life_days: null,
        blacklisted: false,
      },
      error: undefined,
      response: { status: 201 },
    });

    render(wrap(<ComponentManager />));

    await screen.findByText(enMessages.components.empty);
    fireEvent.change(screen.getByLabelText(enMessages.components.form.name), {
      target: { value: "Quinoa" },
    });
    fireEvent.click(screen.getByRole("button", { name: enMessages.components.form.submit }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledTimes(1);
    });
    expect(await screen.findByText("Quinoa")).toBeInTheDocument();
  });
});
