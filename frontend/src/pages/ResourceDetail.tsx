import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type {
  ResourceDetail as ResourceDetailData,
  ResourceMovement,
  Expense,
} from '../types';
import { formatDate, formatMoney, formatNumber, toNumber } from '../utils/format';

type MovementType = 'purchase' | 'delivery' | 'usage' | 'adjustment';

interface MovementFormState {
  movement_type: MovementType;
  movement_date: string;
  quantity: string;
  unit_cost: string;
  expense_id: string;
  supplier: string;
  reference: string;
  receiver: string;
  linked_purchase_movement_id: string;
  project_stage: string;
  activity: string;
  responsible_person: string;
  notes: string;
  authorized_by: string;
  authorization_reason: string;
}

const MOVEMENT_META: Record<string, { label: string; badge: string; color: string }> = {
  purchase: { label: 'Purchase', badge: 'bg-blue-50 text-blue-700 border-blue-200', color: 'text-blue-800' },
  delivery: { label: 'Delivery', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', color: 'text-emerald-800' },
  usage: { label: 'Usage', badge: 'bg-amber-50 text-amber-700 border-amber-200', color: 'text-amber-800' },
  adjustment: { label: 'Adjustment', badge: 'bg-purple-50 text-purple-700 border-purple-200', color: 'text-purple-800' },
};

const QUANTITY_RE = /^-?\d{1,12}(\.\d{1,2})?$/;
const MONEY_RE = /^\d{1,13}(\.\d{1,2})?$/;

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
  return err?.message || 'Request failed.';
};

const movementQuantity = (movement: ResourceMovement) => {
  const quantity = toNumber(movement.quantity) ?? 0;
  if (movement.movement_type === 'adjustment') {
    return `${quantity > 0 ? '+' : ''}${formatNumber(quantity)}`;
  }
  return formatNumber(quantity);
};

