/**
 * routes/plantDiagnose.js - AI Plant Diagnosis via Gemini Vision
 * POST /api/plant-diagnose  { image: base64string }
 * Delegates to /api/doctor pattern using Gemini 2.0 Flash Vision
 * No mock data - real AI results only.
 */

const express = require('express');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const router = express.Router();

let genAI = null;
function getClient() {
  if (!genAI && process.env.GEMINI_API_KEY) {
    genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
  }
  return genAI;
}

const DOCTOR_PROMPT = `You are an expert botanist and plant pathologist with 20+ years of experience.
Analyse this plant image and return ONLY valid JSON (no markdown, no code blocks):

{
  "plantName": "Common plant name",
  "scientificName": "Genus species",
  "confidence": 87,
  "healthStatus": "Healthy",
  "healthScore": 87,
  "healthDotClass": "ok",
  "diagnosis": "Precise 1-2 sentence diagnosis based on what you actually see.",
  "issues": ["Issue 1 if any"],
  "treatments": [
    "Specific actionable step 1",
    "Specific actionable step 2",
    "Specific actionable step 3"
  ]
}

Rules:
- healthDotClass: exactly "ok" (80-100), "warn" (40-79), or "bad" (0-39)
- healthScore: integer 0-100 reflecting actual observed health
- confidence: integer 0-100 for species identification confidence
- issues: empty array [] if plant is healthy
- treatments: 2-4 precise, actionable steps specific to what you observe
- If image does not show a plant: plantName "No plant detected", healthStatus "Unknown", healthScore 0`;

function parseJSON(raw) {
  return JSON.parse(raw.replace(/^```(?:json)?\n?/i, '').replace(/\n?```$/, '').trim());
}

router.post('/', async (req, res) => {
  try {
    const { image } = req.body;
    if (!image) return res.status(400).json({ error: 'image (base64) is required' });
    if (image.length > 14_000_000) return res.status(413).json({ error: 'Image too large. Max 10 MB.' });

    const client = getClient();
    if (!client) return res.status(503).json({ error: 'AI not configured - add GEMINI_API_KEY to .env' });

    const model = client.getGenerativeModel({ model: 'gemini-3.8-flash' });
    const result = await model.generateContent([
      { inlineData: { data: image, mimeType: 'image/jpeg' } },
      { text: DOCTOR_PROMPT },
    ]);

    const raw = result.response.text();
    let parsed;
    try { parsed = parseJSON(raw); }
    catch (e) { return res.status(500).json({ error: 'Failed to parse AI response', raw }); }

    return res.json({ result: parsed });
  } catch (err) {
    console.error('[plant-diagnose]', err.message);
    if (err.status === 429 || err.message?.includes('quota')) {
      return res.status(429).json({ error: 'AI quota reached. Please try again shortly.' });
    }
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;

