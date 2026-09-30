import { beforeEach, describe, expect, it, vi } from "vitest";
const { apiMock, redirectMock } = vi.hoisted(() => ({ apiMock: vi.fn(), redirectMock: vi.fn((url: string): never => { throw new Error(`REDIRECT:${url}`); }) }));
vi.mock("../lib/api", () => ({ api: apiMock }));
vi.mock("next/navigation", () => ({ redirect: redirectMock }));
import { addCandidate, reviewCandidate } from "./actions";
function form(values: Record<string, string>) { const data = new FormData(); Object.entries(values).forEach(([key, value]) => data.set(key, value)); return data; }
describe("candidate actions", () => {
  beforeEach(() => { apiMock.mockReset(); redirectMock.mockClear(); });
  it("submits an inert candidate and returns to the private queue", async () => {
    await expect(addCandidate(form({ name: " Example ", url: "https://example.org", platform: "web", language: "en", suggestion_reason: " Reporting " }))).rejects.toThrow("REDIRECT:/candidates");
    expect(apiMock).toHaveBeenCalledWith("/candidates", "POST", { name: "Example", url: "https://example.org", platform: "web", language: "en", suggestion_reason: "Reporting" });
  });
  it.each(["", "0", "-1", "1.5", "NaN", "9007199254740992"])("refuses invalid candidate ID %s before an API write", async (candidate_id) => {
    await expect(reviewCandidate(form({ candidate_id }))).rejects.toThrow("REDIRECT:/candidates?error=");
    expect(apiMock).not.toHaveBeenCalled();
  });
  it("sends explicit checked and unchecked human attestations", async () => {
    await expect(reviewCandidate(form({ candidate_id: "3", decision: "rejected", reason: " Policy unclear ", accessibility_checked: "on", relevance_checked: "on", identity_checked: "on", provenance_checked: "on" }))).rejects.toThrow("REDIRECT:/candidates");
    expect(apiMock).toHaveBeenCalledWith("/candidates/3/reviews", "POST", { decision: "rejected", reason: "Policy unclear", checks: { accessibility_checked: true, relevance_checked: true, identity_checked: true, provenance_checked: true, policy_checked: false } });
  });
  it.each(["candidate", "source"])("reports a validated %s conflict ID", async (kind) => {
    apiMock.mockRejectedValue(Object.assign(new Error("untrusted detail"), { conflict: { kind, id: 3 } }));
    await expect(addCandidate(form({}))).rejects.toThrow("REDIRECT:/candidates?error=");
    const destination = redirectMock.mock.calls[0][0];
    expect(decodeURIComponent(destination.replaceAll("+", " "))).toContain(`${kind} #3`);
    expect(destination).not.toContain("untrusted");
    if (kind === "candidate") expect(destination).toContain("candidate=3");
  });
  it.each([{ kind: "secret", id: 3 }, { kind: "candidate", id: -1 }, { kind: "source", id: 1.5 }])("ignores malformed conflict metadata %j", async (conflict) => {
    apiMock.mockRejectedValue(Object.assign(new Error("secret detail"), { conflict }));
    await expect(addCandidate(form({}))).rejects.toThrow("REDIRECT:/candidates?error=");
    expect(redirectMock.mock.calls[0][0]).not.toContain("candidate=");
    expect(redirectMock.mock.calls[0][0]).not.toContain("secret");
  });
  it("does not expose arbitrary API errors in the redirect", async () => {
    apiMock.mockRejectedValue(new Error("secret " + "x".repeat(1000)));
    await expect(addCandidate(form({}))).rejects.toThrow("REDIRECT:/candidates?error=");
    const destination = redirectMock.mock.calls[0][0];
    expect(destination).not.toContain("secret");
    expect(destination.length).toBeLessThan(300);
  });
});
