/**
 * routes/doctor.js — AI Plant Doctor (image analysis via Google Gemini)
 * POST /api/doctor  { image: base64string, mimeType: "image/jpeg" }
 */

const express  = require('express');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const router = express.Router();

let genAI = null;
function getClient() {
  if (!genAI && process.env.GEMINI_API_KEY) {
    genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
  }
  return genAI;
}

const DOCTOR_PROMPT = `You are an expert botanist and plant health specialist with 20+ years of experience identifying plant diseases and providing treatment advice.

Analyse the provided plant image and return ONLY valid JSON (no markdown, no code blocks, no extra text) in this EXACT format:

{
  "plantName": "Common plant name",
  "scientificName": "Genus species",
  "confidence": 87,
  "healthStatus": "Healthy",
  "healthScore": 87,
  "healthDotClass": "ok",
  "diagnosis": "Brief 1-2 sentence diagnosis of the plant's current condition.",
  "issues": ["Issue 1 if any", "Issue 2 if any"],
  "treatments": [
    "Specific actionable treatment step 1",
    "Specific actionable treatment step 2",
    "Specific actionable treatment step 3"
  ]
}

Rules:
- healthDotClass MUST be exactly "ok" (healthy), "warn" (minor issues), or "bad" (serious problems)
- healthScore: integer 0-100
- confidence: integer 0-100
- If the plant is healthy, issues array should be empty []
- treatments should always have 2-4 practical, actionable steps
- If the image doesn't show a plant, set plantName to "No plant detected" and healthStatus to "Unknown"`;

// ── JSON parse helper (strips markdown fences if present) ─────────────────────
function parseJSON(raw) {
  const cleaned = raw.replace(/^```(?:json)?\n?/i, '').replace(/\n?```$/,'').trim();
  return JSON.parse(cleaned);
}

// ── POST /api/doctor ───────────────────────────────────────────────────────────
router.post('/', async (req, res) => {
  try {
    const { image, mimeType } = req.body;

    if (!image) {
      return res.status(400).json({ error: 'image (base64) is required' });
    }

    // Validate mime type
    const allowedMimes = ['image/jpeg', 'image/png', 'image/webp'];
    const mime = allowedMimes.includes(mimeType) ? mimeType : 'image/jpeg';

    // Validate image size (max ~10 MB base64 ≈ ~7.5 MB raw)
    if (image.length > 14_000_000) {
      return res.status(413).json({ error: 'Image too large. Maximum size is 10 MB.' });
    }

    const client = getClient();
    if (!client) {
      return res.status(503).json({ error: 'AI service not configured — add GEMINI_API_KEY to .env' });
    }

    const model = client.getGenerativeModel({
      model: 'gemini-2.0-flash',
    });

    const result_gen = await model.generateContent([
      { inlineData: { data: image, mimeType: mime } },
      { text: DOCTOR_PROMPT },
    ]);

    const raw = result_gen.response.text();

    let result;
    try {
      result = parseJSON(raw);
    } catch (parseErr) {
      console.error('[doctor] JSON parse failed:', raw);
      return res.status(500).json({ error: 'Failed to parse AI response', raw: raw });
    }

    res.json({ result });
  } catch (err) {
    console.error('[doctor]', err.message);
    if (err.status === 429 || err.message?.includes('quota')) {
      return res.status(429).json({ error: 'Gemini quota reached. Please try again shortly.' });
    }
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
