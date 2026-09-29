// Replica local/image_processor.py: BGR -> cinza, GaussianBlur(5,5) e magnitude Sobel.
// A matematica do navegador e do OpenCV pode diferir em um arredondamento.
export const HALO = 3; // Linhas de contexto: 2 para o blur e 1 para o Sobel.

export function processPixels(rgba, width, height) {
  return processRows(rgba, width, height, 0, 0, height);
}

// Processa as linhas de saida [outStart, outEnd) de uma imagem com `height` linhas.
// `rgba` contem as linhas [sliceStart, sliceStart + rows) e deve cobrir
// [outStart - HALO, outEnd + HALO), limitado ao tamanho da imagem, para que
// as faixas produzam exatamente o mesmo resultado da imagem inteira.
export function processRows(rgba, width, height, sliceStart, outStart, outEnd) {
  const rows = rgba.length / (4 * width);
  const count = rows * width;
  const gray = new Uint8Array(count);
  const horizontal = new Float32Array(count);
  const blurred = new Uint8Array(count);
  const edges = new Uint8ClampedArray((outEnd - outStart) * width);
  const kernel = [1, 4, 6, 4, 1];
  // Equivalente ao BORDER_REFLECT_101 do OpenCV, inclusive para imagens de 1 ou 2 pixels.
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
