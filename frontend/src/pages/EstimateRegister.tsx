import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { Estimate } from '../types';

export default function EstimateRegister() {
  const { canWrite, isAdmin } = useAuth();
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    api.listEstimates()
      .then((data) => setEstimates(data.estimates))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id: string, title: string) => {
    if (!window.confirm(`Delete estimate "${title}" and all its line items?\n\nThis cannot be undone.`)) return;
    setDeletingId(id);
    try {
      await api.deleteEstimate(id);
      setEstimates((prev) => prev.filter((e) => e.id !== id));
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err.message || 'Failed to delete estimate');
    } finally {
      setDeletingId(null);
    }
  };

  const formatCurrency = (amount: number | null, currency: string) => {
    if (amount === null || amount === undefined) return '—';
    return `${currency} ${amount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      extracted: 'bg-amber-100 text-amber-800 border-amber-200',
      confirmed: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      rejected: 'bg-red-100 text-red-800 border-red-200',
    };
    return styles[status] || 'bg-slate-100 text-slate-800 border-slate-200';
  };

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Estimate Register</h1>
            <p className="mt-1 text-slate-500">
              All uploaded and confirmed estimates
            </p>
          </div>
          {canWrite && (
            <Link
              to="/upload"
              className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
            >
              Upload New
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
          <p className="mt-4 text-slate-500">Loading estimates...</p>
        </div>
      ) : estimates.length === 0 ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-slate-900">No estimates yet</h3>
          <p className="mt-1 text-slate-500">
            Upload your first estimate document to get started.
          </p>
          {canWrite && (
            <Link
              to="/upload"
              className="mt-4 inline-flex items-center px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
            >
              Upload Estimate
            </Link>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Estimate
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Source Document
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Total
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {estimates.map((est) => (
                <tr key={est.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-slate-900">{est.title}</div>
                    {est.contractor && (
                      <div className="text-sm text-slate-500">{est.contractor}</div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-slate-600 max-w-[200px] truncate">
                      {est.original_filename}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusBadge(est.status)}`}>
                      {est.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm font-medium text-slate-900">
                    {formatCurrency(est.total_estimated_amount, est.currency)}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-500">
                    {formatDate(est.created_at)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-4">
                      <Link
                        to={`/estimates/${est.id}`}
                        className="text-blue-800 hover:text-blue-600 text-sm font-medium"
                      >
                        View
                      </Link>
                      {isAdmin && (
                        <button
                          onClick={() => handleDelete(est.id, est.title)}
                          disabled={deletingId === est.id}
                          className="text-sm font-medium text-red-600 hover:text-red-800 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {deletingId === est.id ? 'Deleting...' : 'Delete'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
