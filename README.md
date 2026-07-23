# 🌿 EcoPlant Pro

**Premium indoor plants delivered across India** — a full-stack e-commerce platform with AI-powered plant care.

🔗 **Live Site:** [https://ecoplant-pro.vercel.app](https://ecoplant-pro.vercel.app)

---

## ✨ Features

- 🛒 **Shop** — Browse 24+ curated indoor plants with filters (sun, care, pet-friendly)
- 🤖 **EcoBot AI** — Gemini-powered chatbot for plant care questions
- 🩺 **Plant Doctor** — Upload a photo for AI health diagnosis and treatment plan
- 🎯 **Plant Quiz** — 4-question quiz for personalised plant recommendations
- 💳 **Razorpay Payments** — Secure UPI/card checkout
- 👤 **Auth** — Email signup/login with JWT; Google SSO ready
- 📱 **Wishlist & Orders** — Save favourites, view order history
- 📧 **Newsletter** — Email subscription with unsubscribe
- 🌙 **Dark-mode ready** — CSS custom properties throughout

---

## 🏗 Architecture

```
ecoplant-website/
├── index.html          # Main SPA (shop, cart, auth, chatbot)
├── quiz.html           # Plant quiz page
├── doctor.html         # Plant Doctor AI page
├── plants-imgs/        # Optimised plant images
│
├── api/                # Python/FastAPI backend (Vercel serverless)
│   ├── index.py        # Entry point
│   ├── main.py         # FastAPI app + security middleware
│   ├── db/             # MongoDB (motor) + JSON fallback
│   ├── middleware/     # Auth, security, validators
│   └── routers/        # auth, plants, orders, reviews, chat, doctor...
│
├── python-backend/     # Local dev copy (same as api/)
├── backend/            # Legacy Node.js/Express (local dev only)
│
├── requirements.txt    # Python dependencies
├── vercel.json         # Vercel deployment config
└── package.json        # Root (minimal, no build step)
```

---

## 🚀 Local Development

### Python backend (production-equivalent)
```bash
# Install deps
pip install -r requirements.txt

# Run
cd python-backend
uvicorn main:app --reload --port 8000
```

Or use the provided script:
```bash
start_python.bat
```

### Frontend
Open `index.html` directly in a browser, or use Live Server. Configure `API_BASE` in the `<script>` section if needed.

---

## 🔐 Environment Variables

Create `python-backend/.env` (or `api/.env`):

```env
MONGODB_URI=mongodb+srv://...
JWT_SECRET=your-very-strong-secret-min-32-chars
GEMINI_API_KEY=your-gemini-key
RAZORPAY_KEY_ID=rzp_live_...
RAZORPAY_KEY_SECRET=your-secret
ADMIN_SECRET=your-admin-panel-secret
ROBOFLOW_API_KEY=your-roboflow-key
```

**⚠️ Never commit `.env` files. See `.gitignore`.**

---

## 🔒 Security

- **Backend:** FastAPI + custom `SecurityMiddleware` (XSS/NoSQL injection blocking, CSP, HSTS, brute-force lockout, bcrypt-12, JWT)
- **Frontend:** Input sanitization, `textContent` for user-derived content, `rel="noopener noreferrer"` on external links
- **Vercel Edge:** HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy applied globally
- **Rate limits:** 10/min on AI endpoints, 5/min on newsletter, brute-force lockout on auth

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, Vanilla CSS, Vanilla JS |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Database | MongoDB (motor async) + JSON fallback |
| AI | Google Gemini 2.0 Flash |
| Payments | Razorpay |
| Auth | JWT (python-jose) + bcrypt |
| Hosting | Vercel (serverless Python functions) |

---

## 📜 License

MIT — feel free to use and adapt.
