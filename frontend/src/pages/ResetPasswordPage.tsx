import { useCallback, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';

const MIN_PASSWORD_LENGTH = 8;

type ResetFields = {
  newPassword: string;
  confirmPassword: string;
};
type ResetTouched = Record<keyof ResetFields, boolean>;

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const { user, loading } = useAuth();

  const [fields, setFields] = useState<ResetFields>({
    newPassword: '',
    confirmPassword: '',
  });
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [touched, setTouched] = useState<ResetTouched>({
    newPassword: false,
    confirmPassword: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState(false);

  const markTouched = useCallback((field: keyof ResetTouched) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  }, []);

  const newPasswordError =
    touched.newPassword && !fields.newPassword
      ? 'Please enter a new password.'
      : touched.newPassword && fields.newPassword.length < MIN_PASSWORD_LENGTH
        ? `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`
        : null;
  const confirmPasswordError =
    touched.confirmPassword &&
    (!fields.confirmPassword
      ? 'Please confirm your new password.'
      : fields.confirmPassword !== fields.newPassword
        ? 'Passwords do not match.'
        : null);
  const canSubmit =
    fields.newPassword.length >= MIN_PASSWORD_LENGTH &&
    !!fields.confirmPassword &&
    fields.confirmPassword === fields.newPassword &&
    !submitting;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setTouched({ newPassword: true, confirmPassword: true });
    if (!canSubmit) {
      return;
    }
    setSubmitting(true);
    try {
      await api.resetPassword({
        new_password: fields.newPassword,
        confirm_password: fields.confirmPassword,
      });
      setResetSuccess(true);
      window.setTimeout(() => navigate('/login', { replace: true }), 1600);
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
        ?.data?.detail;
      if (status === 401) {
        setError('Your session has expired. Please sign in and try again.');
      } else if (status === 429) {
        setError('Too many attempts. Please try again later.');
      } else if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('We could not reset your password right now. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-8 pt-10 pb-8 text-center">
            <div className="w-16 h-16 mx-auto rounded-xl bg-blue-800 flex items-center justify-center mb-5 shadow-sm">
              <span className="text-white font-bold text-xl tracking-tight">PT</span>
            </div>

            {loading ? null : !user ? (
              <>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                  Reset your password
                </h1>
                <p className="text-sm text-slate-500 mt-3 leading-relaxed">
                  Please sign in first. For security, the password reset for your
                  account requires a verified session.
                </p>

                <button
                  type="button"
                  onClick={() => navigate('/login')}
                  className="w-full mt-8 inline-flex items-center justify-center rounded-lg bg-blue-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 transition-colors"
                >
                  Go to Sign in
                </button>
              </>
            ) : (
              <>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                  Create New Password
                </h1>
                <p className="text-sm text-slate-500 mt-1.5">
                  Set a new password for your account.
                </p>

                {resetSuccess ? (
                  <>
                    <div className="w-14 h-14 mx-auto rounded-full bg-green-50 border border-green-200 flex items-center justify-center mt-8">
                      <svg className="w-7 h-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <p className="text-sm text-green-700 mt-4 font-semibold">
                      Password has been reset successfully.
                    </p>
                    <p className="text-sm text-slate-500 mt-1">
                      Redirecting to Sign in...
                    </p>
                  </>
                ) : (
                  <form
                    onSubmit={handleSubmit}
                    noValidate
                    className="mt-8 space-y-5 text-left"
                  >
                    <div>
                      <label
                        htmlFor="resetNewPassword"
                        className="block text-sm font-medium text-slate-700 mb-1.5"
                      >
                        Create New Password
                      </label>
                      <div className="relative">
                        <input
                          id="resetNewPassword"
                          type={showNewPassword ? 'text' : 'password'}
                          autoComplete="new-password"
                          value={fields.newPassword}
                          onChange={(e) => {
                            setFields((prev) => ({
                              ...prev,
                              newPassword: e.target.value,
                            }));
                            if (error) setError(null);
                          }}
                          onBlur={() => markTouched('newPassword')}
                          disabled={submitting}
                          aria-invalid={!!newPasswordError}
                          aria-describedby={
                            newPasswordError ? 'resetNewPassword-error' : undefined
                          }
                          className={`w-full rounded-lg border px-3.5 py-2.5 pr-10 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 disabled:opacity-50 disabled:cursor-not-allowed ${
                            newPasswordError
                              ? 'border-red-300 bg-red-50'
                              : 'border-slate-300 bg-white'
                          }`}
                        />
                        <button
                          type="button"
                          tabIndex={-1}
                          onClick={() => setShowNewPassword((v) => !v)}
                          aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                          className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 transition-colors"
                        >
                          {showNewPassword ? (
                            <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                            </svg>
                          ) : (
                            <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                          )}
                        </button>
                      </div>
                      {newPasswordError && (
                        <p
                          id="resetNewPassword-error"
                          className="mt-1.5 text-xs text-red-600"
                          role="alert"
                        >
                          {newPasswordError}
                        </p>
                      )}
                      {!newPasswordError && (
                        <p className="mt-1.5 text-xs text-slate-400">
                          Use at least {MIN_PASSWORD_LENGTH} characters.
                        </p>
                      )}
                    </div>

                    <div>
                      <label
                        htmlFor="resetConfirmPassword"
                        className="block text-sm font-medium text-slate-700 mb-1.5"
                      >
                        Confirm Password
                      </label>
                      <div className="relative">
                        <input
                          id="resetConfirmPassword"
                          type={showConfirmPassword ? 'text' : 'password'}
                          autoComplete="new-password"
                          value={fields.confirmPassword}
                          onChange={(e) => {
                            setFields((prev) => ({
                              ...prev,
                              confirmPassword: e.target.value,
                            }));
                            if (error) setError(null);
                          }}
                          onBlur={() => markTouched('confirmPassword')}
                          disabled={submitting}
                          aria-invalid={!!confirmPasswordError}
                          aria-describedby={
                            confirmPasswordError ? 'resetConfirmPassword-error' : undefined
                          }
                          className={`w-full rounded-lg border px-3.5 py-2.5 pr-10 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 disabled:opacity-50 disabled:cursor-not-allowed ${
                            confirmPasswordError
                              ? 'border-red-300 bg-red-50'
                              : 'border-slate-300 bg-white'
                          }`}
                        />
                        <button
                          type="button"
                          tabIndex={-1}
                          onClick={() => setShowConfirmPassword((v) => !v)}
                          aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                          className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 transition-colors"
                        >
                          {showConfirmPassword ? (
                            <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                            </svg>
                          ) : (
                            <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                          )}
                        </button>
                      </div>
                      {confirmPasswordError && (
                        <p
                          id="resetConfirmPassword-error"
                          className="mt-1.5 text-xs text-red-600"
                          role="alert"
                        >
                          {confirmPasswordError}
                        </p>
                      )}
                    </div>

                    {error && (
                      <div
                        className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 flex items-start gap-2.5"
                        role="alert"
                      >
                        <svg className="w-4 h-4 mt-0.5 shrink-0 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                        </svg>
                        <span>{error}</span>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={!canSubmit}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {submitting && (
                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      )}
                      {submitting ? 'Resetting...' : 'Reset Password'}
                    </button>
                  </form>
                )}
              </>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          Project Tracking System
        </p>
      </div>
    </div>
  );
}