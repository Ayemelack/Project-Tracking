import type { Activity } from '../types';

export interface ActivityFormState {
  name: string;
  project: string;
  description: string;
  project_stage: string;
  estimate_id: string;
  planned_start_date: string;
  planned_end_date: string;
  actual_start_date: string;
  actual_end_date: string;
  status: string;
  progress_percentage: string;
  responsible_person: string;
  resource_dependency: string;
  notes: string;
}

export type ActivityFormErrors = Partial<Record<keyof ActivityFormState, string>>;

export const EMPTY_ACTIVITY_FORM: ActivityFormState = {
  name: '',
  project: '',
  description: '',
  project_stage: '',
  estimate_id: '',
  planned_start_date: '',
  planned_end_date: '',
  actual_start_date: '',
  actual_end_date: '',
  status: 'not_started',
  progress_percentage: '0',
  responsible_person: '',
  resource_dependency: '',
  notes: '',
};

export const activityFormFromActivity = (activity: Activity): ActivityFormState => ({
  name: activity.name,
  project: activity.project ?? '',
  description: activity.description ?? '',
  project_stage: activity.project_stage ?? '',
  estimate_id: activity.estimate_id ?? '',
  planned_start_date: activity.planned_start_date ?? '',
  planned_end_date: activity.planned_end_date ?? '',
  actual_start_date: activity.actual_start_date ?? '',
  actual_end_date: activity.actual_end_date ?? '',
  status: activity.status,
  progress_percentage: String(activity.progress_percentage ?? 0),
  responsible_person: activity.responsible_person ?? '',
  resource_dependency: activity.resource_dependency ?? '',
  notes: activity.notes ?? '',
});

export const validateActivityForm = (form: ActivityFormState): ActivityFormErrors => {
  const next: ActivityFormErrors = {};
  if (!form.name.trim()) next.name = 'Activity name is required.';

  const progress = Number(form.progress_percentage);
  if (form.progress_percentage.trim() === '' || !Number.isInteger(progress)) {
    next.progress_percentage = 'Progress must be a whole number between 0 and 100.';
  } else if (progress < 0 || progress > 100) {
    next.progress_percentage = 'Progress must be between 0 and 100.';
  }

  if (form.planned_start_date && form.planned_end_date && form.planned_end_date < form.planned_start_date) {
    next.planned_end_date = 'Planned end cannot be before the planned start.';
  }
  if (form.actual_start_date && form.actual_end_date && form.actual_end_date < form.actual_start_date) {
    next.actual_end_date = 'Actual end cannot be before the actual start.';
  }
  return next;
};

export const toActivityPayload = (form: ActivityFormState) => ({
  name: form.name.trim(),
  project: form.project.trim() || null,
  description: form.description.trim() || null,
  project_stage: form.project_stage.trim() || null,
  estimate_id: form.estimate_id || null,
  planned_start_date: form.planned_start_date || null,
  planned_end_date: form.planned_end_date || null,
  actual_start_date: form.actual_start_date || null,
  actual_end_date: form.actual_end_date || null,
  status: form.status,
  progress_percentage: Number(form.progress_percentage),
  responsible_person: form.responsible_person.trim() || null,
  resource_dependency: form.resource_dependency.trim() || null,
  notes: form.notes.trim() || null,
});

export const inputClass = (hasError: boolean) =>
  `w-full rounded-lg border ${hasError ? 'border-red-300' : 'border-slate-300'} bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-800/20 focus:border-blue-800`;