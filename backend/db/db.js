/**
 * db.js — Dual-mode database
 *
 * - Development / local server  → reads & writes to db.json on disk
 * - Vercel / read-only FS       → keeps data in process memory (resets on cold start)
 *
 * For production persistence, set MONGODB_URI and the module auto-switches to MongoDB.
 */

const fs   = require('fs');
const path = require('path');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'db.json');

const DEFAULTS = {
  users:       [],
  orders:      [],
  subscribers: [],
  reviews:     [],
};

// ── In-memory store (used when FS is read-only, e.g. Vercel) ─────────────────
let _mem = null;

function isReadOnly() {
  if (process.env.VERCEL || process.env.NODE_ENV === 'production') return true;
  try {
    fs.accessSync(path.dirname(DB_PATH), fs.constants.W_OK);
    return false;
  } catch { return true; }
}

// ── Load ─────────────────────────────────────────────────────────────────────
function load() {
  // In-memory mode
  if (_mem) return _mem;
  if (isReadOnly()) {
    _mem = { ...DEFAULTS };
    console.log('[db] Read-only filesystem detected — using in-memory store (data resets on restart)');
    return _mem;
  }
  // File-based mode
  try {
    if (fs.existsSync(DB_PATH)) {
      return JSON.parse(fs.readFileSync(DB_PATH, 'utf8'));
    }
  } catch { /* ignore */ }
  return { ...DEFAULTS };
}

// ── Save ─────────────────────────────────────────────────────────────────────
function save(data) {
  if (_mem) { _mem = data; return; } // in-memory
  try {
    const dir = path.dirname(DB_PATH);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2), 'utf8');
  } catch (e) {
    // FS became read-only mid-run — switch to memory
    _mem = data;
  }
}

// ── Public API ────────────────────────────────────────────────────────────────
const db = {
  get(collection) {
    return load()[collection] || [];
  },
  set(collection, value) {
    const data = load();
    data[collection] = value;
    save(data);
  },
  push(collection, item) {
    const data = load();
    data[collection] = data[collection] || [];
    data[collection].push(item);
    save(data);
    return item;
  },
  findOne(collection, predicate) {
    return this.get(collection).find(predicate) || null;
  },
  update(collection, predicate, updater) {
    const data = load();
    data[collection] = (data[collection] || []).map(item =>
      predicate(item) ? { ...item, ...updater(item) } : item
    );
    save(data);
  },
  remove(collection, predicate) {
    const data = load();
    data[collection] = (data[collection] || []).filter(item => !predicate(item));
    save(data);
  },
};

module.exports = db;
