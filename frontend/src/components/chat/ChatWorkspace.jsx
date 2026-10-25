import React, { useState } from 'react';
import ConversationSidebar from './ConversationSidebar';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import { useChatSessions } from '../../hooks/useChatSessions';

export default function ChatWorkspace({ onClose, isExpanded, onToggleExpand }) {
  const {
    sessions,
    activeSessionId,
    messages,
    loadingSessions,
    sending,
    loadingStage,
    error,
    selectSession,
    startNewConversation,
    sendMessage,
    retryLastMessage,
    deleteSession,
  } = useChatSessions();

  const [inputVal, setInputVal] = useState('');
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);

  const handleSend = () => {
    const text = inputVal.trim();
    if (!text || sending) return;
    setInputVal('');
    sendMessage(text);
  };

  const handleSelectSuggestion = (suggestionText) => {
    sendMessage(suggestionText);
  };

  return (
    <div style={styles.workspace} className="nyaayukti-workspace-root">
      {/* ── Slide-over Conversation History Drawer ── */}
      {historyDrawerOpen && (
        <div style={styles.drawerBackdrop} onClick={() => setHistoryDrawerOpen(false)}>
          <div style={styles.drawerPane} onClick={(e) => e.stopPropagation()}>
            <ConversationSidebar
              sessions={sessions}
              activeSessionId={activeSessionId}
              loadingSessions={loadingSessions}
              onSelectSession={(id) => {
                selectSession(id);
                setHistoryDrawerOpen(false);
              }}
              onNewConversation={() => {
                startNewConversation();
                setHistoryDrawerOpen(false);
              }}
              onDeleteSession={deleteSession}
              onCloseMobile={() => setHistoryDrawerOpen(false)}
            />
          </div>
        </div>
      )}

      {/* ── Main Chat Area ── */}
      <main style={styles.mainArea} className="nyaayukti-chat-main">
        {/* Header with clean AI Assistant on left and only one Nyaayukti logo at top right */}
        <header style={styles.header}>
          <div style={styles.headerLeft}>
            <div style={styles.headerTitleColumn}>
              <h2 style={styles.headerTitle}>AI Assistant</h2>
              <div style={styles.onlineStatusRow}>
                <span style={styles.onlineDot} />
                <span style={styles.onlineText}>ONLINE • READY TO HELP</span>
              </div>
            </div>
          </div>

          <div style={styles.headerRight}>
            {/* The ONLY Nyaayukti Logo in the workspace — at the right top */}
            <div style={styles.topRightLogoGroup} title="Nyaayukti Indian Statutory Intelligence">
              <img src="/nyaayukti-mark.png" alt="Nyaayukti" style={styles.topRightLogo} />
              <span style={styles.topRightBrandText}>Nyaayukti</span>
            </div>

            <div style={styles.headerDivider} />

            {/* New Conversation (+) Button */}
            <button
              type="button"
              onClick={startNewConversation}
              style={styles.iconButton}
              title="New Conversation (+)"
              aria-label="New Conversation"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>

            {/* History Drawer Toggle Button */}
            <button
              type="button"
              onClick={() => setHistoryDrawerOpen((prev) => !prev)}
              style={styles.iconButton}
              title="Recent Conversations"
              aria-label="Recent Conversations"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </button>

            {/* Expand / Fullscreen Toggle */}
            {onToggleExpand && (
              <button
                type="button"
                onClick={onToggleExpand}
                style={styles.iconButton}
                title={isExpanded ? 'Restore window size' : 'Expand workspace'}
                aria-label={isExpanded ? 'Restore window size' : 'Expand workspace'}
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M15 3h6v6" />
                  <path d="M9 21H3v-6" />
                  <path d="M21 3l-7 7" />
                  <path d="M3 21l7-7" />
                </svg>
              </button>
            )}

            {/* Close Button */}
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                style={styles.iconButton}
                title="Close chat workspace"
                aria-label="Close chat workspace"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        </header>

        {/* Scrollable Chat Area */}
        <ChatMessages
          messages={messages}
          loading={sending}
          loadingStage={loadingStage}
          error={error}
          onRetry={retryLastMessage}
          onSelectSuggestion={handleSelectSuggestion}
        />

        {/* Fixed Sticky Input Area at Bottom */}
        <footer style={styles.footerInputArea}>
          <ChatInput
            value={inputVal}
            onChange={setInputVal}
            onSubmit={handleSend}
            disabled={sending}
          />
        </footer>
      </main>
    </div>
  );
}

const styles = {
  workspace: {
    display: 'flex',
    width: '100%',
    height: '100%',
    backgroundColor: '#ffffff',
    overflow: 'hidden',
    position: 'relative',
  },
  drawerBackdrop: {
    position: 'absolute',
    inset: 0,
    zIndex: 100,
    backgroundColor: 'rgba(15, 23, 42, 0.4)',
    display: 'flex',
    backdropFilter: 'blur(3px)',
  },
  drawerPane: {
    width: '290px',
    height: '100%',
    backgroundColor: '#ffffff',
    boxShadow: '4px 0 24px rgba(0, 0, 0, 0.15)',
    display: 'flex',
    animation: 'drawerSlideIn 0.2s ease-out forwards',
  },
  mainArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    width: '100%',
    minWidth: 0,
    backgroundColor: '#fafbfc',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0.75rem 1.75rem',
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #f1f5f9',
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
  },
  headerTitleColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.15rem',
  },
  headerTitle: {
    fontSize: '0.9375rem' /* 15px */,
    fontWeight: '700',
    color: '#111827',
    margin: 0,
    lineHeight: '1.25',
    letterSpacing: '-0.01em',
  },
  onlineStatusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
  },
  onlineDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#10b981',
    boxShadow: '0 0 4px rgba(16, 185, 129, 0.6)',
  },
  onlineText: {
    fontSize: '0.625rem' /* 10px */,
    fontWeight: '700',
    color: '#0f766e',
    letterSpacing: '0.06em',
    lineHeight: '1',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  topRightLogoGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.45rem',
    padding: '0.2rem 0.5rem',
    borderRadius: '6px',
    cursor: 'default',
  },
  topRightLogo: {
    height: '28px',
    width: 'auto',
    maxHeight: '30px',
    objectFit: 'contain',
    display: 'block',
  },
  topRightBrandText: {
    fontSize: '0.90625rem',
    fontWeight: '700',
    color: '#0f3a68',
    letterSpacing: '-0.01em',
  },
  headerDivider: {
    width: '1px',
    height: '20px',
    backgroundColor: '#e2e8f0',
    margin: '0 0.25rem',
  },
  iconButton: {
    width: '32px',
    height: '32px',
    borderRadius: '6px',
    backgroundColor: 'transparent',
    border: 'none',
    color: '#64748b',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  footerInputArea: {
    padding: '0.85rem 1.4rem 1.1rem 1.4rem',
    backgroundColor: '#ffffff',
    borderTop: '1px solid #f1f5f9',
    flexShrink: 0,
  },
};
