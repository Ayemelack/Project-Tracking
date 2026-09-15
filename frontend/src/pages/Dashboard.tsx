import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import type { EstimateListResponse } from '../types';

export default function Dashboard() {
  const { canWrite } = useAuth();
  const [data, setData] = useState<EstimateListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listEstimates()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-w-0 overflow-x-clip">
      <div className="mb-6 sm:mb-8">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm sm:text-base text-slate-500">
          Project cost and resource tracking system
        </p>
      </div>

      <div className="grid grid-cols-1 min-[400px]:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8">
        <div className="bg-white rounded-lg border border-slate-200 p-5 sm:p-6">
          <div className="text-xs sm:text-sm font-medium text-slate-500">Total Estimates</div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-slate-900">
            {loading ? '—' : data?.total ?? 0}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5 sm:p-6">
          <div className="text-xs sm:text-sm font-medium text-slate-500">Confirmed</div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-emerald-600">
            {loading ? '—' : data?.estimates.filter(e => e.status === 'confirmed').length ?? 0}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-5 sm:p-6">
          <div className="text-xs sm:text-sm font-medium text-slate-500">Pending Review</div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-amber-600">
            {loading ? '—' : data?.estimates.filter(e => e.status === 'extracted').length ?? 0}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 text-sm break-words">{error}</p>
        </div>
      )}

      <div className="bg-white rounded-lg border border-slate-200 p-5 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base sm:text-lg font-semibold text-slate-900">Quick Actions</h2>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
          {canWrite && (
            <Link
              to="/upload"
              className="inline-flex items-center justify-center w-full sm:w-auto px-4 py-2.5 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
            >
              Upload New Estimate
            </Link>
          )}
          <Link
            to="/estimates"
            className="inline-flex items-center justify-center w-full sm:w-auto px-4 py-2.5 bg-white border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
          >
            View Estimate Register
          </Link>
        </div>
      </div>
    </div>
  );
}
