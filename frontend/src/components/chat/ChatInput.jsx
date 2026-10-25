import React, { useRef, useEffect } from 'react';

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled,
  placeholder = 'Ask me anything about legal matters...',
  onSignIn,
}) {
  const textareaRef = useRef(null);

  // Auto-resize textarea height up to 140px
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const newHeight = Math.min(el.scrollHeight, 140);
    el.style.height = `${Math.max(newHeight, 38)}px`;
  }, [value]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSubmit();
      }
    }
  };

  const handleSignInClick = (e) => {
    e.preventDefault();
    if (typeof onSignIn === 'function') {
      onSignIn();
    } else {
      window.history.pushState(null, '', '/signin');
      window.dispatchEvent(new PopStateEvent('popstate'));
    }
  };

  const canSubmit = Boolean(value.trim()) && !disabled;

  return (
    <div style={styles.container}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) onSubmit();
        }}
        style={styles.form}
      >
        <div style={styles.inputWrapper}>
          <textarea
            ref={textareaRef}
            rows={1}
            maxLength={2000}
            aria-label="Your legal question"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            style={styles.textarea}
          />

          <button
            type="submit"
            disabled={!canSubmit}
            style={{
              ...styles.sendButton,
              ...(canSubmit ? styles.sendButtonActive : styles.sendButtonIdle),
            }}
            aria-label="Send query"
            title="Send"
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#ffffff"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ transform: 'rotate(0deg)' }}
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </form>

      <div style={styles.disclaimerContainer}>
        <span style={styles.disclaimerText}>
          Legal information, not legal advice. Verify before relying on it. 1 free question left —{' '}
          <button type="button" onClick={handleSignInClick} style={styles.signInLink}>
            sign in
          </button>{' '}
          for more.
        </span>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
    width: '100%',
    maxWidth: '920px',
    margin: '0 auto',
  },
  form: {
    width: '100%',
  },
  inputWrapper: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    padding: '0.45rem 0.55rem 0.45rem 1.15rem',
    boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
    transition: 'border-color 0.18s ease, box-shadow 0.18s ease',
  },
  textarea: {
    flex: 1,
    border: 'none',
    outline: 'none',
    backgroundColor: 'transparent',
    resize: 'none',
    fontFamily: 'inherit',
    fontSize: '0.9375rem',
    color: '#1f2937',
    lineHeight: '1.45',
    maxHeight: '140px',
    padding: '0.35rem 0.6rem 0.35rem 0',
  },
  sendButton: {
    width: '36px',
    height: '36px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.18s ease',
    flexShrink: 0,
    backgroundColor: '#95b8a6', // Soft sage green matching image
  },
  sendButtonActive: {
    backgroundColor: '#82a994',
    boxShadow: '0 2px 6px rgba(130, 169, 148, 0.35)',
    transform: 'scale(1.02)',
  },
  sendButtonIdle: {
    backgroundColor: '#95b8a6',
    opacity: 0.9,
  },
  disclaimerContainer: {
    textAlign: 'center',
    padding: '0 0.5rem',
  },
  disclaimerText: {
    fontSize: '0.71875rem' /* ~11.5px */,
    color: '#94a3b8',
    lineHeight: '1.4',
  },
  signInLink: {
    background: 'none',
    border: 'none',
    padding: 0,
    margin: 0,
    color: '#0f766e',
    fontSize: 'inherit',
    fontWeight: '500',
    cursor: 'pointer',
    textDecoration: 'underline',
    textUnderlineOffset: '2px',
  },
};
