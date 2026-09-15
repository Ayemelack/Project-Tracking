import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Estimate } from '../types';
import { useAuth } from '../auth/AuthContext';
import { ActivityFields } from '../components/ActivityFields';
import {
  EMPTY_ACTIVITY_FORM,
  validateActivityForm,
  toActivityPayload,
  type ActivityFormState,
  type ActivityFormErrors,
} from '../utils/activityForm';

const formatApiError = (err: any): string => {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg || 'Invalid value').join('; ');
  }
  if (typeof detail === 'string' && detail.trim()) return detail;
  return err?.message || 'Failed to create the activity.';
};

export default function ActivityForm() {
  const navigate = useNavigate();
  const { canWrite } = useAuth();
  const [form, setForm] = useState<ActivityFormState>(EMPTY_ACTIVITY_FORM);
  const [errors, setErrors] = useState<ActivityFormErrors>({});
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

  const set = (field: keyof ActivityFormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;

    const nextErrors = validateActivityForm(form);
    setErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length > 0) return;

    setSaving(true);
    try {
      const activity = await api.createActivity(toActivityPayload(form));
      navigate(`/schedule/${activity.id}`);
    } catch (err: any) {
      setSubmitError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  if (!canWrite) {
    return (
      <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Your access is read-only. To add activities, ask a project member or administrator.
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
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Add Activity</h1>
        <p className="mt-1 text-slate-500">
          Schedule a project activity. Planned dates drive automatic delay detection; progress and
          status updates are recorded here and on the activity page.
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
          className="bg-white rounded-lg border border-slate-200 p-6"
        >
          <ActivityFields
            form={form}
            errors={errors}
            estimates={estimates}
            onChange={set}
          />

          <div className="flex items-center justify-end gap-3 pt-6">
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
              {saving ? 'Saving...' : 'Create Activity'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}