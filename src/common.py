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
    return sorted(dataset_dir.glob("*.jpg"))


def prepare_output_dir(output_dir: Path) -> None:
    # Apaga os .png de execucoes anteriores: sobras de um dataset maior
    # fariam o verify.py comparar arquivos que nao foram gerados agora.
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*.png"):
        old.unlink()


def write_report(report_path: Path, rows: Iterable[tuple[str, str, str]] = ()) -> None:
    # Cria o relatorio por imagem (arquivo, tempo, processo). Sem linhas, grava
    # so o cabecalho: e o caso do paralelo, em que cada worker anexa a sua.
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
