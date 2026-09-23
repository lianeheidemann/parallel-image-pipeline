// Page wiring: image selection, preparation and the "Processar imagens" button.
import { benchmark } from "./runner.js?v=20260925a";
import { $, display } from "./render.js?v=20260925a";
const state = {sources: [], busy: false};
const LIMIT = 12;
const MAX_PIXELS = 4_000_000;
const status = (message, error = false) => { $("status").textContent = message; $("status").classList.toggle("error", error); };
function resetResults() { $("results").hidden = true; $("empty").hidden = false; }
function selectSources(sources) {
  if (state.busy) return;
  state.sources = sources;
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
  selectSources(list.map(file => ({file})));
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
    if (width * height > MAX_PIXELS) throw new Error("Cada imagem deve ter no máximo 4 megapixels.");
    const canvas = document.createElement("canvas"); canvas.width=width; canvas.height=height;
    const ctx=canvas.getContext("2d", {willReadFrequently:true});
    ctx.drawImage(bitmap,0,0); bitmap.close(); bitmap=null;
    return {width,height,rgba:ctx.getImageData(0,0,width,height).data,preview:canvas.toDataURL("image/png")};
  } finally { bitmap?.close(); }
}
$("run").addEventListener("click",async () => {
  if (state.busy) return;
  if (!state.sources.length) { status("Adicione imagens para processar.",true); $("images").focus(); return; }
  state.busy=true; $("run").disabled=true; $("images").disabled=true; resetResults();
  $("empty").hidden=true; $("loading").hidden=false;
  try {
    const images=[];
    for (let i=0; i<state.sources.length; i++) { status(`Preparando imagens: ${i+1}/${state.sources.length}`); images.push(await prepare(state.sources[i])); }
    const {sequential,runs}=await benchmark(images,message => status(message));
    const workers=Number(document.querySelector('input[name="workers"]:checked').value);
    display(images,sequential,runs,workers);
    status("Processamento concluído.");
  } catch (error) { status(error.message || "Não foi possível processar as imagens.",true); }
  finally {
    state.busy=false; $("run").disabled=false; $("images").disabled=false;
    $("loading").hidden=true; $("empty").hidden=!$("results").hidden;
  }
});