export default function ResourceDetailPage() {
  const { id = '' } = useParams();
  const { canWrite, isAdmin } = useAuth();
  const [detail, setDetail] = useState<ResourceDetailData | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [movementOpen, setMovementOpen] = useState(false);

  const load = () => {
    setLoading(true);
    api.getResource(id)
      .then(setDetail)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    api.listExpenses(0, 200)
      .then((data) => setExpenses(data.expenses))
      .catch(() => setExpenses([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  const attachEvidence = (movementId: string) => {
    const picker = document.createElement('input');
    picker.type = 'file';
    picker.accept = '.pdf,.png,.jpg,.jpeg,.webp,.gif';
    picker.onchange = async () => {
      const file = picker.files?.[0];
      if (!file) return;
      try {
        await api.attachMovementEvidence(id, movementId, file);
        load();
      } catch (err: any) {
        window.alert(err.response?.data?.detail || err.message);
      }
    };
    picker.click();
  };

  const removeEvidence = async (movementId: string) => {
    if (!window.confirm('Remove this supporting document?')) return;
    try {
      await api.removeMovementEvidence(id, movementId);
      load();
    } catch (err: any) {
      window.alert(err.response?.data?.detail || err.message);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="mt-4 text-slate-500">Loading resource...</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <p className="text-red-800 text-sm">{error ?? 'Resource not found.'}</p>
        <Link to="/resources" className="mt-4 inline-block text-blue-800 hover:text-blue-600 text-sm">
          &larr; Back to Resource Register
        </Link>
      </div>
    );
  }

  const unit = detail.unit ? ` ${detail.unit}` : '';
  const remaining = toNumber(detail.remaining_quantity) ?? 0;
  const variances = detail.cost_variance != null ? toNumber(detail.cost_variance) ?? 0 : null;
  const purchaseMovements = detail.movements.filter((m) => m.movement_type === 'purchase');

  return (
    <div>
      <div className="mb-8">
        <Link to="/resources" className="text-sm text-blue-800 hover:text-blue-600">
          &larr; Back to Resource Register
        </Link>
        <div className="mt-2 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{detail.name}</h1>
            <p className="mt-1 text-slate-500">
              {detail.category || 'Uncategorized'}
              {detail.unit ? ` \u00b7 measured in ${detail.unit}` : ''}
              {detail.currency ? ` \u00b7 ${detail.currency}` : ''}
            </p>
          </div>
          {canWrite && (
            <button
              onClick={() => setMovementOpen(true)}
              className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
            >
              Record Movement
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Budgeted</div>
          <div className="mt-2 text-xl font-bold text-slate-900">
            {detail.budgeted_quantity != null ? `${formatNumber(detail.budgeted_quantity)}${unit}` : '—'}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Purchased</div>
          <div className="mt-2 text-xl font-bold text-blue-800">
            {formatNumber(detail.purchased_quantity)}{unit}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Delivered</div>
          <div className="mt-2 text-xl font-bold text-emerald-700">
            {formatNumber(detail.delivered_quantity)}{unit}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Used</div>
          <div className="mt-2 text-xl font-bold text-amber-700">
            {formatNumber(detail.used_quantity)}{unit}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Remaining</div>
          <div className={`mt-2 text-xl font-bold ${remaining < 0 ? 'text-red-600' : 'text-emerald-700'}`}>
            {formatNumber(detail.remaining_quantity)}{unit}
          </div>
          <div className="mt-1 text-sm text-slate-500">
            {formatNumber(detail.adjustment_quantity)} adjusted
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Pending delivery</div>
          <div className="mt-2 text-xl font-bold text-amber-600">
            {formatNumber(detail.pending_delivery_quantity)}{unit}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Budgeted cost</div>
          <div className="mt-2 text-xl font-bold text-slate-900">
            {detail.budgeted_cost != null ? formatMoney(detail.budgeted_cost, detail.currency) : '—'}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Actual purchase cost</div>
          <div className="mt-2 text-xl font-bold text-blue-800">
            {formatMoney(detail.total_purchase_cost, detail.currency)}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Cost variance</div>
          <div className={`mt-2 text-xl font-bold ${variances !== null && variances < 0 ? 'text-red-600' : 'text-slate-900'}`}>
            {variances == null ? '—' : formatMoney(detail.cost_variance!, detail.currency)}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Movement records</div>
          <div className="mt-2 text-xl font-bold text-slate-900">{formatNumber(detail.movements.length)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-white rounded-lg border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Movement history</h2>
            {canWrite && (
              <button
                onClick={() => setMovementOpen(true)}
                className="text-sm text-blue-800 hover:text-blue-600 font-medium"
              >
                + Record movement
              </button>
            )}
          </div>
          {detail.movements.length === 0 ? (
            <p className="text-sm text-slate-500">
              No movements recorded yet. Record the first purchase, delivery, usage or adjustment.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Movement</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Quantity</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Reference</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Responsible</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Notes</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Evidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {detail.movements.map((movement) => {
                    const meta = MOVEMENT_META[movement.movement_type] || MOVEMENT_META.usage;
                    const evidenceUrl = `${API_BASE}/api/v1/resources/${id}/movements/${movement.id}/evidence`;
                    return (
                      <tr key={movement.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">{formatDate(movement.movement_date)}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${meta.badge}`}>
                            {meta.label}
                          </span>
                          {movement.movement_type === 'purchase' && movement.unit_cost != null && (
                            <div className="mt-1 text-xs text-slate-500">
                              {formatNumber(movement.quantity)} \u00d7 {formatMoney(movement.unit_cost)}{movement.supplier ? ` \u00b7 ${movement.supplier}` : ''}
                            </div>
                          )}
                          {movement.movement_type === 'usage' && movement.activity && (
                            <div className="mt-1 text-xs text-slate-500">{movement.activity}</div>
                          )}
                          {movement.movement_type === 'adjustment' && movement.authorized_by && (
                            <div className="mt-1 text-xs text-purple-700">
                              Authorized: {movement.authorized_by}
                            </div>
                          )}
                        </td>
                        <td className={`px-4 py-3 text-sm font-medium text-right ${meta.color}`}>
                          {movementQuantity(movement)}{unit}
                          {movement.movement_type === 'purchase' && movement.total_cost != null && (
                            <div className="text-xs text-slate-500 font-normal">
                              {formatMoney(movement.total_cost, detail.currency)}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600">{movement.reference || '—'}</td>
                        <td className="px-4 py-3 text-sm text-slate-600">
                          {movement.receiver ? `${movement.receiver} (received)` : movement.responsible_person || '—'}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-500 max-w-[220px] truncate" title={movement.notes || ''}>
                          {movement.notes || '—'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {movement.evidence_filename ? (
                            <div className="flex items-center gap-2">
                              <a
                                href={evidenceUrl}
                                download={movement.evidence_original_filename || movement.evidence_filename}
                                className="text-blue-800 hover:text-blue-600 truncate max-w-[140px]"
                              >
                                {movement.evidence_original_filename || 'document'}
                              </a>
                              {isAdmin && (
                              <button onClick={() => removeEvidence(movement.id)} className="text-red-600 hover:text-red-800 text-xs" title="Remove">
                                Remove
                              </button>
                            )}
                          </div>
                        ) : (
                          canWrite && (
                            <button
                              onClick={() => attachEvidence(movement.id)}
                              className="text-blue-800 hover:text-blue-600 font-medium text-sm"
                            >
                              + Attach
                            </button>
                          )
                        )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Traceability</h2>
            <dl className="space-y-3 text-sm">
              <div className="grid grid-cols-1 gap-1">
                <dt className="text-slate-500">Estimate</dt>
                <dd className="font-medium text-slate-900">
                  {detail.estimate_id ? (
                    <Link to={`/estimates/${detail.estimate_id}`} className="text-blue-800 hover:text-blue-600">
                      {detail.estimate_title || 'View estimate'}
                    </Link>
                  ) : '—'}
                </dd>
              </div>
              <div className="grid grid-cols-1 gap-1">
                <dt className="text-slate-500">Estimate line item</dt>
                <dd className="font-medium text-slate-900">{detail.estimate_item_description || '—'}</dd>
              </div>
              {detail.notes && (
                <div className="grid grid-cols-1 gap-1">
                  <dt className="text-slate-500">Notes</dt>
                  <dd className="whitespace-pre-line text-slate-900">{detail.notes}</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="bg-white rounded-lg border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Related expenses</h2>
            {detail.related_expenses.length === 0 ? (
              <p className="text-sm text-slate-500">No expenses linked to this resource yet.</p>
            ) : (
              <ul className="space-y-3">
                {detail.related_expenses.map((expense) => (
                  <li key={expense.id}>
                    <Link to={`/expenses/${expense.id}`} className="block rounded-lg border border-slate-200 p-3 hover:border-blue-300 hover:bg-blue-50/40 transition-colors">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium text-slate-900 truncate">{expense.description}</span>
                        <span className="text-sm font-medium text-slate-900 whitespace-nowrap">
                          {formatMoney(expense.amount, expense.currency)}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {formatDate(expense.expense_date)}
                        {expense.reference ? ` \u00b7 ${expense.reference}` : ''}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      <MovementModal
        open={movementOpen}
        resourceId={id}
        unit={unit}
        currency={detail.currency}
        expenses={expenses}
        purchaseMovements={purchaseMovements}
        onClose={() => setMovementOpen(false)}
        onSaved={() => {
          setMovementOpen(false);
          load();
        }}
      />
    </div>
  );
}

function MovementModal({
  open,
  resourceId,
  unit,
  currency,
  expenses,
  purchaseMovements,
  onClose,
  onSaved,
}: {
  open: boolean;
  resourceId: string;
  unit: string;
  currency: string;
  expenses: Expense[];
  purchaseMovements: ResourceMovement[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<MovementFormState>({
    movement_type: 'purchase',
    movement_date: new Date().toISOString().slice(0, 10),
    quantity: '',
    unit_cost: '',
    expense_id: '',
    supplier: '',
    reference: '',
    receiver: '',
    linked_purchase_movement_id: '',
    project_stage: '',
    activity: '',
    responsible_person: '',
    notes: '',
    authorized_by: '',
    authorization_reason: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm({
        movement_type: 'purchase',
        movement_date: new Date().toISOString().slice(0, 10),
        quantity: '',
        unit_cost: '',
        expense_id: '',
        supplier: '',
        reference: '',
        receiver: '',
        linked_purchase_movement_id: '',
        project_stage: '',
        activity: '',
        responsible_person: '',
        notes: '',
        authorized_by: '',
        authorization_reason: '',
      });
      setError(null);
      setFieldErrors({});
    }
  }, [open]);

  const set = (field: keyof MovementFormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: '' }));
  };

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    const quantity = form.quantity.trim();
    if (!QUANTITY_RE.test(quantity) || parseNum(quantity) === null) {
      next.quantity = 'Enter a valid quantity (up to 2 decimal places).';
    } else {
      const value = parseNum(quantity)!;
      if (form.movement_type === 'adjustment') {
        if (value === 0) next.quantity = 'Adjustment quantity cannot be zero.';
      } else if (value <= 0) {
        next.quantity = 'Quantity must be greater than zero.';
      }
    }
    if (form.movement_type === 'purchase') {
      if (!MONEY_RE.test(form.unit_cost.trim()) || parseNum(form.unit_cost) === null) {
        next.unit_cost = 'Enter a valid unit cost.';
      }
    }
    if (form.movement_type === 'adjustment') {
      if (parseNum(quantity) !== null && parseNum(quantity)! < 0 && form.authorized_by.trim() === '') {
        next.authorized_by = 'Negative adjustments require authorization.';
      }
      if (form.notes.trim() === '') {
        next.notes = 'Every adjustment must state a reason.';
      }
    }
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  };

  if (!open) return null;

  const switchType = (type: MovementType) => {
    setForm((prev) => ({ ...prev, movement_type: type }));
    setFieldErrors({});
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;
    if (!validate()) return;

    setSaving(true);
    setError(null);
    const quantity = parseNum(form.quantity)!;
    const base = {
      movement_date: form.movement_date || null,
      responsible_person: form.responsible_person.trim() || null,
      notes: form.notes.trim() || null,
    };
    try {
      if (form.movement_type === 'purchase') {
        await api.recordPurchase(resourceId, {
          ...base,
          quantity,
          unit_cost: parseNum(form.unit_cost)!,
          expense_id: form.expense_id || null,
          supplier: form.supplier.trim() || null,
          reference: form.reference.trim() || null,
        });
      } else if (form.movement_type === 'delivery') {
        await api.recordDelivery(resourceId, {
          ...base,
          quantity,
          linked_purchase_movement_id: form.linked_purchase_movement_id || null,
          supplier: form.supplier.trim() || null,
          reference: form.reference.trim() || null,
          receiver: form.receiver.trim() || null,
        });
      } else if (form.movement_type === 'usage') {
        await api.recordUsage(resourceId, {
          ...base,
          quantity,
          project_stage: form.project_stage.trim() || null,
          activity: form.activity.trim() || null,
        });
      } else {
        await api.recordAdjustment(resourceId, {
          ...base,
          quantity,
          authorized_by: form.authorized_by.trim() || null,
          authorization_reason: form.authorization_reason.trim() || null,
        });
      }
      onSaved();
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const inputClass = (field: string) =>
    `w-full rounded-lg border ${fieldErrors[field] ? 'border-red-300' : 'border-slate-300'} bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-800/20 focus:border-blue-800`;

  const tabs: { id: MovementType; label: string }[] = [
    { id: 'purchase', label: 'Purchase' },
    { id: 'delivery', label: 'Delivery' },
    { id: 'usage', label: 'Usage' },
    { id: 'adjustment', label: 'Adjustment' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900">Record movement</h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-xl leading-none"
            aria-label="Close"
          >
            &times;
          </button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => switchType(tab.id)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  form.movement_type === tab.id
                    ? 'bg-blue-800 text-white border-blue-800'
                    : 'text-slate-600 border-slate-300 hover:bg-slate-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="movement_date" className="block text-sm font-medium text-slate-700 mb-1">
                Date *
              </label>
              <input
                id="movement_date"
                type="date"
                required
                value={form.movement_date}
                onChange={(e) => set('movement_date', e.target.value)}
                className={inputClass('movement_date')}
              />
            </div>
            <div>
              <label htmlFor="quantity" className="block text-sm font-medium text-slate-700 mb-1">
                {form.movement_type === 'adjustment' ? 'Quantity (signed)' : `Quantity (${unit.trim() || 'units'})`} *
              </label>
              <input
                id="quantity"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                maxLength={15}
                value={form.quantity}
                onChange={(e) => set('quantity', e.target.value)}
                className={inputClass('quantity')}
                placeholder={form.movement_type === 'adjustment' ? '+10 or -5' : 'e.g. 100'}
              />
              {fieldErrors.quantity && <p className="mt-1 text-sm text-red-600">{fieldErrors.quantity}</p>}
            </div>
          </div>

          {form.movement_type === 'purchase' && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="unit_cost" className="block text-sm font-medium text-slate-700 mb-1">
                    Unit cost ({currency}) *
                  </label>
                  <input
                    id="unit_cost"
                    type="text"
                    inputMode="decimal"
                    autoComplete="off"
                    maxLength={18}
                    value={form.unit_cost}
                    onChange={(e) => set('unit_cost', e.target.value)}
                    className={inputClass('unit_cost')}
                    placeholder="e.g. 7500"
                  />
                  {fieldErrors.unit_cost && <p className="mt-1 text-sm text-red-600">{fieldErrors.unit_cost}</p>}
                </div>
                <div>
                  <label htmlFor="expense_id" className="block text-sm font-medium text-slate-700 mb-1">
                    Linked expense (Phase 3)
                  </label>
                  <select
                    id="expense_id"
                    value={form.expense_id}
                    onChange={(e) => set('expense_id', e.target.value)}
                    className={inputClass('expense_id')}
                  >
                    <option value="">— None —</option>
                    {expenses
                      .filter((exp) => exp.status === 'recorded')
                      .map((exp) => (
                        <option key={exp.id} value={exp.id}>
                          {exp.description} — {formatMoney(exp.amount)}
                        </option>
                      ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="supplier" className="block text-sm font-medium text-slate-700 mb-1">
                    Supplier
                  </label>
                  <input
                    id="supplier"
                    type="text"
                    autoComplete="off"
                    maxLength={500}
                    value={form.supplier}
                    onChange={(e) => set('supplier', e.target.value)}
                    className={inputClass('supplier')}
                  />
                </div>
                <div>
                  <label htmlFor="reference" className="block text-sm font-medium text-slate-700 mb-1">
                    Reference
                  </label>
                  <input
                    id="reference"
                    type="text"
                    autoComplete="off"
                    maxLength={200}
                    value={form.reference}
                    onChange={(e) => set('reference', e.target.value)}
                    className={inputClass('reference')}
                    placeholder="Invoice / purchase number"
                  />
                </div>
              </div>
            </>
          )}

          {form.movement_type === 'delivery' && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="receiver" className="block text-sm font-medium text-slate-700 mb-1">
                    Receiver
                  </label>
                  <input
                    id="receiver"
                    type="text"
                    autoComplete="off"
                    maxLength={500}
                    value={form.receiver}
                    onChange={(e) => set('receiver', e.target.value)}
                    className={inputClass('receiver')}
                  />
                </div>
                <div>
                  <label htmlFor="linked_purchase" className="block text-sm font-medium text-slate-700 mb-1">
                    Related purchase
                  </label>
                  <select
                    id="linked_purchase"
                    value={form.linked_purchase_movement_id}
                    onChange={(e) => set('linked_purchase_movement_id', e.target.value)}
                    className={inputClass('linked_purchase')}
                  >
                    <option value="">— None —</option>
                    {purchaseMovements.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.supplier || 'Purchase'} — {formatNumber(p.quantity)}{unit} ({formatDate(p.movement_date)})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="supplier" className="block text-sm font-medium text-slate-700 mb-1">
                    Supplier
                  </label>
                  <input
                    id="supplier"
                    type="text"
                    autoComplete="off"
                    maxLength={500}
                    value={form.supplier}
                    onChange={(e) => set('supplier', e.target.value)}
                    className={inputClass('supplier')}
                  />
                </div>
                <div>
                  <label htmlFor="reference" className="block text-sm font-medium text-slate-700 mb-1">
                    Delivery / reference number
                  </label>
                  <input
                    id="reference"
                    type="text"
                    autoComplete="off"
                    maxLength={200}
                    value={form.reference}
                    onChange={(e) => set('reference', e.target.value)}
                    className={inputClass('reference')}
                  />
                </div>
              </div>
            </>
          )}

          {form.movement_type === 'usage' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                  onChange={(e) => set('project_stage', e.target.value)}
                  className={inputClass('project_stage')}
                  placeholder="Foundation, Structure..."
                />
              </div>
              <div>
                <label htmlFor="activity" className="block text-sm font-medium text-slate-700 mb-1">
                  Activity / purpose
                </label>
                <input
                  id="activity"
                  type="text"
                  autoComplete="off"
                  maxLength={2000}
                  value={form.activity}
                  onChange={(e) => set('activity', e.target.value)}
                  className={inputClass('activity')}
                />
              </div>
            </div>
          )}

          {form.movement_type === 'adjustment' && (
            <>
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                <p className="text-sm text-amber-800">
                  Positive adjustments record stock found/donated on site. Negative adjustments
                  reduce stock and require explicit authorization.
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="authorized_by" className="block text-sm font-medium text-slate-700 mb-1">
                    Authorized by
                  </label>
                  <input
                    id="authorized_by"
                    type="text"
                    autoComplete="off"
                    maxLength={500}
                    value={form.authorized_by}
                    onChange={(e) => set('authorized_by', e.target.value)}
                    className={inputClass('authorized_by')}
                  />
                  {fieldErrors.authorized_by && <p className="mt-1 text-sm text-red-600">{fieldErrors.authorized_by}</p>}
                </div>
                <div>
                  <label htmlFor="authorization_reason" className="block text-sm font-medium text-slate-700 mb-1">
                    Authorization reason
                  </label>
                  <input
                    id="authorization_reason"
                    type="text"
                    autoComplete="off"
                    maxLength={1000}
                    value={form.authorization_reason}
                    onChange={(e) => set('authorization_reason', e.target.value)}
                    className={inputClass('authorization_reason')}
                  />
                </div>
              </div>
            </>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                onChange={(e) => set('responsible_person', e.target.value)}
                className={inputClass('responsible_person')}
              />
            </div>
          </div>

          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-slate-700 mb-1">
              Notes {form.movement_type === 'adjustment' ? '*' : ''}
            </label>
            <textarea
              id="notes"
              rows={2}
              maxLength={2000}
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
              className={inputClass('notes')}
            />
            {fieldErrors.notes && <p className="mt-1 text-sm text-red-600">{fieldErrors.notes}</p>}
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving...' : 'Save Movement'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}