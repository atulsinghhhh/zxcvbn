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
      ? 'text-slate-500'
      : signed
      ? value > 0
        ? 'text-amber-400'
        : 'text-blue-400'
      : 'text-white';

  return (
    <div
      title={tooltip}
      className="rounded border border-slate-700 bg-slate-900 px-3 py-3"
    >
      <p className="mb-1 text-xs text-slate-500">{label}</p>
      <p className={`text-xl font-bold tabular-nums ${valueColor}`}>
        {displayValue}
        {value !== null && (
          <span className="ml-1 text-xs font-normal text-slate-400">{unit}</span>
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

function AggregatePanel({
  metrics,
  totalDays,
  daysWithData,
  failedDates,
}: AggregatePanelProps) {
  return (
    <div>
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
        January 2026 — Aggregate
      </h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <AggKpi
          label="MAE"
          value={metrics.mae_mw}
          unit="MW"
          tooltip="Mean Absolute Error across all evaluated intervals in January 2026."
        />
        <AggKpi
          label="RMSE"
          value={metrics.rmse_mw}
          unit="MW"
          tooltip="Root Mean Squared Error — penalises large errors more than MAE."
        />
        <AggKpi
          label="Bias"
          value={metrics.bias_mw}
          unit="MW"
          signed
          tooltip="Mean signed error (forecast − actual). Positive = systematic over-forecast. Negative = systematic under-forecast."
        />
        <AggKpi
          label="P90 Abs Error"
          value={metrics.p90_abs_error_mw}
          unit="MW"
          tooltip="90th-percentile absolute error — the worst-case threshold exceeded in only 10% of intervals."
        />
      </div>
      <div className="mt-3 flex flex-wrap gap-6 text-xs text-slate-400">
        <span>
          {daysWithData} of {totalDays} days with data
        </span>
        <span>{metrics.evaluation_hours} intervals evaluated</span>
        {failedDates.length > 0 && (
          <span className="text-amber-400">
            {failedDates.length} date{failedDates.length !== 1 ? 's' : ''} skipped (no
            eligible vintage)
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
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">
        Day-by-Day Accuracy
      </h3>
      <div className="overflow-x-auto rounded border border-slate-700">
        <table className="w-full text-xs" aria-label="Day-by-day forecast accuracy">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-900 text-left text-slate-400">
              <th className="px-3 py-2 font-medium">Delivery Date</th>
              <th className="px-3 py-2 font-medium">Selected Vintage</th>
              <th className="px-3 py-2 text-right font-medium">Eval Hrs</th>
              <th className="px-3 py-2 text-right font-medium">MAE</th>
              <th className="px-3 py-2 text-right font-medium">RMSE</th>
              <th className="px-3 py-2 text-right font-medium">Bias</th>
              <th className="px-3 py-2 text-right font-medium">Max Abs Err</th>
            </tr>
          </thead>
          <tbody>
            {days.map((day) => {
              const isHighlighted = day.delivery_date === highlightDeliveryDate;
              const bias = day.metrics.bias_mw;
              const biasColor =
                bias === null
                  ? 'text-slate-500'
                  : bias > 0
                  ? 'text-amber-400'
                  : 'text-blue-400';

              return (
                <tr
                  key={day.delivery_date}
                  className={`border-b border-slate-800 transition-colors ${
                    isHighlighted
                      ? 'bg-emerald-900/30 ring-1 ring-inset ring-emerald-700/50'
                      : 'hover:bg-slate-800/50'
                  }`}
                >
                  <td
                    className={`px-3 py-2 font-medium ${
                      isHighlighted ? 'text-emerald-300' : 'text-slate-200'
                    }`}
                  >
                    {formatDate(day.delivery_date)}
                    {isHighlighted && (
                      <span className="ml-2 rounded bg-emerald-900/60 px-1.5 py-0.5 text-[10px] text-emerald-400">
                        selected
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    {formatDateTimeUtc(day.selected_vintage_utc)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {day.metrics.evaluation_hours}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {formatMw(day.metrics.mae_mw)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {formatMw(day.metrics.rmse_mw)}
                  </td>
                  <td className={`px-3 py-2 text-right font-medium tabular-nums ${biasColor}`}>
                    {bias !== null
                      ? (bias > 0 ? '+' : '') + bias.toFixed(0) + ' MW'
                      : '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-400">
                    {formatMw(day.metrics.max_abs_error_mw)}
                  </td>
                </tr>
              );
            })}
            {days.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-3 py-8 text-center text-slate-500"
                >
                  No accuracy data available for January 2026.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {failedDates.length > 0 && (
        <p className="mt-2 text-xs text-amber-400">
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
  /** The delivery date currently selected in the single-day view, for row highlighting. */
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
        <span className="ml-3 text-slate-400">
          Loading January 2026 accuracy data…
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Overview aggregate metrics */}
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
        <p className="text-sm text-slate-500">
          No aggregate metrics available — all January dates may have failed.
        </p>
      )}

      {/* Day-by-day table from /api/accuracy */}
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
