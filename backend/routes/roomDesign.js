/**
 * routes/roomDesign.js - AI Room Design (Gemini Vision + Imagen Inpainting)
 * POST /api/room-design  { image: base64string, mimeType: "image/jpeg" }
 *
 * Step 1: Gemini 2.0 Flash Vision analyses the room -> returns JSON with plant placement plan
 * Step 2: For each placement, Imagen 3 inpaints a photorealistic plant into the room image
 * Step 3: Returns the final composed image + recommendations
 */

const express = require('express');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const router = express.Router();

// -- Gemini client
let genAI = null;
function getClient() {
  if (!genAI && process.env.GEMINI_API_KEY) {
    genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
  }
  return genAI;
}

// -- Gemini Vision Prompt
const ROOM_ANALYSIS_PROMPT = `You are an expert interior designer and botanist. Analyse this room photo carefully.

Return ONLY valid JSON (no markdown, no code blocks) in EXACTLY this format:

{
  "roomType": "Living Room",
  "lightLevel": "bright indirect",
  "style": "modern minimalist",
  "colorPalette": ["warm whites", "natural wood", "grey"],
  "placements": [
    {
      "plant_name": "Monstera Deliciosa",
      "scientific_name": "Monstera deliciosa",
      "location_description": "left corner near the window",
      "reason": "Thrives in bright indirect light, adds tropical drama to the neutral palette",
      "pot_style": "white ceramic pot",
      "care_level": "easy",
      "price_range": "Rs. 599 - Rs. 1,499",
      "bounding_box": { "x": 5, "y": 40, "width": 20, "height": 45 }
    },
    {
      "plant_name": "Snake Plant",
      "scientific_name": "Dracaena trifasciata",
      "location_description": "right side of the sofa",
      "reason": "Tolerates low light, architectural form complements modern furniture",
      "pot_style": "dark matte concrete pot",
      "care_level": "very easy",
      "price_range": "Rs. 349 - Rs. 899",
      "bounding_box": { "x": 70, "y": 45, "width": 15, "height": 40 }
    }
  ],
  "overall_tip": "This room would benefit most from plants with bold leaf shapes to contrast the clean lines."
}

Rules:
- Suggest 2-3 plants maximum
- bounding_box values are PERCENTAGES of the image (0-100) - place plants in empty floor/shelf spaces
- Choose plants that match the room light level and style
- Be specific about location_description (e.g. "left corner beside the bookshelf")
- Match pot_style to room aesthetics
- care_level must be one of: very easy, easy, moderate, demanding`;

// -- JSON parse helper
function parseJSON(raw) {
  const cleaned = raw
    .replace(/^```(?:json)?\n?/i, '')
    .replace(/\n?```$/, '')
    .trim();
  return JSON.parse(cleaned);
}

