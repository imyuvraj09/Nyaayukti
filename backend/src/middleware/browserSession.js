const { FRONTEND_URL, NODE_ENV } = require('../config/env');
const COOKIE_NAME = 'nyaayukti_session';
const LEGACY_COOKIE_NAME = 'nyayasetu_session';
const cookieOptions = {
  httpOnly: true,
  secure: NODE_ENV === 'production',
  sameSite: 'strict',
  path: '/api',
};
function cookieToken(req) {
  const cookies = (req.headers.cookie || '').split(';').map((v) => v.trim());
  const raw =
    cookies.find((v) => v.startsWith(COOKIE_NAME + '=')) ||
    cookies.find((v) => v.startsWith(LEGACY_COOKIE_NAME + '='));
  if (!raw) return null;
  const prefix = raw.startsWith(COOKIE_NAME + '=') ? COOKIE_NAME : LEGACY_COOKIE_NAME;
  try {
    return decodeURIComponent(raw.slice(prefix.length + 1));
  } catch {
    return null;
  }
}
function setSession(res, result) {
  res.cookie(COOKIE_NAME, result.token, { ...cookieOptions, expires: new Date(result.expiresAt) });
  const { token, ...publicResult } = result;
  return publicResult;
}
function clearSession(res) {
  res.clearCookie(COOKIE_NAME, cookieOptions);
  res.clearCookie(LEGACY_COOKIE_NAME, cookieOptions);
}
function browserGuard(req, res, next) {
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) return next();
  const origin = req.headers.origin;
  const allowed = [
    FRONTEND_URL,
    ...(NODE_ENV !== 'production' ? ['http://localhost:5173', 'http://127.0.0.1:5173'] : []),
  ];
  if (origin && !allowed.includes(origin))
    return res.status(403).json({ success: false, message: 'Untrusted request origin.' });
  // Cookies are ambient credentials; require a non-simple browser request header.
  const hasReqHeader =
    req.headers['x-nyaayukti-request'] === '1' || req.headers['x-nyayasetu-request'] === '1';
  if (cookieToken(req) && !hasReqHeader) {
    return res
      .status(403)
      .json({ success: false, message: 'Missing request verification header.' });
  }
  next();
}
module.exports = { COOKIE_NAME, cookieToken, setSession, clearSession, browserGuard };
