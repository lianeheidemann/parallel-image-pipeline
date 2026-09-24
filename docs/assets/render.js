// Draws the results panel: metrics, chart, image comparison, run details and explanations.
import { explainTimes, NOISE } from "./explain.js?v=20260926c";
import { ROUNDS, WORKER_COUNTS } from "./runner.js?v=20260926c";
import { integer, list, num, percent, seconds, times } from "./format.js?v=20260926c";
export const $ = (id) => document.getElementById(id);
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
    value.append(seconds(run.seconds),speed);
    row.title=`${label.textContent}: ${seconds(run.seconds)} (${times(base/run.seconds)} em relação ao sequencial)`;
    if (run.workers>1) row.title+=` · ideal ${seconds(ideal)} · eficiência ${percent(base/run.seconds/run.workers)}`;
    row.append(label,track,value); chart.append(row);
  }
  chart.setAttribute("aria-label",`Tempo por número de processos: ${runs.map(run=>`${run.workers}: ${seconds(run.seconds)}${run.workers>1 ? ` (ideal ${seconds(base/run.workers)})` : ""}`).join("; ")}`);
}
function showPreview(images,outputs,index) {
  const img=images[index], ordinal=`imagem ${index+1} de ${images.length}`;
  $("original-preview").src=img.preview; $("original-preview").alt=`Original, ${ordinal}`;
  const canvas=$("edge-preview"), {width,height}=img; canvas.width=width; canvas.height=height;
  canvas.setAttribute("aria-label",`Bordas detectadas, ${ordinal}`);
  const context=canvas.getContext("2d"); const frame=context.createImageData(width,height); const edges=outputs[index];
  for (let i=0; i<edges.length; i++) { const j=i*4; frame.data[j]=frame.data[j+1]=frame.data[j+2]=edges[i]; frame.data[j+3]=255; }
  context.putImageData(frame,0,0);
  for (const [i,thumb] of Array.from($("thumbs").children).entries()) thumb.setAttribute("aria-pressed",String(i===index));
}
// Thumbnails of every processed image; clicking one swaps the comparison above.
function renderGallery(images,outputs) {
  $("thumbs").replaceChildren(...images.map((img,index) => {
    const button=document.createElement("button"); button.type="button"; button.className="thumb";
    button.setAttribute("aria-label",`Mostrar imagem ${index+1} de ${images.length}`);
    const picture=document.createElement("img"); picture.src=img.preview; picture.alt="";
    button.append(picture);
    button.addEventListener("click",() => showPreview(images,outputs,index));
    return button;
  }));
  $("gallery").hidden=images.length<2;
  showPreview(images,outputs,0);
}
// runs: [{workers,seconds,mismatch}] for each of WORKER_COUNTS; seconds are medians.
export function display(images,sequential,runs,workers) {
  const parallel=runs.find(run=>run.workers===workers);
  $("sequential-time").textContent=seconds(sequential.seconds);
  $("parallel-time").textContent=seconds(parallel.seconds);
  const ratio=sequential.seconds/parallel.seconds;
  $("speedup").textContent=Math.abs(ratio-1)<=NOISE ? "Praticamente igual" : ratio >= 1 ? `${num(ratio)}× mais rápido` : `${num(1/ratio)}× mais lento`;
  const pixels=integer(sequential.outputs.reduce((sum,out)=>sum+out.length,0));
  const mismatched=runs.filter(run=>run.mismatch>0);
  const same=mismatched.length===0;
  $("verification").textContent=same
    ? `✓ ${pixels} pixels comparados em ${ROUNDS} rodadas: ${list(WORKER_COUNTS)} processos geraram exatamente o mesmo resultado do sequencial`
    : `✗ Diferença em relação ao sequencial: ${mismatched.map(run=>`${run.workers} processos (${integer(run.mismatch)} pixels)`).join(", ")}`;
  const runsAll=[{workers:1,seconds:sequential.seconds},...runs];
  renderChart(runsAll,workers);
  $("verification").classList.toggle("failed",!same);
  renderGallery(images,sequential.outputs);
  const info=[
    ["Imagens",`${images.length}`],
    ["Gráfico",`Sequencial (thread principal) e ${list(WORKER_COUNTS)} Web Workers`],
    ["Quadros do topo",`"Paralelo" usa ${workers} processos, a opção escolhida em Processos`],
    ["Divisão do trabalho","Cada imagem é cortada em faixas horizontais, uma por processo, que rodam ao mesmo tempo e depois são juntadas"],
    ["Conferência","Cada pixel do resultado paralelo é comparado com o sequencial, para garantir que dividir o trabalho não mudou a imagem"],
    ["Tempo medido",`Mediana de ${ROUNDS} rodadas, incluindo o envio de dados aos workers`],
  ];
  $("detail").replaceChildren(...info.map(([term,text]) => {
    const pair=document.createElement("div"), dt=document.createElement("dt"), dd=document.createElement("dd");
    dt.textContent=term; dd.textContent=text; pair.append(dt,dd); return pair;
  }));
  $("explain-list").replaceChildren(...explainTimes(runsAll,workers,navigator.hardwareConcurrency).map(text => {
    const item=document.createElement("li"); item.textContent=text; return item;
  }));
  $("empty").hidden=true; $("results").hidden=false;
}
// Progress block shown in the results panel while the benchmark runs.
export const stageName = workers => workers===1 ? "Sequencial" : `${workers} processos`;
const count = (done,total,one,many) => `${integer(done)} de ${integer(total)} ${total===1 ? one : many}`;
function setBars(stepFraction,totalFraction) {
  $("progress-step-bar").value=stepFraction;
  $("progress-total-bar").value=totalFraction;
  // Rounded down so "100%" only appears once the last strip is done.
  $("progress-total").textContent=percent(Math.floor(totalFraction*100)/100);
}
export function renderPreparing(done,total) {
  $("progress-round").hidden=true; $("progress-stages").hidden=true;
  $("progress-step").textContent="Preparando imagens";
  $("progress-count").textContent=count(done,total,"imagem","imagens");
  setBars(total ? done/total : 0,0);
}
// p: {round, rounds, stage, stages, workers, done, total} from runner.benchmark.
export function renderProgress({round,rounds,stage,stages,workers,done,total}) {
  $("progress-round").hidden=false;
  $("progress-round").textContent=`Rodada ${round+1} de ${rounds}`;
  const list=$("progress-stages"); list.hidden=false;
  if (list.children.length!==stages.length) list.replaceChildren(...stages.map(() => document.createElement("li")));
  stages.forEach((w,i) => {
    const item=list.children[i], state=i<stage ? "done" : i===stage ? "current" : "";
    item.className=state; item.textContent=`${state==="done" ? "✓ " : ""}${stageName(w)}`;
    if (state==="current") item.setAttribute("aria-current","step"); else item.removeAttribute("aria-current");
  });
  $("progress-step").textContent=workers===1 ? "Sequencial" : `Paralelo · ${workers} processos`;
  $("progress-count").textContent=workers===1 ? count(done,total,"imagem","imagens") : count(done,total,"faixa","faixas");
  const stepFraction=total ? done/total : 0;
  setBars(stepFraction,(round*stages.length+stage+stepFraction)/(rounds*stages.length));
}
