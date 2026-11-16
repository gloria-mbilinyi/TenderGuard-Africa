import type {
  BrowserSession,
  CatalogResponse,
  EvaluationResult,
  EvaluationSummary,
  ReportItem,
  SystemStatus,
} from "../types";

const DEFAULT_TIMEOUT_MS = 10_000;
const EVALUATION_TIMEOUT_MS = 180_000;
let csrfToken: string | null = null;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class AuthenticationError extends ApiError {
  constructor(message = "Dashboard sign-in required.") {
    super(message, 401);
    this.name = "AuthenticationError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, {
      ...options,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
      signal: controller.signal,
    });
    if (!response.ok) {
      const payload = (await response.json().catch(() => ({}))) as { detail?: string };
      const message = payload.detail || `Request failed with status ${response.status}.`;
      if (response.status === 401) {
        csrfToken = null;
        throw new AuthenticationError(message);
      }
      throw new ApiError(message, response.status);
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The request timed out. The local AI service may still be busy.", 408);
    }
    throw new ApiError("TenderGuard could not reach the local backend.", 0);
  } finally {
    window.clearTimeout(timer);
  }
}

function rememberSession(session: BrowserSession): BrowserSession {
  csrfToken = session.csrf_token;
  return session;
}

function csrfHeaders(): HeadersInit {
  if (!csrfToken) {
    throw new AuthenticationError("The dashboard session is missing its CSRF token.");
  }
  return { "X-CSRF-Token": csrfToken };
}

export async function restoreSession(): Promise<BrowserSession> {
  return rememberSession(await request<BrowserSession>("/api/browser/session"));
}

export async function login(password: string): Promise<BrowserSession> {
  return rememberSession(
    await request<BrowserSession>("/api/browser/session", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  );
}

export async function logout(): Promise<void> {
  await request<void>("/api/browser/logout", {
    method: "POST",
    headers: csrfHeaders(),
  });
  csrfToken = null;
}

export async function getCatalog(): Promise<CatalogResponse> {
  return request<CatalogResponse>("/api/browser/catalog");
}

export async function getEvaluations(): Promise<EvaluationSummary[]> {
  const result = await request<{ evaluations: EvaluationSummary[] }>(
    "/api/browser/evaluations",
  );
  return result.evaluations;
}

export async function getReports(): Promise<ReportItem[]> {
  const result = await request<{ reports: ReportItem[] }>("/api/browser/reports");
  return result.reports;
}

export async function getSystemStatus(): Promise<SystemStatus> {
  return request<SystemStatus>("/api/browser/system");
}

export async function createEvaluation(
  tenderId: string,
  bidId: string,
): Promise<EvaluationResult> {
  return request<EvaluationResult>(
    "/api/browser/evaluations",
    {
      method: "POST",
      headers: csrfHeaders(),
      body: JSON.stringify({ tender_id: tenderId, bid_id: bidId }),
    },
    EVALUATION_TIMEOUT_MS,
  );
}

export function clearSessionMemory(): void {
  csrfToken = null;
}
