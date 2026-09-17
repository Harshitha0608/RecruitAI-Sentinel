import {
  HealthResponse,
  PrecomputeResponse,
  RankResponse,
  CandidateDetailResponse,
  AnalyticsResponse,
  PrecomputeStatusResponse,
  JobDescription,
} from "../types";

export function getBaseUrl(): string {
  if (typeof window !== "undefined") {
    const override = localStorage.getItem("sentinel_api_url");
    if (override) return override;
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
}

export function setBaseUrl(url: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("sentinel_api_url", url);
  }
}

async function request<T>(path: string, options?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl.replace(/\/$/, "")}${path}`;

  const timeoutMs = options?.timeoutMs ?? 10000;
  const isGet = (options?.method || "GET").toUpperCase() === "GET";
  const maxRetries = isGet ? 2 : 0;
  let attempt = 0;

  const fetchOptions = { ...options };
  delete fetchOptions.timeoutMs;

  while (true) {
    const controller = new AbortController();
    const timerId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          Accept: "application/json",
          ...(fetchOptions?.headers || {}),
        },
      });
      clearTimeout(timerId);

      if (!res.ok) {
        let message = `API request failed with status ${res.status}`;
        try {
          const errorData = await res.json();
          message = errorData.detail || errorData.message || message;
        } catch {}
        throw new Error(message);
      }

      return (await res.json()) as T;
    } catch (error: any) {
      clearTimeout(timerId);
      const isAbort = error.name === "AbortError" || error.name === "CancelError" || error.message?.includes("aborted");

      if (isAbort) {
        throw new Error(`Request timed out after ${timeoutMs / 1000} seconds.`);
      }

      if (attempt >= maxRetries) {
        console.error(`Request to ${url} failed after ${attempt + 1} attempts:`, error);
        throw error;
      }

      attempt++;
      // Wait 500ms before retrying
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
}

export const apiService = {
  getBaseUrl,
  setBaseUrl,
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },

  async precompute(): Promise<PrecomputeResponse> {
    return request<PrecomputeResponse>("/api/precompute", {
      method: "POST",
      timeoutMs: 60000,
    });
  },

  async rankCandidates(file: File | null, text: string | null): Promise<RankResponse> {
    const formData = new FormData();
    if (file) {
      formData.append("file", file);
    }
    if (text) {
      formData.append("text", text);
    }

    return request<RankResponse>("/api/rank", {
      method: "POST",
      body: formData,
      timeoutMs: 300000, // 5 minutes
    });
  },

  async parseJd(file: File | null, text: string | null): Promise<JobDescription> {
    const formData = new FormData();
    if (file) {
      formData.append("file", file);
    }
    if (text) {
      formData.append("text", text);
    }

    return request<JobDescription>("/api/parse-jd", {
      method: "POST",
      body: formData,
      timeoutMs: 30000, // 30 seconds
    });
  },

  async getTop100(): Promise<RankResponse> {
    return request<RankResponse>("/api/top100", { timeoutMs: 30000 });
  },

  async getCandidateDetail(candidateId: string): Promise<CandidateDetailResponse> {
    return request<CandidateDetailResponse>(`/api/candidate/${candidateId}`);
  },

  async getAnalytics(): Promise<AnalyticsResponse> {
    return request<AnalyticsResponse>("/api/analytics");
  },

  async getPrecomputeStatus(): Promise<PrecomputeStatusResponse> {
    return request<PrecomputeStatusResponse>("/api/precompute/status");
  },

  async getScreeningProgress(): Promise<{ stage: string; percentage: number; status_message: string }> {
    return request<{ stage: string; percentage: number; status_message: string }>("/api/screening-progress");
  },

  async getActiveJd(): Promise<JobDescription> {
    return request<JobDescription>("/api/active-jd");
  },
};
