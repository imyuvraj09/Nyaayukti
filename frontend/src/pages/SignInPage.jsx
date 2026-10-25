import { accountAction } from '../services/api';
import React, { useMemo, useState } from 'react';
import { useAuth } from '../auth/AuthContext';

export default function SignInPage({ onSuccess, onNavigateHome }) {
  const { signIn, register } = useAuth();
  const [mode, setMode] = useState('signin');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const isRegister = mode === 'register';
  const title = isRegister ? 'CREATE ACCOUNT' : 'SIGN IN';
  const eyebrow = isRegister ? 'JOIN NYAAYUKTI' : 'WELCOME BACK';
  const subtitle = isRegister
    ? 'Create your account to start private, source-backed legal conversations.'
    : 'Sign in to continue your legal research conversations.';

  const buttonText = useMemo(() => {
    if (submitting) return isRegister ? 'Creating account…' : 'Signing in…';
    return isRegister ? 'Create account' : 'Sign in';
  }, [submitting, isRegister]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError('');

    const result = isRegister
      ? await register({ displayName, email, password })
      : await signIn({ email, password });

    setSubmitting(false);
    if (!result.success) {
      setError(result.error || 'Authentication failed. Please try again.');
      return;
    }
    onSuccess?.(result.user);
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setError('');
    setPassword('');
  }

  return (
    <main style={styles.page}>
      <div style={styles.backgroundMark} aria-hidden="true">
        §
      </div>
      <section style={styles.card} aria-labelledby="auth-title">
        <div style={styles.brandMarkWrap}>
          <img src="/nyaayukti-mark.png" alt="" style={styles.brandMark} />
        </div>

        <div style={styles.eyebrow}>{eyebrow}</div>
        <h1 id="auth-title" style={styles.title}>
          {title}
        </h1>
        <p style={styles.subtitle}>{subtitle}</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          {isRegister && (
            <label style={styles.fieldGroup}>
              <span style={styles.label}>FULL NAME *</span>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Your name"
                autoComplete="name"
                minLength={2}
                maxLength={80}
                required
                className="auth-field-input"
                style={styles.input}
              />
            </label>
          )}

          <label style={styles.fieldGroup}>
            <span style={styles.label}>EMAIL *</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
              className="auth-field-input"
              style={styles.input}
            />
          </label>

          <label style={styles.fieldGroup}>
            <span style={styles.label}>PASSWORD *</span>
            <div style={styles.passwordWrap}>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isRegister ? 'Minimum 8 characters' : 'Your password'}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                minLength={8}
                maxLength={128}
                required
                className="auth-field-input"
                style={{ ...styles.input, paddingRight: '4.4rem', width: '100%' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                style={styles.showButton}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? 'HIDE' : 'SHOW'}
              </button>
            </div>
          </label>

          {error && (
            <div role="alert" style={styles.errorBox}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            style={{ ...styles.submitButton, opacity: submitting ? 0.7 : 1 }}
          >
            {buttonText}
          </button>
        </form>

        {!isRegister && (
          <button
            type="button"
            style={styles.homeLink}
            onClick={async () => {
              const result = await accountAction('forgot-password', { email });
              setError(result.success ? result.message : result.error);
            }}
          >
            Forgot password? Enter your email above, then click here.
          </button>
        )}

        <div style={styles.divider}>
          <span style={styles.dividerLine} />
          <span>OR</span>
          <span style={styles.dividerLine} />
        </div>

        <p style={styles.switchText}>
          {isRegister ? 'Already have an account?' : 'New to Nyaayukti?'}{' '}
          <button
            type="button"
            onClick={() => switchMode(isRegister ? 'signin' : 'register')}
            style={styles.switchButton}
          >
            {isRegister ? 'Sign in' : 'Create account'}
          </button>
        </p>

        <button type="button" onClick={onNavigateHome} style={styles.homeLink}>
          ← Back to home
        </button>

        <div style={styles.securityNote}>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <rect x="3" y="11" width="18" height="10" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span>
            Your chat history is separated by account. Passwords are stored only as salted hashes.
          </span>
        </div>
      </section>
    </main>
  );
}

const styles = {
  page: {
    flex: 1,
    minHeight: 'calc(100vh - var(--header-height, 58px))',
    background: 'linear-gradient(180deg, #fbfaf7 0%, #f8fafc 100%)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'flex-start',
    padding: '2.5rem 1rem 4rem',
    position: 'relative',
    overflow: 'hidden',
  },
  backgroundMark: {
    position: 'absolute',
    right: '7%',
    top: '12%',
    fontFamily: 'Georgia, serif',
    fontSize: '24rem',
    lineHeight: 1,
    color: 'rgba(13, 148, 136, 0.035)',
    userSelect: 'none',
    pointerEvents: 'none',
  },
  card: {
    width: 'min(440px, 100%)',
    backgroundColor: '#ffffff',
    border: '1px solid #e4e1da',
    borderRadius: '12px',
    padding: '2rem 1.7rem 1.5rem',
    boxShadow: '0 18px 45px rgba(15, 23, 42, 0.06)',
    position: 'relative',
    zIndex: 1,
  },
  brandMarkWrap: {
    width: '42px',
    height: '42px',
    margin: '0 auto 0.7rem',
    borderRadius: '50%',
    backgroundColor: '#f0fdfa',
    display: 'grid',
    placeItems: 'center',
  },
  brandMark: { width: '31px', height: '31px', objectFit: 'contain' },
  eyebrow: {
    textAlign: 'center',
    color: '#0f766e',
    fontSize: '0.69rem',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.13em',
    fontWeight: 700,
    marginBottom: '0.35rem',
  },
  title: {
    textAlign: 'center',
    fontSize: '1.85rem',
    lineHeight: 1.1,
    letterSpacing: '-0.025em',
    color: '#111827',
    marginBottom: '0.55rem',
  },
  subtitle: {
    textAlign: 'center',
    color: '#64748b',
    fontSize: '0.9rem',
    lineHeight: 1.55,
    maxWidth: '340px',
    margin: '0 auto 1.55rem',
  },
  form: { display: 'flex', flexDirection: 'column', gap: '1rem' },
  fieldGroup: { display: 'flex', flexDirection: 'column', gap: '0.38rem' },
  label: {
    color: '#8b7660',
    fontSize: '0.66rem',
    letterSpacing: '0.1em',
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
  },
  input: {
    height: '46px',
    border: '1px solid #d9d6cf',
    borderRadius: '8px',
    padding: '0 0.8rem',
    backgroundColor: '#fffefa',
    color: '#0f172a',
    fontSize: '0.9rem',
    outline: 'none',
  },
  passwordWrap: { position: 'relative' },
  showButton: {
    position: 'absolute',
    right: '0.75rem',
    top: '50%',
    transform: 'translateY(-50%)',
    color: '#756553',
    fontFamily: 'var(--font-mono)',
    fontSize: '0.65rem',
    fontWeight: 700,
    letterSpacing: '0.05em',
  },
  errorBox: {
    border: '1px solid #fecaca',
    backgroundColor: '#fff7f7',
    color: '#b91c1c',
    borderRadius: '8px',
    padding: '0.7rem 0.8rem',
    fontSize: '0.82rem',
    lineHeight: 1.45,
  },
  submitButton: {
    marginTop: '0.15rem',
    height: '47px',
    borderRadius: '999px',
    backgroundColor: '#0f766e',
    color: '#ffffff',
    fontWeight: 700,
    fontSize: '0.9rem',
    boxShadow: '0 8px 18px rgba(15, 118, 110, 0.14)',
  },
  divider: {
    display: 'grid',
    gridTemplateColumns: '1fr auto 1fr',
    alignItems: 'center',
    gap: '0.65rem',
    color: '#a59a8d',
    fontFamily: 'var(--font-mono)',
    fontSize: '0.65rem',
    margin: '1.2rem 0 0.9rem',
  },
  dividerLine: { height: '1px', backgroundColor: '#e5e1da' },
  switchText: { textAlign: 'center', color: '#64748b', fontSize: '0.84rem' },
  switchButton: { color: '#0f766e', fontWeight: 700, fontSize: '0.84rem' },
  homeLink: {
    display: 'block',
    margin: '0.8rem auto 0',
    color: '#64748b',
    fontSize: '0.8rem',
  },
  securityNote: {
    marginTop: '1.15rem',
    paddingTop: '1rem',
    borderTop: '1px solid #f0ece6',
    color: '#7c8797',
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'flex-start',
    fontSize: '0.72rem',
    lineHeight: 1.45,
  },
};
