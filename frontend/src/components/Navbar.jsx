import { accountAction } from '../services/api';
import React, { useEffect, useRef, useState } from 'react';

export default function Navbar({
  activeTab = 'home',
  onNavigate,
  onClearChat,
  isChatView = false,
  user = null,
  authLoading = false,
  onSignOut,
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [accountNotice, setAccountNotice] = useState('');
  const accountRef = useRef(null);

  const navItems = [
    { id: 'home', label: 'Home', href: '/' },
    { id: 'chat', label: 'Chat Nyaayukti', href: '#chat' },
    { id: 'about', label: 'About', href: '/about' },
  ];

  useEffect(() => {
    const closeMenu = (event) => {
      if (accountRef.current && !accountRef.current.contains(event.target)) {
        setAccountMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', closeMenu);
    return () => document.removeEventListener('mousedown', closeMenu);
  }, []);

  const handleNavClick = (id, e) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    setAccountMenuOpen(false);
    onNavigate(id);
  };

  const initials = user?.displayName
    ? user.displayName
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join('')
    : 'NS';

  return (
    <header style={styles.header}>
      <div className="container" style={styles.navContainer}>
        <a
          href="/"
          onClick={(e) => {
            e.preventDefault();
            onNavigate('home');
          }}
          style={styles.logoLink}
        >
          <img src="/nyaayukti-mark.png" alt="Nyaayukti Logo" style={styles.logoImg} />
          <div style={styles.logoTextWrapper}>
            <span style={styles.logoTitle}>
              Nyaay<span style={styles.logoAccent}>ukti</span>
            </span>
            <span style={styles.logoSubtitle}>The Bridge to Justice</span>
          </div>
        </a>

        <nav className="desktop-nav" style={styles.desktopNav}>
          {navItems.map((item) => {
            const isActive = !isChatView && activeTab === item.id;
            return (
              <a
                key={item.id}
                href={item.href}
                onClick={(e) => handleNavClick(item.id, e)}
                style={{ ...styles.navLink, ...(isActive ? styles.navLinkActive : {}) }}
              >
                {item.label}
              </a>
            );
          })}
        </nav>

        <div style={styles.actions}>
          <a
            href="https://github.com/imyuvraj09/Nyaayukti"
            target="_blank"
            rel="noopener noreferrer"
            style={styles.githubBtn}
            title="View on GitHub"
            className="nav-github-btn"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            <span>GitHub</span>
          </a>

          {!authLoading && !user && (
            <button
              type="button"
              onClick={() => onNavigate('signin')}
              style={{
                ...styles.signInBtn,
                ...(activeTab === 'signin' ? styles.signInBtnActive : {}),
              }}
            >
              Sign in
            </button>
          )}

          {!authLoading && user && (
            <div ref={accountRef} style={styles.accountWrap}>
              <button
                type="button"
                onClick={() => setAccountMenuOpen((open) => !open)}
                style={styles.accountButton}
                aria-expanded={accountMenuOpen}
                aria-haspopup="menu"
                title={user.email}
              >
                <span style={styles.avatar}>{initials}</span>
                <span className="account-name" style={styles.accountName}>
                  {user.displayName}
                </span>
                <span style={styles.chevron}>⌄</span>
              </button>

              {accountMenuOpen && (
                <div role="menu" style={styles.accountMenu}>
                  <div style={styles.accountIdentity}>
                    <strong style={styles.identityName}>{user.displayName}</strong>
                    <span style={styles.identityEmail}>{user.email}</span>
                  </div>
                  {!user.emailVerified && (
                    <button
                      type="button"
                      role="menuitem"
                      onClick={async () => {
                        const result = await accountAction('send-verification');
                        setAccountNotice(result.success ? result.message : result.error);
                      }}
                    >
                      Verify email
                    </button>
                  )}
                  {accountNotice && <p role="status">{accountNotice}</p>}
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setAccountMenuOpen(false);
                      onSignOut?.();
                    }}
                    style={styles.signOutButton}
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          )}

          {isChatView ? (
            <button
              onClick={onClearChat}
              style={styles.clearBtn}
              title="Clear current legal conversation"
            >
              Clear chat
            </button>
          ) : (
            <button onClick={() => onNavigate('chat')} style={styles.chatBtn}>
              <span>{user ? 'Start Conversation' : 'Use Legal Assistant'}</span>
              <span style={{ fontSize: '1rem', lineHeight: 1 }}>→</span>
            </button>
          )}

          <img
            src="/ashoka-emblem.png"
            alt="Ashoka Emblem"
            style={styles.navEmblemLogo}
            title="State Emblem of India"
          />

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="mobile-menu-btn"
            style={styles.mobileMenuBtn}
            aria-label="Toggle navigation menu"
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              {mobileMenuOpen ? (
                <path d="M18 6L6 18M6 6l12 12" />
              ) : (
                <path d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <div style={styles.mobileDropdown}>
          {navItems.map((item) => (
            <a
              key={item.id}
              href={item.href}
              onClick={(e) => handleNavClick(item.id, e)}
              style={{
                ...styles.mobileNavLink,
                ...(activeTab === item.id ? { color: '#0d9488', fontWeight: '700' } : {}),
              }}
            >
              {item.label}
            </a>
          ))}

          {!user ? (
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                onNavigate('signin');
              }}
              style={styles.mobileSignInBtn}
            >
              Sign in
            </button>
          ) : (
            <div style={styles.mobileAccountBlock}>
              <div style={styles.mobileAccountIdentity}>
                <span style={styles.avatar}>{initials}</span>
                <div>
                  <div style={styles.identityName}>{user.displayName}</div>
                  <div style={styles.identityEmail}>{user.email}</div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setMobileMenuOpen(false);
                  onSignOut?.();
                }}
                style={styles.mobileSignOutBtn}
              >
                Sign out
              </button>
            </div>
          )}

          <a
            href="https://github.com/imyuvraj09/Nyaayukti"
            target="_blank"
            rel="noopener noreferrer"
            style={styles.mobileNavLink}
            onClick={() => setMobileMenuOpen(false)}
          >
            GitHub ↗
          </a>

          <button
            onClick={() => {
              setMobileMenuOpen(false);
              onNavigate('chat');
            }}
            style={styles.mobileChatBtn}
          >
            {user ? 'Start Legal Conversation' : 'Sign in to use Legal Assistant'}
          </button>
        </div>
      )}
    </header>
  );
}

