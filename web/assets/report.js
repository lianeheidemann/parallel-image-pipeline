// Linhas do CSV no mesmo formato de results/benchmark.csv (local/benchmark.py),
// para que local/compare_environments.py junte web, local e aws numa tabela so.
// Sem DOM: testado direto no Node (tests/web/report.test.mjs).

export const CSV_HEADER = ["processos", "tempo_s", "speedup", "speedup_amdahl_previsto", "verificado"];

const round = (value, digits) => Math.round(value * 10 ** digits) / 10 ** digits;

// Mesmas formulas de local/benchmark.py: amdahl_speedup e estimate_parallel_fraction.
export function amdahlSpeedup(parallelFraction, workers) {
  return 1 / ((1 - parallelFraction) + parallelFraction / workers);
}

export function estimateParallelFraction(seqTime, parTime, workers) {
  if (workers <= 1 || seqTime <= 0 || parTime <= 0) return 0;
  const denom = 1 - 1 / workers;
  if (denom === 0) return 0;
  const p = (1 - parTime / seqTime) / denom;
  return Math.max(0, Math.min(1, p));
}

// sequential: {seconds}; runs: [{workers, seconds, mismatch}] na ordem de WORKER_COUNTS.
// Como no Python, p vem do primeiro run e preve o speedup dos demais.
export function buildRows(sequential, runs) {
  const seq = sequential.seconds;
  const rows = [{ processos: 1, tempo_s: round(seq, 4), speedup: 1, speedup_amdahl_previsto: 1, verificado: "" }];
  if (runs.length === 0) return rows;
  const p = estimateParallelFraction(seq, runs[0].seconds, runs[0].workers);
  for (const run of runs) {
    rows.push({
      processos: run.workers,
      tempo_s: round(run.seconds, 4),
      speedup: run.seconds > 0 ? round(seq / run.seconds, 3) : Infinity,
      speedup_amdahl_previsto: round(amdahlSpeedup(p, run.workers), 3),
      verificado: run.mismatch === 0 ? "sim" : "nao",
    });
  }
  return rows;
}

export function toCsv(rows) {
  const lines = [CSV_HEADER.join(","), ...rows.map(row => CSV_HEADER.map(key => row[key]).join(","))];
  return `${lines.join("\n")}\n`;
}
