// Mirrors src/image_processor.py: BGR->gray, GaussianBlur(5,5), Sobel magnitude.
// Browser pixel math and OpenCV can differ by a rounding level at some pixels.
export function processPixels(rgba, width, height) {
  const count = width * height;
  const gray = new Uint8Array(count);
  const horizontal = new Float32Array(count);
  const blurred = new Uint8Array(count);
  const edges = new Uint8ClampedArray(count);
  const kernel = [1, 4, 6, 4, 1];
  const reflect = (n, limit) => n < 0 ? -n : n >= limit ? 2 * limit - n - 2 : n;
  for (let i = 0; i < count; i++) {
    const j = i * 4;
    gray[i] = Math.round(.299 * rgba[j] + .587 * rgba[j + 1] + .114 * rgba[j + 2]);
  }
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    let sum = 0;
    for (let k = -2; k <= 2; k++) sum += gray[y * width + reflect(x + k, width)] * kernel[k + 2];
    horizontal[y * width + x] = sum / 16;
  }
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    let sum = 0;
    for (let k = -2; k <= 2; k++) sum += horizontal[reflect(y + k, height) * width + x] * kernel[k + 2];
    blurred[y * width + x] = Math.round(sum / 16);
  }
  const at = (x, y) => blurred[reflect(y, height) * width + reflect(x, width)];
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const gx = -at(x - 1,y - 1) + at(x + 1,y - 1) - 2*at(x - 1,y) + 2*at(x + 1,y) - at(x - 1,y + 1) + at(x + 1,y + 1);
    const gy = -at(x - 1,y - 1) - 2*at(x,y - 1) - at(x + 1,y - 1) + at(x - 1,y + 1) + 2*at(x,y + 1) + at(x + 1,y + 1);
    edges[y * width + x] = Math.min(255, Math.trunc(Math.hypot(gx, gy)));
  }
  return edges;
}
