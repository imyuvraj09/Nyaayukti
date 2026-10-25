/**
 * API service for Nyaayukti.
 * Chat endpoints are authenticated with an opaque bearer session token.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
const AUTH_TOKEN_STORAGE_KEY = 'nyaayukti_auth_token';

// Sessions are HttpOnly cookies. Remove legacy browser-readable credentials.
try {
  localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
} catch {}
export function getStoredAuthToken() {
  return null;
}
export function storeAuthToken() {
  try {
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {}
}
function authHeaders(extra = {}) {
  return { ...extra, 'X-Nyaayukti-Request': '1', 'X-NyayaSetu-Request': '1' };
}
async function apiFetch(url, options = {}) {
  return fetch(url, {
    ...options,
    credentials: 'include',
    headers: authHeaders(options.headers || {}),
  });
}

async function readJson(response) {
  return response.json().catch(() => null);
}

function extractError(data, fallback) {
  const rawError = data?.error;
  return data?.message || (typeof rawError === 'string' ? rawError : rawError?.message) || fallback;
}

function handleAuthenticationFailure(response) {
  if (response.status === 401) {
    storeAuthToken(null);
    window.dispatchEvent(new CustomEvent('nyaayukti-auth-expired'));
  }
}

export async function registerAccount({ displayName, email, password }) {
  try {
    const response = await apiFetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ displayName, email, password }),
    });
    const data = await readJson(response);
    if (!response.ok) {
      return { success: false, error: extractError(data, 'Unable to create account.') };
    }
    const token = data?.data?.token;
    if (token) storeAuthToken(token);
    return {
      success: true,
      token,
      user: data?.data?.user,
      expiresAt: data?.data?.expiresAt,
    };
  } catch {
    return { success: false, error: 'Unable to connect to Nyaayukti backend service.' };
  }
}

export async function loginAccount({ email, password }) {
  try {
    const response = await apiFetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await readJson(response);
    if (!response.ok) {
      return { success: false, error: extractError(data, 'Unable to sign in.') };
    }
    const token = data?.data?.token;
    if (token) storeAuthToken(token);
    return {
      success: true,
      token,
      user: data?.data?.user,
      expiresAt: data?.data?.expiresAt,
    };
  } catch {
    return { success: false, error: 'Unable to connect to Nyaayukti backend service.' };
  }
}

export async function getCurrentUser() {
  try {
    const response = await apiFetch(`${API_BASE_URL}/auth/me`, {
      headers: authHeaders({ Accept: 'application/json' }),
    });
    const data = await readJson(response);
    handleAuthenticationFailure(response);
    if (!response.ok) {
      return { success: false, error: extractError(data, 'Session is no longer valid.') };
    }
    return { success: true, user: data?.data?.user };
  } catch {
    return { success: false, error: 'Unable to verify your sign-in session.' };
  }
}

export async function logoutAccount() {
  try {
    const response = await apiFetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: authHeaders({ Accept: 'application/json' }),
    });
    if (!response.ok && response.status !== 401)
      return { success: false, error: 'Sign out failed. Please retry.' };
    storeAuthToken(null);
    return { success: true };
  } catch {
    return {
      success: false,
      error: 'Unable to reach the server to end your session. Please retry.',
    };
  }
}

export async function sendChatMessage(message, sessionId = null, requestId = null) {
  const activeRequestId =
    requestId || `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 245000);

  try {
    const response = await apiFetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'X-Request-Id': activeRequestId,
      }),
      body: JSON.stringify({
        sessionId: sessionId || null,
        message,
        requestId: activeRequestId,
      }),
      signal: controller.signal,
    });

    const data = await readJson(response);
    clearTimeout(timeoutId);
    handleAuthenticationFailure(response);

    if (!response.ok) {
      return {
        success: false,
        error: extractError(data, `Server responded with error status ${response.status}`),
        authRequired: response.status === 401,
        sessionId: response.headers.get('X-Conversation-Id'),
      };
    }

    return {
      success: true,
      sessionId: data.sessionId || data.data?.sessionId,
      message: data.message || data.data?.message,
      userMessage: data.userMessage || data.data?.userMessage,
    };
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      return {
        success: false,
        error: 'The AI legal analysis timed out. Please try asking a more specific question.',
      };
    }
    return { success: false, error: 'Unable to connect to Nyaayukti backend service.' };
  }
}

export async function getChatSession(sessionId) {
  try {
    const response = await apiFetch(`${API_BASE_URL}/chat/${sessionId}`, {
      headers: authHeaders({ Accept: 'application/json' }),
    });
    const data = await readJson(response);
    handleAuthenticationFailure(response);
    if (!response.ok) {
      return {
        success: false,
        error: extractError(data, 'Failed to retrieve session'),
        authRequired: response.status === 401,
        sessionId: response.headers.get('X-Conversation-Id'),
      };
    }
    return {
      success: true,
      session: data.data?.session,
      messages: data.data?.messages || [],
    };
  } catch {
    return { success: false, error: 'Network error retrieving session history' };
  }
}

export async function listChatSessions(page = 1, limit = 20) {
  try {
    const response = await apiFetch(`${API_BASE_URL}/chats?page=${page}&limit=${limit}`, {
      headers: authHeaders({ Accept: 'application/json' }),
    });
    const data = await readJson(response);
    handleAuthenticationFailure(response);
    return {
      success: response.ok,
      sessions: data?.data?.sessions || [],
      total: data?.data?.total || 0,
      error: response.ok ? null : extractError(data, 'Unable to load conversations.'),
      authRequired: response.status === 401,
    };
  } catch {
    return {
      success: false,
      sessions: [],
      total: 0,
      error: 'Network error loading conversations.',
    };
  }
}

export async function deleteChatSession(sessionId) {
  try {
    const response = await apiFetch(`${API_BASE_URL}/chat/${sessionId}`, {
      method: 'DELETE',
      headers: authHeaders({ Accept: 'application/json' }),
    });
    const data = await readJson(response);
    handleAuthenticationFailure(response);
    return {
      success: response.ok,
      error: response.ok ? null : extractError(data, 'Unable to delete conversation.'),
      authRequired: response.status === 401,
    };
  } catch {
    return { success: false, error: 'Network error deleting session' };
  }
}

export async function checkBackendHealth() {
  try {
    const response = await apiFetch(`${API_BASE_URL}/health`, {
      headers: { Accept: 'application/json' },
    });
    const data = await response.json();
    return {
      healthy: response.ok && data.status === 'healthy',
      databaseConnected: !!data.database?.connected,
    };
  } catch {
    return { healthy: false, databaseConnected: false };
  }
}

export { API_BASE_URL, AUTH_TOKEN_STORAGE_KEY };

export async function accountAction(action, payload = {}) {
  try {
    const response = await apiFetch(`${API_BASE_URL}/auth/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await readJson(response);
    return {
      success: response.ok,
      message: data?.message,
      error: response.ok ? null : extractError(data, 'Unable to complete account action.'),
    };
  } catch {
    return { success: false, error: 'Unable to reach the account service.' };
  }
}
