class SimpleCache {
  constructor(ttlMs) {
    this.ttlMs = ttlMs;
    this.items = new Map();
  }

  get(key) {
    const item = this.items.get(key);
    if (!item) return null;
    if (Date.now() > item.expiresAt) {
      this.items.delete(key);
      return null;
    }
    return item.value;
  }

  set(key, value) {
    this.items.set(key, { value, expiresAt: Date.now() + this.ttlMs });
  }
}

module.exports = { SimpleCache };
