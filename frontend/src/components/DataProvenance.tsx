import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

interface Props {
  /** Human-readable analysis period, e.g. "26 Sep – 26 Oct 2026". Falls back to a generic label. */
  analysisPeriod?: string;
}

export function DataProvenance({ analysisPeriod }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <section
      className="rounded-lg"
      style={{ background: '#ffffff', border: '1px solid #d4d4dc' }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        aria-expanded={open}
        aria-controls="provenance-body"
        style={{ background: 'none', border: 'none', cursor: 'pointer' }}
      >
        <span className="text-xs font-medium uppercase tracking-widest" style={{ color: '#686b82' }}>
          Data Provenance &amp; Assumptions
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4" style={{ color: '#9497a9' }} />
        ) : (
          <ChevronDown className="h-4 w-4" style={{ color: '#9497a9' }} />
        )}
      </button>

      {open && (
        <div id="provenance-body" className="px-4 py-4" style={{ borderTop: '1px solid #d4d4dc' }}>
          <div className="grid gap-6 text-sm md:grid-cols-2">
            <div>
              <h3 className="mb-2 font-semibold" style={{ color: '#101114' }}>Data Sources</h3>
              <ul className="space-y-2" style={{ color: '#686b82' }}>
                <li>
                  <span className="font-medium" style={{ color: '#101114' }}>Actuals (FUELHH):</span>
                  <br />
                  <a
                    href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs underline"
                    style={{ color: '#7132f5' }}
                  >
                    BMRS FUELHH stream
                    <ExternalLink className="h-3 w-3" />
                  </a>
                  <br />
                  <span className="text-xs">Filtered to fuelType=WIND</span>
                </li>
                <li>
                  <span className="font-medium" style={{ color: '#101114' }}>Forecasts (WINDFOR):</span>
                  <br />
                  <a
                    href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs underline"
                    style={{ color: '#7132f5' }}
                  >
                    BMRS WINDFOR stream
                    <ExternalLink className="h-3 w-3" />
                  </a>
                  <br />
                  <span className="text-xs">Supplies forecast values and publishTime</span>
                </li>
              </ul>
            </div>

            <div>
              <h3 className="mb-2 font-semibold" style={{ color: '#101114' }}>Modelling Assumptions</h3>
              <ul className="space-y-1.5 text-xs" style={{ color: '#686b82' }}>
                <li>• Delivery intervals are 30 minutes in source data.</li>
                <li>• Analysis period: {analysisPeriod ?? 'rolling 30-day window'}.</li>
                <li>• Forecast vintage is the latest eligible publication at or before the decision cutoff.</li>
                <li>• Decision cutoff is a configurable modelling assumption, not a confirmed market deadline.</li>
                <li>• Forecast errors = forecast − actual.</li>
                <li>• Positive error = over-forecast; negative = under-forecast.</li>
                <li>• Missing observations are not treated as zero.</li>
                <li>• Data freshness depends on source and cache behaviour.</li>
                <li>• This is a historical analytics pilot, not a live trading or automated procurement system.</li>
              </ul>
            </div>
          </div>

          <div
            className="mt-4 rounded-lg px-3 py-2 text-xs"
            style={{ background: '#fef3c7', border: '1px solid rgba(245,158,11,0.3)', color: '#92400e' }}
          >
            <strong>Note:</strong> Wind-generation forecast errors indicate forecast uncertainty.
            They do not represent the utility's electricity procurement requirement. This system
            uses historical Elexon BMRS data and AI-assisted development (disclosed in the README).
          </div>
        </div>
      )}
    </section>
  );
}
