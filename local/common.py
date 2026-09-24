"""Constantes e utilitarios compartilhados entre os scripts de processamento."""

import argparse
import csv
from collections.abc import Iterable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
SEQUENTIAL_OUTPUT = PROJECT_ROOT / "output" / "sequential"
PARALLEL_OUTPUT = PROJECT_ROOT / "output" / "parallel"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORT_HEADER = ["arquivo", "tempo", "processo"]


def list_images(dataset_dir: Path) -> list[Path]:
    # A unidade de trabalho: um arquivo .jpg. Ordenado para que as duas versoes
    # recebam a mesma entrada, na mesma ordem.
    return sorted(dataset_dir.glob("*.jpg"))


def prepare_output_dir(output_dir: Path) -> None:
    # Apaga os .png de execucoes anteriores, para que o verify.py compare so o que
    # esta execucao gerou (sobras de um dataset maior falseariam a verificacao).
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*.png"):
        old.unlink()


def write_report(report_path: Path, rows: Iterable[tuple[str, str, str]] = ()) -> None:
    # Relatorio por imagem: arquivo (sobre o que), tempo e processo (quem).
    # Sem linhas grava so o cabecalho: e o caso da versao paralela, em que cada
    # processo anexa a sua linha dentro da secao critica.
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(REPORT_HEADER)
        writer.writerows(rows)


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"deve ser >= 1 (recebido: {value})")
    return number
