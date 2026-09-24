import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardClient } from "./DashboardClient";
import { loadPublicDataset } from "../lib/load-public-dataset";
import { loadPublicNewsWire } from "../lib/load-public-news-wire";

const renderDashboard = () =>
  render(
    <DashboardClient
      dataset={loadPublicDataset()}
      newsWire={loadPublicNewsWire()}
    />,
  );

describe("DashboardClient", () => {
  it("filters by category and announces the result count", () => {
    renderDashboard();

    fireEvent.click(screen.getByRole("checkbox", { name: /infrastructure/i }));

    expect(screen.getByRole("status")).toHaveTextContent("1 incident");
    expect(screen.getAllByTestId("incident-card")).toHaveLength(1);
  });

  it("switches to Arabic without clearing active filters", () => {
    renderDashboard();
    fireEvent.click(screen.getByRole("checkbox", { name: /infrastructure/i }));

    fireEvent.click(screen.getByRole("button", { name: "العربية" }));

    expect(screen.getByTestId("dashboard-root")).toHaveAttribute("dir", "rtl");
    expect(screen.getByRole("checkbox", { name: /البنية التحتية/i })).toBeChecked();
    expect(screen.getAllByTestId("incident-card")).toHaveLength(1);
  });

  it("renders HTML-like text without creating executable elements", () => {
    const dataset = structuredClone(loadPublicDataset());
    dataset.incidents[0].title.en = "<img src=x onerror=alert(1)>";

    render(<DashboardClient dataset={dataset} newsWire={loadPublicNewsWire()} />);

    expect(screen.getAllByText("<img src=x onerror=alert(1)>")).not.toHaveLength(0);
    expect(document.querySelector("img[src='x']")).toBeNull();
  });

  it("opens and closes incident detail using buttons", () => {
    renderDashboard();

    fireEvent.click(screen.getAllByRole("button", { name: /view details/i })[0]);
    expect(screen.getByRole("complementary")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /close details/i }));
    expect(screen.queryByRole("complementary")).toBeNull();
  });
});
