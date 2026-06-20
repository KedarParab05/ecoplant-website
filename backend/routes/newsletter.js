/**
 * routes/newsletter.js — Subscribe / unsubscribe (MongoDB + JSON fallback)
 */
const express = require('express');
const { isConnected } = require('../db/mongoose');

const router = express.Router();
function getSub() { return require('../db/models').Subscriber; }
const db = () => require('../db/db');

// ── POST /api/newsletter/subscribe ────────────────────────────────────────────
router.post('/subscribe', async (req, res) => {
  try {
    const { email } = req.body;
    if (!email?.includes('@')) return res.status(400).json({ error: 'Valid email is required' });

    if (isConnected()) {
      await getSub().findOneAndUpdate(
        { email: email.toLowerCase().trim() },
        { email: email.toLowerCase().trim() },
        { upsert: true, new: true }
      );
    } else {
      const store = db();
      const exists = store.findOne('subscribers', s => s.email === email.toLowerCase().trim());
      if (!exists) store.push('subscribers', { email: email.toLowerCase().trim(), createdAt: new Date().toISOString() });
    }

    res.json({ message: '🌱 Subscribed! Welcome to the EcoPlant family. Expect weekly plant love in your inbox.' });
  } catch (err) {
    if (err.code === 11000) return res.json({ message: '🌱 Already subscribed! Thank you for your enthusiasm.' });
    console.error('[newsletter/subscribe]', err);
    res.status(500).json({ error: err.message });
  }
});

// ── POST /api/newsletter/unsubscribe ──────────────────────────────────────────
router.post('/unsubscribe', async (req, res) => {
  try {
    const { email } = req.body;
    if (!email) return res.status(400).json({ error: 'Email is required' });

    if (isConnected()) {
      await getSub().deleteOne({ email: email.toLowerCase().trim() });
    } else {
      db().remove('subscribers', s => s.email === email.toLowerCase().trim());
    }
    res.json({ message: 'Unsubscribed successfully.' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── GET /api/newsletter/subscribers — Admin only ──────────────────────────────
router.get('/subscribers', async (req, res) => {
  const adminSecret = req.headers['x-admin-secret'];
  if (!adminSecret || adminSecret !== process.env.ADMIN_SECRET)
    return res.status(403).json({ error: 'Forbidden' });

  try {
    let subscribers;
    if (isConnected()) {
      subscribers = await getSub().find().sort({ createdAt: -1 }).lean();
    } else {
      subscribers = db().get('subscribers');
    }
    res.json({ subscribers, total: subscribers.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
