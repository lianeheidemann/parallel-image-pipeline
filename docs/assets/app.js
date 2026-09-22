import { processPixels } from "./processor.js";
const $ = (id) => document.getElementById(id);
const state = {sources: [], preview: null, busy: false};
const LIMIT = 12;
const MAX_PIXELS = 4_000_000;
const CONFIGS = [
  {label: "Sequencial", workers: 0},
  {label: "2 processos", workers: 2},
  {label: "4 processos", workers: 4},
  {label: "8 processos", workers: 8},
];
const status = (message, error = false) => { $("status").textContent = message; $("status").classList.toggle("error", error); };
const nextFrame = () => new Promise(resolve => requestAnimationFrame(() => setTimeout(resolve, 0)));
function resetResults() { $("results").hidden = true; $("empty").hidden = false; $("example-panel").hidden = true; }
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
$("examples").addEventListener("click", () => {
  const samples = Array.from({length:8}, (_, index) => ({sample:index}));
  $("images").value = "";
  selectSources(samples, "8 imagens de exemplo selecionadas");
});
function drawSample(index) {
  const canvas = document.createElement("canvas"); canvas.width = 800; canvas.height = 600;
  const ctx = canvas.getContext("2d", {willReadFrequently:true});
  ctx.fillStyle = ["#d6e9ee","#e9d9cc","#cfe0d9","#d9e0eb"][index % 4]; ctx.fillRect(0,0,800,600);
  let seed = (index + 1) * 87321;
  const rand = () => { seed = (Math.imul(seed,1664525) + 1013904223) >>> 0; return seed / 4294967296; };
  for (let i=0; i<18; i++) {
    ctx.strokeStyle = `hsl(${Math.floor(rand()*360)} 40% 40%)`; ctx.lineWidth = 2 + rand()*8;
    ctx.beginPath(); ctx.ellipse(rand()*800,rand()*600,20+rand()*150,20+rand()*100,rand()*3,0,Math.PI*2); ctx.stroke();
  }
  return canvas;
}
async function prepare(source) {
  let bitmap;
  try {
    bitmap = source.file ? await createImageBitmap(source.file) : await createImageBitmap(drawSample(source.sample));
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
    await nextFrame();
  }
  return {outputs,seconds:elapsed/1000};
}
function runParallel(images, requested) {
  return new Promise((resolve,reject) => {
    const outputs=new Array(images.length); const workers=[];
    let next=0, done=0, settled=false;
    const start=performance.now();
    const finish=(error) => {
      if (settled) return; settled=true; workers.forEach(worker=>worker.terminate());
      if (error) reject(error); else resolve({outputs,seconds:(performance.now()-start)/1000});
    };
    const dispatch=(worker) => {
      if (next >= images.length) return;
      const index=next++; const img=images[index];
      // Copy only for transfer; preserve the sequential input and previews.
      const bytes=new Uint8ClampedArray(img.rgba);
      worker.postMessage({index,width:img.width,height:img.height,rgba:bytes.buffer},[bytes.buffer]);
    };
    try {
      for (let i=0; i<Math.min(requested,images.length); i++) {
        const worker=new Worker(new URL("./worker.js",import.meta.url),{type:"module"});
        workers.push(worker);
        worker.onerror=() => finish(new Error("Não foi possível executar os Web Workers neste navegador."));
        worker.onmessage=({data}) => {
          if (settled) return;
          if (data.error) { finish(new Error(data.error)); return; }
          outputs[data.index]=new Uint8ClampedArray(data.output); done++;
          if (done===images.length) finish(); else dispatch(worker);
        };
        dispatch(worker);
      }
    } catch (error) { finish(error); }
  });
}
function identical(a,b) {
  return a.length === b.length && a.every((pixels,i) => pixels.length === b[i].length && pixels.every((value,j) => value === b[i][j]));
}
async function runConfig(config, images, repeats) {
  let totalSeconds = 0, outputs = null;
  for (let r=0; r<repeats; r++) {
    status(`Executando: ${config.label} — repetição ${r+1}/${repeats}`);
    const result = config.workers === 0 ? await runSequential(images) : await runParallel(images, config.workers);
    totalSeconds += result.seconds;
    outputs = result.outputs;
    await nextFrame();
  }
  return {label: config.label, seconds: totalSeconds, outputs};
}
function formatSeconds(seconds) {
  return `${seconds.toLocaleString("pt-BR",{minimumFractionDigits:1,maximumFractionDigits:1})} s`;
}
function renderBars(results) {
  const max = Math.max(...results.map(result => result.seconds)) || 1;
  const fastest = results.reduce((a,b) => b.seconds < a.seconds ? b : a);
  const bars = $("bars"); bars.innerHTML = "";
  for (const result of results) {
    const row = document.createElement("div");
    row.className = "bar-row" + (result === fastest && results.length > 1 ? " fastest" : "");
    const pct = Math.max(2, (result.seconds / max) * 100);
    row.innerHTML = `<span class="bar-label">${result.label}</span><span class="bar-track"><span class="bar-fill" style="width:${pct}%"></span></span><span class="bar-value">${formatSeconds(result.seconds)}</span>`;
    bars.appendChild(row);
  }
  return fastest;
}
function display(images, results, repeats) {
  const fastest = renderBars(results);
  const sequential = results.find(result => result.label === "Sequencial") ?? results[0];
  $("summary-row").hidden = results.length <= 1;
  if (results.length > 1) {
    const ratio = sequential.seconds / fastest.seconds;
    $("fastest").innerHTML = `Mais rápido: <strong>${fastest.label}</strong> · <strong>${ratio.toLocaleString("pt-BR",{maximumFractionDigits:1})}×</strong>`;
    const allIdentical = results.every(result => identical(result.outputs, sequential.outputs));
    $("verification").textContent = allIdentical ? "✓ Saídas idênticas" : "✗ Saídas diferentes";
    $("verification").classList.toggle("failed", !allIdentical);
  } else {
    $("fastest").innerHTML = ""; $("verification").textContent = ""; $("verification").classList.remove("failed");
  }
  $("original-preview").src = images[0].preview;
  const canvas = $("edge-preview"), {width,height} = images[0]; canvas.width=width; canvas.height=height;
  const context = canvas.getContext("2d"); const frame = context.createImageData(width,height); const edges = fastest.outputs[0];
  for (let i=0; i<edges.length; i++) { const j=i*4; frame.data[j]=frame.data[j+1]=frame.data[j+2]=edges[i]; frame.data[j+3]=255; }
  context.putImageData(frame,0,0);
  $("example-panel").hidden = false;
  $("detail").textContent = `${images.length} ${images.length===1?"imagem":"imagens"} · ${repeats} ${repeats===1?"repetição":"repetições"} por configuração · comparação dos pixels de todas as saídas. O tempo inclui o envio de dados aos workers. O código Python usa multiprocessing e pode apresentar tempos diferentes.`;
  $("empty").hidden = true; $("results").hidden = false;
}
$("run").addEventListener("click",async () => {
  if (state.busy) return;
  if (!state.sources.length) { status("Adicione imagens ou use as de exemplo.",true); $("images").focus(); return; }
  const repeats = Math.min(30, Math.max(1, Math.round(Number($("repeats").value)) || 1));
  $("repeats").value = repeats;
  const configs = $("compare-all").checked ? CONFIGS : CONFIGS.slice(0,1);
  state.busy=true; $("run").disabled=true; $("examples").disabled=true; $("images").disabled=true; $("repeats").disabled=true; $("compare-all").disabled=true; resetResults();
  try {
    const images=[];
    for (let i=0; i<state.sources.length; i++) { status(`Preparando imagens: ${i+1}/${state.sources.length}`); images.push(await prepare(state.sources[i])); }
    await nextFrame();
    const results=[];
    for (const config of configs) results.push(await runConfig(config,images,repeats));
    display(images,results,repeats);
    status("Comparação concluída.");
  } catch (error) { status(error.message || "Não foi possível processar as imagens.",true); }
  finally { state.busy=false; $("run").disabled=false; $("examples").disabled=false; $("images").disabled=false; $("repeats").disabled=false; $("compare-all").disabled=false; }
});
