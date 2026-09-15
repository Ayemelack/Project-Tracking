import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { FundAllocation, FundReceiptDetail, Estimate } from '../types';
import { formatDate, formatMoney, formatNumber } from '../utils/format';

interface AllocationForm {
  amount: string;
  estimate_id: string;
  category: string;
  purpose: string;
  responsible_person: string;
  allocation_date: string;
  notes: string;
}

export default function FundReceiptDetail() {
  const { id = '' } = useParams();
  const { canWrite, isAdmin } = useAuth();
  const [detail, setDetail] = useState<FundReceiptDetail | null>(null);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // allocation modal
  const [showAllocation, setShowAllocation] = useState(false);
  const [allocForm, setAllocForm] = useState<AllocationForm>({
    amount: '',
    estimate_id: '',
    category: '',
    purpose: '',
    responsible_person: '',
    allocation_date: new Date().toISOString().slice(0, 10),
    notes: '',
  });
  const [allocErrors, setAllocErrors] = useState<Partial<Record<keyof AllocationForm, string>>>({});
  const [allocSaving, setAllocSaving] = useState(false);

  // evidence
  const [attaching, setAttaching] = useState<'receipt' | string | null>(null);

  const load = () => {
    setLoading(true);
    api.getFundReceipt(id)
      .then(setDetail)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    api.listEstimates(0, 200)
      .then((data) => setEstimates(data.estimates))
      .catch(() => setEstimates([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const availableAmount = detail ? Number(detail.unallocated_amount) : 0;

  const openAllocation = () => {
    setAllocErrors({});
    setAllocForm((prev) => ({
      ...prev,
      amount: '',
      estimate_id: '',
      category: '',
      purpose: '',
      responsible_person: '',
      notes: '',
    }));
    setShowAllocation(true);
  };

  const closeAllocation = () => {
    if (!allocSaving) setShowAllocation(false);
  };

  const validateAllocation = (): boolean => {
    const next: Partial<Record<keyof AllocationForm, string>> = {};
    const amount = Number(allocForm.amount);
    if (allocForm.amount.trim() === '' || !Number.isFinite(amount) || amount <= 0) {
      next.amount = 'Enter the allocation amount (greater than zero).';
    } else if (amount > availableAmount) {
      next.amount = `This exceeds the available funds (${formatNumber(availableAmount)}).`;
    }
    if (!allocForm.purpose.trim()) next.purpose = 'Enter what the money is used for.';
    setAllocErrors(next);
    return Object.keys(next).length === 0;
  };

  const submitAllocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateAllocation()) return;
    setAllocSaving(true);
    try {
      await api.createAllocation(id, {
        amount: Number(allocForm.amount),
        estimate_id: allocForm.estimate_id || null,
        category: allocForm.category.trim() || null,
        purpose: allocForm.purpose.trim(),
        responsible_person: allocForm.responsible_person.trim() || null,
        allocation_date: allocForm.allocation_date || null,
        notes: allocForm.notes.trim() || null,
      });
      setShowAllocation(false);
      load();
    } catch (err: any) {
      setAllocErrors((prev) => ({ ...prev, amount: err.response?.data?.detail || err.message }));
    } finally {
      setAllocSaving(false);
    }
  };

  const cancelAllocation = async (allocation: FundAllocation) => {
    const reason = window.prompt(`Provide a reason for cancelling this allocation of ${formatMoney(allocation.amount, allocation.currency)}?`);
    if (reason === null) return;
    try {
      await api.cancelAllocation(allocation.id, reason.trim() || undefined);
      load();
    } catch (err: any) {
      window.alert(err.response?.data?.detail || err.message);
    }
  };

  const attachEvidence = async (target: { type: 'receipt' } | { type: 'allocation'; id: string }) => {
    const picker = document.createElement('input');
    picker.type = 'file';
    picker.accept = '.pdf,.png,.jpg,.jpeg,.webp,.gif';
    picker.onchange = async () => {
      const file = picker.files?.[0];
      if (!file) return;
      setAttaching(target.type === 'receipt' ? 'receipt' : target.id);
      try {
        if (target.type === 'receipt') await api.attachReceiptEvidence(id, file);
        else await api.attachAllocationEvidence(target.id, file);
        load();
      } catch (err: any) {
        window.alert(err.response?.data?.detail || err.message);
      } finally {
        setAttaching(null);
      }
    };
    picker.click();
  };

  const removeEvidence = async (target: { type: 'receipt' } | { type: 'allocation'; id: string }) => {
    if (!window.confirm('Remove this supporting document?')) return;
    try {
      if (target.type === 'receipt') await api.removeReceiptEvidence(id);
      else await api.removeAllocationEvidence(target.id);
      load();
    } catch (err: any) {
      window.alert(err.response?.data?.detail || err.message);
    }
  };

  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const evidenceDownloadUrl = (target: { type: 'receipt' } | { type: 'allocation'; id: string }) =>
    target.type === 'receipt'
      ? `${API_BASE}/api/v1/funds/${id}/evidence`
      : `${API_BASE}/api/v1/allocations/${target.id}/evidence`;

  const EvidenceRow = ({ target }: { target: { type: 'receipt' } | { type: 'allocation'; id: string } }) => {
    const ev =
      target.type === 'receipt'
        ? { filename: detail?.evidence_filename, original: detail?.evidence_original_filename }
        : { filename: detail?.allocations.find((a) => a.id === target.id)?.evidence_filename, original: detail?.allocations.find((a) => a.id === target.id)?.evidence_original_filename };
    const busy = attaching !== null;
    return (
      <div className="space-y-2">
        {ev.filename ? (
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <a
              href={evidenceDownloadUrl(target)}
              download={ev.original ?? ev.filename}
              className="text-sm text-blue-800 hover:text-blue-600 truncate max-w-[220px]"
            >
              {ev.original ?? ev.filename}
            </a>
            {isAdmin && (
              <button onClick={() => removeEvidence(target)} className="text-sm text-red-600 hover:text-red-800" title="Remove">
                Remove
              </button>
            )}
          </div>
        ) : (
          canWrite && (
            <button
              onClick={() => attachEvidence(target)}
              disabled={busy}
              className="text-sm text-blue-800 hover:text-blue-600 disabled:opacity-50"
            >
              {busy ? 'Uploading...' : '+ Attach supporting document'}
            </button>
          )
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="mt-4 text-slate-500">Loading fund receipt...</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <p className="text-red-800 text-sm">{error ?? 'Fund receipt not found.'}</p>
        <Link to="/funding" className="mt-4 inline-block text-blue-800 hover:text-blue-600 text-sm">
          &larr; Back to Funding Register
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <Link to="/funding" className="text-sm text-blue-800 hover:text-blue-600">
          &larr; Back to Funding Register
        </Link>
        <div className="mt-2 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{detail.source}</h1>
            <p className="mt-1 text-slate-500">
              {formatDate(detail.received_date)}
              {detail.reference ? ` · Ref: ${detail.reference}` : ''}
            </p>
          </div>
          <span className="inline-flex px-3 py-1 rounded-full text-xs font-medium border bg-emerald-100 text-emerald-800 border-emerald-200">
            {detail.status}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Received</div>
          <div className="mt-2 text-xl font-bold text-emerald-600">
            {formatMoney(detail.amount, detail.currency)}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Allocated</div>
          <div className="mt-2 text-xl font-bold text-blue-800">
            {formatMoney(detail.allocated_amount, detail.currency)}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5">
          <div className="text-xs font-medium text-slate-500 uppercase">Available</div>
          <div className="mt-2 text-xl font-bold text-amber-600">
            {formatMoney(detail.unallocated_amount, detail.currency)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Allocations</h2>
            {canWrite && (
              <button
                onClick={openAllocation}
                className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={availableAmount <= 0}
                title={availableAmount <= 0 ? 'No available funds to allocate' : undefined}
              >
                + New Allocation
              </button>
            )}
          </div>
          {detail.allocations.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-slate-500">
                No allocations yet. Use &ldquo;New Allocation&rdquo; to direct funds to works.
              </p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Purpose</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Category</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {detail.allocations.map((allocation) => (
                  <tr key={allocation.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-900">
                        {allocation.purpose || '—'}
                        {allocation.estimate_title && (
                          <span className="ml-2 text-xs font-normal text-slate-500">→ {allocation.estimate_title}</span>
                        )}
                      </div>
                      <div className="mt-1 text-sm text-slate-500">
                        {allocation.responsible_person || '—'}
                        {allocation.allocation_date ? ` · ${formatDate(allocation.allocation_date)}` : ''}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{allocation.category || '—'}</td>
                    <td className="px-6 py-4 text-sm font-medium text-slate-900 text-right">
                      {formatMoney(allocation.amount, allocation.currency)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                        allocation.status === 'cancelled'
                          ? 'bg-red-50 text-red-700 border-red-200'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                      }`}>
                        {allocation.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-3">
                        {allocation.status === 'allocated' && isAdmin && (
                          <button
                            onClick={() => cancelAllocation(allocation)}
                            className="text-sm text-red-600 hover:text-red-800"
                          >
                            Cancel
                          </button>
                        )}
                        <EvidenceRow target={{ type: 'allocation', id: allocation.id }} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Receipt Details</h2>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-slate-500">Purpose</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{detail.purpose || '—'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Reference</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{detail.reference || '—'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Currency</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{detail.currency}</dd>
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
                <EvidenceRow target={{ type: 'receipt' }} />
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {showAllocation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4" onClick={closeAllocation}>
          <div
            className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">New Allocation</h3>
              <button onClick={closeAllocation} className="text-slate-400 hover:text-slate-600 text-xl leading-none" aria-label="Close">
                &times;
              </button>
            </div>
            <form onSubmit={submitAllocation} className="p-6 space-y-4">
              <div>
                <label htmlFor="alloc-amount" className="block text-sm font-medium text-slate-700 mb-1">
                  Amount *
                </label>
                <input
                  id="alloc-amount"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={allocForm.amount}
                  onChange={(e) => setAllocForm((p) => ({ ...p, amount: e.target.value }))}
                  className={`w-full rounded-lg border ${allocErrors.amount ? 'border-red-300' : 'border-slate-300'} bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20`}
                  placeholder={`Available: ${formatNumber(availableAmount)}`}
                />
                {allocErrors.amount && <p className="mt-1 text-sm text-red-600">{allocErrors.amount}</p>}
              </div>
              <div>
                <label htmlFor="alloc-estimate" className="block text-sm font-medium text-slate-700 mb-1">
                  Link to estimate (optional)
                </label>
                <select
                  id="alloc-estimate"
                  value={allocForm.estimate_id}
                  onChange={(e) => setAllocForm((p) => ({ ...p, estimate_id: e.target.value }))}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
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
              <div>
                <label htmlFor="alloc-category" className="block text-sm font-medium text-slate-700 mb-1">
                  Category
                </label>
                <input
                  id="alloc-category"
                  type="text"
                  value={allocForm.category}
                  onChange={(e) => setAllocForm((p) => ({ ...p, category: e.target.value }))}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                  placeholder="e.g. Foundation, Structures, Finishes"
                />
              </div>
              <div>
                <label htmlFor="alloc-purpose" className="block text-sm font-medium text-slate-700 mb-1">
                  Purpose *
                </label>
                <input
                  id="alloc-purpose"
                  type="text"
                  value={allocForm.purpose}
                  onChange={(e) => setAllocForm((p) => ({ ...p, purpose: e.target.value }))}
                  className={`w-full rounded-lg border ${allocErrors.purpose ? 'border-red-300' : 'border-slate-300'} bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20`}
                  placeholder="What these funds will be used for"
                />
                {allocErrors.purpose && <p className="mt-1 text-sm text-red-600">{allocErrors.purpose}</p>}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="alloc-person" className="block text-sm font-medium text-slate-700 mb-1">
                    Responsible person
                  </label>
                  <input
                    id="alloc-person"
                    type="text"
                    value={allocForm.responsible_person}
                    onChange={(e) => setAllocForm((p) => ({ ...p, responsible_person: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                  />
                </div>
                <div>
                  <label htmlFor="alloc-date" className="block text-sm font-medium text-slate-700 mb-1">
                    Date
                  </label>
                  <input
                    id="alloc-date"
                    type="date"
                    value={allocForm.allocation_date}
                    onChange={(e) => setAllocForm((p) => ({ ...p, allocation_date: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="alloc-notes" className="block text-sm font-medium text-slate-700 mb-1">
                  Notes
                </label>
                <textarea
                  id="alloc-notes"
                  rows={2}
                  value={allocForm.notes}
                  onChange={(e) => setAllocForm((p) => ({ ...p, notes: e.target.value }))}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-800/20"
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeAllocation}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={allocSaving}
                  className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {allocSaving ? 'Saving...' : 'Allocate Funds'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}