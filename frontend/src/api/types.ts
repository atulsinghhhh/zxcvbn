export interface HealthResponse {
  status: 'ok';
  version: string;
}

export interface HourDetail {
  start_utc: string;
  start_uk: string;
  forecast_mw: number | null;
  actual_mw: number | null;
  signed_error_mw: number | null;
  abs_error_mw: number | null;
}

export interface MetricsSummary {
  total_hours: number;
  evaluation_hours: number;
  missing_forecast_hours: number;
  missing_actual_hours: number;
  invalid_hours: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  max_abs_error_mw: number | null;
  min_abs_error_mw: number | null;
  p90_abs_error_mw: number | null;
  max_signed_error_mw: number | null;
  min_signed_error_mw: number | null;
}

export interface DayAccuracy {
  delivery_date: string;
  decision_cutoff_utc: string;
  selected_vintage_utc: string;
  metrics: MetricsSummary;
}

export interface ForecastResponse {
  delivery_date: string;
  decision_cutoff_utc: string;
  selected_vintage_utc: string;
  metrics: MetricsSummary;
  hours: HourDetail[];
}

export interface IntervalsResponse {
  delivery_date: string;
  decision_cutoff_utc: string;
  selected_vintage_utc: string;
  total: number;
  offset: number;
  limit: number;
  hours: HourDetail[];
}

export interface AccuracyResponse {
  from_date: string;
  to_date: string;
  cutoff_hour: number;
  total_days: number;
  days_with_data: number;
  failed_dates: string[];
  days: DayAccuracy[];
}

export interface OverviewResponse {
  from_date: string;
  to_date: string;
  cutoff_hour: number;
  total_days: number;
  days_with_data: number;
  failed_dates: string[];
  aggregate_metrics: MetricsSummary | null;
  days: DayAccuracy[];
}

export interface ApiError {
  error: string;
  detail: string;
}
