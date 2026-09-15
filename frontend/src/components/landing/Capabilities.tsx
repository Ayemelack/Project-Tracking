import Reveal from './Reveal';
import {
  IconBanknotes,
  IconCalendar,
  IconChat,
  IconCube,
  IconDocument,
  IconReceipt,
  IconShield,
  IconEye,
} from './icons';

const features = [
  {
    icon: IconDocument,
    title: 'Estimate management',
    text: 'Upload a project estimate in PDF form; line items are extracted, reviewed, corrected, and confirmed with accurate totals.',
  },
  {
    icon: IconBanknotes,
    title: 'Funding register',
    text: 'Record every fund receipt with amount, source, and reference; track allocations and understand how funding is applied.',
  },
  {
    icon: IconReceipt,
    title: 'Expense tracking',
    text: 'Log expenses against the project with categories, references, and links to estimates — so spending is traceable.',
  },
  {
    icon: IconCube,
    title: 'Resource management',
    text: 'Track materials and labour by budgeted, purchased, delivered, and used quantities — with cost variance in view.',
  },
  {
    icon: IconCalendar,
    title: 'Project schedule',
    text: 'Manage activities with planned and actual dates, progress status, responsible owners, and delay tracking.',
  },
  {
    icon: IconChat,
    title: 'Ask the Assistant',
    text: 'Ask plain-language questions about estimates, funding, expenses, resources, or delays and receive answers grounded in your records.',
  },
];

const roles = [
  {
    icon: IconShield,
    label: 'Administrator',
    text: 'Manage users, control access, create and manage records',
    color: 'bg-blue-800 text-white',
    textColor: 'text-white',
  },
  {
    icon: null,
    label: 'Member',
    text: 'Create and edit project records within permitted areas',
    color: 'bg-blue-50 border border-blue-200',
    textColor: 'text-blue-800',
  },
  {
    icon: IconEye,
    label: 'Viewer',
    text: 'View all registers and project data in read-only access',
    color: 'bg-slate-100 border border-slate-200',
    textColor: 'text-slate-700',
  },
];

export default function Capabilities() {
  return (
    <section id="capabilities" className="relative overflow-hidden bg-slate-50 pt-20 sm:pt-28 pb-24 sm:pb-32">
      <div className="absolute inset-0 pt-blueprint pt-grid-fade opacity-80" aria-hidden="true" />
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <Reveal>
          <div className="max-w-2xl mx-auto text-center">
            <p className="text-sm font-semibold text-blue-800 tracking-wide uppercase">What it does</p>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-[2.75rem] font-bold tracking-tight text-slate-900">
              Six systems that bring a project together
            </h2>
            <p className="mt-4 text-base sm:text-lg text-slate-600 leading-relaxed">
              Instead of scattered spreadsheets, PDFs, and manual updates, Project Tracking
              gives your team one place for the numbers that matter.
            </p>
          </div>
        </Reveal>

        <div className="mt-14 sm:mt-20 grid md:grid-cols-2 xl:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <Reveal key={f.title} delay={i * 60}>
              <div className="group h-full rounded-2xl border border-slate-200 bg-white p-7 sm:p-8 transition-all duration-300 hover:shadow-lg hover:border-blue-200 hover:-translate-y-1">
                <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 text-blue-800 transition-colors duration-300 group-hover:bg-blue-100">
                  <f.icon className="w-6 h-6" />
                </div>
                <h3 className="mt-5 text-lg font-bold text-slate-900">{f.title}</h3>
                <p className="mt-2.5 text-sm text-slate-600 leading-relaxed">{f.text}</p>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={100}>
          <div className="mt-16 sm:mt-20 text-center">
            <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">Access that fits your team</h3>
            <p className="mt-2.5 text-sm sm:text-base text-slate-600">
              Three role levels keep every person focused on what they should see and do.
            </p>

            <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
              {roles.map((r) => (
                <div
                  key={r.label}
                  className={`rounded-xl px-6 py-5 text-left transition-transform duration-300 hover:-translate-y-0.5 ${r.color}`}
                >
                  <div className={`flex items-center gap-2 font-semibold text-sm ${r.textColor}`}>
                    {r.icon ? <r.icon className={`w-4 h-4`} /> : null}
                    {r.label}
                  </div>
                  <p className={`mt-1.5 text-xs sm:text-sm leading-relaxed ${r.textColor === 'text-white' ? 'text-blue-100' : 'text-slate-600'}`}>
                    {r.text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}