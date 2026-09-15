import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Estimate, EstimateDetail } from '../types';
import { formatMoney } from '../utils/format';
import { useAuth } from '../auth/AuthContext';

interface FormState {
  name: string;
  project: string;
  category: string;
  unit: string;
  currency: string;
  estimate_id: string;
  estimate_line_item_id: string;
  budgeted_quantity: string;
  budgeted_cost: string;
  notes: string;
}

type FormErrors = Partial<Record<keyof FormState, string>>;

const SUPPORTED_CURRENCIES = ['FCFA', 'XAF'];
const DECIMAL_RE = /^\d{1,12}(\.\d{1,2})?$/;
const MONEY_RE = /^\d{1,13}(\.\d{1,2})?$/;

const EMPTY_FORM: FormState = {
  name: '',
  project: '',
  category: '',
  unit: '',
  currency: 'FCFA',
  estimate_id: '',
  estimate_line_item_id: '',
  budgeted_quantity: '',
  budgeted_cost: '',
  notes: '',
};

const parseNum = (value: string): number | null => {
  if (value.trim() === '') return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

const formatApiError = (err: any): string => {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg || 'Invalid value').join('; ');
  }
  if (typeof detail === 'string' && detail.trim()) return detail;
  return err?.message || 'Failed to create resource.';
};

const validate = (form: FormState): FormErrors => {
  const next: FormErrors = {};
  if (!form.name.trim()) next.name = 'Resource name is required.';
  if (form.budgeted_quantity.trim() !== '' && !DECIMAL_RE.test(form.budgeted_quantity.trim())) {
    next.budgeted_quantity = 'Enter a valid positive quantity (up to 2 decimal places).';
  }
  if (form.budgeted_cost.trim() !== '' && !MONEY_RE.test(form.budgeted_cost.trim())) {
    next.budgeted_cost = 'Enter a valid positive amount (up to 2 decimal places).';
  }
  if (form.currency.trim() !== '' && !SUPPORTED_CURRENCIES.includes(form.currency.trim().toUpperCase())) {
    next.currency = `Unsupported currency. Choose one of: ${SUPPORTED_CURRENCIES.join(', ')}.`;
  }
  return next;
};

