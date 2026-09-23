// Timing of the sequential run (main thread) and the parallel runs (Web Workers).
// No DOM access: progress is reported through the onStatus callback.
import { processPixels, HALO } from "./processor.js?v=20260925a";
export const ROUNDS = 3; // each configuration is timed this many times; the median is shown
export const WORKER_COUNTS = [2,4,8];
const nextFrame = () => new Promise(resolve => requestAnimationFrame(() => setTimeout(resolve, 0)));
export const median = values => [...values].sort((a,b)=>a-b)[Math.floor(values.length/2)];
async function runSequential(images, onStatus) {
  const outputs = []; let elapsed = 0;
  for (let i=0; i<images.length; i++) {
    const img=images[i]; const start=performance.now();
    outputs.push(processPixels(img.rgba,img.width,img.height));
    elapsed += performance.now() - start;
    onStatus(`Processamento sequencial: ${i+1}/${images.length}`);
    await nextFrame();
  }
  return {outputs,seconds:elapsed/1000};
}
// Each image is cut into horizontal strips so every worker has work even with few images.
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
// Input rows a strip needs: its own rows plus HALO rows of context on each side.
// slice() copies only those rows, preserving the sequential input.
export function stripSlice(img, {outStart,outEnd}) {
  const sliceStart=Math.max(0,outStart-HALO), sliceEnd=Math.min(img.height,outEnd+HALO);
  return {sliceStart, rgba:img.rgba.slice(sliceStart*img.width*4,sliceEnd*img.width*4)};
}
function runParallel(images, requested, onStatus) {
  return new Promise((resolve,reject) => {
    const outputs=images.map(img => new Uint8ClampedArray(img.width*img.height));
    const tasks=stripTasks(images,requested); const workers=[];
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
        const worker=new Worker(new URL("./worker.js?v=20260925a",import.meta.url),{type:"module"});
        workers.push(worker);
        worker.onerror=() => finish(new Error("Não foi possível executar os Web Workers neste navegador."));
        worker.onmessage=({data}) => {
          if (settled) return;
          if (data.error) { finish(new Error(data.error)); return; }
          const {image,outStart}=tasks[data.task];
          outputs[image].set(new Uint8ClampedArray(data.output),outStart*images[image].width); done++;
          onStatus(`Processamento paralelo (${requested} processos): ${done}/${tasks.length} faixas`);
          if (done===tasks.length) finish(); else dispatch(worker);
        };
        dispatch(worker);
      }
    } catch (error) { finish(error); }
  });
}
// Number of output pixels that differ between two runs (all images).
function differences(a,b) {
  let count=0;
  a.forEach((pixels,i) => { for (let j=0; j<pixels.length; j++) if (pixels[j]!==b[i][j]) count++; });
  return count;
}
// Returns the sequential result and, per worker count, the median time and the
// number of pixels that differed from the sequential output across all rounds.
export async function benchmark(images, onStatus) {
  // Rounds interleave the configurations so a slowdown (heat, battery) hits all of them alike.
  const times={1:[]}, mismatch={};
  for (const count of WORKER_COUNTS) { times[count]=[]; mismatch[count]=0; }
  let reference=null;
  for (let round=0; round<ROUNDS; round++) {
    const report=message => onStatus(`Rodada ${round+1}/${ROUNDS} · ${message}`);
    await nextFrame();
    const sequential=await runSequential(images,report);
    times[1].push(sequential.seconds);
    reference ??= sequential.outputs;
    for (const count of WORKER_COUNTS) {
      await nextFrame();
      const run=await runParallel(images,count,report);
      times[count].push(run.seconds);
      mismatch[count]+=differences(reference,run.outputs);
    }
  }
  return {
    sequential:{outputs:reference,seconds:median(times[1])},
    runs:WORKER_COUNTS.map(count=>({workers:count,seconds:median(times[count]),mismatch:mismatch[count]})),
  };
}
