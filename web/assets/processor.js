// Mirrors local/image_processor.py: BGR->gray, GaussianBlur(5,5), Sobel magnitude.
// Browser pixel math and OpenCV can differ by a rounding level at some pixels.
export const HALO = 3; // rows of context a strip needs: 2 for the blur + 1 for Sobel

export function processPixels(rgba, width, height) {
  return processRows(rgba, width, height, 0, 0, height);
}

// Processes output rows [outStart, outEnd) of an image `height` rows tall.
// `rgba` holds only rows [sliceStart, sliceStart + rows) of that image and must
// cover [outStart - HALO, outEnd + HALO) clamped to the image, so strips match
// the whole-image result exactly.
export function processRows(rgba, width, height, sliceStart, outStart, outEnd) {
  const rows = rgba.length / (4 * width);
  const count = rows * width;
  const gray = new Uint8Array(count);
  const horizontal = new Float32Array(count);
  const blurred = new Uint8Array(count);
  const edges = new Uint8ClampedArray((outEnd - outStart) * width);
  const kernel = [1, 4, 6, 4, 1];
  // OpenCV's BORDER_REFLECT_101, also valid for images only 1 or 2 pixels wide/tall.
  const reflect = (n, limit) => {
    if (limit === 1) return 0;
    const period = 2 * (limit - 1);
    n = Math.abs(n) % period;
    return n < limit ? n : period - n;
  };
  const row = (y) => (reflect(y, height) - sliceStart) * width;
  for (let i = 0; i < count; i++) {
    const j = i * 4;
    gray[i] = Math.round(.299 * rgba[j] + .587 * rgba[j + 1] + .114 * rgba[j + 2]);
  }
  for (let y = 0; y < rows; y++) for (let x = 0; x < width; x++) {
    let sum = 0;
    for (let k = -2; k <= 2; k++) sum += gray[y * width + reflect(x + k, width)] * kernel[k + 2];
    horizontal[y * width + x] = sum / 16;
  }
  const blurEnd = Math.min(height, outEnd + 1);
  for (let y = Math.max(0, outStart - 1); y < blurEnd; y++) for (let x = 0; x < width; x++) {
    let sum = 0;
    for (let k = -2; k <= 2; k++) sum += horizontal[row(y + k) + x] * kernel[k + 2];
    blurred[row(y) + x] = Math.round(sum / 16);
  }
  const at = (x, y) => blurred[row(y) + reflect(x, width)];
  for (let y = outStart; y < outEnd; y++) for (let x = 0; x < width; x++) {
    const gx = -at(x - 1,y - 1) + at(x + 1,y - 1) - 2*at(x - 1,y) + 2*at(x + 1,y) - at(x - 1,y + 1) + at(x + 1,y + 1);
    const gy = -at(x - 1,y - 1) - 2*at(x,y - 1) - at(x + 1,y - 1) + at(x - 1,y + 1) + 2*at(x,y + 1) + at(x + 1,y + 1);
    edges[(y - outStart) * width + x] = Math.min(255, Math.trunc(Math.hypot(gx, gy)));
  }
  return edges;
}
