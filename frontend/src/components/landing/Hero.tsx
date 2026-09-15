import type { CSSProperties } from 'react';
import Reveal from './Reveal';
import useCountUp from './useCountUp';
import { IconArrowRight, IconCheck, IconLock, IconShield } from './icons';

function Stat({ target, suffix = '', label }: { target: number; suffix?: string; label: string }) {
  const [value, ref] = useCountUp(target);
  return (
    <div className="text-center sm:text-left">
      <div className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">
        <span ref={ref}>
          {value}
          {suffix}
        </span>
      </div>
      <div className="mt-1 text-sm text-slate-500">{label}</div>
    </div>
  );
}

function EstimatePreview() {
  return (
    <div className="relative">
      <div className="absolute -top-5 -right-3 sm:-right-6 z-20 hidden md:block pt-float-y">
        <div className="bg-white rounded-xl shadow-xl border border-slate-200 px-4 py-3">
          <div className="text-[11px] font-medium text-slate-500">Total committed</div>
          <div className="mt-0.5 text-[15px] font-bold text-slate-900 tabular-nums">24,600,000 FCFA</div>
          <div className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 pt-pulse-soft" />
            Estimate confirmed
          </div>
        </div>
      </div>

      <div className="absolute -bottom-6 -left-3 sm:-left-6 z-20 hidden md:block pt-float-y" style={{ animationDelay: '1.2s' }}>
        <div className="bg-white rounded-xl shadow-xl border border-slate-200 px-4 py-3 max-w-[240px]">
          <div className="text-[11px] font-medium text-slate-500">Ask the Assistant</div>
          <div className="mt-1 text-xs text-slate-800 leading-snug">
            “How much funding has been received?”
          </div>
          <div className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-blue-800">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
            </svg>
            Answer from your records
          </div>
        </div>
      </div>

      <div className="rounded-2xl bg-white shadow-2xl ring-1 ring-slate-900/10 overflow-hidden">
        <div className="flex items-center gap-3 px-4 h-10 bg-slate-50 border-b border-slate-200">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-300" />
            <span className="w-2.5 h-2.5 rounded-full bg-slate-300" />
            <span className="w-2.5 h-2.5 rounded-full bg-slate-300" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="mx-auto max-w-xs rounded-md bg-white border border-slate-200 px-3 py-1 text-[11px] text-slate-500 text-center truncate">
              app.project-tracking.local/dashboard
            </div>
          </div>
        </div>

        <div className="flex">
          <aside className="hidden sm:flex w-40 flex-col bg-slate-50 border-r border-slate-200 shrink-0">
            <div className="flex items-center gap-2 px-3 h-12 border-b border-slate-200">
              <img src="/favicon.svg" alt="" width="24" height="24" className="w-6 h-6" />
              <span className="text-xs font-semibold text-slate-900 truncate">Project Tracking</span>
            </div>
            <div className="p-2 space-y-0.5">
              {[
                ['Dashboard', true],
                ['Estimate Register', false],
                ['Funding Register', false],
                ['Expense Register', false],
                ['Resource Register', false],
                ['Project Schedule', false],
                ['Ask the Assistant', false],
              ].map(([label, active]) => (
                <div
                  key={label as string}
                  className={`flex items-center px-2 py-1.5 rounded-md text-[11px] font-medium ${
                    active ? 'bg-blue-800 text-white' : 'text-slate-500'
                  }`}
                >
                  {label as string}
                </div>
              ))}
            </div>
          </aside>

          <div className="flex-1 min-w-0 p-4 sm:p-5 bg-white">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h3 className="text-sm sm:text-base font-bold text-slate-900">Dashboard</h3>
                <p className="text-[11px] text-slate-500">Project cost and resource tracking</p>
              </div>
              <div className="hidden sm:flex items-center gap-1.5 rounded-md bg-blue-800 text-white text-[11px] font-semibold px-2.5 py-1.5">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Upload estimate
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2.5">
              <div className="rounded-lg border border-slate-200 p-3">
                <div className="text-[10px] sm:text-[11px] font-medium text-slate-500">Total estimates</div>
                <div className="mt-1 text-lg sm:text-xl font-bold text-slate-900 tabular-nums">3</div>
              </div>
              <div className="rounded-lg border border-emerald-100 bg-emerald-50/60 p-3">
                <div className="text-[10px] sm:text-[11px] font-medium text-emerald-700">Confirmed</div>
                <div className="mt-1 text-lg sm:text-xl font-bold text-emerald-600 tabular-nums">2</div>
              </div>
              <div className="rounded-lg border border-amber-100 bg-amber-50/60 p-3">
                <div className="text-[10px] sm:text-[11px] font-medium text-amber-700">Pending review</div>
                <div className="mt-1 text-lg sm:text-xl font-bold text-amber-600 tabular-nums">1</div>
              </div>
            </div>

            <div className="mt-4 rounded-lg border border-slate-200 overflow-hidden">
              <div className="px-3 py-2 border-b border-slate-200 bg-slate-50 text-[11px] font-semibold text-slate-700">
                Estimate register
              </div>
              <div className="divide-y divide-slate-100">
                {[
                  ['Site construction — phase 1', 'Confirmed', 'emerald'],
                  ['Electrical works', 'Confirmed', 'emerald'],
                  ['Finishing & paint', 'Pending review', 'amber'],
                ].map(([name, status, tone]) => (
                  <div key={name as string} className="flex items-center justify-between gap-2 px-3 py-2">
                    <span className="text-[11px] text-slate-700 truncate min-w-0">{name as string}</span>
                    <span
                      className={`inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        tone === 'emerald' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                      }`}
                    >
                      {status as string}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Hero() {
  return (
    <section id="top" className="relative overflow-hidden">
      <div className="pt-float-y absolute -top-32 -left-40 w-[480px] h-[480px] rounded-full pt-glow-a pointer-events-none">
        <div className="w-full h-full rounded-full bg-blue-200/50 blur-[110px]" />
      </div>
      <div className="pt-float-y absolute -top-24 -right-40 w-[520px] h-[520px] rounded-full pt-glow-b pointer-events-none">
        <div className="w-full h-full rounded-full bg-emerald-100/70 blur-[120px]" />
      </div>
      <div className="absolute inset-0 pt-blueprint pt-grid-fade pointer-events-none" aria-hidden="true" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-16 sm:pt-36 sm:pb-20 lg:pt-40 lg:pb-24">
        <div className="grid lg:grid-cols-[1.05fr_0.95fr] gap-14 lg:gap-12 items-center">
          <div>
            <div className="pt-hero-anim" style={{ '--d': '50ms' } as CSSProperties}>
              <span className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50/70 px-3.5 py-1.5 text-xs font-semibold text-blue-800">
                <img src="/favicon.svg" alt="Project Tracking logo" width="18" height="18" className="w-[18px] h-[18px]" />
                Construction Financial &amp; Resource Management
              </span>
            </div>

            <h1
              className="pt-hero-anim mt-6 text-4xl sm:text-5xl xl:text-6xl font-bold tracking-tight text-slate-900 leading-[1.08]"
              style={{ '--d': '150ms' } as CSSProperties}
            >
              Construction projects deserve{' '}
              <span className="text-blue-800">financial</span> and{' '}
              <span className="text-blue-800">resource</span> accountability.
            </h1>

            <p
              className="pt-hero-anim mt-6 max-w-xl text-base sm:text-lg text-slate-600 leading-relaxed"
              style={{ '--d': '280ms' } as CSSProperties}
            >
              Project Tracking brings estimates, funding, expenses, resources, and your project
              schedule into one secure workspace — so every record is visible, every amount is
              accounted for, and every decision is grounded in data.
            </p>

            <div
              className="pt-hero-anim mt-8 flex flex-col sm:flex-row items-stretch sm:items-center gap-3"
              style={{ '--d': '400ms' } as CSSProperties}
            >
              <a
                href="/login"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-800 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-900/20 hover:bg-blue-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-all active:scale-[0.98]"
              >
                Get started
                <IconArrowRight className="w-4 h-4" />
              </a>
              <a
                href="/login"
                className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-6 py-3.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 hover:border-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-colors active:scale-[0.98]"
              >
                Sign in
              </a>
            </div>

            <ul
              className="pt-hero-anim mt-8 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6 text-sm text-slate-600"
              style={{ '--d': '520ms' } as CSSProperties}
            >
              <li className="flex items-center gap-2">
                <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-800">
                  <IconShield className="w-3 h-3" />
                </span>
                Role-based access
              </li>
              <li className="flex items-center gap-2">
                <span className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-700">
                  <IconCheck className="w-3 h-3" />
                </span>
                Reviewed &amp; confirmed records
              </li>
              <li className="flex items-center gap-2">
                <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-800">
                  <IconLock className="w-3 h-3" />
                </span>
                One secure workspace
              </li>
            </ul>
          </div>

          <div className="relative">
            <div className="pt-hero-anim" style={{ '--d': '350ms' } as CSSProperties}>
              <EstimatePreview />
            </div>
          </div>
        </div>

        <Reveal delay={80} className="mt-20 sm:mt-24">
          <div className="rounded-2xl border border-slate-200 bg-white/80 backdrop-blur px-6 sm:px-10 py-7 sm:py-8">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 sm:gap-6">
              <Stat target={5} label="Core registers — estimates, funding, expenses, resources, schedule" />
              <Stat target={3} label="Access tiers — Viewer, Member, Administrator" />
              <Stat target={1} label="Secure workspace for every record" />
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}