"""Constantes e utilitarios compartilhados entre os scripts de processamento."""

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_HEADER = ["arquivo", "tempo", "processo"]


def list_images(dataset_dir: Path) -> list[Path]:
    return sorted(dataset_dir.glob("*.jpg"))


def prepare_output_dir(output_dir: Path) -> None:
    # Apaga os .png de execucoes anteriores: sobras de um dataset maior
    # fariam o verify.py comparar arquivos que nao foram gerados agora.
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*.png"):
        old.unlink()


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"deve ser >= 1 (recebido: {value})")
    return number
