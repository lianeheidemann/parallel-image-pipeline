// O CSV da pagina web precisa sair no mesmo formato e com a mesma conta de
// Amdahl de local/benchmark.py, para comparar os ambientes numa tabela so.
import { test } from "node:test";
import assert from "node:assert/strict";
import { amdahlSpeedup, buildRows, datasetInfo, estimateParallelFraction, toCsv } from "../../web/assets/report.js";

const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} != ${expected}`);

// Mesmos valores de tests/local/test_benchmark.py.
test("Amdahl: totalmente paralelo escala linear", () => close(amdahlSpeedup(1, 4), 4));
test("Amdahl: totalmente serial nao ganha", () => close(amdahlSpeedup(0, 8), 1));
test("Amdahl: valor conhecido p=0,9 n=4", () => close(amdahlSpeedup(0.9, 4), 1 / 0.325));

for (const p of [0, 0.5, 0.9, 1]) {
  test(`estimativa inverte Amdahl (p=${p})`, () => {
    close(estimateParallelFraction(10, 10 / amdahlSpeedup(p, 4), 4), p);
  });
}

test("estimativa limitada a [0, 1]", () => {
  assert.equal(estimateParallelFraction(10, 20, 4), 0);
  assert.equal(estimateParallelFraction(10, 1, 4), 1);
});

for (const [seq, par, workers] of [[10, 5, 1], [10, 0, 4], [0, 5, 4]]) {
  test(`estimativa com entrada degenerada (${seq}, ${par}, ${workers}) = 0`, () => {
    assert.equal(estimateParallelFraction(seq, par, workers), 0);
  });
}

const IMAGES = [{ width: 1920, height: 1080 }, { width: 1920, height: 1080 }];

test("datasetInfo: quantidade e resolucao das imagens", () => {
  assert.deepEqual(datasetInfo(IMAGES), { imagens: 2, resolucao: "1920x1080" });
  assert.deepEqual(datasetInfo([...IMAGES, { width: 640, height: 480 }]), { imagens: 3, resolucao: "variada" });
  assert.deepEqual(datasetInfo([]), { imagens: 0, resolucao: "" });
});

test("buildRows: sequencial, verificado, Amdahl e dataset", () => {
  const rows = buildRows({ seconds: 10 }, [
    { workers: 2, seconds: 6, mismatch: 0 },
    { workers: 4, seconds: 4, mismatch: 3 },
  ], IMAGES);
  assert.deepEqual(rows[0], {
    processos: 1, tempo_s: 10, speedup: 1, speedup_amdahl_previsto: 1, verificado: "", imagens: 2, resolucao: "1920x1080",
  });
  assert.equal(rows[2].resolucao, "1920x1080");
  assert.equal(rows[1].processos, 2);
  assert.equal(rows[1].speedup, 1.667);
  assert.equal(rows[1].verificado, "sim");
  assert.equal(rows[2].verificado, "nao");
  // p estimado no primeiro run (2 processos) preve o proprio run de volta.
  close(rows[1].speedup_amdahl_previsto, 1.667);
  assert.ok(rows[2].speedup_amdahl_previsto > rows[1].speedup_amdahl_previsto);
});

test("toCsv: cabecalho igual ao de results/benchmark.csv", () => {
  const csv = toCsv([
    { processos: 1, tempo_s: 10, speedup: 1, speedup_amdahl_previsto: 1, verificado: "", imagens: 2, resolucao: "1920x1080" },
    { processos: 2, tempo_s: 6, speedup: 1.667, speedup_amdahl_previsto: 1.667, verificado: "sim", imagens: 2, resolucao: "1920x1080" },
  ]);
  assert.equal(csv, "processos,tempo_s,speedup,speedup_amdahl_previsto,verificado,imagens,resolucao\n"
    + "1,10,1,1,,2,1920x1080\n2,6,1.667,1.667,sim,2,1920x1080\n");
});
