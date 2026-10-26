import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

export function DataProvenance() {
  const [open, setOpen] = useState(false);

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-800">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        aria-expanded={open}
        aria-controls="provenance-body"
      >
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Data Provenance &amp; Assumptions
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4 text-slate-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-500" />
        )}
      </button>

      {open && (
        <div id="provenance-body" className="border-t border-slate-700 px-4 py-4">
          <div className="grid gap-6 text-sm md:grid-cols-2">
            <div>
              <h3 className="mb-2 font-semibold text-slate-200">Data Sources</h3>
              <ul className="space-y-2 text-slate-400">
                <li>
                  <span className="font-medium text-slate-300">Actuals (FUELHH):</span>
                  <br />
                  <a
                    href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-400 underline hover:text-blue-300"
                  >
                    BMRS FUELHH stream
                    <ExternalLink className="h-3 w-3" />
                  </a>
                  <br />
                  <span className="text-xs">Filtered to fuelType=WIND</span>
                </li>
                <li>
                  <span className="font-medium text-slate-300">Forecasts (WINDFOR):</span>
                  <br />
                  <a
                    href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-400 underline hover:text-blue-300"
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
              <h3 className="mb-2 font-semibold text-slate-200">Modelling Assumptions</h3>
              <ul className="space-y-1.5 text-xs text-slate-400">
                <li>• Delivery intervals are 30 minutes in source data.</li>
                <li>• Analysis period: January 2026.</li>
                <li>
                  • Forecast vintage is the latest eligible publication at or before the
                  decision cutoff.
                </li>
                <li>• Decision cutoff is a configurable modelling assumption, not a confirmed market deadline.</li>
                <li>• Forecast errors = forecast − actual.</li>
                <li>• Positive error = over-forecast; negative = under-forecast.</li>
                <li>• Missing observations are not treated as zero.</li>
                <li>• Data freshness depends on source and cache behaviour.</li>
                <li>
                  • This is a historical analytics pilot, not a live trading or automated
                  procurement system.
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-4 rounded-md border border-amber-800/50 bg-amber-900/20 px-3 py-2 text-xs text-amber-300">
            <strong>Note:</strong> Wind-generation forecast errors indicate forecast uncertainty.
            They do not represent the utility's electricity procurement requirement. This system
            uses historical Elexon BMRS data and AI-assisted development (disclosed in the README).
          </div>
        </div>
      )}
    </section>
  );
}
