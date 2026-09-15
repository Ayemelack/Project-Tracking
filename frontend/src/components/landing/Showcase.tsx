import Reveal from './Reveal';
import { IconCheck } from './icons';

const steps = [
  {
    num: '1',
    title: 'Upload',
    text: 'Bring your project estimate into the system as a PDF.',
  },
  {
    num: '2',
    title: 'Review & confirm',
    text: 'Line items are extracted automatically; review, correct, and confirm the totals.',
  },
  {
    num: '3',
    title: 'Track & manage',
    text: 'Log funding, expenses, resources, and schedule — then ask the assistant for answers.',
  },
];

export default function Showcase() {
  return (
    <section id="showcase" className="relative overflow-hidden bg-white py-20 sm:py-28">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <Reveal>
          <div className="max-w-2xl mx-auto text-center">
            <p className="text-sm font-semibold text-blue-800 tracking-wide uppercase">How it works</p>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-[2.75rem] font-bold tracking-tight text-slate-900">
              From uploaded estimate to full project visibility
            </h2>
          </div>
        </Reveal>

        <div className="mt-14 sm:mt-20 relative max-w-4xl mx-auto">
          <div
            className="hidden md:block absolute left-0 right-0 top-[28px] h-px bg-slate-200"
            aria-hidden="true"
          />
          <ol className="relative grid md:grid-cols-3 gap-10 md:gap-8">
            {steps.map((s, i) => (
              <Reveal key={s.num} delay={i * 70}>
                <li className="relative flex flex-col text-center md:text-left items-center md:items-start">
                  <span className="relative z-10 flex items-center justify-center w-14 h-14 rounded-full bg-blue-800 text-white text-xl font-bold shadow-lg shadow-blue-800/30">
                    {s.num}
                  </span>
                  <h3 className="mt-5 text-lg font-bold text-slate-900">{s.title}</h3>
                  <p className="mt-2 text-sm text-slate-600 leading-relaxed max-w-xs">{s.text}</p>
                </li>
              </Reveal>
            ))}
          </ol>
        </div>

        <Reveal delay={120}>
          <div className="mt-20 sm:mt-24 rounded-2xl border border-slate-200 bg-slate-50 shadow-xl overflow-hidden">
            <div className="grid lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-200">
              <div className="p-6 sm:p-8">
                <div className="text-sm font-semibold text-slate-900">Estimate register</div>
                <div className="mt-1 text-xs text-slate-500">Confirmed estimates visible across the team</div>

                <div className="mt-5 rounded-lg bg-white border border-slate-200 overflow-hidden">
                  <div className="grid grid-cols-[1fr_120px_100px] text-[11px] font-semibold text-slate-500 bg-slate-50 border-b border-slate-200 px-4 py-2">
                    <span>Title</span>
                    <span>Status</span>
                    <span className="text-right">Amount</span>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {[
                      {
                        title: 'Site construction — phase 1',
                        status: 'Confirmed',
                        emerald: true,
                        amount: '16,768,565',
                      },
                      {
                        title: 'Electrical works',
                        status: 'Confirmed',
                        emerald: true,
                        amount: '2,340,000',
                      },
                      {
                        title: 'Finishing & paint',
                        status: 'Pending review',
                        emerald: false,
                        amount: '1,492,000',
                      },
                    ].map((row) => (
                      <div
                        key={row.title}
                        className="grid grid-cols-[1fr_120px_100px] items-center px-4 py-2.5 gap-2"
                      >
                        <span className="text-xs text-slate-700 truncate">{row.title}</span>
                        <span
                          className={`inline-flex justify-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            row.emerald ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                          }`}
                        >
                          {row.status}
                        </span>
                        <span className="text-xs font-medium text-slate-700 text-right tabular-nums">
                          {row.amount} <span className="text-slate-400 font-normal">FCFA</span>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
                  <IconCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                  2 confirmed · 1 pending review
                </div>
              </div>

              <div className="bg-white p-6 sm:p-8 flex flex-col">
                <div className="text-sm font-semibold text-slate-900">Ask the Assistant</div>
                <div className="mt-1 text-xs text-slate-500">Natural-language answers from your records</div>

                <div className="mt-5 flex-1 space-y-4">
                  <div className="flex justify-end">
                    <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-800 px-4 py-2.5 text-sm text-white leading-snug">
                      How much funding has been received?
                    </div>
                  </div>
                  <div className="flex items-end gap-2">
                    <div className="w-7 h-7 shrink-0 rounded-full bg-blue-100 flex items-center justify-center text-blue-800">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
                      </svg>
                    </div>
                    <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-slate-100 px-4 py-3 text-sm text-slate-700 leading-relaxed">
                      <p>You have received <strong>18,200,000 FCFA</strong> across 4 recorded fund receipts.</p>
                      <div className="mt-2.5 flex flex-wrap gap-1.5">
                        {['Fund receipt · GS-0001', 'Fund receipt · GS-0002', 'Fund receipt · GS-0003'].map((ref) => (
                          <span
                            key={ref}
                            className="inline-flex items-center gap-1 rounded-md bg-white border border-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-600"
                          >
                            {ref}
                          </span>
                        ))}
                        <span className="text-[10px] text-slate-400">+1 more</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-5 flex items-center gap-2 text-xs text-slate-500">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 pt-pulse-soft" />
                  Assistant uses your registered records only
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}