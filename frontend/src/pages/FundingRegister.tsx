import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { FundReceiptSummaryItem, FundingSummary } from '../types';
import { formatDate, formatMoney, formatNumber } from '../utils/format';

export default function FundingRegister() {
  const { canWrite } = useAuth();
  const [receipts, setReceipts] = useState<FundReceiptSummaryItem[]>([]);
  const [summary, setSummary] = useState<FundingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listFunds()
      .then((data) => {
        setReceipts(data.receipts);
        setSummary(data.summary);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const statusBadge = (status: string) => ({
    recorded: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  }[status] || 'bg-slate-100 text-slate-800 border-slate-200');

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Funding Register</h1>
            <p className="mt-1 text-slate-500">
              Money provided to the project and how it has been allocated
            </p>
          </div>
          {canWrite && (
            <Link
              to="/funding/new"
              className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
            >
              Add Funding
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
          <p className="mt-4 text-slate-500">Loading funding records...</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Approved Estimate</div>
              <div className="mt-2 text-xl font-bold text-slate-900">
                {formatMoney(summary?.approved_estimated_amount)}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Total Received</div>
              <div className="mt-2 text-xl font-bold text-emerald-600">
                {formatMoney(summary?.total_received)}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Total Allocated</div>
              <div className="mt-2 text-xl font-bold text-blue-800">
                {formatMoney(summary?.total_allocated)}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Unallocated</div>
              <div className="mt-2 text-xl font-bold text-amber-600">
                {formatMoney(summary?.total_unallocated)}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Funding Coverage</div>
              <div className="mt-2 text-xl font-bold text-slate-900">
                {summary?.funding_coverage_percentage == null
                  ? '—'
                  : `${formatNumber(summary.funding_coverage_percentage)}%`}
              </div>
            </div>
          </div>

          {receipts.length === 0 ? (
            <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-slate-900">No funding recorded yet</h3>
              <p className="mt-1 text-slate-500">
                Record the first money received by the project to get started.
              </p>
              {canWrite && (
                <Link
                  to="/funding/new"
                  className="mt-4 inline-flex items-center px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
                >
                  Record Funding
                </Link>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Source</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Received</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Allocated</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Unallocated</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Reference</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {receipts.map((receipt) => (
                    <tr key={receipt.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {formatDate(receipt.received_date)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-medium text-slate-900">{receipt.source}</div>
                        {receipt.purpose && (
                          <div className="text-sm text-slate-500 max-w-[240px] truncate">{receipt.purpose}</div>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-slate-900 text-right">
                        {formatMoney(receipt.amount, receipt.currency)}
                      </td>
                      <td className="px-6 py-4 text-sm text-blue-800 text-right">
                        {formatMoney(receipt.allocated_amount, receipt.currency)}
                      </td>
                      <td className="px-6 py-4 text-sm text-amber-600 text-right">
                        {formatMoney(receipt.unallocated_amount, receipt.currency)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusBadge(receipt.status)}`}>
                          {receipt.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">{receipt.reference || '—'}</td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          to={`/funding/${receipt.id}`}
                          className="text-blue-800 hover:text-blue-600 text-sm font-medium"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}