const styles = {
  header: {
    position: 'sticky',
    top: 0,
    zIndex: 100,
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    height: 'var(--header-height, 58px)',
    display: 'flex',
    alignItems: 'center',
  },
  navContainer: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  logoLink: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.65rem',
    textDecoration: 'none',
    color: '#0f172a',
  },
  logoImg: {
    height: '38px',
    width: 'auto',
    maxHeight: '40px',
    objectFit: 'contain',
    display: 'block',
  },
  logoTextWrapper: { display: 'flex', flexDirection: 'column', lineHeight: 1.1 },
  logoTitle: { fontSize: '1.28rem', fontWeight: '800', letterSpacing: '-0.02em', color: '#0f172a' },
  logoAccent: { color: '#0284c7', fontWeight: '700' },
  logoSubtitle: {
    fontSize: '0.6875rem',
    fontWeight: '500',
    color: '#64748b',
    letterSpacing: '0.01em',
    marginTop: '1px',
  },
  desktopNav: { display: 'flex', alignItems: 'center', gap: '0.5rem' },
  navLink: {
    fontSize: '0.875rem',
    fontWeight: '500',
    color: '#334155',
    padding: '0.4rem 0.95rem',
    borderRadius: '20px',
    textDecoration: 'none',
  },
  navLinkActive: { backgroundColor: '#e6f4f1', color: '#0d9488', fontWeight: '600' },
  actions: { display: 'flex', alignItems: 'center', gap: '0.62rem' },
  githubBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.35rem',
    color: '#0f172a',
    fontSize: '0.82rem',
    fontWeight: '600',
    padding: '0.35rem 0.45rem',
    borderRadius: '6px',
  },
  signInBtn: {
    color: '#334155',
    fontSize: '0.86rem',
    fontWeight: '600',
    padding: '0.42rem 0.72rem',
    borderRadius: '6px',
    border: '1px solid transparent',
  },
  signInBtnActive: { color: '#0f766e', backgroundColor: '#f0fdfa', borderColor: '#ccfbf1' },
  chatBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    fontSize: '0.84rem',
    fontWeight: '600',
    padding: '0.45rem 0.92rem',
    borderRadius: '6px',
    boxShadow: '0 2px 8px rgba(13, 148, 136, 0.2)',
  },
  clearBtn: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    color: '#475569',
    fontSize: '0.8125rem',
    fontWeight: '500',
    padding: '0.4rem 0.75rem',
    borderRadius: '4px',
  },
  navEmblemLogo: {
    height: '36px',
    width: 'auto',
    objectFit: 'contain',
    display: 'block',
    marginLeft: '0.05rem',
  },
  accountWrap: { position: 'relative' },
  accountButton: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.42rem',
    padding: '0.27rem 0.5rem 0.27rem 0.3rem',
    borderRadius: '999px',
    border: '1px solid #e2e8f0',
    backgroundColor: '#ffffff',
    color: '#334155',
  },
  avatar: {
    width: '29px',
    height: '29px',
    borderRadius: '50%',
    backgroundColor: '#e6f4f1',
    color: '#0f766e',
    display: 'inline-grid',
    placeItems: 'center',
    fontSize: '0.68rem',
    fontWeight: 800,
    flexShrink: 0,
  },
  accountName: {
    maxWidth: '92px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    fontSize: '0.78rem',
    fontWeight: 600,
  },
  chevron: { color: '#94a3b8', fontSize: '0.8rem', marginTop: '-2px' },
  accountMenu: {
    position: 'absolute',
    top: 'calc(100% + 10px)',
    right: 0,
    width: '235px',
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    boxShadow: '0 14px 35px rgba(15, 23, 42, 0.13)',
    padding: '0.55rem',
    zIndex: 200,
  },
  accountIdentity: {
    padding: '0.55rem 0.6rem 0.7rem',
    borderBottom: '1px solid #f1f5f9',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.15rem',
  },
  identityName: { fontSize: '0.82rem', color: '#0f172a' },
  identityEmail: {
    fontSize: '0.72rem',
    color: '#64748b',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  signOutButton: {
    width: '100%',
    textAlign: 'left',
    marginTop: '0.45rem',
    padding: '0.55rem 0.6rem',
    borderRadius: '6px',
    color: '#b91c1c',
    fontSize: '0.8rem',
    fontWeight: 600,
  },
  mobileMenuBtn: { display: 'none', color: '#334155', padding: '0.25rem' },
  mobileDropdown: {
    position: 'absolute',
    top: 'var(--header-height, 58px)',
    left: 0,
    right: 0,
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    padding: '1.1rem 1.5rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.65rem',
    boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  },
  mobileNavLink: {
    padding: '0.5rem 0',
    fontSize: '0.94rem',
    color: '#334155',
    textDecoration: 'none',
    borderBottom: '1px solid #f1f5f9',
  },
  mobileSignInBtn: {
    textAlign: 'left',
    padding: '0.55rem 0',
    color: '#0f766e',
    fontSize: '0.94rem',
    fontWeight: 700,
    borderBottom: '1px solid #f1f5f9',
  },
  mobileAccountBlock: {
    padding: '0.65rem 0',
    borderBottom: '1px solid #f1f5f9',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '1rem',
  },
  mobileAccountIdentity: { display: 'flex', alignItems: 'center', gap: '0.65rem', minWidth: 0 },
  mobileSignOutBtn: { color: '#b91c1c', fontSize: '0.8rem', fontWeight: 700, whiteSpace: 'nowrap' },
  mobileChatBtn: {
    marginTop: '0.4rem',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    padding: '0.65rem',
    borderRadius: '6px',
    fontWeight: '600',
  },
};
