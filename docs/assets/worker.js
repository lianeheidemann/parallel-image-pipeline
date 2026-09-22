import { processPixels } from "./processor.js";
self.onmessage = ({data}) => {
  try {
    const output = processPixels(new Uint8ClampedArray(data.rgba), data.width, data.height);
    self.postMessage({index:data.index, output:output.buffer}, [output.buffer]);
  } catch (error) {
    self.postMessage({error:error.message || "Erro no processamento."});
  }
};
