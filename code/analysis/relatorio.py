"""Gera o relatorio (doc/analysis/comparacao.md), os graficos (output/graficos/*.svg) e a
tabela com todos os tempos (output/results/analysis/dados.csv)."""

import csv
import os
from datetime import datetime
from pathlib import Path

from cenarios import CENARIOS
from dados import Medicao, medidas, mesmo_dataset, tempo
from graficos import grafico_cenarios, grafico_tempo, pt

CAMPOS = ["cenario", "processos", "tempo_s", "speedup", "verificado", "imagens", "resolucao"]
COMO_LER = (
    "Os três cenários processam as mesmas imagens com o mesmo pipeline (cinza → blur → Sobel), "
    "mas diferem em hardware, na linguagem (Python com OpenCV no PC e na AWS, JavaScript no "
    "navegador) e na unidade paralela: em Python, `multiprocessing` cria **processos** que o "
    "sistema distribui pelos **núcleos** da CPU; no navegador, **Web Workers** (que o navegador "
    "também distribui pelos núcleos do PC). Nos dois, cada imagem inteira vai para um processo ou "
    "worker, e o tempo cobre as mesmas 6 etapas por imagem: ler o JPG, cinza, blur, Sobel X/Y, "
    "magnitude e gerar o PNG (a geração do dataset não entra). Um cenário ainda sem resultado "
    "aparece com tempos zerados. Os segundos mostram quanto tempo cada cenário precisa para o mesmo "
    "trabalho; o *speedup* mostra quanto cada um ganha ao paralelizar."
)


def relativo(segundos: float, mais_rapido: float) -> str:
    razao = segundos / mais_rapido
    return "mais rápido" if razao < 1.005 else f"{pt(razao, 2)}× mais lento"


def comparacao_direta(medicoes: list[Medicao]) -> list[str]:
    com_seq = [m for m in medidas(medicoes) if m.sequencial]
    if len(com_seq) < 2:
        return []
    seq_min = min(tempo(m.sequencial) for m in com_seq)
    paralelos = [tempo(m.melhor_paralelo) for m in com_seq if m.melhor_paralelo]
    par_min = min(paralelos) if paralelos else None
    linhas = ["## Comparação direta", "",
              "| Cenário | Sequencial (s) | Em relação ao mais rápido | Paralelo mais rápido (s) | Com | Em relação ao mais rápido |",
              "|---|---:|---|---:|---:|---|"]
    for m in com_seq:
        seq, best = tempo(m.sequencial), m.melhor_paralelo
        par = (f"{pt(tempo(best), 2)} | {m.cenario.rotulo(best['processos'])} | {relativo(tempo(best), par_min)}"
               if best and par_min else "— | — | —")
        linhas.append(f"| {m.cenario.titulo} | {pt(seq, 2)} | {relativo(seq, seq_min)} | {par} |")
    return linhas + [""]


def resumo(m: Medicao) -> str | None:
    seq, best = m.sequencial, m.melhor_paralelo
    if m.pendente or seq is None or best is None:
        return None
    return (f"**{m.cenario.titulo}**: sequencial {pt(tempo(seq), 2)} s; paralelo mais rápido "
            f"{pt(tempo(best), 2)} s com {m.cenario.rotulo(best['processos'])} (speedup {pt(float(best['speedup']), 2)}×)")


