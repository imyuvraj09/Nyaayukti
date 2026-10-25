import React, { useState } from 'react';
import { accountAction } from '../services/api';

export default function AccountActionPage({ onDone }) {
  const fragment = window.location.hash.slice(1);
  const action = fragment.startsWith('/account/verify') ? 'verify-email' : 'reset-password';
  const [token] = useState(
    () => new URLSearchParams(fragment.split('?')[1] || '').get('token') || '',
  );
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    const result = await accountAction(action, { token, password });
    setBusy(false);
    setDone(result.success);
    setStatus(
      result.success
        ? action === 'verify-email'
          ? 'Email verified.'
          : 'Password updated. Sign in with your new password.'
        : result.error,
    );
    if (result.success) window.history.replaceState(null, '', '/');
  }
  return (
    <main style={{ maxWidth: 480, margin: '6rem auto', padding: '2rem' }}>
      <h1>{action === 'verify-email' ? 'Verify email' : 'Reset password'}</h1>
      <form onSubmit={submit}>
        {action === 'reset-password' && !done && (
          <label>
            New password
            <input
              aria-label="New password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              maxLength={128}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
        )}
        {!done && <button disabled={busy || !token}>{busy ? 'Working…' : 'Confirm'}</button>}
      </form>
      <p role="status">{status}</p>
      {done && <button onClick={onDone}>Go to sign in</button>}
    </main>
  );
}
