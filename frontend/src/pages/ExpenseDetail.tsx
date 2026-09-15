import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { ExpenseDetail } from '../types';
import { formatDate, formatMoney, formatNumber } from '../utils/format';

interface EditFormState {
  description: string;
  project: string;
  category: string;
  supplier: string;
  payment_method: string;
  reference: string;
  purpose: string;
  responsible_person: string;
  notes: string;
}

const SUPPORTED_PAYMENT_METHODS = ['', 'CASH', 'BANK_TRANSFER', 'CHEQUE', 'MOBILE_MONEY', 'CARD', 'OTHER'];
const PAYMENT_LABELS: Record<string, string> = {
  CASH: 'Cash',
  BANK_TRANSFER: 'Bank Transfer',
  CHEQUE: 'Cheque',
  MOBILE_MONEY: 'Mobile Money',
  CARD: 'Card',
  OTHER: 'Other',
};

const paymentMethodLabel = (method: string | null) => PAYMENT_LABELS[method || ''] || method || '—';

const formatApiError = (err: any): string => {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg || 'Invalid value').join('; ');
  }
  if (typeof detail === 'string' && detail.trim()) return detail;
  return err?.message || 'Request failed.';
};

export default function ExpenseDetailPage() {
  const { id = '' } = useParams();
  const { canWrite, isAdmin } = useAuth();
  const [detail, setDetail] = useState<ExpenseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attaching, setAttaching] = useState(false);
  const [editForm, setEditForm] = useState<EditFormState | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api.getExpense(id)
      .then(setDetail)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const evidenceUrl = `${API_BASE}/api/v1/expenses/${id}/evidence`;

  const attachEvidence = () => {
    const picker = document.createElement('input');
    picker.type = 'file';
    picker.accept = '.pdf,.png,.jpg,.jpeg,.webp,.gif';
    picker.onchange = async () => {
      const file = picker.files?.[0];
      if (!file) return;
      setAttaching(true);
      try {
        await api.attachExpenseEvidence(id, file);
        load();
      } catch (err: any) {
        window.alert(err.response?.data?.detail || err.message);
      } finally {
        setAttaching(false);
      }
    };
    picker.click();
  };

  const removeEvidence = async () => {
    if (!window.confirm('Remove this supporting document?')) return;
    try {
      await api.removeExpenseEvidence(id);
      load();
    } catch (err: any) {
      window.alert(err.response?.data?.detail || err.message);
    }
  };

  const openEdit = () => {
    if (!detail) return;
    setEditError(null);
    setEditForm({
      description: detail.description,
      project: detail.project || '',
      category: detail.category || '',
      supplier: detail.supplier || '',
      payment_method: detail.payment_method || '',
      reference: detail.reference || '',
      purpose: detail.purpose || '',
      responsible_person: detail.responsible_person || '',
      notes: detail.notes || '',
    });
  };

  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editForm) return;
    setEditSaving(true);
    setEditError(null);
    try {
      await api.updateExpense(id, {
        description: editForm.description.trim(),
        project: editForm.project.trim() || null,
        category: editForm.category.trim() || null,
        supplier: editForm.supplier.trim() || null,
        payment_method: editForm.payment_method || null,
        reference: editForm.reference.trim() || null,
        purpose: editForm.purpose.trim() || null,
        responsible_person: editForm.responsible_person.trim() || null,
        notes: editForm.notes.trim() || null,
      });
      setEditForm(null);
      load();
    } catch (err: any) {
      setEditError(formatApiError(err));
    } finally {
      setEditSaving(false);
    }
  };

  const setEditField = (field: keyof EditFormState, value: string) =>
    setEditForm((p) => (p ? { ...p, [field]: value } : p));

  const reverseExpense = async () => {
    if (!detail) return;
    const reason = window.prompt(
      'Reversing excludes this expense from all totals. Provide a reason (optional):'
    );
    if (reason === null) return;
    try {
      await api.reverseExpense(id, reason.trim() || undefined);
      load();
    } catch (err: any) {
      window.alert(err.response?.data?.detail || err.message);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="mt-4 text-slate-500">Loading expense...</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <p className="text-red-800 text-sm">{error ?? 'Expense not found.'}</p>
        <Link to="/expenses" className="mt-4 inline-block text-blue-800 hover:text-blue-600 text-sm">
          &larr; Back to Expense Register
        </Link>
      </div>
    );
  }

  const purchaseTotal =
    detail.quantity && detail.unit_price
      ? Number(detail.quantity) * Number(detail.unit_price)
      : null;

  const editable = detail.status === 'recorded';

  return (
    <div>
      <div className="mb-8">
        <Link to="/expenses" className="text-sm text-blue-800 hover:text-blue-600">
          &larr; Back to Expense Register
        </Link>
        <div className="mt-2 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{detail.description}</h1>
            <p className="mt-1 text-slate-500">
              {formatDate(detail.expense_date)}
              {detail.reference ? ` · Ref: ${detail.reference}` : ''}
              {detail.category ? ` · ${detail.category}` : ''}
            </p>
          </div>
          <span
            className={`inline-flex px-3 py-1 rounded-full text-xs font-medium border ${
              detail.status === 'reversed'
                ? 'bg-slate-100 text-slate-600 border-slate-200'
                : 'bg-emerald-100 text-emerald-800 border-emerald-200'
            }`}
          >
            {detail.status}
          </span>
        </div>
      </div>

      {detail.status === 'reversed' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
          <p className="text-red-800 text-sm">
            This expense has been reversed. It is excluded from all totals and cannot be edited. Record a new expense instead.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Amount</div>
          <div className="mt-2 text-xl font-bold text-slate-900">
            {formatMoney(detail.amount, detail.currency)}
          </div>
          {purchaseTotal !== null && (
            <div className="mt-1 text-sm text-slate-500">
              {formatNumber(detail.quantity)} {detail.unit || 'units'} × {formatMoney(detail.unit_price)}
            </div>
          )}
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Allocation remaining</div>
          <div className={`mt-2 text-xl font-bold ${Number(detail.allocation_remaining_amount ?? 0) < 0 ? 'text-red-600' : 'text-amber-600'}`}>
            {detail.allocation_remaining_amount == null
              ? '—'
              : formatMoney(detail.allocation_remaining_amount, detail.allocation_currency || detail.currency)}
          </div>
          {detail.allocation_remaining_amount != null && (
            <div className="mt-1 text-sm text-slate-500">
              of {formatMoney(detail.allocation_spent_amount, detail.allocation_currency || detail.currency)} spent
            </div>
          )}
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Payment</div>
          <div className="mt-2 text-xl font-bold text-slate-900">{paymentMethodLabel(detail.payment_method)}</div>
          {detail.supplier && <div className="mt-1 text-sm text-slate-500">{detail.supplier}</div>}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-white rounded-lg border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Traceability</h2>
            {editable && canWrite && (
              <button
                onClick={openEdit}
                className="text-sm text-blue-800 hover:text-blue-600 font-medium"
              >
                Edit details
              </button>
            )}
          </div>
          <dl className="space-y-3 text-sm">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <dt className="text-slate-500">Estimate</dt>
              <dd className="sm:col-span-2 font-medium text-slate-900">
                {detail.estimate_id ? (
                  <Link to={`/estimates/${detail.estimate_id}`} className="text-blue-800 hover:text-blue-600">
                    {detail.estimate_title || 'View estimate'}
                  </Link>
                ) : (
                  '—'
                )}
              </dd>
              <dt className="text-slate-500">Line item</dt>
              <dd className="sm:col-span-2 font-medium text-slate-900">{detail.estimate_item_description || '—'}</dd>
              <dt className="text-slate-500">Allocation</dt>
              <dd className="sm:col-span-2 font-medium text-slate-900">
                {detail.allocation_id
                  ? `${detail.allocation_purpose || 'Allocation'}${detail.allocation_category ? ` · ${detail.allocation_category}` : ''}`
                  : '—'}
              </dd>
              <dt className="text-slate-500">Responsible person</dt>
              <dd className="sm:col-span-2 font-medium text-slate-900">{detail.responsible_person || '—'}</dd>
            </div>
            {detail.authorized_by && (
              <>
                <dt className="text-slate-500">Authorized excess by</dt>
                <dd className="font-medium text-amber-700">
                  {detail.authorized_by}
                  {detail.authorization_reason ? ` — ${detail.authorization_reason}` : ''}
                </dd>
              </>
            )}
            <div>
              <dt className="text-slate-500">Purpose</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{detail.purpose || '—'}</dd>
            </div>
            {detail.notes && (
              <div>
                <dt className="text-slate-500">Notes</dt>
                <dd className="mt-0.5 whitespace-pre-line text-slate-900">{detail.notes}</dd>
              </div>
            )}
            <div>
              <dt className="text-slate-500">Supporting document</dt>
              <dd className="mt-1">
                {detail.evidence_filename ? (
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <a
                      href={evidenceUrl}
                      download={detail.evidence_original_filename || detail.evidence_filename}
                      className="text-sm text-blue-800 hover:text-blue-600 truncate max-w-[220px]"
                    >
                      {detail.evidence_original_filename || detail.evidence_filename}
                    </a>
                    {isAdmin && (
                      <button onClick={removeEvidence} className="text-sm text-red-600 hover:text-red-800" title="Remove">
                        Remove
                      </button>
                    )}
                  </div>
                ) : (
                  canWrite && (
                    <button
                      onClick={attachEvidence}
                      disabled={attaching}
                      className="text-sm text-blue-800 hover:text-blue-600 disabled:opacity-50"
                    >
                      {attaching ? 'Uploading...' : '+ Attach supporting document'}
                    </button>
                  )
                )}
              </dd>
            </div>
          </dl>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6 h-fit">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Corrections</h2>
          <p className="text-sm text-slate-500 mb-4">
            Financial values can never be edited after saving. To correct the amount, reverse this expense and record a new one. Non-financial details can be edited.
          </p>
          {editable && isAdmin && (
            <button
              onClick={reverseExpense}
              className="w-full px-4 py-2 rounded-lg border border-red-200 text-red-700 text-sm font-medium hover:bg-red-50 transition-colors"
            >
              Reverse expense
            </button>
          )}
        </div>
      </div>

      {editForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">Edit expense details</h3>
              <button
                onClick={() => setEditForm(null)}
                className="text-slate-400 hover:text-slate-600 text-xl leading-none"
                aria-label="Close"
              >
                &times;
              </button>
            </div>
            <form onSubmit={saveEdit} className="p-6 space-y-4">
              {editError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-red-800 text-sm">{editError}</p>
                </div>
              )}
              <div>
                <label htmlFor="edit-description" className="block text-sm font-medium text-slate-700 mb-1">
                  Description *
                </label>
                <input
                  id="edit-description"
                  type="text"
                  maxLength={2000}
                  value={editForm.description}
                  onChange={(e) => setEditField('description', e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="edit-category" className="block text-sm font-medium text-slate-700 mb-1">
                    Category
                  </label>
                  <input
                    id="edit-category"
                    type="text"
                    maxLength={300}
                    value={editForm.category}
                    onChange={(e) => setEditField('category', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                  />
                </div>
                <div>
                  <label htmlFor="edit-supplier" className="block text-sm font-medium text-slate-700 mb-1">
                    Supplier / payee
                  </label>
                  <input
                    id="edit-supplier"
                    type="text"
                    maxLength={500}
                    value={editForm.supplier}
                    onChange={(e) => setEditField('supplier', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="edit-payment" className="block text-sm font-medium text-slate-700 mb-1">
                    Payment method
                  </label>
                  <select
                    id="edit-payment"
                    value={editForm.payment_method}
                    onChange={(e) => setEditField('payment_method', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                  >
                    {SUPPORTED_PAYMENT_METHODS.map((m) => (
                      <option key={m} value={m}>
                        {m === '' ? '— Select —' : m.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="edit-reference" className="block text-sm font-medium text-slate-700 mb-1">
                    Reference
                  </label>
                  <input
                    id="edit-reference"
                    type="text"
                    maxLength={200}
                    value={editForm.reference}
                    onChange={(e) => setEditField('reference', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="edit-purpose" className="block text-sm font-medium text-slate-700 mb-1">
                  Purpose
                </label>
                <input
                  id="edit-purpose"
                  type="text"
                  maxLength={1000}
                  value={editForm.purpose}
                  onChange={(e) => setEditField('purpose', e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                />
              </div>
              <div>
                <label htmlFor="edit-responsible" className="block text-sm font-medium text-slate-700 mb-1">
                  Responsible person
                </label>
                <input
                  id="edit-responsible"
                  type="text"
                  maxLength={500}
                  value={editForm.responsible_person}
                  onChange={(e) => setEditField('responsible_person', e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                />
              </div>
              <div>
                <label htmlFor="edit-notes" className="block text-sm font-medium text-slate-700 mb-1">
                  Notes
                </label>
                <textarea
                  id="edit-notes"
                  rows={3}
                  maxLength={2000}
                  value={editForm.notes}
                  onChange={(e) => setEditField('notes', e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setEditForm(null)}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSaving || editForm.description.trim() === ''}
                  className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {editSaving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}