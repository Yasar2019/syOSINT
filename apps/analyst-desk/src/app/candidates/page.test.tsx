import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
const { apiMock } = vi.hoisted(() => ({ apiMock: vi.fn() }));
vi.mock("../../lib/api", () => ({ api: apiMock }));
vi.mock("../actions", () => ({ addCandidate: vi.fn(), reviewCandidate: vi.fn() }));
import Candidates from "./page";
const checks = { accessibility_checked: true, relevance_checked: true, identity_checked: true, provenance_checked: true, policy_checked: false };
const candidate = { id: 3, platform: "web", canonical_url: "https://example.org", name: "<script>alert(1)</script>", language: "mixed", suggestion_reason: "Public reporting", status: "accepted", created_at: "2026-09-29T12:00:00Z", updated_at: "2026-09-30T12:00:00Z" };
describe("Private candidate review", () => {
  beforeEach(() => { apiMock.mockReset(); apiMock.mockResolvedValue([]); });
  it("offers manual submission and explains that acceptance never activates collection", async () => {
    render(await Candidates({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText(/No candidates/)).toBeTruthy();
    expect(screen.getByLabelText("Display name").getAttribute("maxlength")).toBe("250");
    expect(screen.getByLabelText("Suggestion reason").hasAttribute("required")).toBe(true);
    expect(screen.getByText(/does not start collection/)).toBeTruthy();
  });
  it("shows an offline alert without presenting a failed retrieval as an empty queue", async () => {
    apiMock.mockRejectedValue(new Error("offline"));
    render(await Candidates({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("alert").textContent).toMatch(/Local API unavailable/);
    expect(screen.queryByText(/No candidates/)).toBeNull();
  });
  it.each(["pending", "accepted", "rejected"])("requests the %s filter", async (status) => {
    render(await Candidates({ searchParams: Promise.resolve({ status }) }));
    expect(apiMock).toHaveBeenCalledWith(`/candidates?status=${status}`);
  });
  it("defaults malformed filters to pending", async () => {
    render(await Candidates({ searchParams: Promise.resolve({ status: "invalid&limit=999" }) }));
    expect(apiMock).toHaveBeenCalledWith("/candidates?status=pending");
  });
  it("retains rejection history after acceptance and renders untrusted text with five explicit checks", async () => {
    apiMock.mockImplementation((path: string) => Promise.resolve(path.startsWith("/candidates?") ? [candidate] : { ...candidate, reviews: [
      { id: 1, candidate_id: 3, decision: "rejected", reason: "Policy unclear", checks, created_at: "2026-09-29T12:00:00Z" },
      { id: 2, candidate_id: 3, decision: "accepted", reason: "Policy resolved", checks: { ...checks, policy_checked: true }, created_at: "2026-09-30T12:00:00Z" },
    ] }));
    const { container } = render(await Candidates({ searchParams: Promise.resolve({ status: "accepted" }) }));
    expect(apiMock).toHaveBeenCalledWith("/candidates/3");
    expect(screen.getByText("Policy unclear")).toBeTruthy();
    expect(screen.getByText("Policy resolved")).toBeTruthy();
    expect(screen.getByText(candidate.name)).toBeTruthy();
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByRole("link", { name: candidate.name }).getAttribute("rel")).toBe("noopener noreferrer");
    expect(screen.getAllByRole("checkbox").map((input) => input.getAttribute("name"))).toEqual(["accessibility_checked", "relevance_checked", "identity_checked", "provenance_checked", "policy_checked"]);
    expect(screen.getByLabelText("Review reason").hasAttribute("required")).toBe(true);
    expect(screen.getByText(/Collection\/reuse policy: unchecked/)).toBeTruthy();
  });
  it("makes the oldest of 101 rejected candidates discoverable while preserving status", async () => {
    const rows = Array.from({ length: 101 }, (_, index) => ({ ...candidate, id: 101 - index, name: `Candidate ${101 - index}`, status: "rejected" }));
    apiMock.mockImplementation((path: string) => {
      const url = new URL(`http://local${path}`);
      if (url.pathname === "/candidates") {
        const offset = Number(url.searchParams.get("offset") ?? 0);
        return Promise.resolve(rows.slice(offset, offset + 100));
      }
      const id = Number(url.pathname.split("/").at(-1));
      return Promise.resolve({ ...rows.find((row) => row.id === id), reviews: id === 1 ? [{ id: 1, candidate_id: 1, decision: "rejected", reason: "Oldest rejection context", checks, created_at: "2026-09-29T12:00:00Z" }] : [] });
    });
    const first = render(await Candidates({ searchParams: Promise.resolve({ status: "rejected" }) }));
    expect(screen.queryByText("Candidate 1")).toBeNull();
    const next = screen.getByRole("link", { name: "Older candidates →" }).getAttribute("href");
    expect(next).toBe("/candidates?status=rejected&offset=100");
    expect(screen.queryByRole("link", { name: "← Newer candidates" })).toBeNull();
    first.unmount();
    const query = new URL(`http://local${next}`).searchParams;
    render(await Candidates({ searchParams: Promise.resolve({ status: query.get("status")!, offset: query.get("offset")! }) }));
    expect(screen.getByText("Candidate 1")).toBeTruthy();
    expect(screen.getByText("Oldest rejection context")).toBeTruthy();
    expect(screen.getByRole("link", { name: "← Newer candidates" }).getAttribute("href")).toBe("/candidates?status=rejected&offset=0");
    expect(screen.queryByRole("link", { name: "Older candidates →" })).toBeNull();
    expect(screen.getByRole("link", { name: "Pending" }).getAttribute("href")).toBe("/candidates?status=pending");
  });
  it.each(["nonsense", "-100", "1.5", "9007199254740992", "1e100", "100&status=accepted"])("bounds malformed or unsafe offset %s to the first page", async (offset) => {
    render(await Candidates({ searchParams: Promise.resolve({ status: "rejected", offset }) }));
    expect(apiMock).toHaveBeenCalledWith("/candidates?status=rejected");
  });
  it("opens the existing candidate after a duplicate even outside the pending filter", async () => {
    apiMock.mockImplementation((path: string) => Promise.resolve(path === "/candidates/3" ? { ...candidate, reviews: [] } : []));
    render(await Candidates({ searchParams: Promise.resolve({ candidate: "3", offset: "100", status: "rejected", error: "Already recorded as candidate #3." }) }));
    expect(screen.getByRole("link", { name: "Existing candidate #3" }).getAttribute("href")).toBe("/candidates?candidate=3");
    expect(screen.getByText(candidate.name)).toBeTruthy();
  });
  it.each(["javascript:alert(1)", "https://127.0.0.1", "https://localhost", "https://user:password@example.org", "https://example.org/#fragment"])("does not link unsafe URL %s", async (url) => {
    apiMock.mockImplementation((path: string) => Promise.resolve(path.startsWith("/candidates?") ? [candidate] : { ...candidate, canonical_url: url, reviews: [] }));
    render(await Candidates({ searchParams: Promise.resolve({}) }));
    expect(screen.queryByRole("link", { name: candidate.name })).toBeNull();
  });
});
