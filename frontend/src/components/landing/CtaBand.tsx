import Reveal from './Reveal';
import { IconArrowRight } from './icons';

export default function CtaBand() {
  return (
    <section id="assistant" className="relative overflow-hidden bg-gradient-to-br from-blue-900 via-blue-800 to-blue-950">
      <div className="absolute inset-0 pt-blueprint opacity-40" aria-hidden="true" />
      <div className="absolute -top-40 -right-32 w-[560px] h-[560px] rounded-full bg-emerald-500/10 blur-[130px] pointer-events-none" aria-hidden="true" />
      <div className="absolute -bottom-44 -left-32 w-[520px] h-[520px] rounded-full bg-white/10 blur-[130px] pointer-events-none" aria-hidden="true" />

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28 text-center">
        <Reveal>
          <img
            src="/favicon.svg"
            alt="Project Tracking logo"
            width="64"
            height="64"
            className="w-16 h-16 mx-auto"
          />
        </Reveal>
        <Reveal delay={60}>
          <h2 className="mt-6 text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-white leading-tight">
            Keep every record visible and every amount accounted for
          </h2>
        </Reveal>
        <Reveal delay={120}>
          <p className="mt-5 max-w-2xl mx-auto text-base sm:text-lg text-blue-100 leading-relaxed">
            Set up your team’s workspace in minutes. Create your account, sign in, and
            start tracking estimates, funding, expenses, resources, and your schedule.
          </p>
        </Reveal>
        <Reveal delay={180}>
          <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="/login"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-7 py-3.5 text-sm font-semibold text-blue-900 shadow-xl hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-800 transition-all active:scale-[0.98]"
            >
              Get started
              <IconArrowRight className="w-4 h-4" />
            </a>
            <a
              href="/login"
              className="inline-flex items-center justify-center rounded-xl border border-white/40 bg-white/5 px-7 py-3.5 text-sm font-semibold text-white hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-800 transition-colors active:scale-[0.98]"
            >
              Sign in
            </a>
          </div>
        </Reveal>
        <Reveal delay={240}>
          <p className="mt-8 text-xs text-blue-200/80">
            Sign in and create account both open the existing secure login page.
          </p>
        </Reveal>
      </div>
    </section>
  );
}