"""Versao sequencial: todo o dataset em um unico processo, imagem por imagem.

E o tempo de referencia do speedup (tempo_sequencial / tempo_paralelo, Ficha D)
e a resposta correta conhecida contra a qual a versao paralela e verificada.
Com um so fluxo nao ha estado compartilhado, logo nao ha secao critica nem lock
(contraste com parallel.py).
"""

import argparse
import time
from pathlib import Path

from common import DATASET_DIR, RESULTS_DIR, SEQUENTIAL_OUTPUT, list_images, prepare_output_dir, write_report
from image_processor import output_filename, process_image


def run(dataset_dir: Path, output_dir: Path, report_path: Path) -> float:
    images = list_images(dataset_dir)
    prepare_output_dir(output_dir)

    rows = []
    # Mesmo criterio de tempo da versao paralela: so o processamento do dataset,
    # sem listar arquivos nem gravar o relatorio.
    start = time.perf_counter()

    for image_path in images:
        img_start = time.perf_counter()
        process_image(image_path, output_dir / output_filename(image_path))
        elapsed = time.perf_counter() - img_start
        rows.append((image_path.name, f"{elapsed:.4f}", "P1"))

    total_time = time.perf_counter() - start

    write_report(report_path, rows)

    print(f"{len(rows)}/{len(images)} imagens processadas")
    print(f"Tempo total: {total_time:.2f}s")
    return total_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Processamento sequencial de imagens")
    parser.add_argument("--dataset", type=Path, default=DATASET_DIR)
    parser.add_argument("--output", type=Path, default=SEQUENTIAL_OUTPUT)
    parser.add_argument("--report", type=Path, default=RESULTS_DIR / "sequential_report.csv")
    args = parser.parse_args()

    run(args.dataset, args.output, args.report)


if __name__ == "__main__":
    main()
