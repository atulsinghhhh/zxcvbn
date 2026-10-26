import { useState } from 'react';
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import type { HourDetail } from '../api/types';
import { formatDateTime } from '../lib/formatters';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorBanner } from './ErrorBanner';

type SortKey = 'start_uk' | 'forecast_mw' | 'actual_mw' | 'signed_error_mw';
type SortDir = 'asc' | 'desc';

function getStatus(h: HourDetail): string {
  if (h.forecast_mw !== null && h.actual_mw !== null) return 'Evaluated';
  if (h.forecast_mw !== null && h.actual_mw === null) return 'No actual';
  if (h.forecast_mw === null && h.actual_mw !== null) return 'No forecast';
  return 'No data';
}

function statusColor(status: string): string {
  switch (status) {
    case 'Evaluated': return '#08844f';
    case 'No actual': return '#d11d45';
    default: return '#9497a9';
  }
}

function rowErrorColor(h: HourDetail): string {
  if (h.abs_error_mw !== null && h.abs_error_mw > 500) return '#d11d45';
  if (h.signed_error_mw !== null && h.signed_error_mw > 0) return '#d11d45';
  if (h.signed_error_mw !== null && h.signed_error_mw < 0) return '#7132f5';
  return '#101114';
}

function fmt(value: number | null, decimals = 0): string {
  return value === null ? '—' : value.toFixed(decimals);
}

interface Props {
  hours: HourDetail[];
  total: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
  isLoading: boolean;
  error: string | null;
}

export function IntervalsTable({ hours, total, offset, limit, onPageChange, isLoading, error }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('start_uk');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  const sorted = [...hours].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (av === null && bv === null) return 0;
    if (av === null) return 1;
    if (bv === null) return -1;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <ChevronUp className="h-3 w-3 opacity-30" />;
    return sortDir === 'asc' ? (
      <ChevronUp className="h-3 w-3" style={{ color: '#7132f5' }} />
    ) : (
      <ChevronDown className="h-3 w-3" style={{ color: '#7132f5' }} />
    );
  }

  function ColHeader({ k, label }: { k: SortKey; label: string }) {
    return (
      <button
        onClick={() => handleSort(k)}
        className="flex items-center gap-1"
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit', padding: 0 }}
        aria-label={`Sort by ${label}`}
      >
        {label}
        <SortIcon k={k} />
      </button>
    );
  }

  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  const canPrev = offset > 0;
  const canNext = offset + limit < total;

  return (
    <div>
      {error && <ErrorBanner message={error} label="Table error" />}

      <div className="overflow-x-auto rounded-lg" style={{ border: '1px solid #d4d4dc' }}>
        <table className="min-w-full text-sm">
          <thead style={{ borderBottom: '1px solid #d4d4dc', background: '#f6f5f9' }}>
            <tr className="text-xs font-medium uppercase tracking-wider" style={{ color: '#686b82' }}>
              <th className="px-4 py-3 text-left">
                <ColHeader k="start_uk" label="Delivery Time (UK)" />
              </th>
              <th className="px-4 py-3 text-right">
                <ColHeader k="forecast_mw" label="Forecast MW" />
              </th>
              <th className="px-4 py-3 text-right">
                <ColHeader k="actual_mw" label="Actual MW" />
              </th>
              <th className="px-4 py-3 text-right">
                <ColHeader k="signed_error_mw" label="Signed Error" />
              </th>
              <th className="px-4 py-3 text-right">Abs Error</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="py-12 text-center">
                  <div className="flex justify-center">
                    <LoadingSpinner />
                  </div>
                </td>
              </tr>
            ) : sorted.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-sm" style={{ color: '#9497a9' }}>
                  No interval data available for this date.
                </td>
              </tr>
            ) : (
              sorted.map((h) => {
                const status = getStatus(h);
                const errColor = rowErrorColor(h);
                return (
                  <tr
                    key={h.start_utc}
                    style={{ borderBottom: '1px solid rgba(212,212,220,0.5)' }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLTableRowElement).style.background = '#f6f5f9'; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLTableRowElement).style.background = ''; }}
                  >
                    <td className="px-4 py-2.5" style={{ color: '#101114' }}>{formatDateTime(h.start_uk)}</td>
                    <td className="px-4 py-2.5 text-right font-mono" style={{ color: h.forecast_mw === null ? '#9497a9' : '#7132f5' }}>
                      {fmt(h.forecast_mw)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono" style={{ color: h.actual_mw === null ? '#9497a9' : '#2e3350' }}>
                      {fmt(h.actual_mw)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono" style={{ color: h.signed_error_mw === null ? '#9497a9' : errColor }}>
                      {h.signed_error_mw !== null && h.signed_error_mw > 0 ? '+' : ''}
                      {fmt(h.signed_error_mw)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono" style={{ color: h.abs_error_mw === null ? '#9497a9' : '#101114' }}>
                      {fmt(h.abs_error_mw)}
                    </td>
                    <td className="px-4 py-2.5 text-xs font-medium" style={{ color: statusColor(status) }}>
                      {status}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="mt-3 flex items-center justify-between text-xs" style={{ color: '#686b82' }}>
          <span>
            Showing {from}–{to} of {total}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(Math.max(0, offset - limit))}
              disabled={!canPrev}
              aria-label="Previous page"
              className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 transition-colors disabled:cursor-not-allowed disabled:opacity-40"
              style={{ border: '1px solid #d4d4dc', color: '#101114', background: '#ffffff' }}
              onMouseEnter={(e) => { if (canPrev) (e.currentTarget as HTMLButtonElement).style.background = '#f6f5f9'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = '#ffffff'; }}
            >
              <ChevronLeft className="h-3 w-3" />
              Prev
            </button>
            <button
              onClick={() => onPageChange(offset + limit)}
              disabled={!canNext}
              aria-label="Next page"
              className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 transition-colors disabled:cursor-not-allowed disabled:opacity-40"
              style={{ border: '1px solid #d4d4dc', color: '#101114', background: '#ffffff' }}
              onMouseEnter={(e) => { if (canNext) (e.currentTarget as HTMLButtonElement).style.background = '#f6f5f9'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = '#ffffff'; }}
            >
              Next
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
