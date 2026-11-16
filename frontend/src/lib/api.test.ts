import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";

describe("browser API client", () => {
  beforeEach(() => {
    api.clearSessionMemory();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses credentialed same-origin requests without a browser API key", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ tenders: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.getCatalog();

    const [path, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/browser/catalog");
    expect(options.credentials).toBe("include");
    const headers = options.headers as Record<string, string>;
    expect(headers["X-TenderGuard-Key"]).toBeUndefined();
    expect(headers.Authorization).toBeUndefined();
  });

  it("keeps the CSRF token in memory and sends it on evaluation requests", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            authenticated: true,
            csrf_token: "memory-only-csrf",
            expires_at: "2026-11-16T12:00:00Z",
            auth_mode: "LOCAL_DEMO_SESSION",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: "AWAITING_HUMAN_REVIEW" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await api.login("local-password");
    await api.createEvaluation("TG-DEMO-001", "BID-ALPHA-001");

    const [, options] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(options.method).toBe("POST");
    expect((options.headers as Record<string, string>)["X-CSRF-Token"]).toBe(
      "memory-only-csrf",
    );
    expect(window.localStorage.getItem("csrf_token")).toBeNull();
  });

  it("clears session memory after a 401 response", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            authenticated: true,
            csrf_token: "temporary-csrf",
            expires_at: "2026-11-16T12:00:00Z",
            auth_mode: "LOCAL_DEMO_SESSION",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Session expired." }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await api.login("local-password");
    await expect(api.getCatalog()).rejects.toBeInstanceOf(api.AuthenticationError);
    await expect(
      api.createEvaluation("TG-DEMO-001", "BID-ALPHA-001"),
    ).rejects.toBeInstanceOf(api.AuthenticationError);
  });
});
