import type { Estimate } from '../types';
import { ACTIVITY_STATUS_OPTIONS, DELAY_REASON_OPTIONS } from '../utils/schedule';
import {
  inputClass,
  type ActivityFormErrors,
  type ActivityFormState,
} from '../utils/activityForm';

export function ActivityFields({
  form,
  errors,
  estimates,
  onChange,
}: {
  form: ActivityFormState;
  errors: ActivityFormErrors;
  estimates: Estimate[];
  onChange: (field: keyof ActivityFormState, value: string) => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-1">
          Activity name *
        </label>
        <input
          id="name"
          type="text"
          autoComplete="off"
          maxLength={500}
          value={form.name}
          onChange={(e) => onChange('name', e.target.value)}
          className={inputClass(Boolean(errors.name))}
          placeholder="e.g. Concrete pour for foundation slab"
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
            onChange={(e) => onChange('project', e.target.value)}
            className={inputClass(Boolean(errors.project))}
            placeholder="e.g. MOLA FAKO & SONS"
          />
        </div>
        <div>
          <label htmlFor="project_stage" className="block text-sm font-medium text-slate-700 mb-1">
            Project stage
          </label>
          <input
            id="project_stage"
            type="text"
            autoComplete="off"
            maxLength={300}
            value={form.project_stage}
            onChange={(e) => onChange('project_stage', e.target.value)}
            className={inputClass(Boolean(errors.project_stage))}
            placeholder="e.g. Foundation, Superstructure, Finishes"
          />
        </div>
      </div>

      <div>
        <label htmlFor="estimate_id" className="block text-sm font-medium text-slate-700 mb-1">
          Link to estimate / project
        </label>
        <select
          id="estimate_id"
          value={form.estimate_id}
          onChange={(e) => onChange('estimate_id', e.target.value)}
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

      <div>
        <label htmlFor="description" className="block text-sm font-medium text-slate-700 mb-1">
          Description
        </label>
        <textarea
          id="description"
          rows={2}
          maxLength={4000}
          value={form.description}
          onChange={(e) => onChange('description', e.target.value)}
          className={inputClass(Boolean(errors.description))}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div>
          <label htmlFor="planned_start_date" className="block text-sm font-medium text-slate-700 mb-1">
            Planned start
          </label>
          <input
            id="planned_start_date"
            type="date"
            value={form.planned_start_date}
            onChange={(e) => onChange('planned_start_date', e.target.value)}
            className={inputClass(Boolean(errors.planned_start_date))}
          />
        </div>
        <div>
          <label htmlFor="planned_end_date" className="block text-sm font-medium text-slate-700 mb-1">
            Planned end
          </label>
          <input
            id="planned_end_date"
            type="date"
            value={form.planned_end_date}
            onChange={(e) => onChange('planned_end_date', e.target.value)}
            className={inputClass(Boolean(errors.planned_end_date))}
          />
          {errors.planned_end_date && <p className="mt-1 text-sm text-red-600">{errors.planned_end_date}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div>
          <label htmlFor="actual_start_date" className="block text-sm font-medium text-slate-700 mb-1">
            Actual start
          </label>
          <input
            id="actual_start_date"
            type="date"
            value={form.actual_start_date}
            onChange={(e) => onChange('actual_start_date', e.target.value)}
            className={inputClass(Boolean(errors.actual_start_date))}
          />
        </div>
        <div>
          <label htmlFor="actual_end_date" className="block text-sm font-medium text-slate-700 mb-1">
            Actual end
          </label>
          <input
            id="actual_end_date"
            type="date"
            value={form.actual_end_date}
            onChange={(e) => onChange('actual_end_date', e.target.value)}
            className={inputClass(Boolean(errors.actual_end_date))}
          />
          {errors.actual_end_date && <p className="mt-1 text-sm text-red-600">{errors.actual_end_date}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div>
          <label htmlFor="status" className="block text-sm font-medium text-slate-700 mb-1">
            Status
          </label>
          <select
            id="status"
            value={form.status}
            onChange={(e) => onChange('status', e.target.value)}
            className={inputClass(Boolean(errors.status))}
          >
            {ACTIVITY_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="progress_percentage" className="block text-sm font-medium text-slate-700 mb-1">
            Progress (%)
          </label>
          <input
            id="progress_percentage"
            type="number"
            inputMode="numeric"
            min={0}
            max={100}
            value={form.progress_percentage}
            onChange={(e) => onChange('progress_percentage', e.target.value)}
            className={inputClass(Boolean(errors.progress_percentage))}
          />
          {errors.progress_percentage && (
            <p className="mt-1 text-sm text-red-600">{errors.progress_percentage}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <div>
          <label htmlFor="responsible_person" className="block text-sm font-medium text-slate-700 mb-1">
            Responsible person
          </label>
          <input
            id="responsible_person"
            type="text"
            autoComplete="off"
            maxLength={500}
            value={form.responsible_person}
            onChange={(e) => onChange('responsible_person', e.target.value)}
            className={inputClass(Boolean(errors.responsible_person))}
            placeholder="e.g. Site Manager"
          />
        </div>
        <div>
          <label htmlFor="resource_dependency" className="block text-sm font-medium text-slate-700 mb-1">
            Resource dependency
          </label>
          <input
            id="resource_dependency"
            type="text"
            autoComplete="off"
            maxLength={500}
            value={form.resource_dependency}
            onChange={(e) => onChange('resource_dependency', e.target.value)}
            className={inputClass(Boolean(errors.resource_dependency))}
            placeholder="e.g. Cement, Sand, Iron rods"
          />
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
          onChange={(e) => onChange('notes', e.target.value)}
          className={inputClass(Boolean(errors.notes))}
        />
      </div>
    </div>
  );
}

export function DelayFields({
  delayReason,
  delayReasonDetail,
  onReasonChange,
  onDetailChange,
}: {
  delayReason: string;
  delayReasonDetail: string;
  onReasonChange: (value: string) => void;
  onDetailChange: (value: string) => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <label htmlFor="delay_reason" className="block text-sm font-medium text-slate-700 mb-1">
          Delay reason
        </label>
        <select
          id="delay_reason"
          value={DELAY_REASON_OPTIONS.includes(delayReason) ? delayReason : ''}
          onChange={(e) => onReasonChange(e.target.value)}
          className={inputClass(false)}
        >
          <option value="">— Unknown / not selected —</option>
          {DELAY_REASON_OPTIONS.map((reason) => (
            <option key={reason} value={reason}>{reason}</option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="delay_reason_detail" className="block text-sm font-medium text-slate-700 mb-1">
          Delay details
        </label>
        <textarea
          id="delay_reason_detail"
          rows={3}
          maxLength={4000}
          value={delayReasonDetail}
          onChange={(e) => onDetailChange(e.target.value)}
          className={inputClass(false)}
          placeholder="e.g. Cement unavailable on site since 05 Sept"
        />
      </div>
    </div>
  );
}