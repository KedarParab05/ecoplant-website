/**
 * db/mongoose.js — MongoDB connection via Mongoose
 * Falls back gracefully if MONGODB_URI is not set (uses the JSON file-based db)
 */
const mongoose = require('mongoose');

let connected = false;

async function connect() {
  if (connected) return true;
  const uri = process.env.MONGODB_URI;
  if (!uri || uri.includes('XXXX') || uri.length < 20) {
    console.warn('[mongo] MONGODB_URI not set — using file-based JSON store');
    return false;
  }
  try {
    await mongoose.connect(uri, {
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 10000,
    });
    connected = true;
    console.log('[mongo] ✅ Connected to MongoDB');
    return true;
  } catch (err) {
    console.error('[mongo] ❌ Connection failed:', err);
    return false;
  }
}

module.exports = { connect, mongoose, isConnected: () => connected };
