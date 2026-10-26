import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { HourDetail } from '../api/types';
import { formatTime, formatDateTime } from '../lib/formatters';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorBanner } from './ErrorBanner';

interface ChartPoint {
  time: string;
  timeLabel: string;
  forecast_mw: number | null;
  actual_mw: number | null;
  signed_error_mw: number | null;
}

interface TooltipPayloadEntry {
  name: string;
  value: number | null;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !label) return null;

  const forecast = payload.find((p) => p.name === 'Forecast')?.value ?? null;
  const actual = payload.find((p) => p.name === 'Actual')?.value ?? null;
  const error = forecast !== null && actual !== null ? forecast - actual : null;

  return (
    <div
      className="rounded-lg p-3 text-xs shadow-xl"
      style={{ background: '#ffffff', border: '1px solid #d4d4dc' }}
    >
      <p className="mb-2 font-semibold" style={{ color: '#101114' }}>{label}</p>
      <p style={{ color: '#7132f5' }}>
        Forecast: {forecast !== null ? `${forecast.toFixed(0)} MW` : '—'}
      </p>
      <p style={{ color: '#2e3350' }}>
        Actual: {actual !== null ? `${actual.toFixed(0)} MW` : '—'}
      </p>
      <p style={{ color: error !== null ? (error > 0 ? '#d11d45' : '#08844f') : '#9497a9' }}>
        Error: {error !== null ? `${error > 0 ? '+' : ''}${error.toFixed(0)} MW` : '—'}
      </p>
    </div>
  );
}

interface Props {
  hours: HourDetail[];
  isLoading: boolean;
  error: string | null;
}

export function ForecastChart({ hours, isLoading, error }: Props) {
  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return <ErrorBanner message={error} label="Chart error" />;
  }

  if (hours.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm" style={{ color: '#9497a9' }}>
        No forecast data available for this date.
      </div>
    );
  }

  const data: ChartPoint[] = hours.map((h) => ({
    time: formatDateTime(h.start_uk),
    timeLabel: formatTime(h.start_uk),
    forecast_mw: h.forecast_mw,
    actual_mw: h.actual_mw,
    signed_error_mw: h.signed_error_mw,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f4" />
        <XAxis
          dataKey="timeLabel"
          tick={{ fill: '#686b82', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: '#d4d4dc' }}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: '#686b82', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: '#d4d4dc' }}
          label={{ value: 'MW', angle: -90, position: 'insideLeft', fill: '#9497a9', fontSize: 11 }}
          width={64}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: 12, color: '#686b82' }} />
        <Line
          type="monotone"
          dataKey="forecast_mw"
          name="Forecast"
          stroke="#7132f5"
          strokeWidth={2}
          dot={false}
          connectNulls={false}
        />
        <Line
          type="monotone"
          dataKey="actual_mw"
          name="Actual"
          stroke="#2e3350"
          strokeWidth={2}
          dot={false}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
