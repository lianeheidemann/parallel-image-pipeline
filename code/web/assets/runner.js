// Mede a execucao sequencial (thread principal) e as execucoes paralelas (Web Workers).
// O tempo cobre as 6 etapas de cada imagem (pipeline.js), como no Python.
// Sem acesso ao DOM: o progresso e enviado como dados pelo callback onProgress.
import { processFile } from "./pipeline.js?v=20261020a";
export const ROUNDS = 3; // Cada configuracao roda 3 vezes; a mediana e exibida.
export const WORKER_COUNTS = [2,4,8];
const nextFrame = () => new Promise(resolve => requestAnimationFrame(() => setTimeout(resolve, 0)));
const median = values => [...values].sort((a,b)=>a-b)[Math.floor(values.length/2)];
async function runSequential(images, onStep) {
  const outputs = []; let elapsed = 0;
  onStep(0, images.length);
  for (let i=0; i<images.length; i++) {
    const start=performance.now();
    outputs.push((await processFile(images[i].file)).edges);
    elapsed += performance.now() - start;
    onStep(i+1, images.length);
    await nextFrame();
  }
  return {outputs,seconds:elapsed/1000};
}
// Uma imagem por tarefa, numa fila: cada worker pega a proxima imagem livre ao terminar
// (como o Pool do Python com chunksize=1). O tempo inclui criar e encerrar os workers.
function runParallel(images, requested, onStep) {
  return new Promise((resolve,reject) => {
    const outputs=new Array(images.length); const workers=[];
    onStep(0, images.length);
    let next=0, done=0, settled=false;
    const start=performance.now();
    const finish=(error) => {
      if (settled) return; settled=true; workers.forEach(worker=>worker.terminate());
      if (error) reject(error); else resolve({outputs,seconds:(performance.now()-start)/1000});
    };
    const dispatch=(worker) => {
      if (next >= images.length) return;
      const task=next++;
      worker.postMessage({task,file:images[task].file});
    };
    try {
      for (let i=0; i<requested; i++) {
        const worker=new Worker(new URL("./worker.js?v=20261020a",import.meta.url),{type:"module"});
        workers.push(worker);
        worker.onerror=() => finish(new Error("Não foi possível executar os Web Workers neste navegador."));
        worker.onmessage=({data}) => {
          if (settled) return;
          if (data.error) { finish(new Error(data.error)); return; }
          outputs[data.task]=new Uint8ClampedArray(data.output); done++;
          onStep(done, images.length);
          if (done===images.length) finish(); else dispatch(worker);
        };
        dispatch(worker);
      }
    } catch (error) { finish(error); }
  });
}
// Conta os pixels de saida diferentes entre duas execucoes, em todas as imagens.
function differences(a,b) {
  let count=0;
  a.forEach((pixels,i) => { for (let j=0; j<pixels.length; j++) if (pixels[j]!==b[i][j]) count++; });
  return count;
}
// Retorna o resultado sequencial e, para cada quantidade de workers, o tempo
// mediano e a quantidade de pixels diferentes ao longo das rodadas.
// onProgress recebe {round, rounds, stage, stages, workers, done, total}; stages
// lista os workers na ordem de execucao (1 = sequencial), e done/total conta imagens.
const STAGES = [1, ...WORKER_COUNTS];
export async function benchmark(images, onProgress) {
  // As configuracoes sao intercaladas para que aquecimento ou bateria afete todas igualmente.
  const times={1:[]}, mismatch={};
  for (const count of WORKER_COUNTS) { times[count]=[]; mismatch[count]=0; }
  let reference=null;
  for (let round=0; round<ROUNDS; round++) {
    const step=(stage) => (done,total) => onProgress({round,rounds:ROUNDS,stage,stages:STAGES,workers:STAGES[stage],done,total});
    await nextFrame();
    const sequential=await runSequential(images,step(0));
    times[1].push(sequential.seconds);
    reference ??= sequential.outputs;
    for (const count of WORKER_COUNTS) {
      await nextFrame();
      const run=await runParallel(images,count,step(STAGES.indexOf(count)));
      times[count].push(run.seconds);
      mismatch[count]+=differences(reference,run.outputs);
    }
  }
  return {
    sequential:{outputs:reference,seconds:median(times[1])},
    runs:WORKER_COUNTS.map(count=>({workers:count,seconds:median(times[count]),mismatch:mismatch[count]})),
  };
}
