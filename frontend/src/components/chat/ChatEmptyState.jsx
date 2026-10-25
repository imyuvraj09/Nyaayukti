import React from 'react';

const SUGGESTED_QUESTIONS = [
  'What constitutes theft under Bharatiya Nyaya Sanhita?',
  'What are consumer rights in India?',
  'What does the Constitution say about fundamental rights?',
  'How are electronic records admitted under Bharatiya Sakshya Adhiniyam?',
];

export default function ChatEmptyState({ onSelectSuggestion }) {
  // Format current time like "11:06 AM"
  const currentTime = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });

  return (
    <div style={styles.container}>
      {/* ── Initial Assistant Welcome Bubble (matching Image 1) ── */}
      <div style={styles.bubbleCard}>
        <p style={styles.greetingText}>
          Hello! I'm your AI legal assistant. How can I help you with your legal questions today?
        </p>
        <span style={styles.timestampText}>{currentTime}</span>
      </div>

      {/* ── Clean, subtle quick question pills ── */}
      <div style={styles.suggestionsWrapper}>
        <div style={styles.suggestionsHeader}>Quick Suggestions</div>
        <div style={styles.chipsRow}>
          {SUGGESTED_QUESTIONS.map((q, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectSuggestion(q)}
              style={styles.chipButton}
              title={`Ask: "${q}"`}
            >
              <span style={styles.chipText}>{q}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    width: '100%',
    maxWidth: '920px',
    margin: '0 auto',
    padding: '0.5rem 0',
  },
  bubbleCard: {
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '12px',
    padding: '0.9rem 1.25rem 0.75rem 1.25rem',
    maxWidth: '520px',
    boxShadow: '0 1px 2px rgba(15, 23, 42, 0.03)',
    marginBottom: '1.25rem',
  },
  greetingText: {
    margin: 0,
    fontSize: '0.9375rem' /* 15px */,
    color: '#1f2937',
    lineHeight: '1.5',
    fontWeight: '400',
  },
  timestampText: {
    display: 'block',
    fontSize: '0.71875rem' /* ~11.5px */,
    color: '#9ca3af',
    marginTop: '0.45rem',
  },
  suggestionsWrapper: {
    marginTop: '0.5rem',
    width: '100%',
  },
  suggestionsHeader: {
    fontSize: '0.6875rem',
    fontWeight: '600',
    color: '#94a3b8',
    letterSpacing: '0.04em',
    marginBottom: '0.55rem',
    textTransform: 'uppercase',
  },
  chipsRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
  },
  chipButton: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '0.45rem 0.85rem',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '9999px',
    color: '#334155',
    fontSize: '0.8125rem',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.02)',
  },
  chipText: {
    lineHeight: '1.3',
  },
};
