import { useEffect, useState } from 'react';

const navLinks = [
  { id: 'overview', label: 'Overview' },
  { id: 'capabilities', label: 'Capabilities' },
  { id: 'showcase', label: 'How it works' },
  { id: 'assistant', label: 'Assistant' },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [menuOpen]);

  const goTo = (id: string) => {
    setMenuOpen(false);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-white/85 backdrop-blur-md border-b border-slate-200 shadow-sm'
          : 'bg-transparent border-b border-transparent'
      }`}
    >
      <nav
        aria-label="Landing navigation"
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"
      >
        <div className="flex h-16 sm:h-[72px] items-center justify-between gap-4">
          <a
            href="#top"
            onClick={(e) => {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="flex items-center gap-3 min-w-0"
            aria-label="Project Tracking — back to top"
          >
            <img
              src="/favicon.svg"
              alt="Project Tracking logo"
              width="38"
              height="38"
              className="w-[38px] h-[38px] shrink-0"
            />
            <span className="hidden sm:block min-w-0">
              <span className="block text-[15px] font-semibold text-slate-900 leading-tight truncate">
                Project Tracking
              </span>
              <span className="block text-xs text-slate-500 leading-tight truncate">
                Construction Financial &amp; Resource Management
              </span>
            </span>
          </a>

          <div className="hidden lg:flex items-center gap-1">
            {navLinks.map((link) => (
              <button
                key={link.id}
                type="button"
                onClick={() => goTo(link.id)}
                className="inline-flex items-center px-3.5 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-colors"
              >
                {link.label}
              </button>
            ))}
          </div>

          <div className="hidden lg:flex items-center gap-3">
            <a
              href="/login"
              className="inline-flex items-center px-4 py-2.5 rounded-lg text-sm font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-colors"
            >
              Sign in
            </a>
            <a
              href="/login"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-colors active:scale-[0.98]"
            >
              Get started
            </a>
          </div>

          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
            aria-controls="landing-mobile-menu"
            aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            className="lg:hidden inline-flex items-center justify-center w-11 h-11 -mr-2 rounded-lg text-slate-700 hover:text-slate-900 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 transition-colors"
          >
            {menuOpen ? (
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </nav>

      {menuOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-slate-900/40" aria-hidden="true" onClick={() => setMenuOpen(false)} />
      )}

      <div
        id="landing-mobile-menu"
        className={`lg:hidden fixed inset-y-0 right-0 z-50 flex w-[290px] max-w-[85vw] flex-col bg-white shadow-2xl transition-transform duration-300 ${
          menuOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-5 h-16 border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <img src="/favicon.svg" alt="" width="32" height="32" className="w-8 h-8 shrink-0" />
            <span className="text-[15px] font-semibold text-slate-900 truncate">Project Tracking</span>
          </div>
          <button
            type="button"
            onClick={() => setMenuOpen(false)}
            aria-label="Close navigation menu"
            className="inline-flex items-center justify-center w-11 h-11 -mr-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <nav aria-label="Mobile navigation" className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
          {navLinks.map((link) => (
            <button
              key={link.id}
              type="button"
              onClick={() => goTo(link.id)}
              className="flex w-full items-center px-3 py-3 rounded-lg text-left text-[15px] font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 transition-colors"
            >
              {link.label}
            </button>
          ))}
        </nav>

        <div className="px-5 py-5 border-t border-slate-200 shrink-0 space-y-3">
          <a
            href="/login"
            className="w-full inline-flex items-center justify-center rounded-lg bg-blue-800 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-colors active:scale-[0.98]"
          >
            Get started
          </a>
          <a
            href="/login"
            className="w-full inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 transition-colors"
          >
            Sign in
          </a>
        </div>
      </div>
    </header>
  );
}