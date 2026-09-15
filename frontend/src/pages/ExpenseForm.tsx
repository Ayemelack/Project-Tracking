import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Estimate, EstimateDetail, ExpenseAllocationItem } from '../types';
import { formatMoney } from '../utils/format';
import { useAuth } from '../auth/AuthContext';

interface FormState {
  amount: string;
  expense_date: string;
  description: string;
  category: string;
  currency: string;
  estimate_id: string;
  estimate_line_item_id: string;
  allocation_id: string;
  supplier: string;
  payment_method: string;
  reference: string;
  purpose: string;
  responsible_person: string;
  notes: string;
  quantity: string;
  unit: string;
  unit_price: string;
  authorized_by: string;
  authorization_reason: string;
}

type FormErrors = Partial<Record<keyof FormState, string>>;

const SUPPORTED_CURRENCIES = ['FCFA', 'XAF'];
const SUPPORTED_PAYMENT_METHODS = ['CASH', 'BANK_TRANSFER', 'CHEQUE', 'MOBILE_MONEY', 'CARD', 'OTHER'];
const LIMITS = { category: 300, supplier: 500, reference: 200, purpose: 1000, responsible_person: 500, notes: 2000, unit: 50, description: 2000, authorization_reason: 1000 };
const MAX_AMOUNT = 9999999999999.99;
const MAX_QUANTITY = 9999999999.99;
const AMOUNT_RE = /^\d{1,13}(\.\d{1,2})?$/;
const DECIMAL_RE = /^\d{1,12}(\.\d{1,2})?$/;

const EMPTY_FORM: FormState = {
  amount: '',
  expense_date: new Date().toISOString().slice(0, 10),
  description: '',
  category: '',
  currency: 'FCFA',
  estimate_id: '',
  estimate_line_item_id: '',
  allocation_id: '',
  supplier: '',
  payment_method: '',
  reference: '',
  purpose: '',
  responsible_person: '',
  notes: '',
  quantity: '',
  unit: '',
  unit_price: '',
  authorized_by: '',
  authorization_reason: '',
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
  return err?.message || 'Failed to save expense.';
};

