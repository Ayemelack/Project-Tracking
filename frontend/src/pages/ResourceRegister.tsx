import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { Resource } from '../types';
import { formatNumber, formatMoney, toNumber } from '../utils/format';

const quantityCell = (value: string, unit: string | null) => (
  <span>{formatNumber(value)}{unit ? ` ${unit}` : ''}</span>
);

export default function ResourceRegister() {
  const { canWrite } = useAuth();
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listResources()
      .then((data) => setResources(data.resources))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const totalPurchaseCost = resources.reduce(
    (sum, r) => sum + (toNumber(r.total_purchase_cost) ?? 0),
    0
  );
  const totalBudgetedCost = resources.reduce(
    (sum, r) => sum + (toNumber(r.budgeted_cost) ?? 0),
    0
  );
  const pendingCount = resources.filter((r) => (toNumber(r.pending_delivery_quantity) ?? 0) > 0).length;

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Resource Register</h1>
            <p className="mt-1 text-slate-500">
              Materials and resources — purchased, delivered, used, and remaining
            </p>
          </div>
          {canWrite && (
            <Link
              to="/resources/new"
              className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
            >
              Add Resource
            </Link>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-slate-500">Loading resources...</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Resources</div>
              <div className="mt-2 text-xl font-bold text-slate-900">
                {formatNumber(resources.length)}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Pending deliveries</div>
              <div className="mt-2 text-xl font-bold text-amber-600">
                {formatNumber(pendingCount)}
              </div>
              <div className="mt-1 text-sm text-slate-500">resources awaiting delivery</div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Actual purchase cost</div>
              <div className="mt-2 text-xl font-bold text-emerald-600">
                {formatMoney(totalPurchaseCost)}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Budgeted cost</div>
              <div className="mt-2 text-xl font-bold text-slate-900">
                {formatMoney(totalBudgetedCost)}
              </div>
            </div>
          </div>

          {resources.length === 0 ? (
            <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-slate-900">No resources registered yet</h3>
              <p className="mt-1 text-slate-500">
                Register the first material or resource to start tracking purchases, deliveries and usage.
              </p>
              {canWrite && (
                <Link
                  to="/resources/new"
                  className="mt-4 inline-flex items-center px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
                >
                  Add Resource
                </Link>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Resource</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Category</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Budgeted</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Purchased</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Delivered</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Used</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Remaining</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Pending delivery</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Purchase cost</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {resources.map((resource) => {
                      const remaining = toNumber(resource.remaining_quantity) ?? 0;
                      return (
                        <tr key={resource.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-6 py-4">
                            <div className="font-medium text-slate-900">{resource.name}</div>
                            {resource.estimate_title && (
                              <div className="text-sm text-slate-500">{resource.estimate_title}</div>
                            )}
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-600">{resource.category || '—'}</td>
                          <td className="px-6 py-4 text-sm text-slate-600 text-right">
                            {resource.budgeted_quantity ? quantityCell(resource.budgeted_quantity, resource.unit) : '—'}
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-600 text-right">
                            {quantityCell(resource.purchased_quantity, resource.unit)}
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-600 text-right">
                            {quantityCell(resource.delivered_quantity, resource.unit)}
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-600 text-right">
                            {quantityCell(resource.used_quantity, resource.unit)}
                          </td>
                          <td className={`px-6 py-4 text-sm text-right font-medium ${remaining < 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                            {quantityCell(resource.remaining_quantity, resource.unit)}
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-600 text-right">
                            {quantityCell(resource.pending_delivery_quantity, resource.unit)}
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-900 text-right">
                            {formatMoney(resource.total_purchase_cost, resource.currency)}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <Link
                              to={`/resources/${resource.id}`}
                              className="text-blue-800 hover:text-blue-600 text-sm font-medium"
                            >
                              View
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}