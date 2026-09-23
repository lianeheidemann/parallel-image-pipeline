import { processRows } from "./processor.js?v=20260924d";
self.onmessage = ({data}) => {
  try {
    const output = processRows(new Uint8ClampedArray(data.rgba), data.width, data.height, data.sliceStart, data.outStart, data.outEnd);
    self.postMessage({task:data.task, output:output.buffer}, [output.buffer]);
  } catch (error) {
    self.postMessage({error:error.message || "Erro no processamento."});
  }
};
