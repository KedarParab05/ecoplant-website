/**
 * routes/orders.js — Razorpay payments + order management (MongoDB + JSON fallback)
 */
const express  = require('express');
const crypto   = require('crypto');
const { v4: uuid } = require('uuid');
const { requireAuth, optionalAuth } = require('../middleware/auth');
const { isConnected } = require('../db/mongoose');

const router = express.Router();

function getOrder() { return require('../db/models').Order; }
const db = () => require('../db/db');

// ── Real Razorpay key validator ────────────────────────────────────────────────
function isRealKey(id, secret) {
  if (!id || !secret) return false;
  if (id.includes('XXXX') || secret.includes('XXXX')) return false;
  if (id.length < 20 || secret.length < 20) return false;
  if (!id.startsWith('rzp_')) return false;
  return true;
}

let razorpay = null;
function getRazorpay() {
  const id = process.env.RAZORPAY_KEY_ID, secret = process.env.RAZORPAY_KEY_SECRET;
  if (!isRealKey(id, secret)) return null;
  if (!razorpay) {
    try { razorpay = new (require('razorpay'))({ key_id: id, key_secret: secret }); }
    catch { return null; }
  }
  return razorpay;
}

// ── POST /api/orders/create-order ─────────────────────────────────────────────
router.post('/create-order', optionalAuth, async (req, res) => {
  try {
    const { amount, currency = 'INR', receipt } = req.body;
    if (!amount || amount < 1) return res.status(400).json({ error: 'amount > 0 is required' });

    const rz = getRazorpay();
    if (!rz) {
      const mockOrder = {
        id: `order_mock_${uuid().replace(/-/g,'').slice(0,16)}`,
        amount: Math.round(amount * 100),
        currency, receipt: receipt || uuid(), status: 'created', _mock: true,
      };
      console.warn('[orders] No real Razorpay key — returning mock order');
      return res.json({ order: mockOrder, key: 'rzp_test_MOCK', mock: true });
    }

    const order = await rz.orders.create({
      amount: Math.round(amount * 100), currency, receipt: receipt || uuid(),
    });
    res.json({ order, key: process.env.RAZORPAY_KEY_ID });
  } catch (err) {
    console.error('[orders/create-order]', err);
    res.status(500).json({ error: err.error?.description || err.message });
  }
});

// ── POST /api/orders/verify ───────────────────────────────────────────────────
router.post('/verify', optionalAuth, async (req, res) => {
  try {
    const { razorpay_order_id, razorpay_payment_id, razorpay_signature, items = [], address = {}, total = 0 } = req.body;
    const secret = process.env.RAZORPAY_KEY_SECRET;

    // Verify signature (skip for mock orders)
    const isMock = !razorpay_order_id || razorpay_order_id.includes('mock') || razorpay_signature === 'mock_sig';
    if (!isMock && secret && isRealKey(process.env.RAZORPAY_KEY_ID, secret)) {
      const expected = crypto.createHmac('sha256', secret)
        .update(`${razorpay_order_id}|${razorpay_payment_id}`).digest('hex');
      if (expected !== razorpay_signature)
        return res.status(400).json({ error: 'Payment verification failed — invalid signature' });
    }

    const userId = req.user?.id || null;
    let order;

    if (isConnected()) {
      const Order = getOrder();
      order = await Order.create({
        userId: userId || undefined,
        razorpayOrderId:   razorpay_order_id  || '',
        razorpayPaymentId: razorpay_payment_id || '',
        items, address, total, status: 'paid',
      });
    } else {
      order = db().push('orders', {
        id: uuid(), userId,
        razorpayOrderId: razorpay_order_id || '',
        razorpayPaymentId: razorpay_payment_id || '',
        items, address, total, status: 'paid',
        createdAt: new Date().toISOString(),
      });
    }

    const orderId = order._id?.toString() || order.id;
    res.json({ success: true, message: '🌿 Order placed! Your plants are on the way.', orderId });
  } catch (err) {
    console.error('[orders/verify]', err);
    res.status(500).json({ error: err.message });
  }
});

// ── GET /api/orders — My orders ───────────────────────────────────────────────
router.get('/', requireAuth, async (req, res) => {
  try {
    let orders;
    if (isConnected()) {
      orders = await getOrder().find({ userId: req.user.id }).sort({ createdAt: -1 }).lean();
      orders = orders.map(o => ({ ...o, id: o._id.toString() }));
    } else {
      orders = db().get('orders')
        .filter(o => o.userId === req.user.id)
        .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    }
    res.json({ orders });
  } catch (err) {
    console.error('[orders GET /]', err);
    res.status(500).json({ error: err.message });
  }
});

// ── GET /api/orders/:id ───────────────────────────────────────────────────────
router.get('/:id', requireAuth, async (req, res) => {
  try {
    let order;
    if (isConnected()) {
      order = await getOrder().findOne({ _id: req.params.id, userId: req.user.id }).lean();
    } else {
      order = db().findOne('orders', o => (o.id === req.params.id) && o.userId === req.user.id);
    }
    if (!order) return res.status(404).json({ error: 'Order not found' });
    res.json({ order });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
