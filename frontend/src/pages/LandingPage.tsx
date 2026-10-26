import { useState } from 'react';
import {
  Wind,
  ArrowRight,
  Clock,
  Target,
  Gauge,
  Database,
  LineChart,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';

interface Props {
  onEnter: () => void;
}

export function LandingPage({ onEnter }: Props) {
  const [decisionDate, setDecisionDate] = useState('2026-01-14');

  return (
    <div className="min-h-screen bg-white text-[#101114] antialiased">
      <Nav onEnter={onEnter} />
      <Hero onEnter={onEnter} decisionDate={decisionDate} setDecisionDate={setDecisionDate} />
      <Showcase />
      <Features />
      <DataSources />
      <CtaBand onEnter={onEnter} />
      <Footer />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── Nav ───────── */

function Nav({ onEnter }: { onEnter: () => void }) {
  return (
    <nav className="sticky top-0 z-50 border-b border-[#eceaf2] bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#7132f5]">
            <Wind className="h-[18px] w-[18px] text-white" />
          </div>
          <span className="text-[17px] font-bold tracking-[-0.02em]">WindSight</span>
        </div>

        <div className="hidden items-center gap-8 md:flex">
          {['Product', 'Features', 'Data', 'Methodology'].map((l) => (
            <a
              key={l}
              href={`#${l.toLowerCase()}`}
              className="text-sm font-medium text-[#686b82] transition-colors hover:text-[#101114]"
            >
              {l}
            </a>
          ))}
        </div>

        <button
          onClick={onEnter}
          className="rounded-lg bg-[#7132f5] px-5 py-2.5 text-sm font-medium text-white shadow-[rgba(16,24,40,0.04)_0px_1px_4px_0px] transition-colors hover:bg-[#5e27d6]"
        >
          Open Dashboard
        </button>
      </div>
    </nav>
  );
}

/* ────────────────────────────────────────────────────────── Hero ───────── */

function Hero({
  onEnter,
  decisionDate,
  setDecisionDate,
}: {
  onEnter: () => void;
  decisionDate: string;
  setDecisionDate: (d: string) => void;
}) {
  return (
    <section id="product" className="relative overflow-hidden bg-[#f6f5f9]">
      {/* ambient violet glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-[-120px] h-[380px] w-[760px] -translate-x-1/2 rounded-full opacity-60 blur-[120px]"
        style={{ background: 'radial-gradient(circle, #d9c7ff 0%, #f6f5f9 70%)' }}
      />

      <div className="relative mx-auto max-w-[900px] px-6 pb-20 pt-24 text-center">
        <span className="inline-flex items-center gap-2 rounded-full bg-[#e4dcf9] px-3.5 py-1.5 text-[13px] font-medium text-[#7132f5]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#7132f5]" />
          UK National Wind · Elexon BMRS · January 2026
        </span>

        <h1 className="mx-auto mt-7 max-w-[820px] text-[clamp(2.75rem,6vw,4.5rem)] font-bold leading-[1.04] tracking-[-0.03em]">
          See the wind before
          <br />
          you commit the trade
        </h1>

        <p className="mx-auto mt-6 max-w-[560px] text-[17px] leading-relaxed text-[#686b82]">
          Day-ahead forecast analytics for UK national wind generation. Measure how
          accurate the latest forecast really was — before your purchasing decision, built
          on real Elexon BMRS data.
        </p>

        {/* capture row — mirrors Kraken's email capture */}
        <div className="mx-auto mt-9 flex max-w-[460px] flex-col items-stretch gap-2.5 sm:flex-row">
          <div className="relative flex flex-1 items-center">
            <Clock className="pointer-events-none absolute left-3.5 h-4 w-4 text-[#9497a9]" />
            <input
              type="date"
              min="2026-01-01"
              max="2026-01-30"
              value={decisionDate}
              onChange={(e) => setDecisionDate(e.target.value)}
              aria-label="Decision date"
              className="w-full rounded-lg border border-[#d4d4dc] bg-white py-3 pl-10 pr-3 text-sm text-[#101114] outline-none transition-colors focus:border-[#101114]"
            />
          </div>
          <button
            onClick={onEnter}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#7132f5] px-6 py-3 text-sm font-medium text-white shadow-[rgba(16,24,40,0.04)_0px_1px_4px_0px] transition-colors hover:bg-[#5e27d6]"
          >
            Analyse forecast
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        <p className="mt-3.5 text-[13px] text-[#9497a9]">
          Half-hourly resolution · no account required · historical analytics pilot
        </p>

        {/* stat band */}
        <div className="mx-auto mt-16 grid max-w-[680px] grid-cols-3 gap-4">
          {[
            { n: '48', l: 'Intervals per delivery day' },
            { n: '2', l: 'Elexon BMRS datasets' },
            { n: 'MAE · RMSE · Bias', l: 'Forecast error metrics' },
          ].map((s) => (
            <div key={s.l} className="px-2">
              <div className="text-[clamp(1.25rem,2.4vw,2.25rem)] font-bold tracking-[-0.02em] text-[#101114]">
                {s.n}
              </div>
              <div className="mt-1 text-[13px] leading-snug text-[#686b82]">{s.l}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────── Product showcase (dark) ───── */

function Showcase() {
  return (
    <section className="bg-white px-6 pt-20">
      <div className="relative mx-auto max-w-[1080px]">
        {/* glow */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-10 top-10 h-[320px] rounded-full opacity-40 blur-[120px]"
          style={{ background: 'radial-gradient(circle, #7132f5 0%, transparent 70%)' }}
        />
        <div
          className="relative overflow-hidden rounded-2xl border border-[#2a2d40] p-5 shadow-2xl sm:p-7"
          style={{ background: 'radial-gradient(120% 120% at 90% -10%, #2e3350 0%, #16182a 55%, #101222 100%)' }}
        >
          <DashboardMock />
        </div>
      </div>
    </section>
  );
}

function DashboardMock() {
  return (
    <div className="rounded-xl bg-[#0e1020]/60 ring-1 ring-white/5">
      {/* window chrome */}
      <div className="flex items-center gap-2 border-b border-white/5 px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        <span className="ml-3 text-[11px] font-medium text-white/40">
          windsight · forecast analysis · delivery 2026-01-15
        </span>
      </div>

      <div className="grid gap-4 p-5 lg:grid-cols-[1fr_260px]">
        {/* chart */}
        <div className="rounded-lg bg-white/[0.03] p-4 ring-1 ring-white/5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-[13px] font-medium text-white/80">
              Forecast vs actual generation
            </span>
            <div className="flex items-center gap-3 text-[11px]">
              <span className="flex items-center gap-1.5 text-white/60">
                <span className="h-2 w-2 rounded-full bg-[#9d6bff]" /> Forecast
              </span>
              <span className="flex items-center gap-1.5 text-white/60">
                <span className="h-2 w-2 rounded-full bg-[#5b9dff]" /> Actual
              </span>
            </div>
          </div>
          <MockChart />
        </div>

        {/* KPI stack */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-1">
          {[
            { l: 'MAE', v: '312', u: 'MW' },
            { l: 'Bias', v: '+148', u: 'MW', accent: true },
            { l: 'RMSE', v: '406', u: 'MW' },
          ].map((k) => (
            <div key={k.l} className="rounded-lg bg-white/[0.04] p-3.5 ring-1 ring-white/5">
              <div className="text-[10px] font-medium uppercase tracking-widest text-white/40">
                {k.l}
              </div>
              <div className="mt-1.5 text-2xl font-bold text-white">
                {k.v}
                <span className="ml-1 text-xs font-normal text-white/40">{k.u}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MockChart() {
  // decorative forecast vs actual lines
  const forecast = '0,78 60,64 120,70 180,46 240,52 300,34 360,40 420,28 480,36 540,22 600,30';
  const actual = '0,84 60,70 120,62 180,58 240,44 300,46 360,32 420,38 480,26 540,32 600,24';
  return (
    <svg viewBox="0 0 600 120" className="h-40 w-full" preserveAspectRatio="none">
      {[20, 50, 80, 110].map((y) => (
        <line key={y} x1="0" y1={y} x2="600" y2={y} stroke="#ffffff" strokeOpacity="0.05" />
      ))}
      <defs>
        <linearGradient id="fArea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#9d6bff" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#9d6bff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,120 ${forecast} 600,120`} fill="url(#fArea)" />
      <polyline points={forecast} fill="none" stroke="#9d6bff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={actual} fill="none" stroke="#5b9dff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 7" />
    </svg>
  );
}

/* ──────────────────────────────────────────────────────── Features ─────── */

function Features() {
  return (
    <section id="features" className="bg-white px-6 py-24">
      <div className="mx-auto max-w-[1200px]">
        <div className="mx-auto max-w-[620px] text-center">
          <h2 className="text-[clamp(2rem,4vw,3rem)] font-bold leading-[1.1] tracking-[-0.03em]">
            Built for the day-ahead decision
          </h2>
          <p className="mt-4 text-[17px] leading-relaxed text-[#686b82]">
            Every number traces back to a published Elexon forecast and a measured actual —
            no invented data, no look-ahead bias.
          </p>
        </div>

        {/* bento grid */}
        <div className="mt-14 grid gap-4 lg:grid-cols-3">
          <FeatureCard
            icon={<Clock className="h-5 w-5" />}
            title="Deterministic vintage selection"
            body="For any purchasing cutoff we select the latest forecast published at or before that moment — reproducible, with no look-ahead."
            wide
          >
            <VintageVisual />
          </FeatureCard>

          <FeatureCard
            icon={<Target className="h-5 w-5" />}
            title="Honest error metrics"
            body="MAE, RMSE, bias and P90 absolute error, computed only over intervals with both a forecast and an actual."
          >
            <MetricsVisual />
          </FeatureCard>

          <FeatureCard
            icon={<Gauge className="h-5 w-5" />}
            title="Interval-level transparency"
            body="Every half-hour is auditable: forecast, actual, signed and absolute error, and an evaluation status."
          />

          <FeatureCard
            icon={<LineChart className="h-5 w-5" />}
            title="Historical accuracy at a glance"
            body="Aggregate January 2026 across every delivery day and spot systematic over- or under-forecasting."
            wide
          >
            <AccuracyVisual />
          </FeatureCard>
        </div>
      </div>
    </section>
  );
}

function FeatureCard({
  icon,
  title,
  body,
  children,
  wide,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  children?: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <div
      className={`flex flex-col rounded-2xl border border-[#eceaf2] bg-white p-6 shadow-[rgba(0,0,0,0.03)_0px_4px_24px_0px] transition-shadow hover:shadow-[rgba(113,50,245,0.08)_0px_8px_32px_0px] ${
        wide ? 'lg:col-span-2' : ''
      }`}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#e4dcf9] text-[#7132f5]">
        {icon}
      </div>
      <h3 className="mt-5 text-[19px] font-bold tracking-[-0.01em]">{title}</h3>
      <p className="mt-2 text-[15px] leading-relaxed text-[#686b82]">{body}</p>
      {children && <div className="mt-6">{children}</div>}
    </div>
  );
}

function VintageVisual() {
  const pubs = [
    { t: '06:00', ok: true },
    { t: '09:00', ok: true },
    { t: '11:00', sel: true },
    { t: '14:00', late: true },
    { t: '17:00', late: true },
  ];
  return (
    <div className="rounded-xl bg-[#f6f5f9] p-4">
      <div className="mb-3 flex items-center justify-between text-[11px] font-medium text-[#9497a9]">
        <span>Forecast publications</span>
        <span>Cutoff 11:00</span>
      </div>
      <div className="flex items-end gap-2">
        {pubs.map((p) => (
          <div key={p.t} className="flex flex-1 flex-col items-center gap-1.5">
            <div
              className={`w-full rounded-md ${
                p.sel ? 'bg-[#7132f5]' : p.late ? 'bg-[#d4d4dc]' : 'bg-[#c3acf5]'
              }`}
              style={{ height: p.sel ? 44 : p.late ? 20 : 30 }}
            />
            <span className={`text-[10px] ${p.sel ? 'font-semibold text-[#7132f5]' : 'text-[#9497a9]'}`}>
              {p.t}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-1.5 text-[11px] text-[#686b82]">
        <CheckCircle2 className="h-3.5 w-3.5 text-[#08844f]" />
        11:00 vintage selected — latest eligible at cutoff
      </div>
    </div>
  );
}

function MetricsVisual() {
  return (
    <div className="grid grid-cols-2 gap-2.5">
      {[
        { l: 'MAE', v: '312 MW' },
        { l: 'RMSE', v: '406 MW' },
        { l: 'Bias', v: '+148 MW', accent: true },
        { l: 'P90', v: '690 MW' },
      ].map((m) => (
        <div key={m.l} className="rounded-lg bg-[#f6f5f9] px-3 py-2.5">
          <div className="text-[10px] font-medium uppercase tracking-widest text-[#9497a9]">
            {m.l}
          </div>
          <div className={`mt-0.5 text-sm font-bold ${m.accent ? 'text-[#7132f5]' : 'text-[#101114]'}`}>
            {m.v}
          </div>
        </div>
      ))}
    </div>
  );
}

function AccuracyVisual() {
  const bars = [40, 62, 35, 70, 48, 80, 30, 55, 42, 66, 38, 72];
  return (
    <div className="rounded-xl bg-[#f6f5f9] p-4">
      <div className="mb-3 text-[11px] font-medium text-[#9497a9]">
        Daily absolute error — January 2026
      </div>
      <div className="flex h-24 items-end gap-1.5">
        {bars.map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm"
            style={{
              height: `${h}%`,
              background: i === 5 ? '#7132f5' : '#d9c7ff',
            }}
          />
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────── Data sources ──── */

function DataSources() {
  return (
    <section id="data" className="bg-[#f6f5f9] px-6 py-24">
      <div className="mx-auto max-w-[1200px]">
        <div className="mx-auto max-w-[620px] text-center">
          <span className="text-[13px] font-semibold uppercase tracking-widest text-[#7132f5]">
            Data provenance
          </span>
          <h2 className="mt-3 text-[clamp(2rem,4vw,3rem)] font-bold leading-[1.1] tracking-[-0.03em]">
            Powered by Elexon BMRS
          </h2>
          <p className="mt-4 text-[17px] leading-relaxed text-[#686b82]">
            Two public datasets, streamed directly. National wind only — nothing
            fabricated, nothing modelled beyond the documented assumptions.
          </p>
        </div>

        <div className="mt-14 grid gap-5 md:grid-cols-2">
          <SourceCard
            tag="Actuals"
            name="FUELHH"
            desc="Half-hourly metered generation by fuel type, filtered to fuelType = WIND. The ground truth every forecast is scored against."
            href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream"
          />
          <SourceCard
            tag="Forecasts"
            name="WINDFOR"
            desc="Published wind-generation forecasts with their publication time, enabling deterministic vintage selection at any decision cutoff."
            href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream"
          />
        </div>
      </div>
    </section>
  );
}

function SourceCard({
  tag,
  name,
  desc,
  href,
}: {
  tag: string;
  name: string;
  desc: string;
  href: string;
}) {
  return (
    <div className="rounded-2xl border border-[#eceaf2] bg-white p-7 shadow-[rgba(0,0,0,0.03)_0px_4px_24px_0px]">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-[#e4dcf9] text-[#7132f5]">
          <Database className="h-5 w-5" />
        </div>
        <div>
          <span className="rounded-full bg-[#f6f5f9] px-2.5 py-0.5 text-[11px] font-medium text-[#686b82]">
            {tag}
          </span>
          <div className="mt-1 text-lg font-bold tracking-[-0.01em]">{name}</div>
        </div>
      </div>
      <p className="mt-4 text-[15px] leading-relaxed text-[#686b82]">{desc}</p>
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-[#7132f5] hover:underline"
      >
        View BMRS endpoint
        <ExternalLink className="h-3.5 w-3.5" />
      </a>
    </div>
  );
}

/* ──────────────────────────────────────────────────────── CTA band ─────── */

function CtaBand({ onEnter }: { onEnter: () => void }) {
  return (
    <section id="methodology" className="bg-white px-6 py-24">
      <div
        className="relative mx-auto max-w-[1080px] overflow-hidden rounded-3xl px-6 py-20 text-center"
        style={{ background: 'radial-gradient(130% 130% at 85% -20%, #916be6 0%, #692fe4 45%, #4f24ad 100%)' }}
      >
        <div className="relative mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/20">
          <Wind className="h-7 w-7 text-white" />
        </div>
        <h2 className="relative mx-auto mt-6 max-w-[620px] text-[clamp(2rem,4.5vw,3.25rem)] font-bold leading-[1.08] tracking-[-0.03em] text-white">
          Make your forecast call with evidence
        </h2>
        <p className="relative mx-auto mt-4 max-w-[480px] text-[17px] leading-relaxed text-white/80">
          Open the dashboard and explore wind-forecast accuracy across January 2026.
        </p>
        <button
          onClick={onEnter}
          className="relative mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-7 py-3.5 text-sm font-semibold text-[#4f24ad] shadow-lg transition-transform hover:scale-[1.02]"
        >
          Open Dashboard
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </section>
  );
}

/* ──────────────────────────────────────────────────────── Footer ───────── */

function Footer() {
  return (
    <footer className="border-t border-[#eceaf2] bg-white px-6 py-12">
      <div className="mx-auto max-w-[1200px]">
        <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#7132f5]">
              <Wind className="h-4 w-4 text-white" />
            </div>
            <span className="text-[15px] font-bold tracking-[-0.02em]">WindSight</span>
          </div>
          <p className="max-w-[560px] text-[13px] leading-relaxed text-[#9497a9]">
            Historical analytics pilot — not a live trading or automated procurement
            system. Wind-forecast error reflects forecast uncertainty, not a utility's
            procurement requirement. AI-assisted development is disclosed in the README.
          </p>
        </div>
        <div className="mt-8 border-t border-[#f0eff4] pt-6 text-[13px] text-[#9497a9]">
          © 2026 WindSight · UK National Wind · Data from Elexon BMRS (FUELHH + WINDFOR)
        </div>
      </div>
    </footer>
  );
}