const validateField = (
  field: keyof FormState,
  value: string,
  form: FormState
): string | null => {
  const trimmed = value.trim();
  const qty = parseNum(form.quantity);
  const price = parseNum(form.unit_price);
  const hasBothPurchase = form.quantity.trim() !== '' && form.unit_price.trim() !== '';
  const purchaseTotal = hasBothPurchase && qty !== null && price !== null ? qty * price : null;

  switch (field) {
    case 'amount': {
      const partialPurchase = (form.quantity.trim() === '') !== (form.unit_price.trim() === '');
      if (partialPurchase) return 'Quantity and unit price must both be provided together.';
      if (trimmed === '' && hasBothPurchase) return null;
      if (trimmed === '') return 'Enter the expense amount (or quantity and unit price).';
      if (!AMOUNT_RE.test(trimmed)) return 'Enter a valid amount (positive, up to 2 decimal places).';
      if (parseNum(trimmed) === null || parseNum(trimmed)! <= 0) return 'Amount must be greater than zero.';
      if (parseNum(trimmed)! > MAX_AMOUNT) return `Amount exceeds the maximum supported value (${MAX_AMOUNT.toLocaleString('en-US')}).`;
      if (hasBothPurchase && purchaseTotal !== null && parseNum(trimmed) !== Math.round(purchaseTotal * 100) / 100) {
        return `Amount must match quantity × unit price (${formatMoney(Math.round(purchaseTotal * 100) / 100)}).`;
      }
      return null;
    }
    case 'expense_date':
      if (trimmed === '') return 'Enter the expense date.';
      if (!/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return 'Enter a valid date (YYYY-MM-DD).';
      {
        const [y, m, d] = trimmed.split('-').map(Number);
        const parsed = new Date(Date.UTC(y, m - 1, d));
        if (parsed.getUTCFullYear() !== y || parsed.getUTCMonth() !== m - 1 || parsed.getUTCDate() !== d) {
          return 'Enter a valid calendar date.';
        }
      }
      return null;
    case 'description':
      if (trimmed === '') return 'Enter what was purchased or paid for.';
      if (trimmed.length > LIMITS.description) return `Description must be ${LIMITS.description} characters or fewer.`;
      return null;
    case 'currency':
      if (!SUPPORTED_CURRENCIES.includes(trimmed.toUpperCase())) {
        return `Unsupported currency. Choose one of: ${SUPPORTED_CURRENCIES.join(', ')}.`;
      }
      return null;
    case 'quantity': {
      if (trimmed === '') return null;
      if (!DECIMAL_RE.test(trimmed)) return 'Enter a valid positive quantity (up to 2 decimal places).';
      if (parseNum(trimmed)! <= 0) return 'Quantity must be greater than zero.';
      if (parseNum(trimmed)! > MAX_QUANTITY) return 'Quantity exceeds the supported maximum.';
      return null;
    }
    case 'unit_price': {
      if (trimmed === '') return null;
      if (!AMOUNT_RE.test(trimmed)) return 'Enter a valid positive unit price.';
      if (parseNum(trimmed)! <= 0) return 'Unit price must be greater than zero.';
      if (parseNum(trimmed)! > MAX_AMOUNT) return 'Unit price exceeds the supported maximum.';
      return null;
    }
    case 'payment_method':
      if (trimmed !== '' && !SUPPORTED_PAYMENT_METHODS.includes(trimmed.toUpperCase())) {
        return `Unsupported payment method. Choose one of: ${SUPPORTED_PAYMENT_METHODS.join(', ')}.`;
      }
      return null;
    case 'authorized_by': {
      if (trimmed === '' && excessRequired(form)) return 'The expense exceeds the allocation. Enter who authorized it.';
      if (trimmed.length > 500) return 'Authorized by must be 500 characters or fewer.';
      return null;
    }
    // length-only optional fields
    default: {
      const limitKey = field as keyof typeof LIMITS;
      if (limitKey in LIMITS && value.length > LIMITS[limitKey]) {
        return `${field} must be ${LIMITS[limitKey]} characters or fewer.`;
      }
      return null;
    }
  }
};

// Whether the resolved amount exceeds the selected allocation's remaining funds.
function excessRequired(form: FormState, allocations?: ExpenseAllocationItem[] | null): boolean {
  const allocation = (allocations || []).find((a) => a.allocation_id === form.allocation_id);
  if (!allocation) return false;
  const qty = parseNum(form.quantity);
  const price = parseNum(form.unit_price);
  const computed = qty !== null && price !== null ? qty * price : null;
  const resolved = computed ?? parseNum(form.amount);
  if (resolved === null) return false;
  return resolved > Number(allocation.remaining_amount);
}

const validateAll = (form: FormState, allocations: ExpenseAllocationItem[] | null): FormErrors => {
  const next: FormErrors = {};
  (Object.keys(form) as (keyof FormState)[]).forEach((field) => {
    const error = validateField(field, form[field], form);
    if (error) next[field] = error;
  });
  if (excessRequired(form, allocations)) {
    if (!next.authorization_reason) {
      next.authorization_reason = 'Tell us why the expense exceeded the allocation (authorization requires a reason).';
    }
  }
  return next;
};

export default function ExpenseForm() {
  const navigate = useNavigate();
  const { canWrite } = useAuth();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [touched, setTouched] = useState<Partial<Record<keyof FormState, boolean>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [estimateDetail, setEstimateDetail] = useState<EstimateDetail | null>(null);
  const [allocations, setAllocations] = useState<ExpenseAllocationItem[] | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);

  const selectedAllocation = (allocations || []).find((a) => a.allocation_id === form.allocation_id) || null;

  useEffect(() => {
    Promise.all([api.listEstimates(0, 200), api.listAllAllocations()])
      .then(([estData, allocData]) => {
        setEstimates(estData.estimates);
        setAllocations(allocData.allocations);
      })
      .catch((e) => setSubmitError(e.message))
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

  const excess = excessRequired(form, allocations);
  const allErrors = validateAll(form, allocations);
  const isFormValid = Object.keys(allErrors).length === 0;

  const set = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleAllocationChange = (allocationId: string) => {
    const allocation = (allocations || []).find((a) => a.allocation_id === allocationId) || null;
    setForm((prev) => ({
      ...prev,
      allocation_id: allocationId,
      currency: allocation ? allocation.currency : prev.currency,
    }));
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

    const errors = validateAll(form, allocations);
    setSubmitError(null);
    if (Object.keys(errors).length > 0) return;

    const qty = parseNum(form.quantity);
    const price = parseNum(form.unit_price);
    const hasBothPurchase = form.quantity.trim() !== '' && form.unit_price.trim() !== '';
    const typedAmount = form.amount.trim();

    setSaving(true);
    try {
      const expense = await api.createExpense({
        amount: typedAmount === '' && hasBothPurchase ? null : typedAmount,
        expense_date: form.expense_date.trim(),
        description: form.description.trim(),
        category: form.category.trim() || null,
        currency: form.currency.trim().toUpperCase() || 'FCFA',
        estimate_id: form.estimate_id || null,
        estimate_line_item_id: form.estimate_line_item_id || null,
        allocation_id: form.allocation_id || null,
        supplier: form.supplier.trim() || null,
        payment_method: form.payment_method || null,
        reference: form.reference.trim() || null,
        purpose: form.purpose.trim() || null,
        responsible_person: form.responsible_person.trim() || null,
        notes: form.notes.trim() || null,
        quantity: qty,
        unit: form.unit.trim() || null,
        unit_price: price,
        authorized_by: form.authorized_by.trim() || null,
        authorization_reason: form.authorization_reason.trim() || null,
      });
      navigate(`/expenses/${expense.id}`);
    } catch (err: any) {
      setSubmitError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const inputClass = (field: keyof FormState) =>
    `w-full rounded-lg border ${touched[field] && allErrors[field] ? 'border-red-300' : 'border-slate-300'} bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-800/20 focus:border-blue-800 disabled:bg-slate-50 disabled:text-slate-400`;

  const showError = (field: keyof FormState) =>
    touched[field] && allErrors[field] ? (
      <p className="mt-1 text-sm text-red-600">{allErrors[field]}</p>
    ) : null;

  if (loadingOptions) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="mt-4 text-slate-500">Loading expense options...</p>
      </div>
    );
  }

  if (!canWrite) {
    return (
      <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Your access is read-only. To add expense records, ask a project member or administrator.
        <Link to="/expenses" className="font-medium text-amber-900 underline ml-1">
          Back to Expense Register
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <Link to="/expenses" className="text-sm text-blue-800 hover:text-blue-600">
          &larr; Back to Expense Register
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Record Expense</h1>
        <p className="mt-1 text-slate-500">
          Log a purchase or payment. You can attach a supporting document after saving.
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
              Amount
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
              placeholder="Leave blank if using quantity × unit price"
            />
            {showError('amount')}
          </div>
          <div>
            <label htmlFor="expense_date" className="block text-sm font-medium text-slate-700 mb-1">
              Expense date *
            </label>
            <input
              id="expense_date"
              type="date"
              value={form.expense_date}
              onChange={(e) => set('expense_date', e.target.value)}
              onBlur={() => setTouchedField('expense_date')}
              className={inputClass('expense_date')}
            />
            {showError('expense_date')}
          </div>
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-slate-700 mb-1">
            Description *
          </label>
          <input
            id="description"
            type="text"
            autoComplete="off"
            maxLength={LIMITS.description}
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            onBlur={() => setTouchedField('description')}
            className={inputClass('description')}
            placeholder="e.g. Cement purchase for foundation works"
          />
          {showError('description')}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Purchase information (optional)</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="quantity" className="block text-sm font-medium text-slate-700 mb-1">
                Quantity
              </label>
              <input
                id="quantity"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                maxLength={14}
                value={form.quantity}
                onChange={(e) => set('quantity', e.target.value)}
                onBlur={() => setTouchedField('quantity')}
                className={inputClass('quantity')}
                placeholder="e.g. 2.5"
              />
              {showError('quantity')}
            </div>
            <div>
              <label htmlFor="unit" className="block text-sm font-medium text-slate-700 mb-1">
                Unit
              </label>
              <input
                id="unit"
                type="text"
                autoComplete="off"
                maxLength={LIMITS.unit}
                value={form.unit}
                onChange={(e) => set('unit', e.target.value)}
                onBlur={() => setTouchedField('unit')}
                className={inputClass('unit')}
                placeholder="bags, m2, etc."
              />
              {showError('unit')}
            </div>
            <div>
              <label htmlFor="unit_price" className="block text-sm font-medium text-slate-700 mb-1">
                Unit price
              </label>
              <input
                id="unit_price"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                maxLength={18}
                value={form.unit_price}
                onChange={(e) => set('unit_price', e.target.value)}
                onBlur={() => setTouchedField('unit_price')}
                className={inputClass('unit_price')}
                placeholder="e.g. 3000"
              />
              {showError('unit_price')}
            </div>
          </div>
          {form.quantity.trim() !== '' && form.unit_price.trim() !== '' && parseNum(form.quantity) !== null && parseNum(form.unit_price) !== null && (
            <p className="mt-2 text-sm text-slate-500">
              Calculated total: <span className="font-medium text-slate-900">{formatMoney(parseNum(form.quantity)! * parseNum(form.unit_price)!)}</span>
            </p>
          )}
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
              maxLength={LIMITS.category}
              value={form.category}
              onChange={(e) => set('category', e.target.value)}
              onBlur={() => setTouchedField('category')}
              className={inputClass('category')}
              placeholder="MATERIALS, LABOUR, etc."
            />
            {showError('category')}
          </div>
          <div>
            <label htmlFor="currency" className="block text-sm font-medium text-slate-700 mb-1">
              Currency *
            </label>
            <select
              id="currency"
              value={form.currency}
              disabled={!!selectedAllocation}
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
            {selectedAllocation && (
              <p className="mt-1 text-xs text-slate-500">
                Currency follows the allocation ({selectedAllocation.currency}).
              </p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label htmlFor="supplier" className="block text-sm font-medium text-slate-700 mb-1">
              Supplier / payee
            </label>
            <input
              id="supplier"
              type="text"
              autoComplete="off"
              maxLength={LIMITS.supplier}
              value={form.supplier}
              onChange={(e) => set('supplier', e.target.value)}
              onBlur={() => setTouchedField('supplier')}
              className={inputClass('supplier')}
            />
            {showError('supplier')}
          </div>
          <div>
            <label htmlFor="payment_method" className="block text-sm font-medium text-slate-700 mb-1">
              Payment method
            </label>
            <select
              id="payment_method"
              value={form.payment_method}
              onChange={(e) => set('payment_method', e.target.value)}
              onBlur={() => setTouchedField('payment_method')}
              className={inputClass('payment_method')}
            >
              <option value="">— Select —</option>
              {SUPPORTED_PAYMENT_METHODS.map((method) => (
                <option key={method} value={method}>
                  {method.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
            {showError('payment_method')}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
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
              placeholder="Invoice / payment number"
            />
            {showError('reference')}
          </div>
          <div>
            <label htmlFor="responsible_person" className="block text-sm font-medium text-slate-700 mb-1">
              Responsible person
            </label>
            <input
              id="responsible_person"
              type="text"
              autoComplete="off"
              maxLength={LIMITS.responsible_person}
              value={form.responsible_person}
              onChange={(e) => set('responsible_person', e.target.value)}
              onBlur={() => setTouchedField('responsible_person')}
              className={inputClass('responsible_person')}
            />
            {showError('responsible_person')}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <label htmlFor="allocation_id" className="block text-sm font-medium text-slate-700 mb-1">
              Link to allocation
            </label>
            <select
              id="allocation_id"
              value={form.allocation_id}
              onChange={(e) => handleAllocationChange(e.target.value)}
              onBlur={() => setTouchedField('allocation_id')}
              className={inputClass('allocation_id')}
            >
              <option value="">— None —</option>
              {(allocations || [])
                .filter((a) => Number(a.remaining_amount) !== 0 || Number(a.remaining_amount) < 0)
                .map((a) => (
                  <option key={a.allocation_id} value={a.allocation_id}>
                    {a.allocation_purpose || a.allocation_category || 'Allocation'} — {formatMoney(a.remaining_amount)} remaining
                  </option>
                ))}
            </select>
            {showError('allocation_id')}
          </div>
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
              onBlur={() => setTouchedField('estimate_id')}
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
            {showError('estimate_id')}
          </div>
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
              onBlur={() => setTouchedField('estimate_line_item_id')}
              className={inputClass('estimate_line_item_id')}
            >
              <option value="">— None —</option>
              {estimateDetail.line_items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.item_number ? `${item.item_number} · ` : ''}
                  {item.description}
                </option>
              ))}
            </select>
            {showError('estimate_line_item_id')}
          </div>
        )}

        {excess && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-4">
            <p className="text-sm text-amber-800">
              This expense exceeds the remaining allocation. It can only be recorded with explicit authorization.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="authorized_by" className="block text-sm font-medium text-slate-700 mb-1">
                  Authorized by *
                </label>
                <input
                  id="authorized_by"
                  type="text"
                  autoComplete="off"
                  maxLength={500}
                  value={form.authorized_by}
                  onChange={(e) => set('authorized_by', e.target.value)}
                  onBlur={() => setTouchedField('authorized_by')}
                  className={inputClass('authorized_by')}
                  placeholder="Name / authority approving the excess"
                />
                {showError('authorized_by')}
              </div>
              <div>
                <label htmlFor="authorization_reason" className="block text-sm font-medium text-slate-700 mb-1">
                  Authorization reason *
                </label>
                <input
                  id="authorization_reason"
                  type="text"
                  autoComplete="off"
                  maxLength={LIMITS.authorization_reason}
                  value={form.authorization_reason}
                  onChange={(e) => set('authorization_reason', e.target.value)}
                  onBlur={() => setTouchedField('authorization_reason')}
                  className={inputClass('authorization_reason')}
                />
                {showError('authorization_reason')}
              </div>
            </div>
          </div>
        )}

        <div>
          <label htmlFor="purpose" className="block text-sm font-medium text-slate-700 mb-1">
            Purpose
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
            to="/expenses"
            className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={!isFormValid || saving}
            className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Expense'}
          </button>
        </div>
      </form>
    </div>
  );
}