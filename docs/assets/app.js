// Page wiring: image selection, preparation and the "Processar imagens" button.
import { benchmark } from "./runner.js?v=20260926c";
import { $, display, renderPreparing, renderProgress, stageName } from "./render.js?v=20260926c";
const state = {sources: [], busy: false};
const status = (message, error = false) => { $("status").textContent = message; $("status").classList.toggle("error", error); };
function resetResults() { $("results").hidden = true; $("empty").hidden = false; }
function selectSources(sources) {
  if (state.busy) return;
  for (const source of state.sources) URL.revokeObjectURL(source.preview);
  state.sources = sources;
  resetResults();
  status(`${sources.length} ${sources.length === 1 ? "imagem pronta" : "imagens prontas"} para processar.`);
}
function pickFiles(files) {
  if (state.busy) return;
  const list = Array.from(files);
  if (!list.length) return;
  if (list.some(file => !["image/jpeg","image/png","image/webp"].includes(file.type))) {
    status("Use apenas imagens JPG, PNG ou WebP.", true); return;
  }
  // The original file is shown as-is; no re-encoded copy of the image is kept in memory.
  selectSources(list.map(file => ({file,preview:URL.createObjectURL(file)})));
}
$("images").addEventListener("change", event => pickFiles(event.target.files));
const drop = $("drop-zone");
for (const eventName of ["dragenter","dragover"]) drop.addEventListener(eventName, event => { event.preventDefault(); if (!state.busy) drop.classList.add("dragging"); });
for (const eventName of ["dragleave","drop"]) drop.addEventListener(eventName, event => { event.preventDefault(); drop.classList.remove("dragging"); });
drop.addEventListener("drop", event => pickFiles(event.dataTransfer.files));
// There is no size limit: if the browser itself cannot decode or hold the image
// (canvas area or memory limits vary per device), a readable error is shown.
async function prepare(source, index) {
  let bitmap, size="";
  try {
    bitmap = await createImageBitmap(source.file);
    const {width,height} = bitmap; size=` (${width}×${height})`;
    const canvas = document.createElement("canvas"); canvas.width=width; canvas.height=height;
    const ctx=canvas.getContext("2d", {willReadFrequently:true});
    if (!ctx) throw new Error("canvas indisponível");
    ctx.drawImage(bitmap,0,0); bitmap.close(); bitmap=null;
    return {width,height,rgba:ctx.getImageData(0,0,width,height).data,preview:source.preview};
  } catch {
    throw new Error(`Não foi possível carregar a imagem ${index+1}${size} neste navegador.`);
  } finally { bitmap?.close(); }
}
$("run").addEventListener("click",async () => {
  if (state.busy) return;
  if (!state.sources.length) { status("Adicione imagens para processar.",true); $("images").focus(); return; }
  state.busy=true; $("run").disabled=true; $("images").disabled=true; resetResults();
  $("empty").hidden=true; $("loading").hidden=false;
  try {
    const images=[];
    status("Preparando imagens…");
    renderPreparing(0,state.sources.length);
    for (let i=0; i<state.sources.length; i++) { images.push(await prepare(state.sources[i],i)); renderPreparing(i+1,state.sources.length); }
    // The detailed progress goes to the results panel; the status line (read aloud
    // by screen readers) only changes when a new round or stage starts.
    let current="";
    const {sequential,runs}=await benchmark(images,progress => {
      renderProgress(progress);
      const summary=`Rodada ${progress.round+1} de ${progress.rounds} · ${stageName(progress.workers)}`;
      if (summary!==current) { current=summary; status(summary); }
    });
    const workers=Number(document.querySelector('input[name="workers"]:checked').value);
    display(images,sequential,runs,workers);
    status("Processamento concluído.");
  } catch (error) { status(error.message || "Não foi possível processar as imagens.",true); }
  finally {
    state.busy=false; $("run").disabled=false; $("images").disabled=false;
    $("loading").hidden=true; $("empty").hidden=!$("results").hidden;
  }
});
