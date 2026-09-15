import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api } from '../services/api';
import type { AuthUser, Project, UserRole } from '../types';
import { useAuth } from '../auth/AuthContext';

const ROLE_OPTIONS: Array<{ value: UserRole; label: string }> = [
  { value: 'administrator', label: 'Administrator' },
  { value: 'member', label: 'Member' },
  { value: 'viewer', label: 'Viewer' },
];

const roleLabel = (role: string): string =>
  role === 'administrator' ? 'Administrator' : role === 'member' ? 'Member' : 'Viewer';

export default function UsersPage() {
  const { user: currentUser, isAdmin } = useAuth();

  const [users, setUsers] = useState<AuthUser[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [membersOf, setMembersOf] = useState<Record<string, string[]>>({});
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [newUsername, setNewUsername] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<UserRole>('member');
  const [creating, setCreating] = useState(false);

  const refreshData = useCallback(async () => {
    try {
      const [u, p] = await Promise.all([api.listUsers(), api.listProjects()]);
      setUsers(u.users);
      setProjects(p.projects);
      if (p.projects.length > 0) {
        setSelectedProjectId((prev) => prev || p.projects[0].id);
      }
    } catch {
      setError('Could not load users and projects.');
    }
  }, []);

  const refreshMembers = useCallback(
    async (projectId: string) => {
      if (!projectId) return;
      try {
        const res = await api.listProjectMembers(projectId);
        setMembersOf((prev) => ({ ...prev, [projectId]: res.users.map((u) => u.id) }));
      } catch {
        setMembersOf((prev) => ({ ...prev, [projectId]: [] }));
      }
    },
    []
  );

  useEffect(() => {
    if (!isAdmin) return;
    refreshData();
  }, [isAdmin, refreshData]);

  useEffect(() => {
    if (selectedProjectId) refreshMembers(selectedProjectId);
  }, [selectedProjectId, refreshMembers]);

  if (!isAdmin) {
    return (
      <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Only project administrators can manage users and access.
      </div>
    );
  }

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    setNotice(null);
    try {
      const created = await api.createUser({
        username: newUsername,
        full_name: newFullName,
        password: newPassword,
        role: newRole,
      });
      setNotice(`User ${created.username} created.`);
      setNewUsername('');
      setNewFullName('');
      setNewPassword('');
      setNewRole('member');
      await refreshData();
    } catch (err) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Could not create user.');
    } finally {
      setCreating(false);
    }
  };

  const handleRoleChange = async (userId: string, role: UserRole) => {
    if (userId === currentUser?.id) {
      setError('You cannot change your own role.');
      return;
    }
    setError(null);
    try {
      await api.updateUser(userId, { role });
      await refreshData();
    } catch {
      setError('Could not update role.');
    }
  };

  const handleStatusChange = async (user: AuthUser) => {
    if (user.id === currentUser?.id) {
      setError('You cannot deactivate your own account.');
      return;
    }
    setError(null);
    try {
      await api.updateUser(user.id, { status: user.status === 'active' ? 'inactive' : 'active' });
      await refreshData();
    } catch {
      setError('Could not update account status.');
    }
  };

  const handleToggleMember = async (userIdValue: string, projectId: string, isMember: boolean) => {
    setError(null);
    try {
      if (isMember) {
        await api.removeProjectMember(projectId, userIdValue);
      } else {
        await api.addProjectMember(projectId, userIdValue);
      }
      await refreshMembers(projectId);
    } catch {
      setError('Could not update project membership.');
    }
  };

  const selectedMembers = membersOf[selectedProjectId] ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Users &amp; Access</h1>
        <p className="mt-1 text-sm text-slate-500">
          One authenticated session controls estimates, funding, expenses, resources and schedule.
        </p>
      </div>

      {notice && (
        <div className="rounded-md bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-800">{notice}</div>
      )}
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Users table */}
        <div className="xl:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <h2 className="font-semibold text-slate-800">Accounts</h2>
            <span className="text-xs text-slate-400">{users.length} user{users.length === 1 ? '' : 's'}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-400 border-b border-slate-100">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 font-medium">Role</th>
                  <th className="px-4 py-2.5 font-medium">Status</th>
                  <th className="px-4 py-2.5 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800">{u.full_name}</p>
                      <p className="text-xs text-slate-400">@{u.username}</p>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={u.role}
                        disabled={u.id === currentUser?.id}
                        onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                        className="rounded-md border border-slate-300 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:bg-slate-50 disabled:text-slate-400"
                        aria-label={`Role for ${u.username}`}
                      >
                        {ROLE_OPTIONS.map((r) => (
                          <option key={r.value} value={r.value}>{r.label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      {u.status === 'active' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-green-50 text-green-700 text-xs font-medium">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-red-50 text-red-700 text-xs font-medium">
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        disabled={u.id === currentUser?.id}
                        onClick={() => handleStatusChange(u)}
                        className="text-xs font-medium text-blue-700 hover:underline disabled:opacity-40"
                      >
                        {u.status === 'active' ? 'Deactivate' : 'Reactivate'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Create user */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">Add user</h2>
          </div>
          <form onSubmit={handleCreate} className="px-4 py-4 space-y-3">
            <div>
              <label htmlFor="new-username" className="block text-xs font-medium text-slate-600 mb-1">Username</label>
              <input
                id="new-username"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                required
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
            <div>
              <label htmlFor="new-fullname" className="block text-xs font-medium text-slate-600 mb-1">Full name</label>
              <input
                id="new-fullname"
                value={newFullName}
                onChange={(e) => setNewFullName(e.target.value)}
                required
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>
            <div>
              <label htmlFor="new-password" className="block text-xs font-medium text-slate-600 mb-1">Password</label>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
              <p className="mt-1 text-xs text-slate-400">Use at least 8 characters.</p>
            </div>
            <div>
              <label htmlFor="new-role" className="block text-xs font-medium text-slate-600 mb-1">Role</label>
              <select
                id="new-role"
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as UserRole)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={creating}
              className="w-full rounded-md bg-blue-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-900 disabled:opacity-60"
            >
              {creating ? 'Creating…' : 'Create user'}
            </button>
          </form>
        </div>
      </div>

      {/* Project membership */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-semibold text-slate-800">Project membership</h2>
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div className="px-4 py-3 divide-y divide-slate-100">
          {users.map((u) => {
            const isMember = selectedMembers.includes(u.id);
            return (
              <div key={u.id} className="py-2.5 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{u.full_name}</p>
                  <p className="text-xs text-slate-400">@{u.username} · {roleLabel(u.role)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleToggleMember(u.id, selectedProjectId, isMember)}
                  className={`shrink-0 inline-flex items-center px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                    isMember
                      ? 'border-slate-300 text-slate-600 hover:border-red-300 hover:text-red-700'
                      : 'border-blue-700 text-blue-700 hover:bg-blue-50'
                  }`}
                >
                  {isMember ? 'Member — remove' : 'Add to project'}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}