const fs = require('fs/promises');
const path = require('path');
const { GoogleAuth } = require('google-auth-library');
const { roomDesignConfig } = require('../config/roomDesign');
const { generateMask, getImageDimensions, validateDimensions } = require('../utils/image');
const { withRetry } = require('../utils/retry');

let auth;

function getAuth() {
  if (!auth) auth = new GoogleAuth({ scopes: ['https://www.googleapis.com/auth/cloud-platform'] });
  return auth;
}

function assertVertexConfigured() {
  if (!roomDesignConfig.vertexProjectId) {
    const error = new Error('Vertex AI is not configured. Add GOOGLE_CLOUD_PROJECT or VERTEX_PROJECT_ID.');
    error.status = 503;
    error.code = 'VERTEX_NOT_CONFIGURED';
    throw error;
  }
}

function getOutputBase64(response) {
  const prediction = response?.predictions?.[0];
  return prediction?.bytesBase64Encoded || prediction?.image?.bytesBase64Encoded || prediction?.generatedImage?.bytesBase64Encoded;
}

async function callImagen({ baseImageBase64, maskBase64, prompt }) {
  assertVertexConfigured();
  const client = await getAuth().getClient();
  const token = await client.getAccessToken();
  const accessToken = typeof token === 'string' ? token : token?.token;

  const endpoint = `https://${roomDesignConfig.vertexLocation}-aiplatform.googleapis.com/v1/projects/${roomDesignConfig.vertexProjectId}/locations/${roomDesignConfig.vertexLocation}/publishers/google/models/${roomDesignConfig.imagenModel}:predict`;
  const body = {
    instances: [{
      prompt,
      negativePrompt: 'cartoon, unrealistic, floating objects, distorted shadows, duplicate objects, blurry',
      referenceImages: [
        {
          referenceType: 'REFERENCE_TYPE_RAW',
          referenceId: 1,
          referenceImage: { bytesBase64Encoded: baseImageBase64 },
        },
        {
          referenceType: 'REFERENCE_TYPE_MASK',
          referenceId: 2,
          referenceImage: { bytesBase64Encoded: maskBase64 },
          maskImageConfig: {
            maskMode: 'MASK_MODE_USER_PROVIDED',
            dilation: 0.01,
          },
        },
      ],
    }],
    parameters: {
      sampleCount: 1,
      editMode: 'EDIT_MODE_INPAINT_INSERTION',
      baseSteps: 75,
      addWatermark: true,
      safetySetting: 'block_medium_and_above',
    },
  };

  const response = await withRetry(async () => {
    const r = await fetch(endpoint, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    const json = await r.json().catch(() => ({}));
    if (!r.ok) {
      const error = new Error(json.error?.message || `Imagen request failed with status ${r.status}`);
      error.status = r.status;
      error.code = 'IMAGEN_REQUEST_FAILED';
      throw error;
    }
    return json;
  }, { retries: 1, baseDelayMs: 900 });

  const imageBase64 = getOutputBase64(response);
  if (!imageBase64) {
    const error = new Error('Imagen did not return an image.');
    error.status = 502;
    error.code = 'IMAGEN_EMPTY_RESPONSE';
    throw error;
  }
  return imageBase64;
}

async function renderPlants({ imageBuffer, mimeType, analysis }) {
  const dimensions = getImageDimensions(imageBuffer, mimeType);
  validateDimensions(dimensions);

  let currentBase64 = imageBuffer.toString('base64');
  for (const placement of analysis.placements) {
    const mask = generateMask(dimensions, placement.bounding_box);
    const prompt = `A photorealistic ${placement.plant_name} in a stylish pot, perfectly matching the ${analysis.global_lighting}, room perspective, shadows, reflections, depth, and color grading.`;
    currentBase64 = await callImagen({
      baseImageBase64: currentBase64,
      maskBase64: mask.toString('base64'),
      prompt,
    });
  }

  if (process.env.VERCEL) {
    return {
      success: true,
      image_base64: currentBase64,
    };
  }

  await fs.mkdir(roomDesignConfig.outputDir, { recursive: true });
  const filename = `room-${Date.now()}-${Math.random().toString(16).slice(2)}.png`;
  const filepath = path.join(roomDesignConfig.outputDir, filename);
  await fs.writeFile(filepath, Buffer.from(currentBase64, 'base64'));

  return {
    success: true,
    image_url: `/generated/rooms/${filename}`,
    image_base64: currentBase64,
  };
}

module.exports = {
  renderPlants,
};
