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
    <header className="px-6 py-4" style={{ borderBottom: '1px solid #d4d4dc', background: '#ffffff' }}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        {/* Title block */}
        <div>
          <h1 className="font-bold" style={{ fontSize: 20, color: '#101114', letterSpacing: '-0.3px' }}>
            Wind Forecast Overview
          </h1>
          <p className="mt-0.5 text-sm" style={{ color: '#686b82' }}>
            UK national wind generation · Day-ahead analytics
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <span
            className="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium"
            style={{ background: '#e4dcf9', color: '#7132f5' }}
          >
            Historical data
          </span>

          {/* Decision date picker */}
          <div className="flex items-center gap-2">
            <label htmlFor="decision-date" className="text-xs font-medium" style={{ color: '#686b82' }}>
              Decision date
            </label>
            <div className="relative flex items-center">
              <Calendar className="pointer-events-none absolute left-2 h-3.5 w-3.5" style={{ color: '#9497a9' }} />
              <input
                id="decision-date"
                type="date"
                min="2026-01-01"
                max="2026-01-30"
                value={decisionDate}
                onChange={(e) => onDateChange(e.target.value)}
                className="rounded-lg py-1.5 pl-7 pr-3 text-sm focus:outline-none"
                style={{
                  border: '1px solid #d4d4dc',
                  background: '#ffffff',
                  color: '#101114',
                }}
                aria-label="Select decision date"
              />
            </div>
          </div>

          {/* Refresh button */}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            aria-label="Refresh data"
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            style={{
              border: '1px solid #d4d4dc',
              background: '#ffffff',
              color: '#101114',
              boxShadow: 'rgba(16,24,40,0.04) 0px 1px 4px 0px',
            }}
            onMouseEnter={(e) => { if (!isLoading) (e.currentTarget as HTMLButtonElement).style.background = '#f6f5f9'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = '#ffffff'; }}
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
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs" style={{ color: '#9497a9' }}>
        <span>
          Delivery date:{' '}
          <span className="font-medium" style={{ color: '#101114' }}>{formatDate(deliveryDate)}</span>
        </span>
        {decisionCutoffUtc && (
          <span>
            Decision cutoff:{' '}
            <span
              className="font-medium"
              style={{ color: '#101114' }}
              title="Modelling assumption, not a confirmed market deadline"
            >
              {formatDateTimeUtc(decisionCutoffUtc)}
            </span>
          </span>
        )}
        {selectedVintageUtc && (
          <span>
            Selected vintage:{' '}
            <span className="font-medium" style={{ color: '#101114' }}>
              {formatDateTimeUtc(selectedVintageUtc)}
            </span>
          </span>
        )}
      </div>
    </header>
  );
}
