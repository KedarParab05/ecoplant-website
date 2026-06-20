# 🌿 EcoPlant Pro

A full-stack plant e-commerce platform with AI-powered features built to showcase modern web development skills.

**Live Demo:** [ecoplant-pro.vercel.app](https://ecoplant-pro.vercel.app)

---

## ✨ Features

- 🛍️ **Plant E-Commerce** — Browse, search, filter & buy 200+ plant varieties
- 🤖 **AI Plant Recommendations** — GPS + climate-matched plant suggestions
- 🩺 **Plant Doctor AI** — On-device 9-zone spatial analysis for plant health diagnosis (12 conditions detected)
- 🌿 **Plant Quiz** — 4-step quiz to find your perfect plant match
- 💬 **AI Chatbot** — Plant care assistant powered by LLM
- 🔐 **Authentication** — Email/password + Google OAuth (GIS)
- 🛒 **Shopping Cart** — Add, update, remove items with localStorage persistence
- ❤️ **Wishlist** — Save favourite plants
- 💳 **Payments** — Razorpay integration
- ⭐ **Reviews** — Rate and review plants
- 📧 **Newsletter** — Email subscription system
- 📱 **Fully Responsive** — Mobile-first design

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, Vanilla CSS, Vanilla JavaScript |
| Backend | Node.js, Express.js |
| Database | MongoDB (Mongoose) |
| Auth | JWT, Google Identity Services |
| AI | On-device pixel analysis engine |
| Payments | Razorpay |
| Deployment | Vercel |

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- MongoDB URI (Atlas or local)

### Installation

```bash
# Clone the repo
git clone https://github.com/KedarParab05/ecoplant-website.git
cd ecoplant-website

# Install dependencies
npm install

# Set up environment variables
cp backend/.env.example backend/.env
# Fill in your values in backend/.env

# Start development server
npm run dev
```

### Environment Variables

Create `backend/.env` with:

```env
PORT=5000
MONGODB_URI=your_mongodb_connection_string
JWT_SECRET=your_jwt_secret
GOOGLE_CLIENT_ID=your_google_client_id
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret
ANTHROPIC_API_KEY=your_anthropic_key
FRONTEND_URL=http://localhost:5000
```

---

## 📁 Project Structure

```
ecoplant-website/
├── index.html              # Main frontend (SPA)
├── quiz.html               # Plant quiz page
├── doctor.html             # Plant Doctor AI page
├── backend/
│   ├── server.js           # Express server
│   ├── public/             # Static assets
│   │   ├── index.html
│   │   ├── quiz.html
│   │   ├── doctor.html
│   │   └── plants-imgs/
│   ├── routes/             # API routes
│   │   ├── auth.js
│   │   ├── chat.js
│   │   ├── orders.js
│   │   ├── plants.js
│   │   ├── reviews.js
│   │   └── newsletter.js
│   └── db/
│       └── mongoose.js
├── vercel.json             # Deployment config
└── package.json
```

---

## 🌐 Deployment

Deployed on **Vercel** with automatic builds.

```bash
vercel --prod
```

---

## 👨‍💻 Author

**Kedar Parab** — [GitHub](https://github.com/KedarParab05)

---

*Built with 🌿 and modern web technologies*
