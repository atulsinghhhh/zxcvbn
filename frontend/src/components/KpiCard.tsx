import { Info } from 'lucide-react';

interface Props {
  label: string;
  value: string | null;
  unit?: string;
  tooltip?: string;
  status: 'ok' | 'warn' | 'unavailable';
  'data-testid'?: string;
}

const statusColor: Record<Props['status'], string> = {
  ok: 'text-white',
  warn: 'text-amber-300',
  unavailable: 'text-slate-500',
};

export function KpiCard({ label, value, unit, tooltip, status, 'data-testid': testId }: Props) {
  return (
    <div
      className="rounded-lg border border-slate-700 bg-slate-800 p-4"
      data-testid={testId}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          {label}
        </span>
        {tooltip && (
          <span title={tooltip} className="cursor-help text-slate-600 hover:text-slate-400">
            <Info className="h-3.5 w-3.5" />
          </span>
        )}
      </div>

      <div className="mt-2">
        {value === null ? (
          <span className="text-2xl font-bold text-slate-500">—</span>
        ) : (
          <span className={`text-2xl font-bold ${statusColor[status]}`}>{value}</span>
        )}
        {unit && value !== null && (
          <span className="ml-1.5 text-sm text-slate-400">{unit}</span>
        )}
      </div>

      {value === null && (
        <p className="mt-1 text-xs text-slate-600">No data available</p>
      )}
    </div>
  );
}
