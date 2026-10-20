"""Leitura dos CSVs de cada cenario (formato de output/results/benchmark.csv) e resumos."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from cenarios import CENARIOS, RESULTS, Cenario


@dataclass
class Medicao:
    cenario: Cenario
    linhas: list[dict[str, str]]  # uma por contagem de processos/workers, ordenadas
    maquina: str = ""
    pendente: bool = False        # sem resultado ainda: linhas zeradas

    @property
    def dataset(self) -> str:
        """"100 imagens 1920x1080", ou "desconhecido" para CSV sem essas colunas."""
        first = self.linhas[0]
        if not first.get("imagens") or not first.get("resolucao"):
            return "desconhecido"
        return f"{first['imagens']} imagens {first['resolucao']}"

    @property
    def nucleos(self) -> str | None:
        """Nucleos logicos da maquina, lidos de maquina.txt ("nucleos: 20 logicos")."""
        found = re.search(r"^nucleos:\s*(\d+)", self.maquina, re.MULTILINE)
        return found.group(1) if found else None

    @property
    def sequencial(self) -> dict[str, str] | None:
        return next((r for r in self.linhas if r["processos"] == "1"), None)

    @property
    def melhor_paralelo(self) -> dict[str, str] | None:
        paralelas = [r for r in self.linhas if r["processos"] != "1"]
        return min(paralelas, key=tempo) if paralelas else None


def tempo(linha: dict[str, str]) -> float:
    return float(linha["tempo_s"])


def ler_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pendente(cenario: Cenario) -> Medicao:
    linhas = [{"processos": str(n), "tempo_s": "0", "speedup": "0", "verificado": ""}
              for n in cenario.contagens_pendentes]
    return Medicao(cenario, linhas, pendente=True)


def carregar(results: Path = RESULTS) -> list[Medicao]:
    """Uma medicao por cenario, na ordem de CENARIOS; sem CSV, zerada se o cenario preve isso."""
    medicoes = []
    for cenario in CENARIOS:
        linhas = ler_csv(cenario.csv(results)) if cenario.csv(results).is_file() else []
        if not linhas:
            if cenario.contagens_pendentes:
                medicoes.append(pendente(cenario))
            continue
        maquina = cenario.maquina(results)
        texto = maquina.read_text(encoding="utf-8").strip() if maquina.is_file() else ""
        medicoes.append(Medicao(cenario, sorted(linhas, key=lambda r: int(r["processos"])), texto))
    return medicoes


def medidas(medicoes: list[Medicao]) -> list[Medicao]:
    return [m for m in medicoes if not m.pendente]


def mesmo_dataset(medicoes: list[Medicao]) -> bool:
    datasets = {m.dataset for m in medidas(medicoes)}
    return len(datasets) == 1 and "desconhecido" not in datasets
