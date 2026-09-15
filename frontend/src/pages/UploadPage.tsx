import { useState, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';

type UploadStatus = 'idle' | 'selected' | 'uploading' | 'processing' | 'success' | 'error';

export default function UploadPage() {
  const navigate = useNavigate();
  const { canWrite } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [message, setMessage] = useState('');
  const [estimateId, setEstimateId] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = useCallback((f: File) => {
    if (f.type !== 'application/pdf') {
      setStatus('error');
      setMessage('Only PDF files are accepted.');
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setStatus('error');
      setMessage('File too large. Maximum size is 50MB.');
      return;
    }
    setFile(f);
    setStatus('selected');
    setMessage('');
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const onDragLeave = useCallback(() => setDragActive(false), []);

  const onFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleUpload = async () => {
    if (!file) return;
    setStatus('uploading');
    setMessage('Uploading document...');

    try {
      setStatus('processing');
      setMessage('Processing PDF and extracting estimate data...');
      const result = await api.uploadEstimate(file);
      setEstimateId(result.id);
      setStatus('success');
      setMessage(result.message);
    } catch (e: unknown) {
      setStatus('error');
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setMessage(err.response?.data?.detail || err.message || 'Upload failed');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (!canWrite) {
    return (
      <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        Your access is read-only. To upload an estimate, ask a project member or administrator.
        <Link to="/estimates" className="font-medium text-amber-900 underline ml-1">
          Back to Estimate Register
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Upload Estimate</h1>
        <p className="mt-1 text-slate-500">
          Upload a PDF estimate document to extract and structure the data
        </p>
      </div>

      <div className="max-w-2xl">
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={() => status === 'idle' && fileInputRef.current?.click()}
          className={`rounded-xl border-2 border-dashed p-12 text-center transition-all cursor-pointer ${
            dragActive
              ? 'border-blue-500 bg-blue-50'
              : status === 'error'
              ? 'border-red-300 bg-red-50'
              : 'border-slate-300 bg-white hover:border-slate-400 hover:bg-slate-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={onFileInput}
            className="hidden"
          />

          {status === 'idle' && (
            <>
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
              </div>
              <p className="text-lg font-medium text-slate-700">
                Drop a PDF estimate here or click to browse
              </p>
              <p className="mt-2 text-sm text-slate-500">
                Supports PDF files up to 50MB
              </p>
            </>
          )}

          {file && status !== 'idle' && (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto rounded-full bg-blue-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-slate-700">{file.name}</p>
                <p className="text-sm text-slate-500">
                  {formatSize(file.size)} &middot; PDF
                </p>
              </div>

              {status === 'uploading' || status === 'processing' ? (
                <div className="space-y-2">
                  <div className="w-full bg-slate-200 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full animate-pulse w-2/3" />
                  </div>
                  <p className="text-sm text-slate-600">{message}</p>
                </div>
              ) : status === 'success' ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-2 text-emerald-600">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="font-medium">{message}</span>
                  </div>
                  <div className="flex gap-3 justify-center">
                    <button
                      onClick={() => estimateId && navigate(`/estimates/${estimateId}`)}
                      className="px-4 py-2 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
                    >
                      Review Estimate
                    </button>
                    <button
                      onClick={() => { setFile(null); setStatus('idle'); setMessage(''); }}
                      className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
                    >
                      Upload Another
                    </button>
                  </div>
                </div>
              ) : status === 'error' ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-2 text-red-600">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    <span className="text-sm">{message}</span>
                  </div>
                  <button
                    onClick={() => { setFile(null); setStatus('idle'); setMessage(''); }}
                    className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {status === 'selected' && (
          <div className="mt-6 flex justify-center">
            <button
              onClick={handleUpload}
              className="px-6 py-3 bg-blue-800 text-white rounded-lg text-sm font-medium hover:bg-blue-900 transition-colors"
            >
              Upload & Process
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
