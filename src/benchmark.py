"""Executa sequencial e paralelo (com varias contagens de processos) e compara os tempos.

Calcula o speedup observado e o speedup previsto pela Lei de Amdahl,
usando a fracao paralelizavel estimada a partir da primeira contagem de processos.
Cada configuracao roda --repeat vezes (intercaladas) e o resultado e a mediana.
"""

import argparse
import csv
import multiprocessing as mp
import statistics
from pathlib import Path

import parallel
import sequential
import verify as verify_module
from common import PROJECT_ROOT, positive_int


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
    if workers <= 1 or seq_time <= 0 or par_time <= 0:
        return 0.0
    observed_speedup = seq_time / par_time
    # observed_speedup = 1 / ((1-p) + p/workers)  =>  p = (1 - 1/observed_speedup) / (1 - 1/workers)
    denom = 1 - 1 / workers
    if denom == 0:
        return 0.0
    p = (1 - 1 / observed_speedup) / denom
    return max(0.0, min(1.0, p))


def run_benchmark(
    dataset_dir: Path, results_dir: Path, worker_counts: list[int], verify_outputs: bool, repeat: int = 3
) -> bool:
    """Roda o benchmark e retorna False se alguma saida paralela divergir da sequencial."""
    results_dir.mkdir(parents=True, exist_ok=True)
    seq_output = PROJECT_ROOT / "output" / "sequential"
    seq_report = results_dir / "sequential_report.csv"
    par_output = PROJECT_ROOT / "output" / "parallel"

    # Rodadas intercalam sequencial e paralelo: o cache de disco e a variacao
    # de frequencia da CPU afetam todas as configuracoes por igual, em vez de
    # favorecer quem roda depois. Cada configuracao usa a mediana das rodadas.
    times: dict[int, list[float]] = {1: [], **{w: [] for w in worker_counts}}
    verified = {w: True for w in worker_counts}
    for round_index in range(repeat):
        print(f"\n=== Rodada {round_index + 1}/{repeat} ===")
        times[1].append(sequential.run(dataset_dir, seq_output, seq_report))
        for workers in worker_counts:
            par_report = results_dir / f"parallel_report_{workers}.csv"
            times[workers].append(parallel.run(dataset_dir, par_output, par_report, workers))

            if verify_outputs:
                print(f"Verificando saida sequencial vs paralela ({workers} processos)...")
                verified[workers] &= verify_module.verify(seq_output, par_output)

    medians = {workers: statistics.median(values) for workers, values in times.items()}
    seq_time = medians[1]
    rows = [{"processos": 1, "tempo_s": round(seq_time, 4), "speedup": 1.0, "speedup_amdahl_previsto": 1.0}]
    for workers in worker_counts:
        par_time = medians[workers]
        speedup = seq_time / par_time if par_time > 0 else float("inf")
        rows.append({
            "processos": workers,
            "tempo_s": round(par_time, 4),
            "speedup": round(speedup, 3),
            "verificado": ("sim" if verified[workers] else "nao") if verify_outputs else "",
        })

    # A fracao p e estimada com a primeira contagem de processos; nas demais,
    # o speedup previsto por Amdahl pode ser comparado com o observado.
    parallel_fraction = estimate_parallel_fraction(seq_time, medians[worker_counts[0]], worker_counts[0])
    print(f"\nFracao paralelizavel estimada (Amdahl): {parallel_fraction:.3f}")
    for row in rows[1:]:
        row["speedup_amdahl_previsto"] = round(amdahl_speedup(parallel_fraction, row["processos"]), 3)

    report_path = results_dir / "benchmark.csv"
    fieldnames = ["processos", "tempo_s", "speedup", "speedup_amdahl_previsto", "verificado"]
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResumo (mediana de {repeat} rodadas) salvo em {report_path}")
    for row in rows:
        print(row)

    ok = all(verified.values())
    if not ok:
        failed = [w for w, good in verified.items() if not good]
        print(f"\nERRO: saida paralela diferente da sequencial com {failed} processos.")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark sequencial vs paralelo")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "dataset")
    parser.add_argument("--results", type=Path, default=PROJECT_ROOT / "results")
    parser.add_argument("--workers", type=positive_int, nargs="+", default=[2, 4, 8])
    parser.add_argument("--repeat", type=positive_int, default=3, help="Rodadas por configuracao (usa a mediana)")
    parser.add_argument("--no-verify", action="store_true", help="Pula a verificacao SHA-256")
    args = parser.parse_args()

    max_workers = mp.cpu_count()
    requested = list(dict.fromkeys(args.workers))  # remove repetidos, mantendo a ordem
    skipped = [w for w in requested if w > max_workers]
    if skipped:
        print(f"Aviso: ignorando {skipped} processos (a maquina tem {max_workers} nucleos logicos).")
    worker_counts = [w for w in requested if w <= max_workers] or [max_workers]

    ok = run_benchmark(args.dataset, args.results, worker_counts, verify_outputs=not args.no_verify, repeat=args.repeat)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
