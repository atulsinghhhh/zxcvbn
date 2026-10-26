import { RefreshCw, Calendar } from 'lucide-react';
import { LoadingSpinner } from './LoadingSpinner';
import { formatDate, formatDateTimeUtc } from '../lib/formatters';

interface Props {
  decisionDate: string;
  deliveryDate: string;
  selectedVintageUtc: string | null;
  decisionCutoffUtc: string | null;
  onDateChange: (date: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export function Header({
  decisionDate,
  deliveryDate,
  selectedVintageUtc,
  decisionCutoffUtc,
  onDateChange,
  onRefresh,
  isLoading,
}: Props) {
  return (
    <header className="border-b border-slate-700 bg-slate-900 px-6 py-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        {/* Title block */}
        <div>
          <h1 className="text-xl font-bold text-white">Wind Forecast Overview</h1>
          <p className="mt-0.5 text-sm text-slate-400">
            UK national wind generation · Day-ahead analytics
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center rounded-full bg-blue-900/50 px-2.5 py-1 text-xs font-medium text-blue-300">
            Historical data
          </span>

          {/* Decision date picker */}
          <div className="flex items-center gap-2">
            <label htmlFor="decision-date" className="text-xs font-medium text-slate-400">
              Decision date
            </label>
            <div className="relative flex items-center">
              <Calendar className="pointer-events-none absolute left-2 h-3.5 w-3.5 text-slate-500" />
              <input
                id="decision-date"
                type="date"
                min="2026-01-01"
                max="2026-01-30"
                value={decisionDate}
                onChange={(e) => onDateChange(e.target.value)}
                className="rounded border border-slate-600 bg-slate-800 py-1.5 pl-7 pr-3 text-sm text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                aria-label="Select decision date"
              />
            </div>
          </div>

          {/* Refresh button */}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            aria-label="Refresh data"
            className="flex items-center gap-1.5 rounded border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? (
              <LoadingSpinner size="sm" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Refresh
          </button>
        </div>
      </div>

      {/* Date metadata strip */}
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-400">
        <span>
          Delivery date:{' '}
          <span className="font-medium text-slate-200">{formatDate(deliveryDate)}</span>
        </span>
        {decisionCutoffUtc && (
          <span>
            Decision cutoff:{' '}
            <span className="font-medium text-slate-200" title="Modelling assumption, not a confirmed market deadline">
              {formatDateTimeUtc(decisionCutoffUtc)}
            </span>
          </span>
        )}
        {selectedVintageUtc && (
          <span>
            Selected vintage:{' '}
            <span className="font-medium text-slate-200">
              {formatDateTimeUtc(selectedVintageUtc)}
            </span>
          </span>
        )}
      </div>
    </header>
  );
}