export default function ResourceForm() {
  const navigate = useNavigate();
  const { canWrite } = useAuth();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [estimateDetail, setEstimateDetail] = useState<EstimateDetail | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);

  useEffect(() => {
    api.listEstimates(0, 200)
      .then((data) => setEstimates(data.estimates))
      .catch(() => setEstimates([]))
      .finally(() => setLoadingOptions(false));
  }, []);

  useEffect(() => {
    if (form.estimate_id) {
      api.getEstimate(form.estimate_id)
        .then(setEstimateDetail)
        .catch(() => setEstimateDetail(null));
    } else {
      setEstimateDetail(null);
    }
  }, [form.estimate_id]);

  const set = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;

    const nextErrors = validate(form);
    setErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length > 0) return;

    setSaving(true);
    try {
      const resource = await api.createResource({
        name: form.name.trim(),
        project: form.project.trim() || null,
        category: form.category.trim() || null,
        unit: form.unit.trim() || null,
        currency: form.currency.trim().toUpperCase(),
        estimate_id: form.estimate_id || null,
        estimate_line_item_id: form.estimate_line_item_id || null,
        budgeted_quantity: parseNum(form.budgeted_quantity),
        budgeted_cost: parseNum(form.budgeted_cost),
        notes: form.notes.trim() || null,
      });
      navigate(`/resources/${resource.id}`);
    } catch (err: any) {
      setSubmitError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const inputClass = (field: keyof FormState) =>
    `w-full rounded-lg border ${errors[field] ? 'border-red-300' : 'border-slate-300'} bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-800/20 focus:border-blue-800`;

  if (!canWrite) {
    return (
      <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Your access is read-only. To add resources, ask a project member or administrator.
        <Link to="/resources" className="font-medium text-amber-900 underline ml-1">
          Back to Resource Register
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <Link to="/resources" className="text-sm text-blue-800 hover:text-blue-600">
          &larr; Back to Resource Register
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Register Resource</h1>
        <p className="mt-1 text-slate-500">
          Create a material/resource master record. Movement quantities are tracked on the resource detail page.
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
        <form onSubmit={handleSubmit} noValidate className="bg-white rounded-lg border border-slate-200 p-6 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-1">
                Resource name *
              </label>
              <input
                id="name"
                type="text"
                autoComplete="off"
                maxLength={500}
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                className={inputClass('name')}
                placeholder="e.g. Cement, Sand, Gravel, Iron rods..."
              />
              {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
            </div>
            <div>
              <label htmlFor="unit" className="block text-sm font-medium text-slate-700 mb-1">
                Unit
              </label>
              <input
                id="unit"
                type="text"
                autoComplete="off"
                maxLength={50}
                value={form.unit}
                onChange={(e) => set('unit', e.target.value)}
                className={inputClass('unit')}
                placeholder="bags, m3, lengths, m2..."
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label htmlFor="category" className="block text-sm font-medium text-slate-700 mb-1">
                Category
              </label>
              <input
                id="category"
                type="text"
                autoComplete="off"
                maxLength={300}
                value={form.category}
                onChange={(e) => set('category', e.target.value)}
                className={inputClass('category')}
                placeholder="MATERIALS, STRUCTURES, FINISHES..."
              />
            </div>
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
                className={inputClass('project')}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <div>
              <label htmlFor="budgeted_quantity" className="block text-sm font-medium text-slate-700 mb-1">
                Budgeted quantity
              </label>
              <input
                id="budgeted_quantity"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                maxLength={14}
                value={form.budgeted_quantity}
                onChange={(e) => set('budgeted_quantity', e.target.value)}
                className={inputClass('budgeted_quantity')}
                placeholder="e.g. 174"
              />
              {errors.budgeted_quantity && <p className="mt-1 text-sm text-red-600">{errors.budgeted_quantity}</p>}
            </div>
            <div>
              <label htmlFor="budgeted_cost" className="block text-sm font-medium text-slate-700 mb-1">
                Budgeted cost
              </label>
              <input
                id="budgeted_cost"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                maxLength={18}
                value={form.budgeted_cost}
                onChange={(e) => set('budgeted_cost', e.target.value)}
                className={inputClass('budgeted_cost')}
                placeholder="e.g. 1305000"
              />
              {errors.budgeted_cost && <p className="mt-1 text-sm text-red-600">{errors.budgeted_cost}</p>}
            </div>
            <div>
              <label htmlFor="currency" className="block text-sm font-medium text-slate-700 mb-1">
                Currency *
              </label>
              <select
                id="currency"
                value={form.currency}
                onChange={(e) => set('currency', e.target.value)}
                className={inputClass('currency')}
              >
                {SUPPORTED_CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              {errors.currency && <p className="mt-1 text-sm text-red-600">{errors.currency}</p>}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
              <label htmlFor="estimate_id" className="block text-sm font-medium text-slate-700 mb-1">
                Link to estimate
              </label>
              <select
                id="estimate_id"
                value={form.estimate_id}
                onChange={(e) => {
                  set('estimate_id', e.target.value);
                  set('estimate_line_item_id', '');
                }}
                className={inputClass('estimate_id')}
              >
                <option value="">— None —</option>
                {estimates
                  .filter((est) => est.status === 'confirmed')
                  .map((est) => (
                    <option key={est.id} value={est.id}>
                      {est.project_name || est.title}
                    </option>
                  ))}
              </select>
            </div>
            {estimateDetail && estimateDetail.line_items.length > 0 && (
              <div>
                <label htmlFor="estimate_line_item_id" className="block text-sm font-medium text-slate-700 mb-1">
                  Estimate line item
                </label>
                <select
                  id="estimate_line_item_id"
                  value={form.estimate_line_item_id}
                  onChange={(e) => set('estimate_line_item_id', e.target.value)}
                  className={inputClass('estimate_line_item_id')}
                >
                  <option value="">— None —</option>
                  {estimateDetail.line_items.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.item_number ? `${item.item_number} · ` : ''}
                      {item.description}
                      {item.total_cost ? ` (${formatMoney(item.total_cost)})` : ''}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-slate-700 mb-1">
              Notes
            </label>
            <textarea
              id="notes"
              rows={3}
              maxLength={2000}
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
              className={inputClass('notes')}
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Link
              to="/resources"
              className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={saving || form.name.trim() === ''}
              className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : 'Create Resource'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}