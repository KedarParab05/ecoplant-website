/**
 * routes/plants.js — Plant catalogue API (mirrors the frontend PLANTS array)
 *
 * GET  /api/plants            → list plants (filter, sort, paginate)
 * GET  /api/plants/:id        → single plant detail
 * GET  /api/plants/search     → search by name / scientific name
 */

const express = require('express');
const PLANTS  = require('../data/plants');   // plant data module

const router = express.Router();

// ── GET /api/plants ───────────────────────────────────────────────────────────
router.get('/', (req, res) => {
  try {
    let list = [...PLANTS];

    const { filter, sort, page = 1, limit = 12, q } = req.query;

    // ── Text search ──
    if (q) {
      const query = q.toLowerCase();
      list = list.filter(p =>
        p.name.toLowerCase().includes(query) ||
        p.sci.toLowerCase().includes(query) ||
        p.tags.some(t => t.toLowerCase().includes(query))
      );
    }

    // ── Category filter ──
    if (filter && filter !== 'all') {
      switch (filter) {
        case 'air':      list = list.filter(p => p.air); break;
        case 'pet':      list = list.filter(p => p.pet); break;
        case 'low':      list = list.filter(p => p.maint === 'low'); break;
        case 'beginner': list = list.filter(p => p.tags.includes('beginner')); break;
        default:         list = list.filter(p => p.tags.includes(filter));
      }
    }

    // ── Sort ──
    switch (sort) {
      case 'price-asc':  list.sort((a, b) => a.price - b.price); break;
      case 'price-desc': list.sort((a, b) => b.price - a.price); break;
      case 'name':       list.sort((a, b) => a.name.localeCompare(b.name)); break;
      case 'rating':     list.sort((a, b) => b.rating - a.rating); break;
      case 'co2':        list.sort((a, b) => b.co2 - a.co2); break;
      default: break; // featured order
    }

    // ── Paginate ──
    const total     = list.length;
    const pageNum   = Math.max(1, parseInt(page, 10));
    const limitNum  = Math.min(50, Math.max(1, parseInt(limit, 10)));
    const offset    = (pageNum - 1) * limitNum;
    const paginated = list.slice(offset, offset + limitNum);

    res.json({
      plants:   paginated,
      total,
      page:     pageNum,
      limit:    limitNum,
      pages:    Math.ceil(total / limitNum),
    });
  } catch (err) {
    console.error('[plants]', err);
    res.status(500).json({ error: 'Could not fetch plants' });
  }
});

// ── GET /api/plants/:id ───────────────────────────────────────────────────────
router.get('/:id', (req, res) => {
  const id   = parseInt(req.params.id, 10);
  const plant = PLANTS.find(p => p.id === id);
  if (!plant) return res.status(404).json({ error: 'Plant not found' });

  // Related plants: same tags, excluding this plant
  const related = PLANTS
    .filter(p => p.id !== id && p.tags.some(t => plant.tags.includes(t)))
    .slice(0, 4);

  res.json({ plant, related });
});

module.exports = router;
