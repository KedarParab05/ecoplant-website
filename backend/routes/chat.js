/**
 * routes/chat.js — EcoBot AI chat (Gemini-powered)
 * POST /api/chat  { messages: [{role, content}] }
 */

const express   = require('express');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const router = express.Router();

// Lazy-init Gemini client (only if API key is set)
let genAI = null;
function getClient() {
  if (!genAI && process.env.GEMINI_API_KEY) {
    genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
  }
  return genAI;
}

const SYSTEM_PROMPT = `You are EcoBot, a friendly and knowledgeable AI plant care assistant for EcoPlant — a premium Indian plant shop.

Your expertise covers:
• Plant identification and species information
• Plant health diagnosis and treatment recommendations
• Watering, fertilising, and soil advice
• Light requirements and placement guidance
• Pest and disease management
• Seasonal care tips specific to Indian climates
• Recommendations for plants based on space, experience level, and light conditions

Tone: Warm, encouraging, and practical. Use relevant plant emojis. Keep answers concise (2–4 short paragraphs max). Always end with an actionable tip.

Context: You serve Indian plant enthusiasts. Prices are in INR. Be aware of Indian seasons (Summer, Monsoon, Post-Monsoon, Winter) and Indian climate zones (tropical, subtropical, temperate).`;

// ── POST /api/chat ─────────────────────────────────────────────────────────────
router.post('/', async (req, res) => {
  try {
    const { messages } = req.body;

    if (!Array.isArray(messages) || messages.length === 0) {
      return res.status(400).json({ error: 'messages array is required' });
    }

    // Validate each message
    const valid = messages.every(
      m => m.role && ['user', 'assistant'].includes(m.role) && typeof m.content === 'string'
    );
    if (!valid) {
      return res.status(400).json({ error: 'Each message must have role (user|assistant) and content (string)' });
    }

    const client = getClient();
    if (!client) {
      // Graceful fallback when no API key configured
      return res.status(503).json({
        error: 'AI service not configured',
        reply: "I'm currently offline for maintenance 🌿 Please try again later or browse our plant collection!",
      });
    }

    // Keep last 20 messages to stay within token limits
    const trimmedMessages = messages.slice(-20);

    const model = client.getGenerativeModel({
      model: 'gemini-2.0-flash',
      systemInstruction: SYSTEM_PROMPT,
    });

    // Gemini expects role to be "user" or "model"
    const geminiHistory = trimmedMessages.slice(0, -1).map(m => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }],
    }));

    const lastMessage = trimmedMessages[trimmedMessages.length - 1].content;

    const chat = model.startChat({
      history: geminiHistory,
    });

    const result = await chat.sendMessage(lastMessage);
    const reply = result.response.text();

    res.json({ reply });
  } catch (err) {
    console.error('[chat]', err.message);

    // Return a user-friendly error rather than crashing
    if (err.status === 401 || err.message?.includes('API key')) {
      return res.status(500).json({ error: 'AI API key invalid', reply: 'AI service temporarily unavailable 🌿' });
    }
    if (err.status === 429 || err.message?.includes('quota')) {
      return res.status(429).json({ error: 'Rate limit reached', reply: 'I\'m a bit busy right now 🌿 Please try again in a moment!' });
    }
    res.status(500).json({ error: err.message, reply: 'Something went wrong. Please try again!' });
  }
});

module.exports = router;
