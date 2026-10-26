import { useWindSight } from './hooks/useWindSight';
import { useActiveSection } from './hooks/useActiveSection';
import { useOverview } from './hooks/useOverview';
import { useAccuracy } from './hooks/useAccuracy';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { StatusSection } from './components/StatusSection';
import { KpiCard } from './components/KpiCard';
import { ForecastChart } from './components/ForecastChart';
import { ErrorChart } from './components/ErrorChart';
import { IntervalsTable } from './components/IntervalsTable';
import { DataProvenance } from './components/DataProvenance';
import { AccuracySection } from './components/AccuracySection';
import { ErrorBanner } from './components/ErrorBanner';
import type { HourDetail } from './api/types';

function avgMw(hours: HourDetail[], key: 'forecast_mw' | 'actual_mw'): number | null {
  const vals = hours.map((h) => h[key]).filter((v): v is number => v !== null);
  if (vals.length === 0) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

export default function App() {
  const {
    decisionDate,
    deliveryDate,
    cutoffHour,
    forecast,
    intervals,
    forecastLoading,
    intervalsLoading,
    forecastError,
    intervalsError,
    setDecisionDate,
    setIntervalsOffset,
    refresh,
  } = useWindSight();

  const [activeSection, navigateTo] = useActiveSection();

  // Monthly data — always fetched so switching tabs never triggers a refetch
  const { overview, loading: overviewLoading, error: overviewError } = useOverview(cutoffHour);
  const { accuracy, loading: accuracyLoading, error: accuracyError } = useAccuracy(cutoffHour);

  const hours = forecast?.hours ?? [];
  const metrics = forecast?.metrics ?? null;
  const avgForecast = avgMw(hours, 'forecast_mw');
  const avgActual = avgMw(hours, 'actual_mw');

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <Sidebar activeSection={activeSection} onNavigate={navigateTo} />

      <div className="ml-60 flex min-h-screen flex-col">
        <Header
          decisionDate={decisionDate}
          deliveryDate={deliveryDate}
          selectedVintageUtc={forecast?.selected_vintage_utc ?? null}
          decisionCutoffUtc={forecast?.decision_cutoff_utc ?? null}
          onDateChange={setDecisionDate}
          onRefresh={refresh}
          isLoading={forecastLoading || intervalsLoading}
        />

        <main className="flex-1 p-6">

          {/* ── Overview ─────────────────────────────────────────────────── */}
          {activeSection === 'overview' && (
            <section id="section-overview" aria-labelledby="section-overview-heading">
              <h2
                id="section-overview-heading"
                className="mb-6 text-xs font-semibold uppercase tracking-widest text-slate-500"
              >
                Overview
              </h2>

              {forecastError && (
                <ErrorBanner message={forecastError} label="Forecast API error" />
              )}

              <div className="grid gap-4 lg:grid-cols-3">
                <div className="lg:col-span-1">
                  <StatusSection
                    decisionDate={decisionDate}
                    deliveryDate={deliveryDate}
                    decisionCutoffUtc={forecast?.decision_cutoff_utc ?? null}
                    selectedVintageUtc={forecast?.selected_vintage_utc ?? null}
                    cutoffHour={cutoffHour}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4 lg:col-span-2">
                  <KpiCard
                    label="Avg Forecast"
                    value={avgForecast !== null ? avgForecast.toFixed(0) : null}
                    unit="MW"
                    tooltip="Average forecast wind generation across all intervals for the delivery day."
                    status={avgForecast !== null ? 'ok' : 'unavailable'}
                    data-testid="kpi-forecast"
                  />
                  <KpiCard
                    label="Avg Actual"
                    value={avgActual !== null ? avgActual.toFixed(0) : null}
                    unit="MW"
                    tooltip="Average actual wind generation across observed intervals. Shown as unavailable if no actuals exist for this date."
                    status={avgActual !== null ? 'ok' : 'unavailable'}
                    data-testid="kpi-actual"
                  />
                  <KpiCard
                    label="MAE"
                    value={
                      metrics?.mae_mw !== null && metrics?.mae_mw !== undefined
                        ? metrics.mae_mw.toFixed(1)
                        : null
                    }
                    unit="MW"
                    tooltip="Mean Absolute Error: average of |forecast − actual| across evaluated intervals. Provided by the backend."
                    status={
                      metrics?.mae_mw !== null && metrics?.mae_mw !== undefined
                        ? 'ok'
                        : 'unavailable'
                    }
                    data-testid="kpi-mae"
                  />
                  <KpiCard
                    label="Bias"
                    value={
                      metrics?.bias_mw !== null && metrics?.bias_mw !== undefined
                        ? metrics.bias_mw.toFixed(1)
                        : null
                    }
                    unit="MW"
                    tooltip="Mean signed forecast error (forecast − actual). Positive = systematic over-forecast. Negative = systematic under-forecast. Provided by the backend."
                    status={
                      metrics?.bias_mw !== null && metrics?.bias_mw !== undefined
                        ? Math.abs(metrics.bias_mw) > 200
                          ? 'warn'
                          : 'ok'
                        : 'unavailable'
                    }
                    data-testid="kpi-bias"
                  />
                </div>
              </div>
            </section>
          )}

          {/* ── Forecast Analysis ────────────────────────────────────────── */}
          {activeSection === 'forecast' && (
            <section id="section-forecast" aria-labelledby="section-forecast-heading">
              <h2
                id="section-forecast-heading"
                className="mb-6 text-xs font-semibold uppercase tracking-widest text-slate-500"
              >
                Forecast Analysis
              </h2>

              <div className="space-y-6">
                <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
                  <h3 className="mb-4 text-sm font-semibold text-slate-200">
                    Forecast vs Actual Generation
                  </h3>
                  <ForecastChart
                    hours={hours}
                    isLoading={forecastLoading}
                    error={forecastError}
                  />
                </div>

                <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
                  <h3 className="mb-1 text-sm font-semibold text-slate-200">
                    Forecast Error by Interval
                  </h3>
                  <ErrorChart
                    hours={hours}
                    isLoading={forecastLoading}
                    error={forecastError}
                  />
                </div>

                <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
                  <h3 className="mb-4 text-sm font-semibold text-slate-200">
                    Interval-Level Data
                  </h3>
                  <IntervalsTable
                    hours={intervals?.hours ?? []}
                    total={intervals?.total ?? 0}
                    offset={intervals?.offset ?? 0}
                    limit={intervals?.limit ?? 50}
                    onPageChange={setIntervalsOffset}
                    isLoading={intervalsLoading}
                    error={intervalsError}
                  />
                </div>
              </div>
            </section>
          )}

          {/* ── Historical Accuracy ───────────────────────────────────────── */}
          {activeSection === 'accuracy' && (
            <section id="section-accuracy" aria-labelledby="section-accuracy-heading">
              <h2
                id="section-accuracy-heading"
                className="mb-6 text-xs font-semibold uppercase tracking-widest text-slate-500"
              >
                Historical Accuracy
              </h2>

              <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
                <AccuracySection
                  overview={overview}
                  overviewLoading={overviewLoading}
                  overviewError={overviewError}
                  accuracy={accuracy}
                  accuracyLoading={accuracyLoading}
                  accuracyError={accuracyError}
                  highlightDeliveryDate={deliveryDate}
                />
              </div>
            </section>
          )}

          {/* ── Data Sources ─────────────────────────────────────────────── */}
          {activeSection === 'data-sources' && (
            <section id="section-data-sources" aria-labelledby="section-data-sources-heading">
              <h2
                id="section-data-sources-heading"
                className="mb-6 text-xs font-semibold uppercase tracking-widest text-slate-500"
              >
                Data Sources
              </h2>
              <DataProvenance />
            </section>
          )}

        </main>
      </div>
    </div>
  );
}
