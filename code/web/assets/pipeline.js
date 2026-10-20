// As 6 etapas medidas para uma imagem, como process_image() em code/local/image_processor.py.
// Roda na thread principal (sequencial) e dentro de cada Web Worker (paralelo).
import { processPixels } from "./processor.js?v=20261020a";

export async function processFile(file) {
  // 01 entrada: decodifica o arquivo (equivalente ao cv2.imread).
  const bitmap = await createImageBitmap(file);
  const { width, height } = bitmap;
  const canvas = new OffscreenCanvas(width, height);
  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.drawImage(bitmap, 0, 0);
  bitmap.close();
  const rgba = context.getImageData(0, 0, width, height).data;

  // 02 a 05: cinza, blur gaussiano, Sobel X/Y e magnitude.
  const edges = processPixels(rgba, width, height);

  // 06 saida: codifica o mapa de bordas em PNG (equivalente ao cv2.imwrite, sem gravar em disco).
  const frame = context.createImageData(width, height);
  for (let i = 0; i < edges.length; i++) {
    const j = i * 4;
    frame.data[j] = frame.data[j + 1] = frame.data[j + 2] = edges[i];
    frame.data[j + 3] = 255;
  }
  context.putImageData(frame, 0, 0);
  await canvas.convertToBlob({ type: "image/png" });
  return { width, height, edges };
}
