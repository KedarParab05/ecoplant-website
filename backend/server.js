/**
 * server.js â€” EcoPlant Pro Â· Node.js Backend
 * â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
 * Endpoints:
 *   POST /api/auth/signup
 *   POST /api/auth/signin
 *   POST /api/auth/forgot
 *   POST /api/auth/reset
 *   GET  /api/auth/me
 *   PUT  /api/auth/me
 *
 *   POST /api/chat
 *   POST /api/doctor
 *   POST /api/chat
 *
 *   POST /api/orders/create-order
 *   POST /api/orders/verify
 *   GET  /api/orders
 *   GET  /api/orders/:id
 *
 *   POST /api/newsletter/subscribe
 *   POST /api/newsletter/unsubscribe
 *   GET  /api/newsletter/subscribers
 *
 *   GET  /api/reviews/:plantId
 *   POST /api/reviews/:plantId
 *   DELETE /api/reviews/:reviewId
 *
 *   GET  /api/plants
 *   GET  /api/plants/:id
 *
 *   GET  /api/health
 */

require('dotenv').config();

const express    = require('express');
const cors       = require('cors');
const rateLimit  = require('express-rate-limit');
const path       = require('path');
const multer     = require('multer');

// â”€â”€ MongoDB (connect before routes handle requests) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const { connect: connectMongo } = require('./db/mongoose');
connectMongo(); // non-blocking; routes auto-fallback to JSON if not ready

// â”€â”€ Route imports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const authRouter       = require('./routes/auth');
const chatRouter       = require('./routes/chat');
const doctorRouter     = require('./routes/doctor');
const ordersRouter     = require('./routes/orders');
const newsletterRouter = require('./routes/newsletter');
const reviewsRouter    = require('./routes/reviews');
const plantsRouter     = require('./routes/plants');
const plantDiagnoseRouter = require('./routes/plantDiagnose');
const roomDesignRouter    = require('./routes/roomDesign');

const app  = express();
const PORT = process.env.PORT || 5000;

// â”€â”€ CORS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const allowedOrigins = new Set([
  process.env.FRONTEND_URL,
  'http://localhost:5000',
  'http://localhost:3000',
  'http://localhost:5173',
  'http://localhost:8080',
  'http://127.0.0.1:5000',
  'http://127.0.0.1:3000',
].filter(Boolean));

function isAllowedOrigin(origin) {
  if (!origin) return true;
  if (allowedOrigins.has(origin)) return true;

  // Let local dev servers work even when the port shifts (5501, 5502, etc.).
  return /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(origin);
}

app.use(cors({
  origin: (origin, cb) => {
    // Allow requests with no origin (Postman, curl, same-origin)
    if (isAllowedOrigin(origin)) return cb(null, true);
    cb(new Error(`CORS: origin ${origin} not allowed`));
  },
  credentials: true,
}));

// â”€â”€ Body parsers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Large limit for base64 image uploads (â‰ˆ10 MB raw â†’ ~14 MB base64)
app.use(express.json({ limit: '20mb' }));
app.use(express.urlencoded({ extended: true, limit: '20mb' }));

// â”€â”€ Rate limiting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const generalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 min
  max:      200,
  standardHeaders: true,
  legacyHeaders:   false,
  message: { error: 'Too many requests â€” please try again later.' },
});

const aiLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 min
  max:      10,         // 10 AI calls/min per IP
  message: { error: 'AI rate limit reached â€” please wait a moment.' },
});

app.use(generalLimiter);

// â”€â”€ Security headers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  next();
});

// â”€â”€ Request logger (dev) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if (process.env.NODE_ENV !== 'production') {
  app.use((req, _res, next) => {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
    next();
  });
}

// â”€â”€ API routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.use('/api/auth',       authRouter);
app.use('/api/chat',       aiLimiter, chatRouter);
app.use('/api/doctor',     aiLimiter, doctorRouter);
app.use('/api/orders',     ordersRouter);
app.use('/api/newsletter', newsletterRouter);
app.use('/api/reviews',    reviewsRouter);
app.use('/api/plants',     plantsRouter);
app.use('/api/plant-diagnose', aiLimiter, plantDiagnoseRouter);
app.use('/api/room-design',    aiLimiter, roomDesignRouter);

// â”€â”€ Health check â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.get('/api/health', (_req, res) => {
  const { isConnected } = require('./db/mongoose');
  res.json({
    status:    'ok',
    service:   'EcoPlant API',
    version:   '1.0.0',
    timestamp: new Date().toISOString(),
    db:        isConnected() ? 'mongodb' : 'json-file',
    ai:        { claude: !!process.env.ANTHROPIC_API_KEY },
    payments:  !!process.env.RAZORPAY_KEY_ID,
  });
});

// â”€â”€ Serve frontend static files â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// public/ lives next to server.js â€” works in both dev and production
const publicDir = path.join(__dirname, 'public');
if (require('fs').existsSync(publicDir)) {
  app.use(express.static(publicDir));
  // SPA fallback â€” return index.html for all non-API routes
  app.get(/^(?!\/api).*/, (_req, res) => {
    res.sendFile(path.join(publicDir, 'index.html'));
  });
}

// â”€â”€ 404 handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.use((req, res) => {
  res.status(404).json({ error: `Route ${req.method} ${req.path} not found` });
});

app.use((err, req, res, _next) => {
  console.error('[Global Error]', err);
  const isMultipartError = err instanceof multer.MulterError || /Multipart|Boundary|Unexpected end of form/i.test(err.message || '');
  const status = isMultipartError ? (err.code === 'LIMIT_FILE_SIZE' ? 413 : 400) : (err.status || 500);
  res.status(status).json({
    success: false,
    error: status >= 500 ? 'Internal Server Error' : 'Bad Request',
    message: isMultipartError ? 'Upload a valid JPG, PNG, or WEBP image using multipart/form-data.' : err.message,
    details: process.env.NODE_ENV === 'production' ? 'Check server logs' : err.stack
  });
});

// â”€â”€ Start server â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.listen(PORT, () => {
  const ck = process.env.ANTHROPIC_API_KEY ? 'âœ…' : 'âŒ';
  const gk = process.env.GEMINI_API_KEY    ? 'âœ…' : 'âŒ';
  const rk = process.env.RAZORPAY_KEY_ID   ? 'âœ…' : 'âŒ';
  console.log('\nâ”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”');
  console.log(`â”‚  ðŸŒ¿ EcoPlant API running on port ${PORT}                 â”‚`);
  console.log(`â”‚  ðŸ“ http://localhost:${PORT}/api/health                   â”‚`);
  console.log(`â”‚  ðŸ¤– Claude  (Chat/Doctor): ${ck} ANTHROPIC_API_KEY      â”‚`);
  console.log(`â”‚  ðŸ’³ Razorpay (Payments):  ${rk} RAZORPAY_KEY_ID        â”‚`);
  console.log('â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜\n');
});

module.exports = app;

