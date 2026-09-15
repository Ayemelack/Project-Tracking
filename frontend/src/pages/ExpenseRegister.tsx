import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { Expense, ExpenseSummary } from '../types';
import { formatDate, formatMoney, formatNumber } from '../utils/format';

const statusBadge = (status: string) =>
  ({
    recorded: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    reversed: 'bg-slate-100 text-slate-600 border-slate-200',
  }[status] || 'bg-slate-100 text-slate-800 border-slate-200');

const budgetStatusBadge = (status: string) => {
  if (status === 'OVER ESTIMATE') return 'bg-red-50 text-red-700 border-red-200';
  if (status === 'ON BUDGET') return 'bg-emerald-100 text-emerald-800 border-emerald-200';
  return 'bg-blue-50 text-blue-700 border-blue-200';
};

const paymentMethodLabel = (method: string | null) =>
  ({
    CASH: 'Cash',
    BANK_TRANSFER: 'Bank Transfer',
    CHEQUE: 'Cheque',
    MOBILE_MONEY: 'Mobile Money',
    CARD: 'Card',
    OTHER: 'Other',
  }[method || ''] || method || '—');

export default function ExpenseRegister() {
  const { canWrite } = useAuth();
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [summary, setSummary] = useState<ExpenseSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listExpenses()
      .then((data) => {
        setExpenses(data.expenses);
        setSummary(data.summary);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Expense Register</h1>
            <p className="mt-1 text-slate-500">
              Purchases and payments made against the project
            </p>
          </div>
          {canWrite && (
            <Link
              to="/expenses/new"
              className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
            >
              Add Expense
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
          <p className="mt-4 text-slate-500">Loading expense records...</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Total Spent</div>
              <div className="mt-2 text-xl font-bold text-emerald-600">
                {formatMoney(summary?.total_expenses)}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Authorized Excess</div>
              <div className="mt-2 text-xl font-bold text-amber-600">
                {formatMoney(summary?.total_authorized_excess)}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-slate-200 p-5">
              <div className="text-xs font-medium text-slate-500 uppercase">Expense Records</div>
              <div className="mt-2 text-xl font-bold text-slate-900">
                {formatNumber(expenses.length)}
              </div>
            </div>
          </div>

          {summary && summary.budget_comparison.length > 0 && (
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden mb-8">
              <div className="px-6 py-4 border-b border-slate-200">
                <h2 className="text-lg font-semibold text-slate-900">Budget Status by Estimate</h2>
              </div>
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Estimate</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Estimated</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actual</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Variance</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {summary.budget_comparison.map((item) => (
                    <tr key={item.estimate_id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 text-sm font-medium text-slate-900">{item.estimate_title}</td>
                      <td className="px-6 py-4 text-sm text-slate-600 text-right">
                        {formatMoney(item.estimated_amount, item.currency)}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-900 text-right">
                        {formatMoney(item.actual_expenditure, item.currency)}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600 text-right">
                        {formatMoney(item.variance_amount, item.currency)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${budgetStatusBadge(item.status)}`}>
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {summary && summary.allocation_breakdown.length > 0 && (
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden mb-8">
              <div className="px-6 py-4 border-b border-slate-200">
                <h2 className="text-lg font-semibold text-slate-900">Allocation Spending</h2>
              </div>
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Purpose</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Category</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Estimate</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Allocated</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Spent</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Remaining</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {summary.allocation_breakdown.map((item) => (
                    <tr key={item.allocation_id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 text-sm font-medium text-slate-900">{item.allocation_purpose || '—'}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">{item.allocation_category || '—'}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">{item.estimate_title || '—'}</td>
                      <td className="px-6 py-4 text-sm text-slate-900 text-right">
                        {formatMoney(item.allocated_amount, item.currency)}
                      </td>
                      <td className="px-6 py-4 text-sm text-blue-800 text-right">
                        {formatMoney(item.spent_amount, item.currency)}
                      </td>
                      <td className={`px-6 py-4 text-sm text-right ${Number(item.remaining_amount) < 0 ? 'text-red-600 font-medium' : 'text-amber-600'}`}>
                        {formatMoney(item.remaining_amount, item.currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {expenses.length === 0 ? (
            <div className="bg-white rounded-lg border border-slate-200 p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-slate-900">No expenses recorded yet</h3>
              <p className="mt-1 text-slate-500">
                Record the first purchase or payment made by the project to get started.
              </p>
              {canWrite && (
                <Link
                  to="/expenses/new"
                  className="mt-4 inline-flex items-center px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
                >
                  Record Expense
                </Link>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Description</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Category</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Payment</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Reference</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {expenses.map((expense) => (
                    <tr key={expense.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 text-sm text-slate-600">{formatDate(expense.expense_date)}</td>
                      <td className="px-6 py-4">
                        <div className="font-medium text-slate-900">{expense.description}</div>
                        {expense.supplier && (
                          <div className="text-sm text-slate-500">{expense.supplier}</div>
                        )}
                        {expense.quantity && expense.unit_price ? (
                          <div className="text-xs text-slate-400">
                            {formatNumber(expense.quantity)} {expense.unit || 'units'} × {formatMoney(expense.unit_price)}
                          </div>
                        ) : null}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">{expense.category || '—'}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">{paymentMethodLabel(expense.payment_method)}</td>
                      <td className="px-6 py-4 text-sm font-medium text-slate-900 text-right">
                        {formatMoney(expense.amount, expense.currency)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusBadge(expense.status)}`}>
                          {expense.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">{expense.reference || '—'}</td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          to={`/expenses/${expense.id}`}
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