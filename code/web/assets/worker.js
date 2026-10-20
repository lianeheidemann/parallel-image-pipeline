// Web Worker: processa uma imagem inteira (as 6 etapas) e devolve o mapa de bordas.
import { processFile } from "./pipeline.js?v=20261020a";
self.onmessage = async ({data}) => {
  try {
    const { edges } = await processFile(data.file);
    self.postMessage({task:data.task, output:edges.buffer}, [edges.buffer]);
  } catch (error) {
    self.postMessage({error:error.message || "Erro no processamento."});
  }
};
