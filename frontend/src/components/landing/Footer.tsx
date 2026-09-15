export default function Footer() {
  return (
    <footer className="bg-slate-100 border-t border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
        <div className="grid md:grid-cols-[1.4fr_1fr] gap-10 items-start">
          <div>
            <a href="#top" className="flex items-center gap-3" aria-label="Project Tracking — back to top">
              <img src="/favicon.svg" alt="Project Tracking logo" width="38" height="38" className="w-[38px] h-[38px] shrink-0" />
              <div className="min-w-0">
                <div className="text-[15px] font-semibold text-slate-900 leading-tight">Project Tracking</div>
                <div className="text-xs text-slate-500 leading-tight">
                  Construction Financial &amp; Resource Management
                </div>
              </div>
            </a>
            <p className="mt-4 max-w-md text-sm text-slate-600 leading-relaxed">
              A secure workspace for estimating, funding, spending, resources, schedule,
              and oversight on construction projects.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-6 sm:max-w-xs md:justify-self-end md:text-right">
            <div>
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wide">Get started</h3>
              <ul className="mt-3 space-y-2.5 text-sm">
                <li>
                  <a href="/login" className="text-slate-600 hover:text-slate-900 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded">
                    Create an account
                  </a>
                </li>
                <li>
                  <a href="/login" className="text-slate-600 hover:text-slate-900 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded">
                    Sign in
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wide">Explore</h3>
              <ul className="mt-3 space-y-2.5 text-sm">
                {[
                  ['Capabilities', 'capabilities'],
                  ['How it works', 'showcase'],
                ].map(([label, id]) => (
                  <li key={id as string}>
                    <button
                      type="button"
                      onClick={() =>
                        document.getElementById(id as string)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                      }
                      className="text-slate-600 hover:text-slate-900 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded"
                    >
                      {label as string}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-sm text-slate-500">Project Tracking System v1.1</p>
          <p className="text-xs text-slate-400">All activity is logged. Authorized access only.</p>
        </div>
      </div>
    </footer>
  );
}