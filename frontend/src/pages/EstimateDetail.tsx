import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { EstimateDetail as EstimateDetailType, EstimateLineItem } from '../types';

export default function EstimateDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { canWrite, isAdmin } = useAuth();
  const [estimate, setEstimate] = useState<EstimateDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Partial<EstimateLineItem>>({});
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.getEstimate(id)
      .then(setEstimate)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const formatCurrency = (amount: number | null) => {
    if (amount === null || amount === undefined) return '—';
    return amount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  };

  const startEdit = (item: EstimateLineItem) => {
    setEditingItem(item.id);
    setEditValues({
      description: item.description,
      quantity: item.quantity,
      unit: item.unit,
      unit_cost: item.unit_cost,
      total_cost: item.total_cost,
      category: item.category,
    });
  };

  const saveEdit = async (itemId: string) => {
    if (!id) return;
    try {
      await api.updateLineItem(id, itemId, editValues);
      const updated = await api.getEstimate(id);
      setEstimate(updated);
      setEditingItem(null);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err.message || 'Failed to update');
    }
  };

  const handleConfirm = async () => {
    if (!id) return;
    setConfirming(true);
    try {
      const result = await api.confirmEstimate(id);
      setEstimate((prev) => prev ? { ...prev, status: result.status } : prev);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err.message || 'Failed to confirm');
    } finally {
      setConfirming(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !confirm('Delete this estimate permanently?')) return;
    try {
      await api.deleteEstimate(id);
      navigate('/estimates');
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err.message || 'Failed to delete');
    }
  };

  const handleDeleteItem = async (itemId: string) => {
    if (!id || !confirm('Delete this line item?')) return;
    try {
      await api.deleteLineItem(id, itemId);
      const updated = await api.getEstimate(id);
      setEstimate(updated);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err.message || 'Failed to delete item');
    }
  };

  const regularItems = estimate?.line_items.filter(
    (i) => i.section_total_type !== 'section_total' && i.section_total_type !== 'grand_total'
  ) || [];

  const sectionTotals = estimate?.line_items.filter(
    (i) => i.section_total_type === 'section_total'
  ) || [];

  const grandTotal = estimate?.line_items.find(
    (i) => i.section_total_type === 'grand_total'
  );

  const categories = [...new Set(regularItems.map((i) => i.category).filter(Boolean))];

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="mt-4 text-slate-500">Loading estimate...</p>
      </div>
    );
  }

  if (!estimate) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
        <p className="text-slate-500">Estimate not found.</p>
      </div>
    );
  }

  return (
    <div>
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      <div className="mb-6">
        <button
          onClick={() => navigate('/estimates')}
          className="text-sm text-slate-500 hover:text-slate-700 mb-2"
        >
          &larr; Back to Register
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{estimate.title}</h1>
            {estimate.contractor && (
              <p className="mt-1 text-slate-500">{estimate.contractor}</p>
            )}
          </div>
          <div className="flex gap-3">
            {isAdmin && estimate.status === 'extracted' && (
              <button
                onClick={handleConfirm}
                disabled={confirming}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50"
              >
                {confirming ? 'Confirming...' : 'Confirm Estimate'}
              </button>
            )}
            {isAdmin && (
              <button
                onClick={handleDelete}
                className="px-4 py-2 border border-red-300 text-red-700 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
              >
                Delete
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase">Status</div>
          <div className="mt-1">
            <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${
              estimate.status === 'confirmed' ? 'bg-emerald-100 text-emerald-800 border-emerald-200' :
              estimate.status === 'extracted' ? 'bg-amber-100 text-amber-800 border-amber-200' :
              'bg-slate-100 text-slate-800 border-slate-200'
            }`}>
              {estimate.status}
            </span>
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase">Total</div>
          <div className="mt-1 text-lg font-bold text-slate-900">
            {estimate.currency} {formatCurrency(estimate.total_estimated_amount)}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase">Source</div>
          <div className="mt-1 text-sm text-slate-700 truncate">{estimate.original_filename}</div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs font-medium text-slate-500 uppercase">Created</div>
          <div className="mt-1 text-sm text-slate-700">
            {new Date(estimate.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>

      {categories.map((category) => {
        const items = regularItems.filter((i) => i.category === category);
        if (items.length === 0) return null;

        return (
          <div key={category} className="mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-3">{category}</h2>
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase w-12">No</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Description</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase w-20">Qty</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase w-20">Unit</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase w-28">Unit Cost</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase w-28">Total</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase w-24">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 text-sm text-slate-500">{item.item_number || '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-900">
                        {editingItem === item.id ? (
                          <input
                            value={editValues.description || ''}
                            onChange={(e) => setEditValues({ ...editValues, description: e.target.value })}
                            className="w-full px-2 py-1 border border-slate-300 rounded text-sm"
                          />
                        ) : (
                          item.description
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-right">
                        {editingItem === item.id ? (
                          <input
                            type="number"
                            value={editValues.quantity ?? ''}
                            onChange={(e) => setEditValues({ ...editValues, quantity: parseFloat(e.target.value) || null })}
                            className="w-20 px-2 py-1 border border-slate-300 rounded text-sm text-right"
                          />
                        ) : (
                          <span className="text-slate-700">{item.quantity ?? '—'}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-right">
                        {editingItem === item.id ? (
                          <input
                            value={editValues.unit || ''}
                            onChange={(e) => setEditValues({ ...editValues, unit: e.target.value })}
                            className="w-16 px-2 py-1 border border-slate-300 rounded text-sm text-right"
                          />
                        ) : (
                          <span className="text-slate-700">{item.unit || '—'}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-right">
                        {editingItem === item.id ? (
                          <input
                            type="number"
                            value={editValues.unit_cost ?? ''}
                            onChange={(e) => setEditValues({ ...editValues, unit_cost: parseFloat(e.target.value) || null })}
                            className="w-24 px-2 py-1 border border-slate-300 rounded text-sm text-right"
                          />
                        ) : (
                          <span className="text-slate-700">{formatCurrency(item.unit_cost)}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-medium text-slate-900">
                        {editingItem === item.id ? (
                          <input
                            type="number"
                            value={editValues.total_cost ?? ''}
                            onChange={(e) => setEditValues({ ...editValues, total_cost: parseFloat(e.target.value) || null })}
                            className="w-28 px-2 py-1 border border-slate-300 rounded text-sm text-right"
                          />
                        ) : (
                          formatCurrency(item.total_cost)
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-sm">
                        {editingItem === item.id ? (
                          <div className="flex gap-2 justify-end">
                            <button
                              onClick={() => saveEdit(item.id)}
                              className="text-emerald-600 hover:text-emerald-800 font-medium"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingItem(null)}
                              className="text-slate-500 hover:text-slate-700"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex gap-2 justify-end">
                            {canWrite && (
                              <button
                                onClick={() => startEdit(item)}
                                className="text-blue-600 hover:text-blue-800"
                              >
                                Edit
                              </button>
                            )}
                            {isAdmin && (
                              <button
                                onClick={() => handleDeleteItem(item.id)}
                                className="text-red-600 hover:text-red-800"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}

      {sectionTotals.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-slate-900 mb-3">Section Totals</h2>
          <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Section</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase w-36">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sectionTotals.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm text-slate-900">{item.description}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium text-slate-900">
                      {estimate.currency} {formatCurrency(item.total_cost)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {grandTotal && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold text-blue-900">Grand Total</span>
            <span className="text-2xl font-bold text-blue-900">
              {estimate.currency} {formatCurrency(grandTotal.total_cost)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
