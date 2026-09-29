// Botao "Baixar CSV": salva os tempos desta execucao no formato de results/benchmark.csv.
import { buildRows, toCsv } from "./report.js?v=20260929a";

export function wireExport(sequential, runs) {
  // onclick (e nao addEventListener) para cada nova execucao substituir a anterior.
  document.getElementById("export-csv").onclick = () => {
    const blob = new Blob([toCsv(buildRows(sequential, runs))], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = "benchmark-web.csv";
    document.body.append(link); link.click(); link.remove();
    URL.revokeObjectURL(url);
  };
}
