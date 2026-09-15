import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';

interface FormState {
  amount: string;
  currency: string;
  received_date: string;
  source: string;
  reference: string;
  purpose: string;
  notes: string;
}

type FormErrors = Partial<Record<keyof FormState, string>>;

const SUPPORTED_CURRENCIES = ['FCFA', 'XAF'];
const LIMITS = { source: 500, reference: 200, purpose: 1000, notes: 2000 };
const MAX_AMOUNT = 9999999999999.99; // matches backend Numeric(15,2)

const EMPTY_FORM: FormState = {
  amount: '',
  currency: 'FCFA',
  received_date: new Date().toISOString().slice(0, 10),
  source: '',
  reference: '',
  purpose: '',
  notes: '',
};

const formatApiError = (err: any): string => {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg || 'Invalid value').join('; ');
  }
  if (typeof detail === 'string' && detail.trim()) return detail;
  return err?.message || 'Failed to save funding.';
};

const validateField = (field: keyof FormState, value: string): string | null => {
  const trimmed = value.trim();
  switch (field) {
    case 'amount':
      if (trimmed === '') return 'Enter the amount received.';
      if (!/^\d{1,13}(\.\d{1,2})?$/.test(trimmed)) {
        return 'Enter a valid amount (positive, up to 2 decimal places).';
      }
      {
        const amount = Number(trimmed);
        if (!Number.isFinite(amount) || amount <= 0) return 'Amount must be greater than zero.';
        if (amount > MAX_AMOUNT) return `Amount exceeds the maximum supported value (${MAX_AMOUNT.toLocaleString('en-US')}).`;
      }
      return null;
    case 'currency':
      if (!SUPPORTED_CURRENCIES.includes(trimmed.toUpperCase())) {
        return `Unsupported currency. Choose one of: ${SUPPORTED_CURRENCIES.join(', ')}.`;
      }
      return null;
    case 'received_date':
      if (trimmed === '') return 'Enter the date the funds were received.';
      if (!/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return 'Enter a valid date (YYYY-MM-DD).';
      {
        const [y, m, d] = trimmed.split('-').map(Number);
        const parsed = new Date(Date.UTC(y, m - 1, d));
        if (
          parsed.getUTCFullYear() !== y ||
          parsed.getUTCMonth() !== m - 1 ||
          parsed.getUTCDate() !== d
        ) {
          return 'Enter a valid calendar date.';
        }
      }
      return null;
    case 'source':
      if (trimmed === '') return 'Enter the funding source (authority, bank, etc.).';
      if (trimmed.length > LIMITS.source) return `Source must be ${LIMITS.source} characters or fewer.`;
      return null;
    case 'reference':
      if (trimmed.length > LIMITS.reference) return `Reference must be ${LIMITS.reference} characters or fewer.`;
      return null;
    case 'purpose':
      if (trimmed === '') return 'Enter the intended use of these funds.';
      if (trimmed.length > LIMITS.purpose) return `Purpose must be ${LIMITS.purpose} characters or fewer.`;
      return null;
    case 'notes':
      if (value.length > LIMITS.notes) return `Notes must be ${LIMITS.notes} characters or fewer.`;
      return null;
  }
  return null;
};

const validateAll = (form: FormState): FormErrors => {
  const next: FormErrors = {};
  (Object.keys(form) as (keyof FormState)[]).forEach((field) => {
    const error = validateField(field, form[field]);
    if (error) next[field] = error;
  });
  return next;
};

export default function FundReceiptForm() {
  const navigate = useNavigate();
  const { canWrite } = useAuth();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [touched, setTouched] = useState<Partial<Record<keyof FormState, boolean>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const allErrors = validateAll(form);
  const isFormValid = Object.keys(allErrors).length === 0;

  const set = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const setTouchedField = (field: keyof FormState) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;

    const allTouched = Object.keys(form).reduce<Partial<Record<keyof FormState, boolean>>>(
      (acc, key) => {
        acc[key as keyof FormState] = true;
        return acc;
      },
      {}
    );
    setTouched(allTouched);

    const errors = validateAll(form);
    setSubmitError(null);
    if (Object.keys(errors).length > 0) return;

    setSaving(true);
    try {
      const receipt = await api.createFundReceipt({
        amount: form.amount.trim(),
        currency: form.currency.trim().toUpperCase() || 'FCFA',
        received_date: form.received_date.trim(),
        source: form.source.trim(),
        reference: form.reference.trim() || null,
        purpose: form.purpose.trim(),
        notes: form.notes.trim() || null,
      });
      navigate(`/funding/${receipt.id}`);
    } catch (err: any) {
      setSubmitError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const inputClass = (field: keyof FormState) =>
    `w-full rounded-lg border ${touched[field] && allErrors[field] ? 'border-red-300' : 'border-slate-300'} bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-800/20 focus:border-blue-800`;

  const showError = (field: keyof FormState) =>
    touched[field] && allErrors[field] ? (
      <p className="mt-1 text-sm text-red-600">{allErrors[field]}</p>
    ) : null;

  if (!canWrite) {
    return (
      <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Your access is read-only. To add funding records, ask a project member or administrator.
        <Link to="/funding" className="font-medium text-amber-900 underline ml-1">
          Back to Funding Register
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <Link to="/funding" className="text-sm text-blue-800 hover:text-blue-600">
          &larr; Back to Funding Register
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Record Funding Received</h1>
        <p className="mt-1 text-slate-500">
          Log money provided to the project. You can attach a supporting document after saving.
        </p>
      </div>

      {submitError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 text-sm">{submitError}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="bg-white rounded-lg border border-slate-200 p-6 space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label htmlFor="amount" className="block text-sm font-medium text-slate-700 mb-1">
              Amount received *
            </label>
            <input
              id="amount"
              type="text"
              inputMode="decimal"
              autoComplete="off"
              maxLength={18}
              value={form.amount}
              onChange={(e) => set('amount', e.target.value)}
              onBlur={() => setTouchedField('amount')}
              className={inputClass('amount')}
              placeholder="e.g. 5000000"
            />
            {showError('amount')}
          </div>
          <div>
            <label htmlFor="currency" className="block text-sm font-medium text-slate-700 mb-1">
              Currency *
            </label>
            <select
              id="currency"
              value={form.currency}
              onChange={(e) => set('currency', e.target.value)}
              onBlur={() => setTouchedField('currency')}
              className={inputClass('currency')}
            >
              {SUPPORTED_CURRENCIES.map((currency) => (
                <option key={currency} value={currency}>
                  {currency}
                </option>
              ))}
            </select>
            {showError('currency')}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label htmlFor="received_date" className="block text-sm font-medium text-slate-700 mb-1">
              Date received *
            </label>
            <input
              id="received_date"
              type="date"
              value={form.received_date}
              onChange={(e) => set('received_date', e.target.value)}
              onBlur={() => setTouchedField('received_date')}
              className={inputClass('received_date')}
            />
            {showError('received_date')}
          </div>
          <div>
            <label htmlFor="reference" className="block text-sm font-medium text-slate-700 mb-1">
              Reference
            </label>
            <input
              id="reference"
              type="text"
              autoComplete="off"
              maxLength={LIMITS.reference}
              value={form.reference}
              onChange={(e) => set('reference', e.target.value)}
              onBlur={() => setTouchedField('reference')}
              className={inputClass('reference')}
              placeholder="Transfer order / receipt number"
            />
            {showError('reference')}
          </div>
        </div>

        <div>
          <label htmlFor="source" className="block text-sm font-medium text-slate-700 mb-1">
            Source of funds *
          </label>
          <input
            id="source"
            type="text"
            autoComplete="off"
            maxLength={LIMITS.source}
            value={form.source}
            onChange={(e) => set('source', e.target.value)}
            onBlur={() => setTouchedField('source')}
            className={inputClass('source')}
            placeholder="Ministry of Public Works, bank transfer, grant, etc."
          />
          {showError('source')}
        </div>

        <div>
          <label htmlFor="purpose" className="block text-sm font-medium text-slate-700 mb-1">
            Purpose *
          </label>
          <input
            id="purpose"
            type="text"
            autoComplete="off"
            maxLength={LIMITS.purpose}
            value={form.purpose}
            onChange={(e) => set('purpose', e.target.value)}
            onBlur={() => setTouchedField('purpose')}
            className={inputClass('purpose')}
            placeholder="Overall use of these funds"
          />
          {showError('purpose')}
        </div>

        <div>
          <label htmlFor="notes" className="block text-sm font-medium text-slate-700 mb-1">
            Notes
          </label>
          <textarea
            id="notes"
            rows={3}
            maxLength={LIMITS.notes}
            value={form.notes}
            onChange={(e) => set('notes', e.target.value)}
            onBlur={() => setTouchedField('notes')}
            className={inputClass('notes')}
            placeholder="Any additional details"
          />
          {showError('notes')}
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Link
            to="/funding"
            className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={!isFormValid || saving}
            className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Funding'}
          </button>
        </div>
      </form>
    </div>
  );
}