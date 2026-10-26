import type { AccuracyResponse, MetricsSummary, OverviewResponse } from '../api/types';
import { formatDate, formatDateTimeUtc, formatMw } from '../lib/formatters';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorBanner } from './ErrorBanner';

// ── Aggregate KPI tile ──────────────────────────────────────────────────────

interface AggKpiProps {
  label: string;
  value: number | null;
  unit: string;
  tooltip: string;
  signed?: boolean;
}

function AggKpi({ label, value, unit, tooltip, signed = false }: AggKpiProps) {
  const displayValue =
    value === null
      ? '—'
      : (signed && value > 0 ? '+' : '') + value.toFixed(0);

  const valueColor =
    value === null
      ? '#9497a9'
      : signed
      ? value > 0
        ? '#d11d45'
        : '#7132f5'
      : '#101114';

  return (
    <div
      title={tooltip}
      className="rounded-lg px-3 py-3"
      style={{ background: '#ffffff', boxShadow: 'rgba(0,0,0,0.03) 0px 4px 24px 0px' }}
    >
      <p className="mb-1 text-xs" style={{ color: '#686b82' }}>{label}</p>
      <p className="text-xl font-bold tabular-nums" style={{ color: valueColor }}>
        {displayValue}
        {value !== null && (
          <span className="ml-1 text-xs font-normal" style={{ color: '#686b82' }}>{unit}</span>
        )}
      </p>
    </div>
  );
}

// ── Aggregate summary ───────────────────────────────────────────────────────

interface AggregatePanelProps {
  metrics: MetricsSummary;
  totalDays: number;
  daysWithData: number;
  failedDates: string[];
}

function AggregatePanel({ metrics, totalDays, daysWithData, failedDates }: AggregatePanelProps) {
  return (
    <div>
      <h3 className="mb-3 text-xs font-medium uppercase tracking-widest" style={{ color: '#686b82' }}>
        January 2026 — Aggregate
      </h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <AggKpi label="MAE" value={metrics.mae_mw} unit="MW" tooltip="Mean Absolute Error across all evaluated intervals in January 2026." />
        <AggKpi label="RMSE" value={metrics.rmse_mw} unit="MW" tooltip="Root Mean Squared Error — penalises large errors more than MAE." />
        <AggKpi label="Bias" value={metrics.bias_mw} unit="MW" signed tooltip="Mean signed error (forecast − actual). Positive = systematic over-forecast. Negative = systematic under-forecast." />
        <AggKpi label="P90 Abs Error" value={metrics.p90_abs_error_mw} unit="MW" tooltip="90th-percentile absolute error — the worst-case threshold exceeded in only 10% of intervals." />
      </div>
      <div className="mt-3 flex flex-wrap gap-6 text-xs" style={{ color: '#686b82' }}>
        <span>{daysWithData} of {totalDays} days with data</span>
        <span>{metrics.evaluation_hours} intervals evaluated</span>
        {failedDates.length > 0 && (
          <span style={{ color: '#d11d45' }}>
            {failedDates.length} date{failedDates.length !== 1 ? 's' : ''} skipped (no eligible vintage)
          </span>
        )}
      </div>
    </div>
  );
}

// ── Day-by-day table ────────────────────────────────────────────────────────

interface DayTableProps {
  days: AccuracyResponse['days'];
  highlightDeliveryDate: string;
  failedDates: string[];
}

