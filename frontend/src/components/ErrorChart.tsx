import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { HourDetail } from '../api/types';
import { formatTime, formatDateTime } from '../lib/formatters';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorBanner } from './ErrorBanner';

interface ChartPoint {
  time: string;
  timeLabel: string;
  error: number;
}

interface TooltipPayloadEntry {
  value: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length || !label) return null;
  const value = payload[0].value;
  return (
    <div className="rounded-lg border border-slate-600 bg-slate-800 p-3 text-xs shadow-xl">
      <p className="mb-1 font-semibold text-slate-200">{label}</p>
      <p className={value > 0 ? 'text-amber-300' : 'text-blue-300'}>
        Error: {value > 0 ? '+' : ''}
        {value.toFixed(0)} MW
      </p>
      <p className="mt-1 text-slate-500">
        {value > 0 ? 'Over-forecast' : 'Under-forecast'}
      </p>
    </div>
  );
}

interface Props {
  hours: HourDetail[];
  isLoading: boolean;
  error: string | null;
}

export function ErrorChart({ hours, isLoading, error }: Props) {
  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return <ErrorBanner message={error} label="Chart error" />;
  }

  const data: ChartPoint[] = hours
    .filter((h) => h.signed_error_mw !== null)
    .map((h) => ({
      time: formatDateTime(h.start_uk),
      timeLabel: formatTime(h.start_uk),
      error: h.signed_error_mw as number,
    }));

  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-slate-500">
        No error data available — requires both forecast and actual observations.
      </div>
    );
  }

  return (
    <div>
      <p className="mb-2 text-xs text-slate-500">
        Positive = over-forecast · Negative = under-forecast · Intervals without actuals excluded
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
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
            label={{
              value: 'MW',
              angle: -90,
              position: 'insideLeft',
              fill: '#64748b',
              fontSize: 11,
            }}
            width={64}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="#64748b" strokeWidth={1.5} />
          <Bar dataKey="error" name="Signed Error" radius={[2, 2, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.error >= 0 ? '#f59e0b' : '#3b82f6'}
                fillOpacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
