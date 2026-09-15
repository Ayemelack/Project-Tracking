import { useCallback, useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../auth/AuthContext';

type Mode = 'welcome' | 'signin' | 'register' | 'success';

type SignInTouched = { username: boolean; password: boolean };
type RegisterFields = {
  fullName: string;
  username: string;
  password: string;
  confirmPassword: string;
  adminKey: string;
};
type RegisterTouched = Record<keyof RegisterFields, boolean>;

const MIN_PASSWORD_LENGTH = 8;
const USERNAME_SEPARATORS = '._-';

const isAsciiAlnum = (ch: string): boolean =>
  (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9');

const isValidEmail = (value: string): boolean => {
  let atCount = 0;
  for (const ch of value) if (ch === '@') atCount += 1;
  if (atCount !== 1) return false;
  const atIndex = value.indexOf('@');
  const local = value.slice(0, atIndex);
  const domain = value.slice(atIndex + 1);
  if (!local || !domain) return false;
  if (local[0] === '.' || local[local.length - 1] === '.') return false;
  if (local.includes('..') || domain.includes('..')) return false;
  for (const ch of local) {
    if (!isAsciiAlnum(ch) && !'._-'.includes(ch)) return false;
  }
  const labels = domain.split('.');
  if (labels.length < 2) return false;
  for (const label of labels) {
    if (!label || label.length > 63) return false;
    if (label[0] === '-' || label[label.length - 1] === '-') return false;
    for (const ch of label) {
      if (!isAsciiAlnum(ch) && ch !== '-') return false;
    }
  }
  return true;
};

const isValidIdentifier = (value: string): boolean => {
  const trimmed = value.trim();
  if (!trimmed) return false;
  if (trimmed.length < 2 || trimmed.length > 100) return false;
  if (/\s/.test(trimmed)) return false;
  if (trimmed.includes('@')) return isValidEmail(trimmed);
  if (!/[\p{L}\p{N}]/u.test(trimmed)) return false;
  const sep = USERNAME_SEPARATORS;
  if (sep.includes(trimmed[0]) || sep.includes(trimmed[trimmed.length - 1])) return false;
  for (let i = 0; i < trimmed.length - 1; i += 1) {
    if (sep.includes(trimmed[i]) && sep.includes(trimmed[i + 1])) return false;
  }
  return [...trimmed].every(
    (ch) => /[\p{L}\p{N}]/u.test(ch) || sep.includes(ch),
  );
};

const isValidFullName = (name: string): boolean => {
  const trimmed = name.trim();
  if (!trimmed) return false;
  const validChars = /^[\p{L}\p{M}'’\- .]+$/u.test(trimmed);
  const hasLetter = /[\p{L}]/u.test(trimmed);
  return validChars && hasLetter;
};

const initialRegisterFields: RegisterFields = {
  fullName: '',
  username: '',
  password: '',
  confirmPassword: '',
  adminKey: '',
};

const zeroRegisterTouched: RegisterTouched = {
  fullName: false,
  username: false,
  password: false,
  confirmPassword: false,
  adminKey: false,
};

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/';

  const [mode, setMode] = useState<Mode>('welcome');

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);
  const [signInSubmitting, setSignInSubmitting] = useState(false);
  const [signInTouched, setSignInTouched] = useState<SignInTouched>({
    username: false,
    password: false,
  });

  const [fields, setFields] = useState<RegisterFields>(initialRegisterFields);
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showRegConfirm, setShowRegConfirm] = useState(false);
  const [showAdminKey, setShowAdminKey] = useState(false);
  const [registerTouched, setRegisterTouched] =
    useState<RegisterTouched>(zeroRegisterTouched);
  const [registerSubmitting, setRegisterSubmitting] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [registeredUsername, setRegisteredUsername] = useState('');

  const dockTo = (mode: Mode) => {
    setMode(mode);
    setSignInError(null);
    setRegisterError(null);
    setSignInTouched({ username: false, password: false });
    setRegisterTouched(zeroRegisterTouched);
  };

  const usernameError =
    signInTouched.username && !username.trim()
      ? 'Please enter your username or email.'
      : signInTouched.username && !isValidIdentifier(username)
        ? 'Please enter a valid username or email.'
        : null;
  const passwordError =
    signInTouched.password && !password ? 'Please enter your password.' : null;
  const signInCanSubmit =
    !!username.trim() && isValidIdentifier(username) && !!password && !signInSubmitting;

  const fullNameError =
    registerTouched.fullName && !fields.fullName.trim()
      ? 'Please enter your full name.'
      : registerTouched.fullName && !isValidFullName(fields.fullName)
        ? 'Please enter a valid full name.'
        : null;
  const registerUsernameError =
    registerTouched.username && !fields.username.trim()
      ? 'Please enter your username or email.'
      : registerTouched.username && !isValidIdentifier(fields.username)
        ? 'Please enter a valid username or email.'
        : null;
  const registerPasswordError =
    registerTouched.password && !fields.password
      ? 'Please enter a password.'
      : registerTouched.password && fields.password.length < MIN_PASSWORD_LENGTH
        ? `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`
        : null;
  const confirmPasswordError =
    registerTouched.confirmPassword &&
    (!fields.confirmPassword
      ? 'Please confirm your password.'
      : fields.confirmPassword !== fields.password
        ? 'Passwords do not match.'
        : null);
  const registerCanSubmit =
    !!fields.fullName.trim() &&
    isValidFullName(fields.fullName) &&
    !!fields.username.trim() &&
    isValidIdentifier(fields.username) &&
    fields.password.length >= MIN_PASSWORD_LENGTH &&
    fields.confirmPassword === fields.password &&
    !registerSubmitting;

  const handleSignInBlur = useCallback((field: keyof SignInTouched) => {
    setSignInTouched((prev) => ({ ...prev, [field]: true }));
  }, []);

  const handleRegisterBlur = useCallback((field: keyof RegisterFields) => {
    setRegisterTouched((prev) => ({ ...prev, [field]: true }));
  }, []);

  const handleSignInSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSignInError(null);
    setSignInTouched({ username: true, password: true });
    if (!username.trim() || !isValidIdentifier(username) || !password) {
      return;
    }
    setSignInSubmitting(true);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 403) {
        setSignInError('Your account is inactive. Contact the project administrator.');
      } else {
        setSignInError('Invalid username or password.');
      }
    } finally {
      setSignInSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setRegisterError(null);
    setRegisterTouched({
      fullName: true,
      username: true,
      password: true,
      confirmPassword: true,
      adminKey: true,
    });
    if (!registerCanSubmit) {
      return;
    }
    setRegisterSubmitting(true);
    try {
      const user = await api.register({
        username: fields.username.trim(),
        full_name: fields.fullName.trim(),
        password: fields.password,
        confirm_password: fields.confirmPassword,
        ...(fields.adminKey.trim()
          ? { admin_registration_secret: fields.adminKey.trim() }
          : {}),
      });
      setRegisteredUsername(user.user.username);
      setFields(initialRegisterFields);
      setShowRegPassword(false);
      setShowRegConfirm(false);
      setShowAdminKey(false);
      setMode('success');
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        setRegisterError(
          'An account with these credentials already exists. Please sign in instead.'
        );
      } else if (status === 403) {
        setRegisterError(
          'The admin registration key is invalid. No account was created.'
        );
      } else if (status === 429) {
        setRegisterError('Too many attempts. Please try again later.');
      } else {
        setRegisterError(
          'We could not create your account right now. Please try again.'
        );
      }
    } finally {
      setRegisterSubmitting(false);
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

            {mode === 'welcome' && (
              <>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                  Project Tracking
                </h1>
                <p className="text-sm text-slate-500 mt-1.5 font-medium">
                  Construction Financial &amp; Resource Management
                </p>
                <p className="text-sm text-slate-500 mt-6 leading-relaxed">
                  Understand and manage your construction project records
                  securely in one workspace.
                </p>

                <div className="mt-8 space-y-3">
                  <button
                    type="button"
                    onClick={() => dockTo('register')}
                    className="w-full inline-flex items-center justify-center rounded-lg bg-blue-800 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 transition-colors"
                  >
                    Create an account
                  </button>
                  <button
                    type="button"
                    onClick={() => dockTo('signin')}
                    className="w-full inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 transition-colors"
                  >
                    Sign in
                  </button>
                </div>

                <p className="text-sm text-slate-500 mt-8">
                  Welcome. Create your account to get started.
                </p>
              </>
            )}

            {mode === 'signin' && (
              <>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                  Sign in
                </h1>
                <p className="text-sm text-slate-500 mt-1.5">
                  Enter your credentials to access your projects.
                </p>

                <form
                  onSubmit={handleSignInSubmit}
                  noValidate
                  className="mt-8 space-y-5 text-left"
                >
                  <div>
                    <label
                      htmlFor="username"
                      className="block text-sm font-medium text-slate-700 mb-1.5"
                    >
                      Username / Email
                    </label>
                    <input
                      id="username"
                      type="text"
                      autoComplete="username"
                      autoCapitalize="none"
                      spellCheck={false}
                      value={username}
                      onChange={(e) => {
                        setUsername(e.target.value);
                        if (signInError) setSignInError(null);
                      }}
                      onBlur={() => handleSignInBlur('username')}
                      disabled={signInSubmitting}
                      aria-invalid={!!usernameError}
                      aria-describedby={usernameError ? 'username-error' : undefined}
                      className={`w-full rounded-lg border px-3.5 py-2.5 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 disabled:opacity-50 disabled:cursor-not-allowed ${
                        usernameError ? 'border-red-300 bg-red-50' : 'border-slate-300 bg-white'
                      }`}
                    />
                    {usernameError && (
                      <p
                        id="username-error"
                        className="mt-1.5 text-xs text-red-600"
                        role="alert"
                      >
                        {usernameError}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="password"
                      className="block text-sm font-medium text-slate-700 mb-1.5"
                    >
                      Password
                    </label>
                    <div className="relative">
                      <input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => {
                          setPassword(e.target.value);
                          if (signInError) setSignInError(null);
                        }}
                        onBlur={() => handleSignInBlur('password')}
                        disabled={signInSubmitting}
                        aria-invalid={!!passwordError}
                        aria-describedby={passwordError ? 'password-error' : undefined}
                        className={`w-full rounded-lg border px-3.5 py-2.5 pr-10 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 disabled:opacity-50 disabled:cursor-not-allowed ${
                          passwordError ? 'border-red-300 bg-red-50' : 'border-slate-300 bg-white'
                        }`}
                      />
                      <button
                        type="button"
                        tabIndex={-1}
                        onClick={() => setShowPassword((v) => !v)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {showPassword ? (
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
                    {passwordError && (
                      <p
                        id="password-error"
                        className="mt-1.5 text-xs text-red-600"
                        role="alert"
                      >
                        {passwordError}
                      </p>
                    )}
                  </div>

                  {signInError && (
                    <div
                      className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 flex items-start gap-2.5"
                      role="alert"
                    >
                      <svg className="w-4 h-4 mt-0.5 shrink-0 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                      </svg>
                      <span>{signInError}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={!signInCanSubmit}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {signInSubmitting && (
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    )}
                    {signInSubmitting ? 'Signing in...' : 'Sign in'}
                  </button>
                </form>

                <p className="text-sm text-slate-500 mt-6">
                  Don&apos;t have an account?{' '}
                  <button
                    type="button"
                    onClick={() => dockTo('register')}
                    className="font-semibold text-blue-800 hover:underline"
                  >
                    Create an account
                  </button>
                </p>

                <p className="text-xs text-slate-400 mt-6">
                  Authorized access only. All activity is logged.
                </p>
              </>
            )}

            {mode === 'register' && (
              <>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                  Create your account
                </h1>
                <p className="text-sm text-slate-500 mt-1.5">
                  Get started with a secure workspace for your projects.
                </p>

                <form
                  onSubmit={handleRegisterSubmit}
                  noValidate
                  className="mt-8 space-y-5 text-left"
                >
                  <div>
                    <label
                      htmlFor="fullName"
                      className="block text-sm font-medium text-slate-700 mb-1.5"
                    >
                      Full name
                    </label>
                    <input
                      id="fullName"
                      type="text"
                      autoComplete="name"
                      spellCheck={false}
                      value={fields.fullName}
                      onChange={(e) => {
                        setFields((prev) => ({ ...prev, fullName: e.target.value }));
                        if (registerError) setRegisterError(null);
                      }}
                      onBlur={() => handleRegisterBlur('fullName')}
                      disabled={registerSubmitting}
                      aria-invalid={!!fullNameError}
                      aria-describedby={fullNameError ? 'fullName-error' : undefined}
                      className={`w-full rounded-lg border px-3.5 py-2.5 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 disabled:opacity-50 disabled:cursor-not-allowed ${
                        fullNameError ? 'border-red-300 bg-red-50' : 'border-slate-300 bg-white'
                      }`}
                    />
                    {fullNameError && (
                      <p
                        id="fullName-error"
                        className="mt-1.5 text-xs text-red-600"
                        role="alert"
                      >
                        {fullNameError}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="registerUsername"
                      className="block text-sm font-medium text-slate-700 mb-1.5"
                    >
                      Username / Email
                    </label>
                    <input
                      id="registerUsername"
                      type="text"
                      autoComplete="username"
                      autoCapitalize="none"
                      spellCheck={false}
                      value={fields.username}
                      onChange={(e) => {
                        setFields((prev) => ({ ...prev, username: e.target.value }));
                        if (registerError) setRegisterError(null);
                      }}
                      onBlur={() => handleRegisterBlur('username')}
                      disabled={registerSubmitting}
                      aria-invalid={!!registerUsernameError}
                      aria-describedby={
                        registerUsernameError ? 'registerUsername-error' : undefined
                      }
                      className={`w-full rounded-lg border px-3.5 py-2.5 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 disabled:opacity-50 disabled:cursor-not-allowed ${
                        registerUsernameError
                          ? 'border-red-300 bg-red-50'
                          : 'border-slate-300 bg-white'
                      }`}
                    />
                    {registerUsernameError && (
                      <p
                        id="registerUsername-error"
                        className="mt-1.5 text-xs text-red-600"
                        role="alert"
                      >
                        {registerUsernameError}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="registerPassword"
                      className="block text-sm font-medium text-slate-700 mb-1.5"
                    >
                      Password
                    </label>
                    <div className="relative">
                      <input
                        id="registerPassword"
                        type={showRegPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        value={fields.password}
                        onChange={(e) => {
                          setFields((prev) => ({ ...prev, password: e.target.value }));
                          if (registerError) setRegisterError(null);
                        }}
                        onBlur={() => handleRegisterBlur('password')}
                        disabled={registerSubmitting}
                        aria-invalid={!!registerPasswordError}
                        aria-describedby={
                          registerPasswordError ? 'registerPassword-error' : undefined
                        }
                        className={`w-full rounded-lg border px-3.5 py-2.5 pr-10 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 disabled:opacity-50 disabled:cursor-not-allowed ${
                          registerPasswordError
                            ? 'border-red-300 bg-red-50'
                            : 'border-slate-300 bg-white'
                        }`}
                      />
                      <button
                        type="button"
                        tabIndex={-1}
                        onClick={() => setShowRegPassword((v) => !v)}
                        aria-label={showRegPassword ? 'Hide password' : 'Show password'}
                        className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {showRegPassword ? (
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
                    {registerPasswordError && (
                      <p
                        id="registerPassword-error"
                        className="mt-1.5 text-xs text-red-600"
                        role="alert"
                      >
                        {registerPasswordError}
                      </p>
                    )}
                    {!registerPasswordError && (
                      <p className="mt-1.5 text-xs text-slate-400">
                        Use at least {MIN_PASSWORD_LENGTH} characters.
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="confirmPassword"
                      className="block text-sm font-medium text-slate-700 mb-1.5"
                    >
                      Confirm password
                    </label>
                    <div className="relative">
                      <input
                        id="confirmPassword"
                        type={showRegConfirm ? 'text' : 'password'}
                        autoComplete="new-password"
                        value={fields.confirmPassword}
                        onChange={(e) => {
                          setFields((prev) => ({
                            ...prev,
                            confirmPassword: e.target.value,
                          }));
                          if (registerError) setRegisterError(null);
                        }}
                        onBlur={() => handleRegisterBlur('confirmPassword')}
                        disabled={registerSubmitting}
                        aria-invalid={!!confirmPasswordError}
                        aria-describedby={
                          confirmPasswordError ? 'confirmPassword-error' : undefined
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
                        onClick={() => setShowRegConfirm((v) => !v)}
                        aria-label={showRegConfirm ? 'Hide password' : 'Show password'}
                        className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {showRegConfirm ? (
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
                        id="confirmPassword-error"
                        className="mt-1.5 text-xs text-red-600"
                        role="alert"
                      >
                        {confirmPasswordError}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="adminKey"
                      className="block text-sm font-medium text-slate-700 mb-1.5"
                    >
                      Admin Registration Key <span className="text-slate-400 font-normal">(optional)</span>
                    </label>
                    <div className="relative">
                      <input
                        id="adminKey"
                        type={showAdminKey ? 'text' : 'password'}
                        autoComplete="off"
                        spellCheck={false}
                        value={fields.adminKey}
                        onChange={(e) => {
                          setFields((prev) => ({
                            ...prev,
                            adminKey: e.target.value,
                          }));
                          if (registerError) setRegisterError(null);
                        }}
                        onBlur={() => handleRegisterBlur('adminKey')}
                        disabled={registerSubmitting}
                        aria-describedby="adminKey-hint"
                        className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 pr-10 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                      <button
                        type="button"
                        tabIndex={-1}
                        onClick={() => setShowAdminKey((v) => !v)}
                        aria-label={showAdminKey ? 'Hide admin key' : 'Show admin key'}
                        className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        {showAdminKey ? (
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
                    <p id="adminKey-hint" className="mt-1.5 text-xs text-slate-400">
                      Optional. Only enter a key if you were given one to create
                      an Administrator account. Leave blank for a standard
                      account.
                    </p>
                  </div>

                  {registerError && (
                    <div
                      className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 flex items-start gap-2.5"
                      role="alert"
                    >
                      <svg className="w-4 h-4 mt-0.5 shrink-0 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                      </svg>
                      <span>{registerError}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={!registerCanSubmit}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {registerSubmitting && (
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    )}
                    {registerSubmitting ? 'Creating account...' : 'Create account'}
                  </button>
                </form>

                <p className="text-sm text-slate-500 mt-6">
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => dockTo('signin')}
                    className="font-semibold text-blue-800 hover:underline"
                  >
                    Sign in
                  </button>
                </p>
              </>
            )}

            {mode === 'success' && (
              <>
                <div className="w-14 h-14 mx-auto rounded-full bg-green-50 border border-green-200 flex items-center justify-center mb-5">
                  <svg className="w-7 h-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                  Account created successfully
                </h1>
                <p className="text-sm text-slate-500 mt-3 leading-relaxed">
                  Your account is ready. Sign in to continue.
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {registeredUsername ? `@${registeredUsername}` : ''}
                </p>

                <button
                  type="button"
                  onClick={() =>
                    dockTo('signin')
                  }
                  className="w-full mt-8 inline-flex items-center justify-center rounded-lg bg-blue-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 transition-colors"
                >
                  Sign in
                </button>
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