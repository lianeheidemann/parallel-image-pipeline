"""Versao paralela: as imagens sao distribuidas entre processos (multiprocessing.Pool).

Decisoes da Ficha B (estrategia):
- Paralelismo de DADOS: a mesma operacao (image_processor.process_image) em cada
  imagem; a unidade de trabalho e uma imagem.
- PROCESSOS, nao threads: o trabalho e limitado por processador. No CPython so
  um fluxo executa bytecode por vez (GIL), entao threads nao somariam nucleos e
  o speedup mediria perto de 1. Cada processo tem o proprio interpretador.
- chunksize=1: cada processo pega a proxima imagem livre (fila dinamica), o que
  evita a divisao desigual de trabalho.

Ficha C (sincronizacao) - estado escrito por mais de um fluxo:
- _counter: contador de imagens concluidas (multiprocessing.Value)
- _report_path: relatorio CSV, uma linha por imagem
Os dois sao escritos em _process_one, dentro da mesma secao critica.
"""

import argparse
import csv
import multiprocessing as mp
import time
from pathlib import Path

from common import (
    DATASET_DIR,
    PARALLEL_OUTPUT,
    RESULTS_DIR,
    list_images,
    positive_int,
    prepare_output_dir,
    write_report,
)
from image_processor import output_filename, process_image

_lock = None
_counter = None
_output_dir = None
_report_path = None


def _init_worker(lock, counter, output_dir: Path, report_path: Path) -> None:
    # Roda uma vez em cada processo do Pool: entrega a ele o lock e o contador
    # compartilhados (nao da para passa-los como argumento de cada tarefa).
    global _lock, _counter, _output_dir, _report_path
    _lock = lock
    _counter = counter
    _output_dir = output_dir
    _report_path = report_path


def _process_one(image_path: Path) -> None:
    # "Quem" do registro de evento: o processo do Pool ("ForkPoolWorker-3" -> P3).
    # Cada linha do CSV registra quem, sobre o que (a imagem) e quanto tempo levou.
    # Os processos nao trocam mensagens entre si (o Pool so entrega nomes de
    # arquivo), entao nao ha causalidade entre eles a ordenar: carimbo logico e
    # relogio vetorial nao se aplicam (Ficha C).
    process_label = f"P{mp.current_process().name.rsplit('-', 1)[-1]}"

    # Fora da secao critica: cada processo le a propria imagem e grava um .png
    # proprio; nada aqui e compartilhado. E onde o tempo e gasto, e roda em paralelo.
    img_start = time.perf_counter()
    process_image(image_path, _output_dir / output_filename(image_path))
    elapsed = time.perf_counter() - img_start

    # SECAO CRITICA (Ficha C). Primitiva: lock (multiprocessing.Lock).
    # - "_counter.value += 1" sao tres passos (ler, somar, gravar): sem o lock,
    #   dois processos leem o mesmo valor e um incremento se perde.
    # - A escrita no CSV, sem o lock, pode intercalar linhas de processos diferentes.
    # E o menor trecho indivisivel: o processamento da imagem fica fora. Com o lock
    # em volta do trabalho todo, o programa ficaria correto, mas serializado (speedup ~1).
    # Prova de estabilidade: contador = total de imagens e CSV com uma linha por imagem
    # em toda execucao (benchmark.py --repeat, tests/local/test_pipeline.py).
    with _lock:
        _counter.value += 1
        with open(_report_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([image_path.name, f"{elapsed:.4f}", process_label])


def run(dataset_dir: Path, output_dir: Path, report_path: Path, workers: int) -> float:
    images = list_images(dataset_dir)
    prepare_output_dir(output_dir)
    write_report(report_path)

    # Processos nao compartilham memoria: o estado comum e criado aqui, em memoria
    # compartilhada, e entregue a cada processo pelo initializer. (Um Manager
    # tambem funcionaria, mas cada acesso viraria uma mensagem a outro processo,
    # aumentando a espera na secao critica.)
    lock = mp.Lock()
    # lock=False: o Value nao precisa de trava propria; o _lock ja protege o incremento.
    counter = mp.Value("i", 0, lock=False)

    # O tempo inclui criar e encerrar o Pool e distribuir as tarefas: e parte do
    # custo que nao se divide entre os processos (a fracao serial de Amdahl, Ficha D).
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
    parser.add_argument("--dataset", type=Path, default=DATASET_DIR)
    parser.add_argument("--output", type=Path, default=PARALLEL_OUTPUT)
    parser.add_argument("--report", type=Path, default=RESULTS_DIR / "parallel_report.csv")
    parser.add_argument("--workers", type=positive_int, default=mp.cpu_count())
    args = parser.parse_args()

    run(args.dataset, args.output, args.report, args.workers)


if __name__ == "__main__":
    main()
