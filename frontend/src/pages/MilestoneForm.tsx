import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Estimate } from '../types';
import { useAuth } from '../auth/AuthContext';
import { MILESTONE_STATUS_OPTIONS } from '../utils/schedule';

interface FormState {
  name: string;
  project: string;
  estimate_id: string;
  planned_date: string;
  actual_date: string;
  status: string;
  notes: string;
}

type FormErrors = Partial<Record<keyof FormState, string>>;

const EMPTY_FORM: FormState = {
  name: '',
  project: '',
  estimate_id: '',
  planned_date: '',
  actual_date: '',
  status: 'pending',
  notes: '',
};

const inputClass = (hasError: boolean) =>
  `w-full rounded-lg border ${hasError ? 'border-red-300' : 'border-slate-300'} bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-800/20 focus:border-blue-800`;

const formatApiError = (err: any): string => {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg || 'Invalid value').join('; ');
  }
  if (typeof detail === 'string' && detail.trim()) return detail;
  return err?.message || 'Failed to create the milestone.';
};

export default function MilestoneForm() {
  const navigate = useNavigate();
  const { canWrite } = useAuth();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(true);

  useEffect(() => {
    api.listEstimates(0, 200)
      .then((data) => setEstimates(data.estimates))
      .catch(() => setEstimates([]))
      .finally(() => setLoadingOptions(false));
  }, []);

  const set = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;

    const next: FormErrors = {};
    if (!form.name.trim()) next.name = 'Milestone name is required.';
    setErrors(next);
    setSubmitError(null);
    if (Object.keys(next).length > 0) return;

    setSaving(true);
    try {
      const milestone = await api.createMilestone({
        name: form.name.trim(),
        project: form.project.trim() || null,
        estimate_id: form.estimate_id || null,
        planned_date: form.planned_date || null,
        actual_date: form.actual_date || null,
        status: form.status,
        notes: form.notes.trim() || null,
      });
      navigate(`/schedule?milestone=${milestone.id}`);
    } catch (err: any) {
      setSubmitError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  if (!canWrite) {
    return (
      <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Your access is read-only. To add milestones, ask a project member or administrator.
        <Link to="/schedule" className="font-medium text-amber-900 underline ml-1">
          Back to Project Schedule
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <Link to="/schedule" className="text-sm text-blue-800 hover:text-blue-600">
          &larr; Back to Project Schedule
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Add Milestone</h1>
        <p className="mt-1 text-slate-500">
          Record an important project milestone such as "Foundation completed" or "Roofing completed".
        </p>
      </div>

      {submitError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 text-sm">{submitError}</p>
        </div>
      )}

      {loadingOptions ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-slate-500">Loading estimate options...</p>
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          noValidate
          className="bg-white rounded-lg border border-slate-200 p-6 space-y-5"
        >
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-1">
              Milestone name *
            </label>
            <input
              id="name"
              type="text"
              autoComplete="off"
              maxLength={500}
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              className={inputClass(Boolean(errors.name))}
              placeholder="e.g. Foundation completed"
            />
            {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label htmlFor="project" className="block text-sm font-medium text-slate-700 mb-1">
                Project
              </label>
              <input
                id="project"
                type="text"
                autoComplete="off"
                maxLength={500}
                value={form.project}
                onChange={(e) => set('project', e.target.value)}
                className={inputClass(Boolean(errors.project))}
              />
            </div>
            <div>
              <label htmlFor="estimate_id" className="block text-sm font-medium text-slate-700 mb-1">
                Link to estimate / project
              </label>
              <select
                id="estimate_id"
                value={form.estimate_id}
                onChange={(e) => set('estimate_id', e.target.value)}
                className={inputClass(Boolean(errors.estimate_id))}
              >
                <option value="">— None —</option>
                {estimates.map((est) => (
                  <option key={est.id} value={est.id}>
                    {est.project_name || est.title}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <div>
              <label htmlFor="planned_date" className="block text-sm font-medium text-slate-700 mb-1">
                Planned date
              </label>
              <input
                id="planned_date"
                type="date"
                value={form.planned_date}
                onChange={(e) => set('planned_date', e.target.value)}
                className={inputClass(Boolean(errors.planned_date))}
              />
            </div>
            <div>
              <label htmlFor="actual_date" className="block text-sm font-medium text-slate-700 mb-1">
                Actual date
              </label>
              <input
                id="actual_date"
                type="date"
                value={form.actual_date}
                onChange={(e) => set('actual_date', e.target.value)}
                className={inputClass(Boolean(errors.actual_date))}
              />
            </div>
            <div>
              <label htmlFor="status" className="block text-sm font-medium text-slate-700 mb-1">
                Status
              </label>
              <select
                id="status"
                value={form.status}
                onChange={(e) => set('status', e.target.value)}
                className={inputClass(Boolean(errors.status))}
              >
                {MILESTONE_STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-slate-700 mb-1">
              Notes
            </label>
            <textarea
              id="notes"
              rows={3}
              maxLength={4000}
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
              className={inputClass(Boolean(errors.notes))}
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Link
              to="/schedule"
              className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={saving || form.name.trim() === ''}
              className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : 'Create Milestone'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}