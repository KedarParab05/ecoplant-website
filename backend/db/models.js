/**
 * db/models.js — Mongoose schemas for User, Order, Review, Subscriber
 */
const { mongoose } = require('./mongoose');
const { Schema } = mongoose;

// ── User ─────────────────────────────────────────────────────────────────────
const userSchema = new Schema({
  name:          { type: String, required: true, trim: true },
  email:         { type: String, required: true, unique: true, lowercase: true, trim: true },
  passwordHash:  { type: String, required: true },
  resetToken:    { type: String, default: null },
  resetExpiry:   { type: Date,   default: null },
}, { timestamps: true });

userSchema.index({ email: 1 }, { unique: true });

// ── Order ────────────────────────────────────────────────────────────────────
const orderSchema = new Schema({
  userId:            { type: Schema.Types.ObjectId, ref: 'User', default: null },
  razorpayOrderId:   { type: String, default: '' },
  razorpayPaymentId: { type: String, default: '' },
  items:             [{ name: String, price: Number, qty: Number, id: Number }],
  address:           {
    name: String, phone: String, email: String,
    street: String, city: String, state: String, pin: String,
  },
  total:  { type: Number, default: 0 },
  status: { type: String, default: 'paid', enum: ['pending','paid','processing','shipped','delivered','cancelled'] },
}, { timestamps: true });

// ── Review ───────────────────────────────────────────────────────────────────
const reviewSchema = new Schema({
  plantId:   { type: Number, required: true },
  userId:    { type: Schema.Types.ObjectId, ref: 'User', default: null },
  userName:  { type: String, default: 'Anonymous' },
  rating:    { type: Number, required: true, min: 1, max: 5 },
  text:      { type: String, required: true, minlength: 5, maxlength: 1000 },
}, { timestamps: true });

reviewSchema.index({ plantId: 1, userId: 1 }); // one review per user per plant

// ── Subscriber ───────────────────────────────────────────────────────────────
const subscriberSchema = new Schema({
  email: { type: String, required: true, unique: true, lowercase: true, trim: true },
}, { timestamps: true });

// Export (guard against recompile errors in dev hot-reload)
const User       = mongoose.models.User       || mongoose.model('User',       userSchema);
const Order      = mongoose.models.Order      || mongoose.model('Order',      orderSchema);
const Review     = mongoose.models.Review     || mongoose.model('Review',     reviewSchema);
const Subscriber = mongoose.models.Subscriber || mongoose.model('Subscriber', subscriberSchema);

module.exports = { User, Order, Review, Subscriber };
