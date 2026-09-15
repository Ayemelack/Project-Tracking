import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { Activity, Estimate } from '../types';
import { ActivityFields, DelayFields } from '../components/ActivityFields';
import {
  activityFormFromActivity,
  validateActivityForm,
  toActivityPayload,
  type ActivityFormState,
  type ActivityFormErrors,
} from '../utils/activityForm';
import {
  ACTIVITY_STATUS_LABELS,
  ACTIVITY_STATUS_CLASSES,
  PROGRESS_BAR_CLASS,
  STATUS_BADGE,
  fmtDate,
} from '../utils/schedule';

const formatApiError = (err: any): string => {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg || 'Invalid value').join('; ');
  }
  if (typeof detail === 'string' && detail.trim()) return detail;
  return err?.message || 'Request failed.';
};

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="px-4 py-3 sm:grid sm:grid-cols-4 sm:gap-4">
      <dt className="text-sm font-medium text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm text-slate-900 sm:mt-0 sm:col-span-3">{value}</dd>
    </div>
  );
}

export default function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { canWrite } = useAuth();
  const [activity, setActivity] = useState<Activity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [form, setForm] = useState<ActivityFormState | null>(null);
  const [errors, setErrors] = useState<ActivityFormErrors>({});
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const [delayReason, setDelayReason] = useState('');
  const [delayReasonDetail, setDelayReasonDetail] = useState('');
  const [savingDelay, setSavingDelay] = useState(false);

  const load = async () => {
    if (!id) return;
    setError(null);
    try {
      const data = await api.getActivity(id);
      setActivity(data);
      setForm(activityFormFromActivity(data));
      setDelayReason(data.delay_reason ?? '');
      setDelayReasonDetail(data.delay_reason_detail ?? '');
    } catch (e: any) {
      setError(e.message || 'Failed to load the activity.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    api.listEstimates(0, 200)
      .then((data) => setEstimates(data.estimates))
      .catch(() => setEstimates([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const set = (field: keyof ActivityFormState, value: string) => {
    if (!form) return;
    setForm((prev) => (prev ? { ...prev, [field]: value } : prev));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form || !id || saving) return;

    const nextErrors = validateActivityForm(form);
    setErrors(nextErrors);
    setSaveMessage(null);
    if (Object.keys(nextErrors).length > 0) return;

    setSaving(true);
    try {
      const updated = await api.updateActivity(id, toActivityPayload(form));
      setActivity(updated);
      setForm(activityFormFromActivity(updated));
      setSaveMessage('Activity updated.');
    } catch (err: any) {
      setSaveMessage(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const handleSaveDelay = async () => {
    if (!id || savingDelay) return;
    setSavingDelay(true);
    setSaveMessage(null);
    try {
      const updated = await api.updateActivity(id, {
        delay_reason: delayReason.trim() || null,
        delay_reason_detail: delayReasonDetail.trim() || null,
      });
      setActivity(updated);
      setDelayReason(updated.delay_reason ?? '');
      setDelayReasonDetail(updated.delay_reason_detail ?? '');
      setSaveMessage('Delay information saved.');
    } catch (err: any) {
      setSaveMessage(formatApiError(err));
    } finally {
      setSavingDelay(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="mt-4 text-slate-500">Loading activity...</p>
      </div>
    );
  }

  if (!activity || error) {
    return (
      <div>
        <Link to="/schedule" className="text-sm text-blue-800 hover:text-blue-600">
          &larr; Back to Project Schedule
        </Link>
        <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{error || 'Activity not found.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <Link to="/schedule" className="text-sm text-blue-800 hover:text-blue-600">
          &larr; Back to Project Schedule
        </Link>
        <div className="mt-2 flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{activity.name}</h1>
            <div className="mt-2 flex items-center gap-3 flex-wrap">
              <span className={STATUS_BADGE(ACTIVITY_STATUS_CLASSES[activity.status] ?? ACTIVITY_STATUS_CLASSES.not_started)}>
                {ACTIVITY_STATUS_LABELS[activity.status] ?? activity.status}
              </span>
              {activity.is_delayed && (
                <span className="text-sm font-semibold text-amber-700">
                  Delayed
                  {activity.delay_days > 0 ? ` · ${activity.delay_days} day${activity.delay_days === 1 ? '' : 's'}` : ''}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {saveMessage && (
        <div
          className={`rounded-lg border p-4 mb-6 text-sm ${
            saving ? 'bg-blue-50 border-blue-200 text-blue-800'
            : saveMessage.startsWith('Failed') || saveMessage.includes('422') || /error|invalid|required|failed/i.test(saveMessage)
              ? 'bg-red-50 border-red-200 text-red-800'
              : 'bg-emerald-50 border-emerald-200 text-emerald-800'
          }`}
        >
          {saveMessage}
        </div>
      )}

      <div className="bg-white rounded-lg border border-slate-200 mb-8">
        <div className="px-6 py-5 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Details</h2>
        </div>
        <dl className="divide-y divide-slate-100">
          <Row label="Project" value={activity.project || '—'} />
          <Row label="Stage" value={activity.project_stage || '—'} />
          <Row label="Estimate" value={activity.estimate_title || '—'} />
          <Row
            label="Planned"
            value={
              <span>
                {fmtDate(activity.planned_start_date)} to {fmtDate(activity.planned_end_date)}
              </span>
            }
          />
          <Row
            label="Actual"
            value={
              <span>
                {fmtDate(activity.actual_start_date)} to {fmtDate(activity.actual_end_date)}
              </span>
            }
          />
          <Row label="Progress" value={<span className="font-semibold">{activity.progress_percentage}%</span>} />
          <Row label="Responsible" value={activity.responsible_person || '—'} />
          <Row label="Resource dependency" value={activity.resource_dependency || '—'} />
          <Row label="Description" value={activity.description || '—'} />
          <Row label="Notes" value={activity.notes || '—'} />
          <Row label="Delay reason" value={activity.delay_reason || '—'} />
          <Row label="Delay details" value={activity.delay_reason_detail || '—'} />
        </dl>
      </div>

      <div className="mb-8">
        <div className="text-xs font-medium text-slate-500 uppercase mb-2">Overall progress</div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="flex items-center gap-3">
            <div className="flex-1 h-3 rounded-full bg-slate-200 overflow-hidden">
              <div
                className={`h-full rounded-full ${PROGRESS_BAR_CLASS(activity.progress_percentage)}`}
                style={{ width: `${Math.max(0, Math.min(100, activity.progress_percentage))}%` }}
              />
            </div>
            <span className="text-lg font-bold text-slate-900">{activity.progress_percentage}%</span>
          </div>
        </div>
      </div>

      {form && canWrite && (
        <form
          onSubmit={handleSave}
          noValidate
          className="bg-white rounded-lg border border-slate-200 p-6 mb-8"
        >
          <h2 className="text-lg font-semibold text-slate-900 mb-5">Update activity</h2>
          <ActivityFields form={form} errors={errors} estimates={estimates} onChange={set} />
          <div className="flex items-center justify-end gap-3 pt-6">
            <button
              type="submit"
              disabled={saving || form.name.trim() === ''}
              className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      )}

      {canWrite && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-1">Delay tracking</h2>
        <p className="text-sm text-slate-500 mb-5">
          The delay is derived from the schedule (planned end compared with today, or the actual end
          for completed work). Record the reason here; it is never required when the reason is unknown.
        </p>
        <DelayFields
          delayReason={delayReason}
          delayReasonDetail={delayReasonDetail}
          onReasonChange={setDelayReason}
          onDetailChange={setDelayReasonDetail}
        />
        <div className="flex items-center justify-end gap-3 pt-6">
          <button
            type="button"
            onClick={handleSaveDelay}
            disabled={savingDelay}
            className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {savingDelay ? 'Saving...' : 'Save Delay Information'}
          </button>
        </div>
      </div>
      )}
    </div>
  );
}