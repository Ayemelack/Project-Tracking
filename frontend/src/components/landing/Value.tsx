import Reveal from './Reveal';
import {
  IconBanknotes,
  IconCalendar,
  IconChat,
  IconCube,
  IconDocument,
  IconReceipt,
} from './icons';

const bullets = [
  {
    icon: IconDocument,
    title: 'Estimates under control',
    text: 'Upload an estimate, extract the line items, review and correct them, and confirm the total — so the numbers everyone works from are real.',
  },
  {
    icon: IconBanknotes,
    title: 'Money in, money out, visible',
    text: 'Every fund receipt and every expense is recorded with amounts, sources, categories, and references in a single register.',
  },
  {
    icon: IconCube,
    title: 'Resources accountable',
    text: 'Materials and labour are tracked by budgeted, purchased, delivered, and used quantities — with costs and variances in view.',
  },
  {
    icon: IconCalendar,
    title: 'Schedules that surface delays',
    text: 'Activities and milestones carry status and progress, and delays are flagged so problems appear early instead of at delivery.',
  },
];

const chain = [
  { icon: IconDocument, label: 'Estimate', sub: 'Extract, review & confirm' },
  { icon: IconBanknotes, label: 'Funding', sub: 'Receipts, sources & allocations' },
  { icon: IconReceipt, label: 'Expenses', sub: 'Categorized & referenced' },
  { icon: IconCube, label: 'Resources', sub: 'Quantities, cost & variance' },
  { icon: IconCalendar, label: 'Schedule', sub: 'Activities, milestones, delays' },
  { icon: IconChat, label: 'Assistant', sub: 'Answers grounded in your data' },
];

export default function Value() {
  return (
    <section id="overview" className="relative overflow-hidden bg-slate-900 text-white">
      <div className="absolute inset-0 pt-blueprint opacity-70" aria-hidden="true" />
      <div className="absolute -bottom-40 left-1/2 -translate-x-1/2 w-[720px] h-[720px] rounded-full bg-blue-900/40 blur-[130px] pointer-events-none" aria-hidden="true" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28">
        <div className="grid lg:grid-cols-[1fr_0.92fr] gap-14 lg:gap-20 items-center">
          <div>
            <Reveal>
              <p className="text-sm font-semibold text-blue-300 tracking-wide uppercase">
                Why Project Tracking
              </p>
            </Reveal>
            <Reveal delay={60}>
              <h2 className="mt-4 text-3xl sm:text-4xl lg:text-[2.75rem] font-bold tracking-tight leading-tight">
                Stop stitching your project story together by hand
              </h2>
            </Reveal>
            <Reveal delay={120}>
              <p className="mt-5 max-w-xl text-base sm:text-lg text-slate-300 leading-relaxed">
                When estimates, payments, purchases, and schedules live in different places, nobody
                sees the whole picture. Project Tracking centralizes them — so the team works from
                the same numbers and leadership decides with confidence.
              </p>
            </Reveal>

            <ul className="mt-10 space-y-7">
              {bullets.map((b, i) => (
                <Reveal key={b.title} as="li" delay={i * 70}>
                  <div className="flex gap-4">
                    <div className="flex items-center justify-center w-11 h-11 shrink-0 rounded-xl bg-blue-800/60 border border-blue-700/50 text-white">
                      <b.icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-white">{b.title}</h3>
                      <p className="mt-1 text-sm text-slate-300 leading-relaxed max-w-lg">{b.text}</p>
                    </div>
                  </div>
                </Reveal>
              ))}
            </ul>
          </div>

          <Reveal delay={150}>
            <div className="rounded-2xl bg-slate-800/70 border border-slate-700/70 p-6 sm:p-8 shadow-2xl">
              <p className="text-sm font-semibold text-slate-300">Every record, tracked</p>
              <ol className="mt-6 space-y-0">
                {chain.map((c, i) => (
                  <li key={c.label}>
                    <div className="flex items-center gap-4 py-3">
                      <div className="flex items-center justify-center w-9 h-9 shrink-0 rounded-lg bg-slate-900/80 border border-slate-700 text-blue-300">
                        <c.icon className="w-4.5 h-4.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-white">{c.label}</div>
                        <div className="text-xs text-slate-400">{c.sub}</div>
                      </div>
                      <span
                        className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                          i < chain.length - 1 ? 'bg-emerald-500/10 text-emerald-300' : 'bg-blue-500/10 text-blue-300'
                        }`}
                      >
                        {i < chain.length - 1 ? 'Tracked' : 'Answers'}
                      </span>
                    </div>
                    {i < chain.length - 1 && (
                      <div className="ml-[18px] h-3 w-px bg-slate-700" aria-hidden="true" />
                    )}
                  </li>
                ))}
              </ol>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}