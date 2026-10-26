import { CheckCircle, XCircle } from 'lucide-react';
import { parseISO } from 'date-fns';
import { formatDate, formatDateTimeUtc } from '../lib/formatters';

interface Props {
  decisionDate: string;
  deliveryDate: string;
  decisionCutoffUtc: string | null;
  selectedVintageUtc: string | null;
  cutoffHour: number;
}

function isVintageEligible(vintageUtc: string | null, cutoffUtc: string | null): boolean | null {
  if (!vintageUtc || !cutoffUtc) return null;
  return parseISO(vintageUtc) <= parseISO(cutoffUtc);
}

interface RowProps {
  label: string;
  value: string;
  hint?: string;
}

function Row({ label, value, hint }: RowProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <dt className="text-sm" style={{ color: '#686b82' }}>{label}</dt>
      <dd className="text-right text-sm font-medium" style={{ color: '#101114' }} title={hint}>
        {value}
      </dd>
    </div>
  );
}

export function StatusSection({
  decisionDate,
  deliveryDate,
  decisionCutoffUtc,
  selectedVintageUtc,
  cutoffHour,
}: Props) {
  const eligible = isVintageEligible(selectedVintageUtc, decisionCutoffUtc);

  return (
    <section
      aria-labelledby="status-heading"
      className="rounded-lg p-4"
      style={{ background: '#ffffff', boxShadow: 'rgba(0,0,0,0.03) 0px 4px 24px 0px' }}
    >
      <h2
        id="status-heading"
        className="mb-2 text-xs font-medium uppercase tracking-widest"
        style={{ color: '#686b82' }}
      >
        Decision &amp; Forecast Status
      </h2>
      <dl style={{ borderTop: '1px solid #d4d4dc' }}>
        <div style={{ borderBottom: '1px solid #d4d4dc' }}>
          <Row label="Decision date" value={formatDate(decisionDate)} />
        </div>
        <div style={{ borderBottom: '1px solid #d4d4dc' }}>
          <Row
            label={`Decision cutoff (hour ${cutoffHour})`}
            value={decisionCutoffUtc ? formatDateTimeUtc(decisionCutoffUtc) : 'Not available'}
            hint="Modelling assumption; not a confirmed market deadline"
          />
        </div>
        <div style={{ borderBottom: '1px solid #d4d4dc' }}>
          <Row
            label="Selected vintage"
            value={selectedVintageUtc ? formatDateTimeUtc(selectedVintageUtc) : 'Not available'}
          />
        </div>
        <div className="flex items-start justify-between gap-4 py-2" style={{ borderBottom: '1px solid #d4d4dc' }}>
          <dt className="text-sm" style={{ color: '#686b82' }}>Vintage eligible at cutoff</dt>
          <dd className="flex items-center gap-1.5 text-sm font-medium">
            {eligible === null ? (
              <span style={{ color: '#9497a9' }}>Not available</span>
            ) : eligible ? (
              <>
                <CheckCircle className="h-4 w-4" style={{ color: '#08844f' }} />
                <span style={{ color: '#08844f' }}>Yes</span>
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4" style={{ color: '#d11d45' }} />
                <span style={{ color: '#d11d45' }}>No</span>
              </>
            )}
          </dd>
        </div>
        <div style={{ borderBottom: '1px solid #d4d4dc' }}>
          <Row label="Delivery date" value={formatDate(deliveryDate)} />
        </div>
        <Row label="Interval resolution" value="30 minutes (source data)" />
      </dl>
    </section>
  );
}