// -- Vertex AI Imagen Inpainting (optional)
async function callImagenInpaint({ baseImageBase64, placement }) {
  const projectId = process.env.GOOGLE_CLOUD_PROJECT || process.env.VERTEX_PROJECT_ID;
  const location = process.env.VERTEX_LOCATION || 'us-central1';
  const model = process.env.IMAGEN_MODEL || 'imagegeneration@006';

  if (!projectId) throw new Error('VERTEX_PROJECT_ID not configured');

  const { GoogleAuth } = require('google-auth-library');
  const auth = new GoogleAuth({ scopes: ['https://www.googleapis.com/auth/cloud-platform'] });
  const client = await auth.getClient();
  const tokenResult = await client.getAccessToken();
  const accessToken = typeof tokenResult === 'string' ? tokenResult : tokenResult?.token;

  const endpoint = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/publishers/google/models/${model}:predict`;

  const prompt = `A photorealistic ${placement.plant_name} in a ${placement.pot_style}, placed ${placement.location_description}. The plant perfectly matches the room lighting, casts realistic shadows, has correct perspective and depth. Ultra-realistic, professional interior photography quality.`;

  const WHITE_1PX_PNG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg==';

  const body = {
    instances: [{
      prompt,
      negativePrompt: 'cartoon, unrealistic, floating, distorted, blurry, duplicate, watermark, text, low quality',
      referenceImages: [
        { referenceType: 'REFERENCE_TYPE_RAW', referenceId: 1, referenceImage: { bytesBase64Encoded: baseImageBase64 } },
        { referenceType: 'REFERENCE_TYPE_MASK', referenceId: 2, referenceImage: { bytesBase64Encoded: WHITE_1PX_PNG }, maskImageConfig: { maskMode: 'MASK_MODE_USER_PROVIDED', dilation: 0.015 } },
      ],
    }],
    parameters: { sampleCount: 1, editMode: 'EDIT_MODE_INPAINT_INSERTION', baseSteps: 75, addWatermark: false, safetySetting: 'block_medium_and_above' },
  };

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const json = await response.json();
  if (!response.ok) throw new Error(json.error?.message || `Imagen failed: ${response.status}`);

  const prediction = json?.predictions?.[0];
  const imageB64 = prediction?.bytesBase64Encoded || prediction?.image?.bytesBase64Encoded;
  if (!imageB64) throw new Error('Imagen returned no image');
  return imageB64;
}

// -- POST /api/room-design
router.post('/', async (req, res) => {
  try {
    const { image, mimeType } = req.body;
    if (!image) return res.status(400).json({ error: 'image (base64) is required' });

    const allowedMimes = ['image/jpeg', 'image/png', 'image/webp'];
    const mime = allowedMimes.includes(mimeType) ? mimeType : 'image/jpeg';
    if (image.length > 14_000_000) return res.status(413).json({ error: 'Image too large. Max 10 MB.' });

    const client = getClient();
    if (!client) return res.status(503).json({ error: 'AI service not configured - add GEMINI_API_KEY to .env' });

    // Step 1: Gemini Vision - analyse the room
    console.log('[room-design] Analysing room with Gemini Vision...');
    const model = client.getGenerativeModel({ model: 'gemini-3.8-flash' });
    const analysisResult = await model.generateContent([
      { inlineData: { data: image, mimeType: mime } },
      { text: ROOM_ANALYSIS_PROMPT },
    ]);

    const rawAnalysis = analysisResult.response.text();
    let analysis;
    try {
      analysis = parseJSON(rawAnalysis);
    } catch (parseErr) {
      console.error('[room-design] JSON parse failed:', rawAnalysis);
      return res.status(500).json({ error: 'Failed to parse room analysis', raw: rawAnalysis });
    }

    console.log('[room-design] Analysis done:', analysis.roomType, '|', analysis.placements?.length, 'plant placements');

    // Step 2: Imagen inpainting (optional - only if Vertex AI configured)
    let renderedImageBase64 = null;
    const projectId = process.env.GOOGLE_CLOUD_PROJECT || process.env.VERTEX_PROJECT_ID;

    if (projectId) {
      try {
        console.log('[room-design] Rendering plants with Imagen...');
        let currentBase64 = image;
        const toRender = (analysis.placements || []).slice(0, 2);
        for (const placement of toRender) {
          currentBase64 = await callImagenInpaint({ baseImageBase64: currentBase64, placement });
          console.log('[room-design]   Rendered:', placement.plant_name);
        }
        renderedImageBase64 = currentBase64;
      } catch (imagenErr) {
        console.warn('[room-design] Imagen failed (non-fatal):', imagenErr.message);
      }
    }

    return res.json({
      success: true,
      analysis,
      renderedImage: renderedImageBase64 ? `data:image/png;base64,${renderedImageBase64}` : null,
      imagenAvailable: !!projectId,
    });

  } catch (err) {
    console.error('[room-design]', err.message);
    if (err.status === 429 || err.message?.includes('quota')) {
      return res.status(429).json({ error: 'AI quota reached. Please try again shortly.' });
    }
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;

