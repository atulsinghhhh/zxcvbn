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
      <dt className="text-sm text-slate-400">{label}</dt>
      <dd className="text-right text-sm font-medium text-slate-200" title={hint}>
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
      className="rounded-lg border border-slate-700 bg-slate-800 p-4"
    >
      <h2
        id="status-heading"
        className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500"
      >
        Decision &amp; Forecast Status
      </h2>
      <dl className="divide-y divide-slate-700">
        <Row label="Decision date" value={formatDate(decisionDate)} />
        <Row
          label={`Decision cutoff (hour ${cutoffHour})`}
          value={decisionCutoffUtc ? formatDateTimeUtc(decisionCutoffUtc) : 'Not available'}
          hint="Modelling assumption; not a confirmed market deadline"
        />
        <Row
          label="Selected vintage"
          value={selectedVintageUtc ? formatDateTimeUtc(selectedVintageUtc) : 'Not available'}
        />
        <div className="flex items-start justify-between gap-4 py-2">
          <dt className="text-sm text-slate-400">Vintage eligible at cutoff</dt>
          <dd className="flex items-center gap-1.5 text-sm font-medium">
            {eligible === null ? (
              <span className="text-slate-500">Not available</span>
            ) : eligible ? (
              <>
                <CheckCircle className="h-4 w-4 text-emerald-400" />
                <span className="text-emerald-300">Yes</span>
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4 text-red-400" />
                <span className="text-red-300">No</span>
              </>
            )}
          </dd>
        </div>
        <Row label="Delivery date" value={formatDate(deliveryDate)} />
        <Row label="Interval resolution" value="30 minutes (source data)" />
      </dl>
    </section>
  );
}
