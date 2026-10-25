import { useSyncExternalStore } from 'react';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import AccountActionPage from './pages/AccountActionPage';
import SignInPage from './pages/SignInPage';
import ChatModal from './components/ChatModal';
import Footer from './components/Footer';
import { useAuth } from './auth/AuthContext';

function subscribe(listener) {
  window.addEventListener('popstate', listener);
  window.addEventListener('hashchange', listener);
  return () => {
    window.removeEventListener('popstate', listener);
    window.removeEventListener('hashchange', listener);
  };
}
function locationSnapshot() {
  return window.location.pathname + window.location.hash;
}
function navigate(view) {
  const routes = { home: '/', about: '/about', signin: '/signin', chat: '/#chat' };
  window.history.pushState(null, '', routes[view] || '/');
  window.dispatchEvent(new PopStateEvent('popstate'));
}

export default function App() {
  const location = useSyncExternalStore(subscribe, locationSnapshot, () => '/');
  const { user, loading, isAuthenticated, signOut } = useAuth();
  const wantsChat = location.endsWith('#chat');
  const account = location.includes('#/account/');
  const view = account
    ? 'account'
    : wantsChat && !isAuthenticated
      ? 'signin'
      : location.startsWith('/signin')
        ? 'signin'
        : location.startsWith('/about')
          ? 'about'
          : 'home';
  const openChat = () => navigate('chat');
  async function handleSignOut() {
    const result = await signOut();
    if (result.success) navigate('home');
    else window.alert(result.error);
  }
  let page;
  if (account) page = <AccountActionPage onDone={() => navigate('signin')} />;
  else if (view === 'signin' && loading)
    page = (
      <p role="status" style={{ padding: '3rem' }}>
        Checking your session...
      </p>
    );
  else if (view === 'signin')
    page = (
      <SignInPage
        onSuccess={() => navigate(wantsChat ? 'chat' : 'home')}
        onNavigateHome={() => navigate('home')}
      />
    );
  else if (view === 'about') page = <AboutPage onStartChat={openChat} />;
  else page = <HomePage onStartChat={openChat} onNavigate={navigate} />;
  return (
    <div className="app-root">
      <Navbar
        activeTab={wantsChat && isAuthenticated ? 'chat' : view}
        isChatView={false}
        onNavigate={navigate}
        user={user}
        authLoading={loading}
        onSignOut={handleSignOut}
      />
      {page}
      {view !== 'signin' && <Footer onNavigate={navigate} />}
      <ChatModal isOpen={wantsChat && isAuthenticated} onClose={() => navigate('home')} />
    </div>
  );
}
