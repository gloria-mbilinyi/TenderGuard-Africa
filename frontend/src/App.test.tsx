import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as api from "./lib/api";

vi.mock("./lib/api", async () => {
  class AuthenticationError extends Error {}
  return {
    AuthenticationError,
    clearSessionMemory: vi.fn(),
    restoreSession: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    getCatalog: vi.fn(),
    getEvaluations: vi.fn(),
    getReports: vi.fn(),
    getSystemStatus: vi.fn(),
    createEvaluation: vi.fn(),
  };
});

describe("TenderGuard dashboard", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.matchMedia = vi.fn().mockReturnValue({ matches: false }) as typeof window.matchMedia;
    vi.mocked(api.restoreSession).mockRejectedValue(new Error("No session"));
    vi.mocked(api.login).mockResolvedValue({
      authenticated: true,
      csrf_token: "csrf",
      expires_at: "2026-11-16T12:00:00Z",
      auth_mode: "LOCAL_DEMO_SESSION",
    });
    vi.mocked(api.getCatalog).mockResolvedValue({ tenders: [] });
    vi.mocked(api.getEvaluations).mockResolvedValue([]);
    vi.mocked(api.getReports).mockResolvedValue([]);
    vi.mocked(api.getSystemStatus).mockResolvedValue({
      api_status: "AVAILABLE",
      api_version: "0.3.0",
      ai_provider: "OLLAMA",
      model: "qwen3:1.7b",
      model_status: "AVAILABLE",
      authentication: "LOCAL_DEMO_SESSION",
      secrets_exposed_to_browser: false,
    });
  });

  it("requires local sign-in before displaying dashboard data", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeTruthy();
    expect(screen.queryByText("Evidence prepared by AI. Decisions retained by people.")).toBeNull();
  });

  it("signs in and renders the live-data overview", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(await screen.findByLabelText("Dashboard password"), "dashboard-secret");
    await user.click(screen.getByRole("button", { name: "Open dashboard" }));

    await waitFor(() => expect(api.login).toHaveBeenCalledWith("dashboard-secret"));
    expect(await screen.findByText("Evidence prepared by AI. Decisions retained by people.")).toBeTruthy();
    await waitFor(() => expect(api.getCatalog).toHaveBeenCalled());
  });
});
