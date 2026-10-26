import type {
  AccuracyResponse,
  ForecastResponse,
  HealthResponse,
  IntervalsResponse,
  OverviewResponse,
} from './types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

async function apiFetch<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { signal });
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: (signal?: AbortSignal) =>
    apiFetch<HealthResponse>('/api/health', signal),

  forecast: (deliveryDate: string, cutoffHour: number, signal?: AbortSignal) =>
    apiFetch<ForecastResponse>(
      `/api/forecast?delivery_date=${deliveryDate}&cutoff_hour=${cutoffHour}`,
      signal,
    ),

  intervals: (
    deliveryDate: string,
    cutoffHour: number,
    limit: number,
    offset: number,
    signal?: AbortSignal,
  ) =>
    apiFetch<IntervalsResponse>(
      `/api/intervals?delivery_date=${deliveryDate}&cutoff_hour=${cutoffHour}&limit=${limit}&offset=${offset}`,
      signal,
    ),

  accuracy: (
    fromDate: string,
    toDate: string,
    cutoffHour: number,
    signal?: AbortSignal,
  ) =>
    apiFetch<AccuracyResponse>(
      `/api/accuracy?from_date=${fromDate}&to_date=${toDate}&cutoff_hour=${cutoffHour}`,
      signal,
    ),

  overview: (
    fromDate: string,
    toDate: string,
    cutoffHour: number,
    signal?: AbortSignal,
  ) =>
    apiFetch<OverviewResponse>(
      `/api/overview?from_date=${fromDate}&to_date=${toDate}&cutoff_hour=${cutoffHour}`,
      signal,
    ),
};
