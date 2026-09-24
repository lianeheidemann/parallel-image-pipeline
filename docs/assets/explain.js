// Builds plain-language reasons for the gap between measured and ideal times.
// runs: [{workers:1,seconds}, {workers:2,seconds}, ...]; cores may be undefined.
import { list, num, percent } from "./format.js?v=20260926c";
import { ROUNDS } from "./runner.js?v=20260926c";
// Differences up to 5% are treated as measurement noise, not as a real effect.
export const NOISE = 0.05;
export function explainTimes(runs, selected, cores) {
  const base=runs[0].seconds, parallel=runs.slice(1);
  const speedup=run => base/run.seconds;
  const reasons=[];
  const chosen=parallel.find(run=>run.workers===selected);
  if (chosen) {
    const s=speedup(chosen);
    const result=s>=1 ? `o ganho foi ${num(s)}× de um ideal de ${selected}× (${percent(s/selected)} de eficiência)` : `o tempo foi ${num(1/s)}× maior que o sequencial, em vez de ${selected}× menor`;
    reasons.push(`Com ${selected} processos ${result}. Parte do tempo vai para criar os workers, copiar cada faixa (com linhas extras de borda) e juntar os resultados. Essas etapas não se dividem entre os processos (Lei de Amdahl).`);
  }
  const over=parallel.filter(run=>cores && run.workers>cores).map(run=>run.workers);
  if (over.length) reasons.push(`O dispositivo informa ${cores} ${cores===1?"núcleo lógico":"núcleos lógicos"}. Com ${list(over)} processos, os workers disputam a CPU, por isso o ganho acima de ${cores} processos é pequeno.`);
  for (let i=1; i<parallel.length; i++) {
    const prev=parallel[i-1], run=parallel[i];
    if (run.seconds>prev.seconds*(1+NOISE)) reasons.push(`${run.workers} processos foram mais lentos que ${prev.workers}: o custo de coordenar mais workers superou o ganho.`);
    else if (run.seconds>=prev.seconds*(1-NOISE)) reasons.push(`${run.workers} processos não foram mais rápidos que ${prev.workers} (diferença de até ${percent(NOISE)}): os núcleos extras costumam ser mais lentos (núcleos de eficiência, comuns em celulares) e o custo de coordenar mais workers cresce.`);
  }
  const slower=parallel.filter(run=>speedup(run)<1-NOISE).map(run=>run.workers);
  if (slower.length) reasons.push(`Com ${list(slower)} processos o paralelo foi mais lento que o sequencial: o custo de criar os workers e copiar os dados superou o trabalho útil, o que é comum com poucas imagens ou imagens pequenas.`);
  const even=parallel.filter(run=>Math.abs(speedup(run)-1)<=NOISE).map(run=>run.workers);
  if (even.length) reasons.push(`Com ${list(even)} processos o tempo ficou praticamente igual ao sequencial (diferença de até ${percent(NOISE)}). Isso costuma ser variação de medição: os workers podem ter rodado em núcleos de eficiência, ou a CPU reduziu a frequência por temperatura ou bateria.`);
  const superlinear=parallel.filter(run=>speedup(run)>run.workers*(1+NOISE)).map(run=>run.workers);
  if (superlinear.length) reasons.push(`Com ${list(superlinear)} processos o ganho passou do ideal: efeitos de cache, aquecimento do JIT ou variação de frequência da CPU durante a medição.`);
  reasons.push(`Os tempos mudam entre execuções: outras abas, modo de economia de energia, aquecimento do celular (throttling), coleta de lixo e núcleos de desempenho/eficiência. Por isso cada configuração roda ${ROUNDS} vezes e o gráfico mostra a mediana.`);
  return reasons;
}
