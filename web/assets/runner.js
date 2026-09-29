// Mede a execucao sequencial (thread principal) e as execucoes paralelas (Web Workers).
// Sem acesso ao DOM: o progresso e enviado como dados pelo callback onProgress.
import { processPixels, HALO } from "./processor.js?v=20260929b";
export const ROUNDS = 3; // Cada configuracao roda 3 vezes; a mediana e exibida.
export const WORKER_COUNTS = [2,4,8];
const nextFrame = () => new Promise(resolve => requestAnimationFrame(() => setTimeout(resolve, 0)));
const median = values => [...values].sort((a,b)=>a-b)[Math.floor(values.length/2)];
async function runSequential(images, onStep) {
  const outputs = []; let elapsed = 0;
  onStep(0, images.length);
  for (let i=0; i<images.length; i++) {
    const img=images[i]; const start=performance.now();
    outputs.push(processPixels(img.rgba,img.width,img.height));
    elapsed += performance.now() - start;
    onStep(i+1, images.length);
    await nextFrame();
  }
  return {outputs,seconds:elapsed/1000};
}
// Cada imagem e dividida em faixas horizontais para distribuir trabalho aos workers.
export function stripTasks(images, requested) {
  const tasks=[];
  images.forEach((img,image) => {
    const parts=Math.min(requested,img.height);
    for (let p=0; p<parts; p++) {
      const outStart=Math.floor(p*img.height/parts), outEnd=Math.floor((p+1)*img.height/parts);
      tasks.push({image,outStart,outEnd});
    }
  });
  return tasks;
}
// Linhas necessarias: as proprias da faixa mais HALO linhas de contexto em cada lado.
// slice() copia somente essas linhas e preserva a entrada usada no sequencial.
export function stripSlice(img, {outStart,outEnd}) {
  const sliceStart=Math.max(0,outStart-HALO), sliceEnd=Math.min(img.height,outEnd+HALO);
  return {sliceStart, rgba:img.rgba.slice(sliceStart*img.width*4,sliceEnd*img.width*4)};
}
function runParallel(images, requested, onStep) {
  return new Promise((resolve,reject) => {
    const outputs=images.map(img => new Uint8ClampedArray(img.width*img.height));
    const tasks=stripTasks(images,requested); const workers=[];
    onStep(0, tasks.length);
    let next=0, done=0, settled=false;
    const start=performance.now();
    const finish=(error) => {
      if (settled) return; settled=true; workers.forEach(worker=>worker.terminate());
      if (error) reject(error); else resolve({outputs,seconds:(performance.now()-start)/1000});
    };
    const dispatch=(worker) => {
      if (next >= tasks.length) return;
      const task=next++; const {image,outStart,outEnd}=tasks[task]; const img=images[image];
      const {sliceStart,rgba}=stripSlice(img,tasks[task]);
      worker.postMessage({task,width:img.width,height:img.height,sliceStart,outStart,outEnd,rgba:rgba.buffer},[rgba.buffer]);
    };
    try {
      for (let i=0; i<requested; i++) {
        const worker=new Worker(new URL("./worker.js?v=20260929b",import.meta.url),{type:"module"});
        workers.push(worker);
        worker.onerror=() => finish(new Error("Não foi possível executar os Web Workers neste navegador."));
        worker.onmessage=({data}) => {
          if (settled) return;
          if (data.error) { finish(new Error(data.error)); return; }
          const {image,outStart}=tasks[data.task];
          outputs[image].set(new Uint8ClampedArray(data.output),outStart*images[image].width); done++;
          onStep(done, tasks.length);
          if (done===tasks.length) finish(); else dispatch(worker);
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
// lista os workers na ordem de execucao (1 = sequencial), e done/total conta
// imagens no sequencial ou faixas no paralelo.
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
