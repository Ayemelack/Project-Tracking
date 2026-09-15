import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

const navItems: { path: string; label: string; roles?: Array<'administrator' | 'member' | 'viewer'> }[] = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/upload', label: 'Upload Estimate', roles: ['administrator', 'member'] },
  { path: '/estimates', label: 'Estimate Register' },
  { path: '/funding', label: 'Funding Register' },
  { path: '/funding/new', label: 'Add Funding', roles: ['administrator', 'member'] },
  { path: '/expenses', label: 'Expense Register' },
  { path: '/expenses/new', label: 'Add Expense', roles: ['administrator', 'member'] },
  { path: '/resources', label: 'Resource Register' },
  { path: '/resources/new', label: 'Add Resource', roles: ['administrator', 'member'] },
  { path: '/schedule', label: 'Project Schedule' },
  { path: '/assistant', label: 'Ask the Assistant' },
  { path: '/users', label: 'Users & Access', roles: ['administrator'] },
];

const isActive = (locationPath: string, itemPath: string): boolean => {
  if (itemPath === '/') return locationPath === '/';
  return locationPath === itemPath || locationPath.startsWith(`${itemPath}/`);
};

const roleLabel = (role: string): string =>
  role === 'administrator' ? 'Administrator' : role === 'member' ? 'Member' : 'Viewer';

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  const onLogout = () => {
    closeMenu();
    logout();
    navigate('/login', { replace: true });
  };

  const visibleItems = navItems.filter((item) =>
    item.roles ? item.roles.includes(user?.role ?? 'viewer') : true
  );

  const navLinkClass = (path: string, block = false) =>
    `${block ? 'flex w-full' : 'flex'} items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
      isActive(location.pathname, path)
        ? 'bg-blue-50 text-blue-800'
        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
    }`;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="lg:hidden sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
        <div className="flex items-center justify-between h-14 px-4">
          <Link to="/dashboard" className="flex items-center gap-3" onClick={closeMenu}>
            <div className="w-8 h-8 bg-blue-800 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">PT</span>
            </div>
            <span className="text-lg font-semibold text-slate-900">Project Tracking</span>
          </Link>
          <div className="flex items-center gap-2">
            {user && (
              <span className="text-xs text-slate-500 hidden xs:inline">{user.full_name}</span>
            )}
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-expanded={menuOpen}
              aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              className="inline-flex items-center justify-center w-10 h-10 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
            >
              {menuOpen ? (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </header>

      <div className="flex min-h-screen">
        {menuOpen && (
          <div
            className="fixed inset-0 z-40 bg-slate-900/50 lg:hidden"
            onClick={closeMenu}
            aria-hidden="true"
          />
        )}

        <aside
          aria-label="Primary navigation"
          className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-white border-r border-slate-200 transform transition-transform duration-200 lg:transform-none lg:w-64 lg:sticky lg:top-0 lg:h-screen lg:z-30 ${
            menuOpen ? 'translate-x-0 shadow-2xl lg:shadow-none' : '-translate-x-full lg:translate-x-0'
          }`}
        >
          <div className="flex items-center gap-3 px-5 h-20 border-b border-slate-200 shrink-0">
            <Link to="/dashboard" className="flex items-center gap-3 min-w-0" onClick={closeMenu}>
              <div className="w-8 h-8 bg-blue-800 rounded-lg flex items-center justify-center shrink-0">
                <span className="text-white font-bold text-sm">PT</span>
              </div>
              <span className="text-lg font-semibold text-slate-900 leading-tight">
                Project Tracking
              </span>
            </Link>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
            {visibleItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={closeMenu}
                className={navLinkClass(item.path, true)}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="px-5 py-4 border-t border-slate-200 shrink-0 space-y-3">
            {user ? (
              <>
                <div className="flex items-center justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-700 truncate">{user.full_name}</p>
                    <p className="text-xs text-slate-400 truncate">@{user.username}</p>
                  </div>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 text-blue-800 text-xs font-medium">
                    {roleLabel(user.role)}
                  </span>
                </div>
                {user.role !== 'viewer' && (
                  <p className="text-xs text-slate-400">
                    {user.role === 'administrator' ? 'Full access · manages users & records' : 'Records & permitted edits'}
                  </p>
                )}
                <button
                  type="button"
                  onClick={onLogout}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-blue-800 px-3 py-2 text-sm font-medium text-white hover:bg-blue-900 transition-colors"
              >
                Sign in
              </Link>
            )}
          </div>
        </aside>

        <div className="flex-1 min-w-0 flex flex-col">
          <main className="flex-1">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <Outlet />
            </div>
          </main>
          <footer className="bg-white border-t border-slate-200 py-4">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-slate-500">
              Project Tracking System v1.1
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}