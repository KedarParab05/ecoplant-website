# 🌿 EcoPlant Pro — Node.js Backend

A secure, scalable Express.js API for the EcoPlant plant e-commerce platform.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
cd backend
npm install
```

### 2. Configure environment
```bash
copy .env.example .env   # Windows
```
Open `.env` and fill in your real keys (see below).

### 3. Start the server
```bash
npm start          # production
npm run dev        # development (auto-reload with nodemon)
```

Server runs at **http://localhost:5000**

---

## 🔑 Environment Variables (`.env`)

| Variable | Description |
|---|---|
| `PORT` | Server port (default: 5000) |
| `JWT_SECRET` | Long random string for signing JWTs |
| `ANTHROPIC_API_KEY` | From [console.anthropic.com](https://console.anthropic.com) |
| `RAZORPAY_KEY_ID` | From [dashboard.razorpay.com](https://dashboard.razorpay.com/app/keys) |
| `RAZORPAY_KEY_SECRET` | Razorpay secret key |
| `FRONTEND_URL` | Frontend origin for CORS (e.g. `http://localhost:5500`) |
| `ADMIN_SECRET` | Secret header value for admin endpoints |

---

## 📡 API Reference

### Auth — `/api/auth`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/signup` | — | Register new account |
| POST | `/signin` | — | Sign in, returns JWT |
| POST | `/forgot` | — | Send password reset link |
| POST | `/reset` | — | Reset password with token |
| GET | `/me` | ✅ | Get current user profile |
| PUT | `/me` | ✅ | Update name, email, password |

### AI Chat — `/api/chat`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/` | — | EcoBot conversation (Claude) |

**Body:** `{ messages: [{role, content}] }`

### Plant Doctor — `/api/doctor`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/` | — | Diagnose plant from image |

**Body:** `{ image: "<base64>", mimeType: "image/jpeg" }`

### Room Design — `/api/room`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/photo` | — | Design from uploaded photo |
| POST | `/describe` | — | Design from text description |

### Orders — `/api/orders`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/create-order` | — | Create Razorpay order |
| POST | `/verify` | — | Verify payment & save order |
| GET | `/` | ✅ | List my orders |
| GET | `/:id` | ✅ | Get single order |

### Newsletter — `/api/newsletter`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/subscribe` | — | Subscribe email |
| POST | `/unsubscribe` | — | Unsubscribe email |
| GET | `/subscribers` | Admin | List all subscribers |

### Reviews — `/api/reviews`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/:plantId` | — | Get reviews + stats for a plant |
| POST | `/:plantId` | ✅ | Submit a review |
| DELETE | `/:reviewId` | ✅ | Delete own review |

### Plants — `/api/plants`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | — | List plants (filter, sort, paginate) |
| GET | `/:id` | — | Single plant + related plants |

### Health — `/api/health`
```
GET http://localhost:5000/api/health
```

---

## 🗂 Directory Structure

```
backend/
├── data/
│   └── plants.js          ← Plant catalogue data
├── db/
│   ├── db.js              ← File-based JSON database
│   └── db.json            ← Auto-generated database file (gitignored)
├── middleware/
│   └── auth.js            ← JWT authentication middleware
├── routes/
│   ├── auth.js            ← Auth endpoints
│   ├── chat.js            ← EcoBot AI chat
│   ├── doctor.js          ← Plant Doctor AI vision
│   ├── room.js            ← Room Design AI
│   ├── orders.js          ← Razorpay orders
│   ├── newsletter.js      ← Newsletter subscriptions
│   ├── plants.js          ← Plant catalogue API
│   └── reviews.js         ← Product reviews
├── server.js              ← Main Express app
├── .env                   ← Your secrets (gitignored)
├── .env.example           ← Template to copy from
└── package.json
```

---

## 💡 Notes

- **No Razorpay key?** The backend returns a mock order so you can test the checkout flow without real payments.
- **No Anthropic key?** Chat, Doctor, and Room Design will return a friendly "service unavailable" message instead of crashing.
- **Database:** Data is stored in `db/db.json`. For production, replace `db/db.js` with a MongoDB/PostgreSQL adapter.
- **Rate limits:** AI endpoints are limited to 10 requests/min per IP. General API is limited to 200 requests/15min.
