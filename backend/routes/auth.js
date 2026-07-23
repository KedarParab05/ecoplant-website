/**
 * routes/auth.js — Signup, Signin, Google OAuth, Forgot, Reset, Me (GET/PUT)
 * Uses MongoDB when MONGODB_URI is set, falls back to JSON file store.
 */
const express  = require('express');
const bcrypt   = require('bcryptjs');
const jwt      = require('jsonwebtoken');
const { v4: uuid } = require('uuid');
const { OAuth2Client } = require('google-auth-library');
const { requireAuth } = require('../middleware/auth');
const { isConnected } = require('../db/mongoose');

const router      = express.Router();
const JWT_SECRET     = process.env.JWT_SECRET || '';
if (!JWT_SECRET && process.env.NODE_ENV === 'production') { console.error('[FATAL] JWT_SECRET not set'); process.exit(1); }
const _JWT_SECRET = JWT_SECRET || 'dev-only-insecure-secret-set-JWT_SECRET-env';
const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || '';
if (!GOOGLE_CLIENT_ID) console.warn('[auth] GOOGLE_CLIENT_ID not set — Google OAuth disabled');
const SALT_ROUNDS = 12;
const googleClient = new OAuth2Client();

// ── Helper: issue JWT ─────────────────────────────────────────────────────────
function signToken(user) {
  const id = user._id?.toString() || user.id;
  return jwt.sign(
    { id, email: user.email, name: user.name },
    JWT_SECRET,
    { expiresIn: '30d' }
  );
}
function userPayload(user) {
  return { id: user._id?.toString() || user.id, name: user.name, email: user.email, createdAt: user.createdAt };
}

// ── Lazy model getter (avoids import before mongoose connects) ─────────────────
function getUser() { return require('../db/models').User; }
const db = () => require('../db/db');

// ── POST /api/auth/signup ──────────────────────────────────────────────────────
router.post('/signup', async (req, res) => {
  try {
    const { name, email, password } = req.body;

    if (!name?.trim())      return res.status(400).json({ error: 'Name is required' });
    if (!email?.includes('@')) return res.status(400).json({ error: 'Valid email is required' });
    if (!password || password.length < 6)
      return res.status(400).json({ error: 'Password must be at least 6 characters' });

    const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);

    if (isConnected()) {
      // ── MongoDB path ──────────────────────────────────────────────────────
      const User = getUser();
      const existing = await User.findOne({ email: email.toLowerCase().trim() });
      if (existing) return res.status(409).json({ error: 'Email already registered. Please sign in.' });

      const user = await User.create({
        name: name.trim(), email: email.toLowerCase().trim(), passwordHash,
      });
      return res.status(201).json({ message: 'Account created!', token: signToken(user), user: userPayload(user) });

    } else {
      // ── JSON fallback ─────────────────────────────────────────────────────
      const store = db();
      const existing = store.findOne('users', u => u.email === email.toLowerCase().trim());
      if (existing) return res.status(409).json({ error: 'Email already registered. Please sign in.' });

      const user = store.push('users', {
        id: uuid(), name: name.trim(),
        email: email.toLowerCase().trim(), passwordHash,
        createdAt: new Date().toISOString(),
      });
      return res.status(201).json({ message: 'Account created!', token: signToken(user), user: userPayload(user) });
    }
  } catch (err) {
    if (err.code === 11000) return res.status(409).json({ error: 'Email already registered. Please sign in.' });
    console.error('[auth/signup]', err);
    res.status(500).json({ error: 'Server error. Please try again.' });
  }
});

// ── POST /api/auth/signin ──────────────────────────────────────────────────────
router.post('/signin', async (req, res) => {
  try {
    const { email, password } = req.body;
    if (!email || !password) return res.status(400).json({ error: 'Email and password are required' });

    let user;
    if (isConnected()) {
      user = await getUser().findOne({ email: email.toLowerCase().trim() });
    } else {
      user = db().findOne('users', u => u.email === email.toLowerCase().trim());
    }

    if (!user) return res.status(401).json({ error: 'Invalid email or password' });

    const match = await bcrypt.compare(password, user.passwordHash);
    if (!match)  return res.status(401).json({ error: 'Invalid email or password' });

    res.json({ message: 'Signed in!', token: signToken(user), user: userPayload(user) });
  } catch (err) {
    console.error('[auth/signin] CRITICAL ERROR:', err);
    res.status(500).json({ error: 'Server error: ' + err.message });
  }
});

// ── POST /api/auth/forgot ──────────────────────────────────────────────────────
router.post('/forgot', async (req, res) => {
  try {
    const { email } = req.body;
    if (!email) return res.status(400).json({ error: 'Email is required' });

    let user;
    if (isConnected()) {
      user = await getUser().findOne({ email: email.toLowerCase().trim() });
    } else {
      user = db().findOne('users', u => u.email === email.toLowerCase().trim());
    }

    // Always return success to prevent email enumeration
    if (!user) return res.json({ message: 'If that email is registered, a reset link has been sent.' });

    const resetToken = jwt.sign({ id: user._id?.toString() || user.id, type: 'reset' }, JWT_SECRET, { expiresIn: '1h' });
    // TODO: Send email via SendGrid/Nodemailer — token intentionally NOT logged for security

    res.json({ message: 'If that email is registered, a reset link has been sent.' });
  } catch (err) {
    console.error('[auth/forgot]', err);
    res.status(500).json({ error: 'Server error' });
  }
});

