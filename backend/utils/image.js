const crypto = require('crypto');
const zlib = require('zlib');

function stripDataUrl(value) {
  return String(value || '').replace(/^data:image\/[a-z0-9.+-]+;base64,/i, '');
}

function getImageDimensions(buffer, mimeType) {
  if (mimeType === 'image/png') {
    if (buffer.toString('ascii', 1, 4) !== 'PNG') throw new Error('Invalid PNG image.');
    return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
  }

  if (mimeType === 'image/jpeg') {
    let offset = 2;
    while (offset < buffer.length) {
      if (buffer[offset] !== 0xff) break;
      const marker = buffer[offset + 1];
      const length = buffer.readUInt16BE(offset + 2);
      if (marker >= 0xc0 && marker <= 0xc3) {
        return { height: buffer.readUInt16BE(offset + 5), width: buffer.readUInt16BE(offset + 7) };
      }
      offset += 2 + length;
    }
  }

  if (mimeType === 'image/webp') {
    const riff = buffer.toString('ascii', 0, 4);
    const webp = buffer.toString('ascii', 8, 12);
    if (riff !== 'RIFF' || webp !== 'WEBP') throw new Error('Invalid WEBP image.');
    const chunk = buffer.toString('ascii', 12, 16);
    if (chunk === 'VP8X') {
      return {
        width: 1 + buffer.readUIntLE(24, 3),
        height: 1 + buffer.readUIntLE(27, 3),
      };
    }
    if (chunk === 'VP8 ') {
      return {
        width: buffer.readUInt16LE(26) & 0x3fff,
        height: buffer.readUInt16LE(28) & 0x3fff,
      };
    }
    if (chunk === 'VP8L') {
      const b0 = buffer[21], b1 = buffer[22], b2 = buffer[23], b3 = buffer[24];
      return {
        width: 1 + (((b1 & 0x3f) << 8) | b0),
        height: 1 + (((b3 & 0x0f) << 10) | (b2 << 2) | ((b1 & 0xc0) >> 6)),
      };
    }
  }

  throw new Error('Unable to read image dimensions.');
}

function validateDimensions({ width, height }) {
  if (!width || !height || width < 64 || height < 64) {
    const error = new Error('Image is too small. Upload a clear room photo at least 64 x 64 pixels.');
    error.status = 400;
    throw error;
  }
  if (width > 4096 || height > 4096) {
    const error = new Error('Image is too large. Please upload a photo up to 4096 pixels on either side.');
    error.status = 413;
    throw error;
  }
}

function convertNormalizedBboxToPixels(box, dimensions) {
  const [ymin, xmin, ymax, xmax] = box;
  const padX = Math.max(8, Math.round(dimensions.width * 0.015));
  const padY = Math.max(8, Math.round(dimensions.height * 0.015));
  return {
    x: Math.max(0, Math.round(xmin * dimensions.width) - padX),
    y: Math.max(0, Math.round(ymin * dimensions.height) - padY),
    width: Math.min(dimensions.width, Math.round(xmax * dimensions.width) + padX) - Math.max(0, Math.round(xmin * dimensions.width) - padX),
    height: Math.min(dimensions.height, Math.round(ymax * dimensions.height) + padY) - Math.max(0, Math.round(ymin * dimensions.height) - padY),
  };
}

function crc32(buffer) {
  let crc = ~0;
  for (let i = 0; i < buffer.length; i += 1) {
    crc ^= buffer[i];
    for (let j = 0; j < 8; j += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return ~crc >>> 0;
}

function pngChunk(type, data) {
  const typeBuffer = Buffer.from(type);
  const length = Buffer.alloc(4);
  const crc = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 0);
  return Buffer.concat([length, typeBuffer, data, crc]);
}

function encodeGrayscalePng(width, height, pixelAt) {
  const rowLength = width + 1;
  const raw = Buffer.alloc(rowLength * height);
  for (let y = 0; y < height; y += 1) {
    const row = y * rowLength;
    raw[row] = 0;
    for (let x = 0; x < width; x += 1) raw[row + 1 + x] = pixelAt(x, y);
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 0;
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;

  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    pngChunk('IHDR', ihdr),
    pngChunk('IDAT', zlib.deflateSync(raw, { level: 6 })),
    pngChunk('IEND', Buffer.alloc(0)),
  ]);
}

function generateMask(dimensions, normalizedBox) {
  const rect = convertNormalizedBboxToPixels(normalizedBox, dimensions);
  const radius = Math.max(10, Math.round(Math.min(rect.width, rect.height) * 0.12));
  return encodeGrayscalePng(dimensions.width, dimensions.height, (x, y) => {
    const inRect = x >= rect.x && x <= rect.x + rect.width && y >= rect.y && y <= rect.y + rect.height;
    if (!inRect) return 0;
    const dx = Math.max(rect.x - x, 0, x - (rect.x + rect.width));
    const dy = Math.max(rect.y - y, 0, y - (rect.y + rect.height));
    return dx * dx + dy * dy <= radius * radius ? 255 : 255;
  });
}

function hashImage(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function compressImage(buffer) {
  return buffer;
}

function preserveMetadata(buffer) {
  return buffer;
}

module.exports = {
  stripDataUrl,
  getImageDimensions,
  validateDimensions,
  convertNormalizedBboxToPixels,
  generateMask,
  compressImage,
  preserveMetadata,
  hashImage,
};
