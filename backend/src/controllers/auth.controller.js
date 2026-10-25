const { setSession, clearSession } = require('../middleware/browserSession');
const { authService } = require('../services/authService');
const { sendSuccess } = require('../utils/apiResponse');

function getUserAgent(req) {
  return req.headers['user-agent'] || '';
}

async function register(req, res, next) {
  try {
    const { displayName, email, password } = req.body || {};
    const result = await authService.register({
      displayName,
      email,
      password,
      userAgent: getUserAgent(req),
    });
    return sendSuccess(res, setSession(res, result), 201, 'Account created successfully');
  } catch (err) {
    return next(err);
  }
}

async function login(req, res, next) {
  try {
    const { email, password } = req.body || {};
    const result = await authService.login({
      email,
      password,
      userAgent: getUserAgent(req),
    });
    return sendSuccess(res, setSession(res, result), 200, 'Signed in successfully');
  } catch (err) {
    return next(err);
  }
}

async function me(req, res, next) {
  try {
    return sendSuccess(res, { user: authService.publicUser(req.user) }, 200);
  } catch (err) {
    return next(err);
  }
}

async function logout(req, res, next) {
  try {
    await authService.logout(req.authToken);
    clearSession(res);
    return sendSuccess(res, { signedOut: true }, 200, 'Signed out successfully');
  } catch (err) {
    return next(err);
  }
}

module.exports = {
  register,
  login,
  me,
  logout,
};
