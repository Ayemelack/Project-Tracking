import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { Activity, ActivitySummary, Milestone } from '../types';
import {
  ACTIVITY_STATUS_LABELS,
  ACTIVITY_STATUS_CLASSES,
  MILESTONE_STATUS_LABELS,
  MILESTONE_STATUS_CLASSES,
  PROGRESS_BAR_CLASS,
  STATUS_BADGE,
  fmtDate,
} from '../utils/schedule';

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-2 min-w-[110px]">
      <div className="flex-1 h-2 rounded-full bg-slate-200 overflow-hidden">
        <div
          className={`h-full rounded-full ${PROGRESS_BAR_CLASS(value)}`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
      <span className="text-xs font-medium text-slate-700 tabular-nums w-9 text-right">{value}%</span>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  tone = 'text-slate-900',
  hint,
}: {
  label: string;
  value: string | number;
  tone?: string;
  hint?: string;
}) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5">
      <div className="text-xs font-medium text-slate-500 uppercase">{label}</div>
      <div className={`mt-2 text-xl font-bold ${tone}`}>{value}</div>
      {hint && <div className="mt-1 text-sm text-slate-500">{hint}</div>}
    </div>
  );
}

const delayCell = (activity: Activity) => {
  if (!activity.is_delayed) {
    return <span className="text-sm text-slate-400">On schedule</span>;
  }
  const reason = activity.delay_reason ? ` · ${activity.delay_reason}` : '';
  return (
    <span>
      <span className={STATUS_BADGE(ACTIVITY_STATUS_CLASSES.delayed)}>Delayed</span>
      <span className="ml-1 text-sm font-semibold text-amber-700">
        {activity.delay_days > 0 ? `${activity.delay_days} day${activity.delay_days === 1 ? '' : 's'}` : 'Overdue'}
        {reason}
      </span>
    </span>
  );
};

