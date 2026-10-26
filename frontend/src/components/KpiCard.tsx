import { Info } from 'lucide-react';

interface Props {
  label: string;
  value: string | null;
  unit?: string;
  tooltip?: string;
  status: 'ok' | 'warn' | 'unavailable';
  'data-testid'?: string;
}

const valueColor: Record<Props['status'], string> = {
  ok: '#101114',
  warn: '#d11d45',
  unavailable: '#9497a9',
};

export function KpiCard({ label, value, unit, tooltip, status, 'data-testid': testId }: Props) {
  return (
    <div
      className="rounded-lg p-4"
      style={{ background: '#ffffff', boxShadow: 'rgba(0,0,0,0.03) 0px 4px 24px 0px' }}
      data-testid={testId}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-widest" style={{ color: '#686b82' }}>
          {label}
        </span>
        {tooltip && (
          <span title={tooltip} className="cursor-help" style={{ color: '#9497a9' }}>
            <Info className="h-3.5 w-3.5" />
          </span>
        )}
      </div>

      <div className="mt-2">
        {value === null ? (
          <span className="text-2xl font-bold" style={{ color: '#9497a9' }}>—</span>
        ) : (
          <span className="text-2xl font-bold" style={{ color: valueColor[status] }}>{value}</span>
        )}
        {unit && value !== null && (
          <span className="ml-1.5 text-sm" style={{ color: '#686b82' }}>{unit}</span>
        )}
      </div>

      {value === null && (
        <p className="mt-1 text-xs" style={{ color: '#9497a9' }}>No data available</p>
      )}
    </div>
  );
}