function DayTable({ days, highlightDeliveryDate, failedDates }: DayTableProps) {
  return (
    <div>
      <h3 className="mb-3 text-xs font-medium uppercase tracking-widest" style={{ color: '#686b82' }}>
        Day-by-Day Accuracy
      </h3>
      <div className="overflow-x-auto rounded-lg" style={{ border: '1px solid #d4d4dc' }}>
        <table className="w-full text-xs" aria-label="Day-by-day forecast accuracy">
          <thead>
            <tr className="text-left" style={{ borderBottom: '1px solid #d4d4dc', background: '#f6f5f9' }}>
              {['Delivery Date', 'Selected Vintage', 'Eval Hrs', 'MAE', 'RMSE', 'Bias', 'Max Abs Err'].map((h, i) => (
                <th key={h} className={`px-3 py-2 font-medium ${i >= 2 ? 'text-right' : ''}`} style={{ color: '#686b82' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {days.map((day) => {
              const isHighlighted = day.delivery_date === highlightDeliveryDate;
              const bias = day.metrics.bias_mw;
              const biasColor = bias === null ? '#9497a9' : bias > 0 ? '#d11d45' : '#7132f5';

              return (
                <tr
                  key={day.delivery_date}
                  style={{
                    borderBottom: '1px solid rgba(212,212,220,0.5)',
                    background: isHighlighted ? '#f0ebfe' : undefined,
                    outline: isHighlighted ? '1px solid rgba(113,50,245,0.2)' : undefined,
                    outlineOffset: -1,
                  }}
                  onMouseEnter={(e) => { if (!isHighlighted) (e.currentTarget as HTMLTableRowElement).style.background = '#f6f5f9'; }}
                  onMouseLeave={(e) => { if (!isHighlighted) (e.currentTarget as HTMLTableRowElement).style.background = ''; }}
                >
                  <td className="px-3 py-2 font-medium" style={{ color: isHighlighted ? '#7132f5' : '#101114' }}>
                    {formatDate(day.delivery_date)}
                    {isHighlighted && (
                      <span
                        className="ml-2 rounded-full px-1.5 py-0.5 text-[10px]"
                        style={{ background: '#e4dcf9', color: '#7132f5' }}
                      >
                        selected
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2" style={{ color: '#686b82' }}>
                    {formatDateTimeUtc(day.selected_vintage_utc)}
                  </td>
                  <td className="px-3 py-2 text-right" style={{ color: '#101114' }}>
                    {day.metrics.evaluation_hours}
                  </td>
                  <td className="px-3 py-2 text-right" style={{ color: '#101114' }}>
                    {formatMw(day.metrics.mae_mw)}
                  </td>
                  <td className="px-3 py-2 text-right" style={{ color: '#101114' }}>
                    {formatMw(day.metrics.rmse_mw)}
                  </td>
                  <td className="px-3 py-2 text-right font-medium tabular-nums" style={{ color: biasColor }}>
                    {bias !== null ? (bias > 0 ? '+' : '') + bias.toFixed(0) + ' MW' : '—'}
                  </td>
                  <td className="px-3 py-2 text-right" style={{ color: '#686b82' }}>
                    {formatMw(day.metrics.max_abs_error_mw)}
                  </td>
                </tr>
              );
            })}
            {days.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center" style={{ color: '#9497a9' }}>
                  No accuracy data available for January 2026.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {failedDates.length > 0 && (
        <p className="mt-2 text-xs" style={{ color: '#d11d45' }}>
          Dates without eligible vintage: {failedDates.join(', ')}
        </p>
      )}
    </div>
  );
}

// ── Public section component ────────────────────────────────────────────────

interface AccuracySectionProps {
  overview: OverviewResponse | null;
  overviewLoading: boolean;
  overviewError: string | null;
  accuracy: AccuracyResponse | null;
  accuracyLoading: boolean;
  accuracyError: string | null;
  highlightDeliveryDate: string;
}

export function AccuracySection({
  overview,
  overviewLoading,
  overviewError,
  accuracy,
  accuracyLoading,
  accuracyError,
  highlightDeliveryDate,
}: AccuracySectionProps) {
  const isLoading = overviewLoading || accuracyLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16" role="status">
        <LoadingSpinner />
        <span className="ml-3" style={{ color: '#686b82' }}>
          Loading January 2026 accuracy data…
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {overviewError ? (
        <ErrorBanner message={overviewError} label="Overview API error" />
      ) : overview?.aggregate_metrics ? (
        <AggregatePanel
          metrics={overview.aggregate_metrics}
          totalDays={overview.total_days}
          daysWithData={overview.days_with_data}
          failedDates={overview.failed_dates}
        />
      ) : (
        <p className="text-sm" style={{ color: '#9497a9' }}>
          No aggregate metrics available — all January dates may have failed.
        </p>
      )}

      {accuracyError ? (
        <ErrorBanner message={accuracyError} label="Accuracy API error" />
      ) : accuracy ? (
        <DayTable
          days={accuracy.days}
          highlightDeliveryDate={highlightDeliveryDate}
          failedDates={accuracy.failed_dates}
        />
      ) : null}
    </div>
  );
}
