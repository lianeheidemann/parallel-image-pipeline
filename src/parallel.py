"""Processa o dataset distribuindo as imagens entre varios processos (multiprocessing).

Estado compartilhado entre os processos:
- contador de imagens concluidas (multiprocessing.Value)
- arquivo results.csv (escrita protegida por Lock)

As duas escritas compartilhadas acontecem dentro da mesma secao critica,
delimitada pelo menor trecho de codigo possivel (o "with lock:" abaixo).
"""

import argparse
import csv
import multiprocessing as mp
import time
from pathlib import Path

from common import PROJECT_ROOT, REPORT_HEADER, list_images
from image_processor import output_filename, process_image

_lock = None
_counter = None
_output_dir = None
_report_path = None


def _init_worker(lock, counter, output_dir: Path, report_path: Path) -> None:
    global _lock, _counter, _output_dir, _report_path
    _lock = lock
    _counter = counter
    _output_dir = output_dir
    _report_path = report_path


def _process_one(image_path: Path) -> None:
    # Estrategia = paralelismo de DADOS: cada worker do Pool recebe uma
    # imagem (chunksize=1 em run()) e aplica a mesma operacao (slide 7/8).
    process_label = f"P{mp.current_process()._identity[0]}" if mp.current_process()._identity else "P1"

    # Fora da secao critica: cada processo tem sua copia da imagem e escreve
    # em um arquivo .png proprio, entao nao ha concorrencia aqui.
    img_start = time.perf_counter()
    process_image(image_path, _output_dir / output_filename(image_path))
    elapsed = time.perf_counter() - img_start

    # SECAO CRITICA (o que a ficha pede no campo C): _counter e _report_path
    # sao escritos por todos os workers. Primitiva = Lock (multiprocessing
    # Manager), delimitando so o incremento + a linha de CSV, nunca o
    # processamento da imagem (senao o programa vira serializado, slide 10).
    with _lock:
        _counter.value += 1
        with open(_report_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([image_path.name, f"{elapsed:.4f}", process_label])


def run(dataset_dir: Path, output_dir: Path, report_path: Path, workers: int) -> float:
    images = list_images(dataset_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(REPORT_HEADER)

    # Lock e Value via Manager: unico jeito de compartilhar estado entre
    # processos separados (memoria nao e compartilhada como em threads).
    manager = mp.Manager()
    lock = manager.Lock()
    counter = manager.Value("i", 0)

    start = time.perf_counter()
    with mp.Pool(
        processes=workers,
        initializer=_init_worker,
        initargs=(lock, counter, output_dir, report_path),
    ) as pool:
        pool.map(_process_one, images, chunksize=1)
    total_time = time.perf_counter() - start

    print(f"{counter.value}/{len(images)} imagens processadas com {workers} processos")
    print(f"Tempo total: {total_time:.2f}s")
    return total_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Processamento paralelo de imagens")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "dataset")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "output" / "parallel")
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "results" / "parallel_report.csv")
    parser.add_argument("--workers", type=int, default=mp.cpu_count())
    args = parser.parse_args()

    run(args.dataset, args.output, args.report, args.workers)


if __name__ == "__main__":
    main()
