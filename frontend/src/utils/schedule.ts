export const ACTIVITY_STATUS_LABELS: Record<string, string> = {
  not_started: 'Not Started',
  in_progress: 'In Progress',
  completed: 'Completed',
  delayed: 'Delayed',
  blocked: 'Blocked',
  cancelled: 'Cancelled',
};

export const ACTIVITY_STATUS_CLASSES: Record<string, string> = {
  not_started: 'bg-slate-100 text-slate-700 ring-slate-200',
  in_progress: 'bg-blue-50 text-blue-800 ring-blue-200',
  completed: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  delayed: 'bg-amber-50 text-amber-800 ring-amber-200',
  blocked: 'bg-rose-50 text-rose-800 ring-rose-200',
  cancelled: 'bg-slate-100 text-slate-500 ring-slate-200',
};

export const ACTIVITY_STATUS_OPTIONS = [
  { value: 'not_started', label: 'Not Started' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'delayed', label: 'Delayed' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'cancelled', label: 'Cancelled' },
];

export const MILESTONE_STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  completed: 'Completed',
  missed: 'Missed',
};

export const MILESTONE_STATUS_CLASSES: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-700 ring-slate-200',
  completed: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  missed: 'bg-rose-50 text-rose-800 ring-rose-200',
};

export const MILESTONE_STATUS_OPTIONS = [
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
  { value: 'missed', label: 'Missed' },
];

export const DELAY_REASON_OPTIONS = [
  'Material shortage',
  'Funding delay',
  'Labour shortage',
  'Weather',
  'Supplier delay',
  'Design change',
  'Site issue',
  'Other',
];

export const PROGRESS_BAR_CLASS = (progress: number): string => {
  if (progress >= 100) return 'bg-emerald-500';
  if (progress >= 1) return 'bg-blue-500';
  return 'bg-slate-200';
};

export const STATUS_BADGE = (classes: string): string =>
  `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ring-1 ring-inset ${classes}`;

export const fmtDate = (value: string | null | undefined): string => {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};