/**
 * middleware/auth.js — JWT authentication middleware
 */

const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'ecoplant_universal_dev_secret_2024';

/**
 * Verifies the Bearer token in the Authorization header.
 * Attaches `req.user = { id, email, name }` on success.
 */
function requireAuth(req, res, next) {
  const header = req.headers.authorization || '';
  const token  = header.startsWith('Bearer ') ? header.slice(7) : null;

  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }

  try {
    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

/**
 * Optional auth — attaches user if token present, otherwise continues.
 */
function optionalAuth(req, res, next) {
  const header = req.headers.authorization || '';
  const token  = header.startsWith('Bearer ') ? header.slice(7) : null;
  if (token) {
    try { req.user = jwt.verify(token, JWT_SECRET); } catch {}
  }
  next();
}

module.exports = { requireAuth, optionalAuth };
