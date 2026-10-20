"""Os 3 cenarios comparados e os caminhos usados por todos os modulos.

Cada cenario diz a linguagem e a unidade de paralelismo que usa:
- Python (local e AWS): multiprocessing.Pool, um PROCESSO por nucleo da CPU, uma imagem por processo;
- JavaScript (GitHub Pages): WEB WORKERS do navegador, uma imagem por worker.
Nos dois, o tempo cobre as mesmas 6 etapas por imagem: ler o JPG, cinza, blur, Sobel,
magnitude e gerar o PNG.
"""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# O mesmo dataset em todos os cenarios: as 100 imagens versionadas no repositorio,
# entao sao identicas no PC, na EC2 (que clona o repositorio) e no navegador.
DATASET = ROOT / "dataset" / "dataset-100"

PAGES_URL = "https://lianeheidemann.github.io/parallel-image-pipeline/"
RESULTS = ROOT / "output" / "results" / "analysis"  # entrada: <cenario>/benchmark.csv e maquina.txt;
                                                    # saida: dados.csv (os 3 cenarios juntos)
DOC = ROOT / "doc" / "analysis"           # saida: relatorio (comparacao.md)
GRAFICOS = ROOT / "output" / "graficos"   # saida: graficos SVG

CSV_NAME = "benchmark.csv"
MACHINE_NAME = "maquina.txt"


@dataclass(frozen=True)
class Cenario:
    chave: str
    nome: str            # onde roda
    linguagem: str
    paralelismo: str     # tecnica usada para paralelizar
    unidade: tuple[str, str]  # unidade paralela (singular, plural): processo(s) ou Web Worker(s)
    sequencial: str      # como roda a versao sequencial
    cor: str
    # Enquanto nao ha resultado, o cenario aparece zerado com estas contagens (1 = sequencial).
    contagens_pendentes: tuple[int, ...] = ()

    @property
    def titulo(self) -> str:
        return f"{self.nome} ({self.linguagem})"

    @property
    def tecnica(self) -> str:
        return f"{self.linguagem} · {self.paralelismo}"

    def rotulo(self, processos: int | str) -> str:
        """"8 processos" / "8 Web Workers"; o sequencial diz como roda."""
        n = int(processos)
        if n == 1:
            return f"sequencial ({self.sequencial})"
        return f"{n} {self.unidade[1]}"

    def rotulo_curto(self, processos: int | str) -> str:
        n = int(processos)
        return "seq." if n == 1 else f"{n} {'proc.' if self.unidade[0] == 'processo' else 'workers'}"

    def pasta(self, results: Path = RESULTS) -> Path:
        return results / self.chave

    def csv(self, results: Path = RESULTS) -> Path:
        return self.pasta(results) / CSV_NAME

    def maquina(self, results: Path = RESULTS) -> Path:
        return self.pasta(results) / MACHINE_NAME


CENARIOS = [
    Cenario("local", "Local", "Python", "multiprocessing: processos nos núcleos da CPU do PC",
            ("processo", "processos"), "1 processo", "#3776AB"),
    # c5.large tem 2 vCPUs; 4 e 8 processos medem sobrecarga acima da capacidade da instância.
    Cenario("aws", "AWS EC2", "Python", "multiprocessing na c5.large (2 vCPUs)",
            ("processo", "processos"), "1 processo", "#FF9900", contagens_pendentes=(1, 2, 4, 8)),
    Cenario("web", "GitHub Pages", "JavaScript", "Web Workers no navegador (Chromium do PC), uma imagem por worker",
            ("Web Worker", "Web Workers"), "thread principal", "#2EA44F"),
]
POR_CHAVE = {c.chave: c for c in CENARIOS}
