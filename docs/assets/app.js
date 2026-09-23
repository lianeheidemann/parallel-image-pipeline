import { processPixels, HALO } from "./processor.js?v=20260923d";
import { explainTimes } from "./explain.js?v=20260923d";
const $ = (id) => document.getElementById(id);
const state = {sources: [], preview: null, busy: false};
const LIMIT = 12;
const MAX_PIXELS = 4_000_000;
const status = (message, error = false) => { $("status").textContent = message; $("status").classList.toggle("error", error); };
const nextFrame = () => new Promise(resolve => requestAnimationFrame(() => setTimeout(resolve, 0)));
function resetResults() { $("results").hidden = true; $("empty").hidden = false; }
function selectSources(sources, label) {
  if (state.busy) return;
  state.sources = sources;
  $("selection").textContent = label;
  resetResults();
  status(`${sources.length} ${sources.length === 1 ? "imagem pronta" : "imagens prontas"} para processar.`);
}
function pickFiles(files) {
  if (state.busy) return;
  const list = Array.from(files);
  if (!list.length) return;
  if (list.length > LIMIT) { status(`Selecione até ${LIMIT} imagens por vez.`, true); return; }
  if (list.some(file => !["image/jpeg","image/png","image/webp"].includes(file.type))) {
    status("Use apenas imagens JPG, PNG ou WebP.", true); return;
  }
  selectSources(list.map(file => ({file})), `${list.length} ${list.length === 1 ? "imagem selecionada" : "imagens selecionadas"}`);
}
$("images").addEventListener("change", event => pickFiles(event.target.files));
const drop = $("drop-zone");
for (const eventName of ["dragenter","dragover"]) drop.addEventListener(eventName, event => { event.preventDefault(); if (!state.busy) drop.classList.add("dragging"); });
for (const eventName of ["dragleave","drop"]) drop.addEventListener(eventName, event => { event.preventDefault(); drop.classList.remove("dragging"); });
drop.addEventListener("drop", event => pickFiles(event.dataTransfer.files));
async function prepare(source) {
  let bitmap;
  try {
    bitmap = await createImageBitmap(source.file);
    const {width,height} = bitmap;
    if (width < 3 || height < 3 || width * height > MAX_PIXELS) throw new Error("Cada imagem deve ter pelo menos 3 × 3 pixels e no máximo 4 megapixels.");
    const canvas = document.createElement("canvas"); canvas.width=width; canvas.height=height;
    const ctx=canvas.getContext("2d", {willReadFrequently:true});
    ctx.drawImage(bitmap,0,0); bitmap.close(); bitmap=null;
    return {width,height,rgba:ctx.getImageData(0,0,width,height).data,preview:canvas.toDataURL("image/png")};
  } finally { bitmap?.close(); }
}
async function runSequential(images) {
  const outputs = []; let elapsed = 0;
  for (let i=0; i<images.length; i++) {
    const img=images[i]; const start=performance.now();
    outputs.push(processPixels(img.rgba,img.width,img.height));
    elapsed += performance.now() - start;
    status(`Processamento sequencial: ${i+1}/${images.length}`);
    await nextFrame();
  }
  return {outputs,seconds:elapsed/1000};
}
// Each image is cut into horizontal strips so every worker has work even with few images.
function stripTasks(images, requested) {
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
function runParallel(images, requested) {
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
      const sliceStart=Math.max(0,outStart-HALO), sliceEnd=Math.min(img.height,outEnd+HALO);
      // slice() copies only the strip's rows, preserving the sequential input.
      const bytes=img.rgba.slice(sliceStart*img.width*4,sliceEnd*img.width*4);
      worker.postMessage({task,width:img.width,height:img.height,sliceStart,outStart,outEnd,rgba:bytes.buffer},[bytes.buffer]);
    };
    try {
      for (let i=0; i<requested; i++) {
        const worker=new Worker(new URL("./worker.js?v=20260923d",import.meta.url),{type:"module"});
        workers.push(worker);
        worker.onerror=() => finish(new Error("Não foi possível executar os Web Workers neste navegador."));
        worker.onmessage=({data}) => {
          if (settled) return;
          if (data.error) { finish(new Error(data.error)); return; }
          const {image,outStart}=tasks[data.task];
          outputs[image].set(new Uint8ClampedArray(data.output),outStart*images[image].width); done++;
          status(`Processamento paralelo (${requested} processos): ${done}/${tasks.length} faixas`);
          if (done===tasks.length) finish(); else dispatch(worker);
        };
        dispatch(worker);
      }
    } catch (error) { finish(error); }
  });
}
function identical(a,b) {
  return a.length === b.length && a.every((pixels,i) => pixels.length === b[i].length && pixels.every((value,j) => value === b[i][j]));
}
const format = n => `${n.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2})} s`;
const times = n => `${n.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2})}×`;
function renderChart(runs,selected) {
  const chart=$("chart"); chart.replaceChildren();
  const base=runs[0].seconds, max=Math.max(...runs.map(run=>run.seconds));
  for (const run of runs) {
    const row=document.createElement("div"); row.className="chart-row"; row.classList.toggle("selected",run.workers===selected);
    const label=document.createElement("span"); label.className="chart-label";
    label.textContent=run.workers===1 ? "1 (sequencial)" : `${run.workers} processos`;
    const track=document.createElement("div"); track.className="chart-track";
    const bar=document.createElement("div"); bar.className="chart-bar"; bar.style.width=`${max>0 ? run.seconds/max*100 : 0}%`;
    track.append(bar);
    const ideal=base/run.workers;
    if (run.workers>1) {
      const marker=document.createElement("div"); marker.className="chart-ideal";
      marker.style.left=`${max>0 ? ideal/max*100 : 0}%`;
      track.append(marker);
    }
    const value=document.createElement("span"); value.className="chart-value";
    const speed=document.createElement("span"); speed.textContent=` · ${times(base/run.seconds)}`;
    value.append(format(run.seconds),speed);
    row.title=`${label.textContent}: ${format(run.seconds)} (${times(base/run.seconds)} em relação ao sequencial)`;
    if (run.workers>1) row.title+=` · ideal ${format(ideal)} · eficiência ${(base/run.seconds/run.workers).toLocaleString("pt-BR",{style:"percent",maximumFractionDigits:0})}`;
    row.append(label,track,value); chart.append(row);
  }
  chart.setAttribute("aria-label",`Tempo por número de processos: ${runs.map(run=>`${run.workers}: ${format(run.seconds)}${run.workers>1 ? ` (ideal ${format(base/run.workers)})` : ""}`).join("; ")}`);
}
function display(images,sequential,runs,workers) {
  const parallel=runs.find(run=>run.workers===workers);
  $("sequential-time").textContent=format(sequential.seconds);
  $("parallel-time").textContent=format(parallel.seconds);
  const ratio=sequential.seconds/parallel.seconds;
  $("speedup").textContent=ratio >= 1 ? `${ratio.toLocaleString("pt-BR",{maximumFractionDigits:2})}× mais rápido` : `${(1/ratio).toLocaleString("pt-BR",{maximumFractionDigits:2})}× mais lento`;
  const same=runs.every(run=>identical(sequential.outputs,run.outputs));
  $("verification").textContent=same ? "✓ Resultados idênticos nas 4 configurações" : "As saídas apresentaram diferenças";
  renderChart([{workers:1,seconds:sequential.seconds},...runs],workers);
  $("verification").classList.toggle("failed",!same);
  $("original-preview").src=images[0].preview;
  const canvas=$("edge-preview"), {width,height}=images[0]; canvas.width=width; canvas.height=height;
  const context=canvas.getContext("2d"); const frame=context.createImageData(width,height); const edges=sequential.outputs[0];
  for (let i=0; i<edges.length; i++) { const j=i*4; frame.data[j]=frame.data[j+1]=frame.data[j+2]=edges[i]; frame.data[j+3]=255; }
  context.putImageData(frame,0,0);
  $("detail").textContent=`${images.length} ${images.length===1?"imagem":"imagens"} · gráfico: 1 processo (sequencial, thread principal), 2, 4 e 8 Web Workers · cartões: ${workers} processos · cada imagem é dividida em faixas horizontais entre os workers · comparação dos pixels de todas as saídas. O tempo inclui o envio de dados aos workers.`;
  const runsAll=[{workers:1,seconds:sequential.seconds},...runs];
  $("explain-list").replaceChildren(...explainTimes(runsAll,workers,navigator.hardwareConcurrency).map(text => {
    const item=document.createElement("li"); item.textContent=text; return item;
  }));
  $("empty").hidden=true; $("results").hidden=false;
}
$("run").addEventListener("click",async () => {
  if (state.busy) return;
  if (!state.sources.length) { status("Adicione imagens para processar.",true); $("images").focus(); return; }
  state.busy=true; $("run").disabled=true; $("images").disabled=true; resetResults();
  try {
    const images=[];
    for (let i=0; i<state.sources.length; i++) { status(`Preparando imagens: ${i+1}/${state.sources.length}`); images.push(await prepare(state.sources[i])); }
    await nextFrame();
    const sequential=await runSequential(images);
    await nextFrame();
    const runs=[];
    for (const count of [2,4,8]) {
      await nextFrame();
      runs.push({workers:count,...await runParallel(images,count)});
    }
    const workers=Number(document.querySelector('input[name="workers"]:checked').value);
    display(images,sequential,runs,workers);
    status("Processamento concluído.");
  } catch (error) { status(error.message || "Não foi possível processar as imagens.",true); }
  finally { state.busy=false; $("run").disabled=false; $("images").disabled=false; }
});
