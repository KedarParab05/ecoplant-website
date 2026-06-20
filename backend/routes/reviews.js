/**
 * routes/reviews.js — Product reviews (MongoDB + JSON fallback)
 */
const express = require('express');
const { v4: uuid } = require('uuid');
const { requireAuth, optionalAuth } = require('../middleware/auth');
const { isConnected } = require('../db/mongoose');

const router = express.Router();
function getReview() { return require('../db/models').Review; }
const db = () => require('../db/db');

// ── GET /api/reviews/:plantId ─────────────────────────────────────────────────
router.get('/:plantId', optionalAuth, async (req, res) => {
  try {
    const plantId = parseInt(req.params.plantId, 10);
    let reviews;

    if (isConnected()) {
      reviews = await getReview().find({ plantId }).sort({ createdAt: -1 }).lean();
    } else {
      reviews = db().get('reviews').filter(r => r.plantId === plantId)
        .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    }

    const total  = reviews.length;
    const avg    = total ? (reviews.reduce((s, r) => s + r.rating, 0) / total).toFixed(1) : '0.0';
    const dist   = [5,4,3,2,1].reduce((acc, s) => {
      acc[s] = reviews.filter(r => r.rating === s).length; return acc;
    }, {});

    res.json({ reviews, total, average: parseFloat(avg), distribution: dist });
  } catch (err) {
    console.error('[reviews GET]', err);
    res.status(500).json({ error: err.message });
  }
});

// ── POST /api/reviews/:plantId ────────────────────────────────────────────────
router.post('/:plantId', requireAuth, async (req, res) => {
  try {
    const plantId = parseInt(req.params.plantId, 10);
    const { rating, text } = req.body;

    if (!rating || rating < 1 || rating > 5)
      return res.status(400).json({ error: 'Rating must be between 1 and 5' });
    if (!text?.trim() || text.trim().length < 5)
      return res.status(400).json({ error: 'Review text must be at least 5 characters' });

    if (isConnected()) {
      const Review = getReview();
      // Allow only one review per user per plant — upsert
      const review = await Review.findOneAndUpdate(
        { plantId, userId: req.user.id },
        { rating, text: text.trim(), userName: req.user.name },
        { upsert: true, new: true, setDefaultsOnInsert: true }
      );
      return res.status(201).json({ message: 'Review submitted!', review });
    } else {
      // Remove any existing review from this user for this plant
      const store = db();
      const existing = store.get('reviews').filter(r => !(r.plantId === plantId && r.userId === req.user.id));
      store.set('reviews', existing);
      const review = store.push('reviews', {
        id: uuid(), plantId, userId: req.user.id,
        userName: req.user.name || 'Anonymous',
        rating, text: text.trim(), createdAt: new Date().toISOString(),
      });
      return res.status(201).json({ message: 'Review submitted!', review });
    }
  } catch (err) {
    console.error('[reviews POST]', err);
    res.status(500).json({ error: err.message });
  }
});

// ── DELETE /api/reviews/:reviewId ─────────────────────────────────────────────
router.delete('/:reviewId', requireAuth, async (req, res) => {
  try {
    if (isConnected()) {
      const deleted = await getReview().findOneAndDelete({ _id: req.params.reviewId, userId: req.user.id });
      if (!deleted) return res.status(404).json({ error: 'Review not found' });
    } else {
      db().remove('reviews', r => r.id === req.params.reviewId && r.userId === req.user.id);
    }
    res.json({ message: 'Review deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
