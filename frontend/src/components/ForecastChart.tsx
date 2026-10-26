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
    <div className="rounded-lg border border-slate-600 bg-slate-800 p-3 text-xs shadow-xl">
      <p className="mb-2 font-semibold text-slate-200">{label}</p>
      <p className="text-emerald-300">
        Forecast: {forecast !== null ? `${forecast.toFixed(0)} MW` : '—'}
      </p>
      <p className="text-blue-300">
        Actual: {actual !== null ? `${actual.toFixed(0)} MW` : '—'}
      </p>
      <p className={error !== null ? (error > 0 ? 'text-amber-300' : 'text-blue-300') : 'text-slate-500'}>
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
      <div className="flex h-64 items-center justify-center text-sm text-slate-500">
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
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="timeLabel"
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: '#475569' }}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: '#475569' }}
          label={{ value: 'MW', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }}
          width={64}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12, color: '#94a3b8' }}
        />
        <Line
          type="monotone"
          dataKey="forecast_mw"
          name="Forecast"
          stroke="#10b981"
          strokeWidth={2}
          dot={false}
          connectNulls={false}
        />
        <Line
          type="monotone"
          dataKey="actual_mw"
          name="Actual"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