// ── POST /api/auth/reset ───────────────────────────────────────────────────────
router.post('/reset', async (req, res) => {
  try {
    const { token, password } = req.body;
    if (!token || !password) return res.status(400).json({ error: 'token and password are required' });
    if (password.length < 6)  return res.status(400).json({ error: 'Password must be at least 6 characters' });

    let payload;
    try { payload = jwt.verify(token, JWT_SECRET); }
    catch { return res.status(400).json({ error: 'Reset link is invalid or has expired' }); }
    if (payload.type !== 'reset') return res.status(400).json({ error: 'Invalid reset token' });

    const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);
    if (isConnected()) {
      await getUser().findByIdAndUpdate(payload.id, { passwordHash });
    } else {
      db().update('users', u => u.id === payload.id, () => ({ passwordHash }));
    }

    res.json({ message: 'Password reset! Please sign in with your new password.' });
  } catch (err) {
    console.error('[auth/reset]', err);
    res.status(500).json({ error: 'Server error' });
  }
});

// ── GET /api/auth/me ───────────────────────────────────────────────────────────
router.get('/me', requireAuth, async (req, res) => {
  try {
    let user;
    if (isConnected()) {
      user = await getUser().findById(req.user.id).select('-passwordHash');
    } else {
      user = db().findOne('users', u => u.id === req.user.id);
    }
    if (!user) return res.status(404).json({ error: 'User not found' });
    res.json({ user: userPayload(user) });
  } catch (err) {
    console.error('[auth/me]', err);
    res.status(500).json({ error: 'Server error' });
  }
});

// ── PUT /api/auth/me ───────────────────────────────────────────────────────────
router.put('/me', requireAuth, async (req, res) => {
  try {
    const { name, email, currentPassword, newPassword } = req.body;
    if (!name?.trim() || !email?.includes('@'))
      return res.status(400).json({ error: 'Valid name and email are required' });

    let user;
    if (isConnected()) {
      user = await getUser().findById(req.user.id);
    } else {
      user = db().findOne('users', u => u.id === req.user.id);
    }
    if (!user) return res.status(404).json({ error: 'User not found' });

    const updates = { name: name.trim(), email: email.toLowerCase().trim() };

    if (newPassword) {
      if (!currentPassword) return res.status(400).json({ error: 'Current password is required' });
      const match = await bcrypt.compare(currentPassword, user.passwordHash);
      if (!match) return res.status(401).json({ error: 'Current password is incorrect' });
      if (newPassword.length < 6) return res.status(400).json({ error: 'New password must be at least 6 characters' });
      updates.passwordHash = await bcrypt.hash(newPassword, SALT_ROUNDS);
    }

    let updated;
    if (isConnected()) {
      updated = await getUser().findByIdAndUpdate(req.user.id, updates, { new: true });
    } else {
      db().update('users', u => u.id === req.user.id, () => updates);
      updated = db().findOne('users', u => u.id === req.user.id);
    }

    res.json({ message: 'Profile updated!', user: userPayload(updated) });
  } catch (err) {
    if (err.code === 11000) return res.status(409).json({ error: 'Email already in use' });
    console.error('[auth/me PUT]', err);
    res.status(500).json({ error: 'Server error' });
  }
});

// ── POST /api/auth/google ─────────────────────────────────────────────────────
router.post('/google', async (req, res) => {
  try {
    const { credential } = req.body;
    if (!credential) return res.status(400).json({ error: 'Google credential is required' });
    if (!GOOGLE_CLIENT_ID) return res.status(500).json({ error: 'Google Sign-In is not configured on the server' });

    // Verify the Google ID token
    let ticket;
    try {
      ticket = await googleClient.verifyIdToken({
        idToken:  credential,
        audience: GOOGLE_CLIENT_ID,
      });
    } catch {
      return res.status(401).json({ error: 'Invalid Google credential. Please try again.' });
    }

    const payload = ticket.getPayload();
    const googleId = payload.sub;
    const email    = payload.email?.toLowerCase().trim();
    const name     = payload.name || payload.email?.split('@')[0] || 'EcoPlant User';

    if (!email) return res.status(400).json({ error: 'Could not retrieve email from Google account' });

    let user;
    let isNew = false;

    if (isConnected()) {
      const User = getUser();
      user = await User.findOne({ email });
      if (!user) {
        // Create account — no passwordHash needed for OAuth users
        user = await User.create({
          name,
          email,
          passwordHash: await bcrypt.hash(googleId + JWT_SECRET, SALT_ROUNDS), // non-guessable
        });
        isNew = true;
      }
    } else {
      const store = db();
      user = store.findOne('users', u => u.email === email);
      if (!user) {
        user = store.push('users', {
          id: uuid(), name, email,
          passwordHash: '',
          createdAt: new Date().toISOString(),
        });
        isNew = true;
      }
    }

    const status = isNew ? 201 : 200;
    const message = isNew ? 'Account created with Google!' : 'Signed in with Google!';
    return res.status(status).json({ message, token: signToken(user), user: userPayload(user), isNew });

  } catch (err) {
    console.error('[auth/google]', err);
    res.status(500).json({ error: 'Server error during Google Sign-In. Please try again.' });
  }
});

module.exports = router;
