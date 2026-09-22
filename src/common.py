"""Constantes e utilitarios compartilhados entre os scripts de processamento."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_HEADER = ["arquivo", "tempo", "processo"]


def list_images(dataset_dir: Path) -> list[Path]:
    return sorted(dataset_dir.glob("*.jpg"))
