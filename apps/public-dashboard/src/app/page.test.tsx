import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "./page";

describe("home page composition", () => {
  it("renders the complete static dashboard without remote visual assets", () => {
    render(<HomePage />);

    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getByText("Demonstration data only")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Syria Situation Desk" })).toBeVisible();
    expect(screen.getByRole("region", { name: "Syria situation map" })).toBeVisible();
    expect(screen.getByRole("region", { name: "Activity timeline" })).toBeVisible();
    expect(screen.getByRole("region", { name: "Incident feed" })).toBeVisible();
    expect(screen.getAllByRole("link", { name: "Methodology" }).length).toBeGreaterThan(0);

    for (const element of document.querySelectorAll("img[src], script[src]")) {
      expect(element.getAttribute("src")).not.toMatch(/^https?:/);
    }
  });
});
