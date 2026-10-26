import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { OverviewResponse } from '../api/types';
import { KpiCard } from './KpiCard';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorBanner } from './ErrorBanner';

interface Props {
  overview: OverviewResponse | null;
  isLoading: boolean;
  error: string | null;
}

interface TrendPoint {
  date: string;
  dateLabel: string;
  mae: number | null;
}

interface TooltipPayloadEntry {
  value: number;
  payload: TrendPoint;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
}

function TrendTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div
      className="rounded-lg p-3 text-xs shadow-xl"
      style={{ background: '#ffffff', border: '1px solid #d4d4dc' }}
    >
      <p className="mb-1 font-semibold" style={{ color: '#101114' }}>
        {format(parseISO(point.date), 'dd MMM yyyy')}
      </p>
      <p style={{ color: '#7132f5' }}>
        MAE: {point.mae !== null ? `${point.mae.toFixed(1)} MW` : '—'}
      </p>
    </div>
  );
}

export function OverviewSummary({ overview, isLoading, error }: Props) {
  if (error) {
    return <ErrorBanner message={error} label="Overview API error" />;
  }

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!overview) {
    return null;
  }

  const agg = overview.aggregate_metrics;
  const coveragePct =
    overview.total_days > 0
      ? Math.round((overview.days_with_data / overview.total_days) * 100)
      : null;

  const trendData: TrendPoint[] = overview.days.map((d) => ({
    date: d.delivery_date,
    dateLabel: format(parseISO(d.delivery_date), 'dd MMM'),
    mae: d.metrics.mae_mw,
  }));

  const rangeLabel = `${format(parseISO(overview.from_date), 'dd MMM')} – ${format(
    parseISO(overview.to_date),
    'dd MMM yyyy',
  )}`;

  return (
    <div className="mb-8">
      <div className="mb-3 flex items-baseline justify-between">
        <span
          className="text-xs font-medium uppercase tracking-widest"
          style={{ color: '#9497a9' }}
        >
          Last 30 Days
        </span>
        <span className="text-xs" style={{ color: '#9497a9' }}>
          {rangeLabel}
        </span>
      </div>

      {/* Range KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          label="30d MAE"
          value={agg?.mae_mw !== null && agg?.mae_mw !== undefined ? agg.mae_mw.toFixed(1) : null}
          unit="MW"
          tooltip="Mean Absolute Error aggregated across all evaluated days in the range."
          status={agg?.mae_mw !== null && agg?.mae_mw !== undefined ? 'ok' : 'unavailable'}
          data-testid="kpi-range-mae"
        />
        <KpiCard
          label="30d Bias"
          value={
            agg?.bias_mw !== null && agg?.bias_mw !== undefined ? agg.bias_mw.toFixed(1) : null
          }
          unit="MW"
          tooltip="Mean signed error (forecast − actual) across the range. Positive = systematic over-forecast."
          status={
            agg?.bias_mw !== null && agg?.bias_mw !== undefined
              ? Math.abs(agg.bias_mw) > 200
                ? 'warn'
                : 'ok'
              : 'unavailable'
          }
          data-testid="kpi-range-bias"
        />
        <KpiCard
          label="Data Coverage"
          value={coveragePct !== null ? `${coveragePct}%` : null}
          tooltip={`${overview.days_with_data} of ${overview.total_days} days returned usable data.`}
          status={
            coveragePct === null ? 'unavailable' : coveragePct >= 80 ? 'ok' : 'warn'
          }
          data-testid="kpi-range-coverage"
        />
        <KpiCard
          label="Failed Days"
          value={String(overview.failed_dates.length)}
          tooltip={
            overview.failed_dates.length > 0
              ? `Dates with no usable data: ${overview.failed_dates.join(', ')}`
              : 'Every day in the range returned data.'
          }
          status={overview.failed_dates.length === 0 ? 'ok' : 'warn'}
          data-testid="kpi-range-failed"
        />
      </div>

      {/* Daily MAE trend */}
      <div
        className="mt-4 rounded-lg p-4"
        style={{ background: '#ffffff', boxShadow: 'rgba(0,0,0,0.03) 0px 4px 24px 0px' }}
      >
        <div className="mb-3 flex items-center justify-between">
          <span
            className="text-xs font-medium uppercase tracking-widest"
            style={{ color: '#686b82' }}
          >
            Daily MAE
          </span>
          <span className="text-xs" style={{ color: '#9497a9' }}>
            Lower is better
          </span>
        </div>

        {trendData.length === 0 ? (
          <p className="py-8 text-center text-xs" style={{ color: '#9497a9' }}>
            No daily data available for this range.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={trendData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f4" />
              <XAxis
                dataKey="dateLabel"
                tick={{ fill: '#686b82', fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: '#d4d4dc' }}
                interval="preserveStartEnd"
                minTickGap={16}
              />
              <YAxis
                tick={{ fill: '#686b82', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#d4d4dc' }}
                label={{
                  value: 'MW',
                  angle: -90,
                  position: 'insideLeft',
                  fill: '#9497a9',
                  fontSize: 11,
                }}
                width={48}
              />
              <Tooltip content={<TrendTooltip />} cursor={{ fill: '#f5f3ff' }} />
              <Bar dataKey="mae" name="MAE" fill="#7132f5" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
