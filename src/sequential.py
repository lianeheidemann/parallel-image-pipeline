"""Processa o dataset inteiro em um unico processo, imagem por imagem."""

import argparse
import csv
import time
from pathlib import Path

from common import PROJECT_ROOT, REPORT_HEADER, list_images
from image_processor import output_filename, process_image


def run(dataset_dir: Path, output_dir: Path, report_path: Path) -> float:
    images = list_images(dataset_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    processed = 0
    start = time.perf_counter()

    for image_path in images:
        img_start = time.perf_counter()
        process_image(image_path, output_dir / output_filename(image_path))
        elapsed = time.perf_counter() - img_start

        processed += 1
        rows.append((image_path.name, f"{elapsed:.4f}", "P1"))

    total_time = time.perf_counter() - start

    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(REPORT_HEADER)
        writer.writerows(rows)

    print(f"{processed}/{len(images)} imagens processadas")
    print(f"Tempo total: {total_time:.2f}s")
    return total_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Processamento sequencial de imagens")
    parser.add_argument("--dataset", type=Path, default=PROJECT_ROOT / "dataset")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "output" / "sequential")
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "results" / "sequential_report.csv")
    args = parser.parse_args()

    run(args.dataset, args.output, args.report)


if __name__ == "__main__":
    main()
