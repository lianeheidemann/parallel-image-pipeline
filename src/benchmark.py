"""Executa sequencial e paralelo (com varias contagens de processos) e compara os tempos.

Calcula o speedup observado e o speedup previsto pela Lei de Amdahl,
usando a fracao paralelizavel estimada a partir da propria execucao com 2 processos.
"""

import argparse
import csv
import multiprocessing as mp
from pathlib import Path

import parallel
import sequential
import verify as verify_module
from common import PROJECT_ROOT


def amdahl_speedup(parallel_fraction: float, workers: int) -> float:
    # Lei de Amdahl: S = 1 / ((1-p) + p/n) — teto previsto de speedup
    # para uma fracao paralelizavel p com n processos (slide 12).
    serial_fraction = 1 - parallel_fraction
    return 1 / (serial_fraction + parallel_fraction / workers)


def estimate_parallel_fraction(seq_time: float, par_time: float, workers: int) -> float:
    """Resolve a fracao paralelizavel p a partir do speedup observado com N processos.

    Usada para comparar previsto vs. observado (campo D/E da ficha): se o
    speedup medido ficar abaixo do previsto, a causa e comunicacao entre
    processos, divisao desigual do trabalho ou espera na secao critica.
    """
    observed_speedup = seq_time / par_time
    if workers <= 1 or observed_speedup <= 0:
        return 0.0
    # observed_speedup = 1 / ((1-p) + p/workers)  =>  p = (1 - 1/observed_speedup) / (1 - 1/workers)
    denom = 1 - 1 / workers
    if denom == 0:
        return 0.0
    p = (1 - 1 / observed_speedup) / denom
    return max(0.0, min(1.0, p))


def run_benchmark(dataset_dir: Path, results_dir: Path, worker_counts: list[int], verify_outputs: bool) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    seq_output = PROJECT_ROOT / "output" / "sequential"
    seq_report = results_dir / "sequential_report.csv"
    seq_time = sequential.run(dataset_dir, seq_output, seq_report)
    rows.append({"processos": 1, "tempo_s": round(seq_time, 4), "speedup": 1.0})

    parallel_fraction = None
    for workers in worker_counts:
        par_output = PROJECT_ROOT / "output" / "parallel"
        par_report = results_dir / f"parallel_report_{workers}.csv"
        par_time = parallel.run(dataset_dir, par_output, par_report, workers)
        speedup = seq_time / par_time if par_time > 0 else float("inf")
        rows.append({"processos": workers, "tempo_s": round(par_time, 4), "speedup": round(speedup, 3)})

        if parallel_fraction is None:
            parallel_fraction = estimate_parallel_fraction(seq_time, par_time, workers)

        if verify_outputs:
            print(f"\nVerificando saida sequencial vs paralela ({workers} processos)...")
            verify_module.verify(seq_output, par_output)

    if parallel_fraction is not None:
        print(f"\nFracao paralelizavel estimada (Amdahl): {parallel_fraction:.3f}")
        for row in rows:
            if row["processos"] > 1:
                row["speedup_amdahl_previsto"] = round(amdahl_speedup(parallel_fraction, row["processos"]), 3)
            else:
                row["speedup_amdahl_previsto"] = 1.0

    report_path = results_dir / "benchmark.csv"
    fieldnames = ["processos", "tempo_s", "speedup", "speedup_amdahl_previsto"]
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"\nResumo salvo em {report_path}")
    for row in rows:
        print(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark sequencial vs paralelo")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "dataset")
    parser.add_argument("--results", type=Path, default=PROJECT_ROOT / "results")
    parser.add_argument("--workers", type=int, nargs="+", default=[2, 4, 8])
    parser.add_argument("--no-verify", action="store_true", help="Pula a verificacao SHA-256")
    args = parser.parse_args()

    max_workers = mp.cpu_count()
    worker_counts = [w for w in args.workers if w <= max_workers] or [max_workers]

    run_benchmark(args.dataset, args.results, worker_counts, verify_outputs=not args.no_verify)


if __name__ == "__main__":
    main()