def markdown(medicoes: list[Medicao], graficos: list[tuple[str, str]]) -> str:
    linhas = ["# Tempo de processamento: Local (Python) × AWS EC2 (Python) × GitHub Pages (JavaScript)", "",
              f"Gerado em {datetime.now():%d/%m/%Y %H:%M} por `python code/analysis/comparar.py`.", ""]
    if not medidas(medicoes):
        return "\n".join(linhas + ["Nenhum cenário medido ainda.", ""])

    linhas += ["## Cenários", ""]
    for c in CENARIOS:
        m = next((m for m in medicoes if m.cenario == c), None)
        estado = m.dataset if m and not m.pendente else "**pendente** (sem resultado ainda; aparece zerado)"
        linhas.append(f"- **{c.titulo}** — {c.paralelismo}: {estado}")
        if m and m.maquina:
            linhas.append(f"  - {'; '.join(l.strip() for l in m.maquina.splitlines() if l.strip())}")
    linhas.append("")

    if not mesmo_dataset(medicoes):
        linhas += ["> **Atenção:** os cenários processaram datasets diferentes; os tempos não são "
                   "comparáveis. Meça todos com o mesmo dataset.", ""]

    linhas += ["## Tempos medidos (mediana das rodadas)", "",
               "| Cenário | Linguagem | Execução | Tempo (s) | Speedup | Verificado |", "|---|---|---|---:|---:|:---:|"]
    for m in medicoes:
        for r in m.linhas:
            tempo_s = "0,00 (pendente)" if m.pendente else pt(tempo(r), 2)
            speedup = "—" if m.pendente else f"{pt(float(r['speedup']), 2)}×"
            linhas.append(f"| {m.cenario.nome} | {m.cenario.linguagem} | {m.cenario.rotulo(r['processos'])} | "
                          f"{tempo_s} | {speedup} | {r.get('verificado') or '—'} |")
    linhas.append("")

    if mesmo_dataset(medicoes):
        linhas += comparacao_direta(medicoes)
    resumos = [s for s in map(resumo, medicoes) if s]
    if resumos:
        linhas += ["## Resumo", "", *[f"- {s}" for s in resumos], ""]
    if graficos:
        linhas += ["## Gráficos", "", *[f"![{alt}]({path})\n" for alt, path in graficos]]
    linhas += ["## Como ler", "", COMO_LER, ""]
    return "\n".join(linhas)


def escrever_graficos(medicoes: list[Medicao], pasta: Path, out: Path) -> list[tuple[str, str]]:
    """Grava os SVGs em `pasta` e devolve (texto alternativo, caminho relativo ao .md em `out`)."""
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob("*.svg"):
        antigo.unlink()  # um grafico de uma execucao anterior nao pode sobrar no relatorio
    if not medidas(medicoes) or not mesmo_dataset(medicoes):
        return []
    graficos = [("cenarios.svg", "Sequencial e paralelo mais rápido de cada cenário", grafico_cenarios(medicoes)),
                ("tempo.svg", "Tempo por número de processos em cada cenário", grafico_tempo(medicoes))]
    for nome, _, svg in graficos:
        (pasta / nome).write_text(svg, encoding="utf-8")
    # Caminho relativo ao relatorio, com "/": as imagens aparecem no GitHub e no VS Code.
    return [(alt, Path(os.path.relpath(pasta / nome, out)).as_posix()) for nome, alt, _ in graficos]


def escrever_csv(medicoes: list[Medicao], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({"cenario": m.cenario.chave, **r} for m in medidas(medicoes) for r in m.linhas)


def gerar(medicoes: list[Medicao], out: Path, pasta_graficos: Path | None = None,
          dados: Path | None = None) -> Path:
    """Relatorio em `out`; graficos em `pasta_graficos` (padrao: out/graficos); tabela em `dados`, se dado."""
    out.mkdir(parents=True, exist_ok=True)
    if dados:
        dados.parent.mkdir(parents=True, exist_ok=True)
        escrever_csv(medicoes, dados)
    graficos = escrever_graficos(medicoes, pasta_graficos or out / "graficos", out)
    if medidas(medicoes) and not mesmo_dataset(medicoes):
        print("Aviso: cenarios com datasets diferentes; os tempos nao sao comparaveis.")
    relatorio = out / "comparacao.md"
    relatorio.write_text(markdown(medicoes, graficos), encoding="utf-8")
    pendentes = [c.titulo for c in CENARIOS if c not in {m.cenario for m in medidas(medicoes)}]
    print(f"Relatorio: {relatorio}" + (f" (sem resultado ainda: {', '.join(pendentes)})" if pendentes else ""))
    if graficos:
        print(f"Graficos: {pasta_graficos or out / 'graficos'}")
    return relatorio