export default function SchedulePage() {
  const { canWrite } = useAuth();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [summary, setSummary] = useState<ActivitySummary | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');

  const loadData = async () => {
    setError(null);
    try {
      const params = filter ? { status: filter } : undefined;
      const [activityList, milestoneList] = await Promise.all([
        api.listActivities(params),
        api.listMilestones(),
      ]);
      setActivities(activityList.activities);
      setSummary(activityList.summary);
      setMilestones(milestoneList.milestones);
    } catch (e: any) {
      setError(e.message || 'Failed to load the project schedule.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Project Schedule</h1>
            <p className="mt-1 text-slate-500">
              Activities, milestones, progress and delay tracking
            </p>
          </div>
          <div className="flex items-center gap-3">
            {canWrite && (
              <>
                <Link
                  to="/schedule/milestones/new"
                  className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Add Milestone
                </Link>
                <Link
                  to="/schedule/new"
                  className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
                >
                  Add Activity
                </Link>
              </>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-slate-500">Loading schedule...</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
            <SummaryCard label="Total activities" value={summary?.total_activities ?? 0} />
            <SummaryCard label="In progress" value={summary?.total_in_progress ?? 0} tone="text-blue-700" />
            <SummaryCard label="Delayed" value={summary?.total_delayed ?? 0} tone="text-amber-700" />
            <SummaryCard label="Blocked" value={summary?.total_blocked ?? 0} tone="text-rose-700" />
            <SummaryCard label="Not started" value={summary?.total_not_started ?? 0} />
            <SummaryCard label="Completed" value={summary?.total_completed ?? 0} tone="text-emerald-700" />
          </div>

          <div className="bg-white rounded-lg border border-slate-200 p-5 mb-8">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <div className="text-xs font-medium text-slate-500 uppercase">
                  Overall recorded progress
                </div>
                <div className="mt-2 flex items-center gap-3">
                  <div className="w-48 h-3 rounded-full bg-slate-200 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${PROGRESS_BAR_CLASS(summary?.overall_progress ?? 0)}`}
                      style={{ width: `${Math.max(0, Math.min(100, summary?.overall_progress ?? 0))}%` }}
                    />
                  </div>
                  <span className="text-xl font-bold text-slate-900">
                    {summary?.overall_progress ?? 0}%
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-500 max-w-sm">
                {summary?.progress_calculation}
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-slate-900">Activities</h2>
            <div className="flex items-center gap-2">
              <label htmlFor="status-filter" className="text-sm text-slate-500">
                Filter:
              </label>
              <select
                id="status-filter"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-800/20 focus:border-blue-800"
              >
                <option value="">All statuses</option>
                {Object.entries(ACTIVITY_STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          {activities.length === 0 ? (
            <div className="bg-white rounded-lg border border-slate-200 p-12 text-center mb-8">
              <h3 className="text-lg font-medium text-slate-900">No activities yet</h3>
              <p className="mt-1 text-slate-500">
                Add the first project activity to start tracking progress and delays.
              </p>
              {canWrite && (
                <Link
                  to="/schedule/new"
                  className="mt-4 inline-flex px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
                >
                  Add Activity
                </Link>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden mb-8">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Activity</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Stage</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Planned</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actual</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Progress</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Delay</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Responsible</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {activities.map((activity) => (
                      <tr key={activity.id} className="hover:bg-slate-50">
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-slate-900">{activity.name}</div>
                          {activity.description && (
                            <div className="mt-0.5 text-sm text-slate-500 truncate max-w-xs">{activity.description}</div>
                          )}
                          {activity.estimate_title && (
                            <div className="mt-0.5 text-xs text-slate-400">{activity.estimate_title}</div>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-600">
                          {activity.project_stage || '—'}
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-600">
                          <div>{fmtDate(activity.planned_start_date)}</div>
                          <div className="text-xs text-slate-400">to {fmtDate(activity.planned_end_date)}</div>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-600">
                          <div>{fmtDate(activity.actual_start_date)}</div>
                          <div className="text-xs text-slate-400">to {fmtDate(activity.actual_end_date)}</div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={STATUS_BADGE(ACTIVITY_STATUS_CLASSES[activity.status] ?? ACTIVITY_STATUS_CLASSES.not_started)}>
                            {ACTIVITY_STATUS_LABELS[activity.status] ?? activity.status}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <ProgressBar value={activity.progress_percentage} />
                        </td>
                        <td className="px-6 py-4">{delayCell(activity)}</td>
                        <td className="px-6 py-4 text-sm text-slate-600">
                          {activity.responsible_person || '—'}
                        </td>
                        <td className="px-6 py-4 text-right whitespace-nowrap">
                          <Link
                            to={`/schedule/${activity.id}`}
                            className="text-sm font-medium text-blue-800 hover:text-blue-600"
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-slate-900">Milestones</h2>
            {canWrite && (
              <Link
                to="/schedule/milestones/new"
                className="text-sm font-medium text-blue-800 hover:text-blue-600"
              >
                Add Milestone
              </Link>
            )}
          </div>

          {milestones.length === 0 ? (
            <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
              <h3 className="text-lg font-medium text-slate-900">No milestones recorded</h3>
              <p className="mt-1 text-slate-500">
                Record important milestones such as "Foundation completed" or "Roofing completed".
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Milestone</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Planned date</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actual date</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {milestones.map((milestone) => (
                      <tr key={milestone.id} className="hover:bg-slate-50">
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-slate-900">{milestone.name}</div>
                          {milestone.estimate_title && (
                            <div className="mt-0.5 text-xs text-slate-400">{milestone.estimate_title}</div>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-600">{fmtDate(milestone.planned_date)}</td>
                        <td className="px-6 py-4 text-sm text-slate-600">{fmtDate(milestone.actual_date)}</td>
                        <td className="px-6 py-4">
                          <span className={STATUS_BADGE(MILESTONE_STATUS_CLASSES[milestone.status] ?? MILESTONE_STATUS_CLASSES.pending)}>
                            {MILESTONE_STATUS_LABELS[milestone.status] ?? milestone.status}
                          </span>
                          {milestone.status === 'pending' &&
                            milestone.planned_date &&
                            new Date(milestone.planned_date) < new Date() && (
                              <span className="ml-1 text-xs text-rose-600">overdue</span>
                            )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}