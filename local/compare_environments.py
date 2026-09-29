"""Junta os resultados dos ambientes (local, aws, actions, web) e gera a comparacao.

Entrada: um CSV por ambiente, no formato de results/benchmark.csv (local/benchmark.py
no PC, na EC2 ou no GitHub Actions; botao "Baixar CSV" da pagina web/). Ambiente sem
arquivo e pulado, entao da para comparar so os que ja foram medidos.

Tudo fica numa pasta (--dir, padrao results/comparacao/):
- entrada: benchmark.csv (PC), benchmark-aws.csv, benchmark-actions.csv, benchmark-web.csv;
- saida: comparison.csv (todas as linhas, com a coluna "ambiente"), comparacao.md
  (datasets, tabela, resumo e graficos) e graficos/tempo.svg, graficos/speedup.svg.

Tempos so sao comparaveis entre ambientes que processaram o mesmo dataset (mesma
quantidade de imagens, mesma resolucao): cada CSV registra isso nas colunas
"imagens" e "resolucao", e o relatorio avisa quando os datasets diferem.

    python local/compare_environments.py
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path

from charts import pt, speedup_chart, time_chart
from common import RESULTS_DIR, read_csv_rows

# "actions" e o mesmo codigo Python de local/ numa maquina do GitHub Actions
# (.github/workflows/benchmark.yml): um ambiente remoto enquanto a AWS nao existe.
ENVIRONMENTS = ["local", "aws", "actions", "web"]
LABELS = {"local": "local (PC)", "aws": "aws (EC2)", "actions": "actions (GitHub)", "web": "web (JS, GitHub Pages)"}
COLORS = {"local": "#3776AB", "aws": "#FF9900", "actions": "#8250DF", "web": "#2EA44F"}
FIELDS = ["ambiente", "processos", "tempo_s", "speedup", "speedup_amdahl_previsto", "verificado", "imagens", "resolucao"]
CHARTS_DIR = "graficos"
CAVEAT = (
    "Mesmo com o mesmo dataset, os ambientes diferem em hardware, na implementação dos "
    "filtros (OpenCV em Python, JavaScript na web) e na granularidade da paralelização "
    "(uma imagem por processo em Python, faixas horizontais por Web Worker na web). O "
    "*speedup* mostra quanto cada ambiente ganha ao paralelizar; os segundos mostram qual "
    "é mais rápido — e só valem entre ambientes com o mesmo dataset."
)


def load_environment(path: Path | None, ambiente: str) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        print(f"Aviso: ambiente '{ambiente}' sem arquivo ({path}); pulando.")
        return []
    return [{"ambiente": ambiente, **row} for row in read_csv_rows(path)]


def merge_environments(paths: dict[str, Path | None]) -> list[dict[str, str]]:
    return [row for ambiente in ENVIRONMENTS for row in load_environment(paths.get(ambiente), ambiente)]


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def group_by_environment(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    groups = {ambiente: [r for r in rows if r["ambiente"] == ambiente] for ambiente in ENVIRONMENTS}
    return {a: sorted(g, key=lambda r: int(r["processos"])) for a, g in groups.items() if g}


def dataset_of(rows: list[dict[str, str]]) -> str:
    """"100 imagens 1920x1080", ou "desconhecido" para CSVs antigos sem essas colunas."""
    first = rows[0]
    if not first.get("imagens") or not first.get("resolucao"):
        return "desconhecido"
    return f"{first['imagens']} imagens {first['resolucao']}"


def same_dataset(groups: dict[str, list[dict[str, str]]]) -> bool:
    datasets = {dataset_of(rows) for rows in groups.values()}
    return len(datasets) == 1 and "desconhecido" not in datasets


def summarize_environment(rows: list[dict[str, str]]) -> str | None:
    """Sequencial x paralelo mais rapido de um ambiente; None se faltar um dos dois."""
    sequential = next((r for r in rows if r["processos"] == "1"), None)
    parallel = [r for r in rows if r["processos"] != "1"]
    if sequential is None or not parallel:
        return None
    best = min(parallel, key=lambda r: float(r["tempo_s"]))
    return (
        f"**{LABELS[sequential['ambiente']]}**: sequencial {pt(float(sequential['tempo_s']), 2)} s; "
        f"mais rápido em paralelo {pt(float(best['tempo_s']), 2)} s com {best['processos']} processos "
        f"(speedup {pt(float(best['speedup']), 2)}×)"
    )


def render_markdown(rows: list[dict[str, str]], charts: list[tuple[str, str]]) -> str:
    groups = group_by_environment(rows)
    missing = [LABELS[a] for a in ENVIRONMENTS if a not in groups]
    lines = [
        "# Comparação de desempenho entre ambientes",
        "",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} por `local/compare_environments.py`.",
    ]
    if missing:
        lines.append(f"Sem dados ainda: {', '.join(missing)}.")
    lines.append("")

    if not rows:
        lines += ["Nenhum resultado encontrado. Gere os CSVs com `local/benchmark.py`, o painel da AWS "
                  "(`/benchmark.csv`) ou o botão \"Baixar CSV\" da página web.", ""]
        return "\n".join(lines)

    lines += ["## Dataset de cada ambiente", "",
              *[f"- **{LABELS[a]}**: {dataset_of(g)}" for a, g in groups.items()], ""]
    if same_dataset(groups):
        lines += ["Todos os ambientes processaram o mesmo dataset: tempos e *speedup* são comparáveis.", ""]
    else:
        lines += ["> **Atenção:** os ambientes processaram datasets diferentes. Os segundos **não** "
                  "são comparáveis entre ambientes (o gráfico de tempo usa escala própria em cada um); "
                  "compare apenas o *speedup*. Para comparar tempos, rode todos com o mesmo dataset "
                  "(ver `doc/como-rodar.md`, seção 4).", ""]

    lines += ["## Tabela", "",
              "| Ambiente | Processos | Tempo (s) | Speedup | Amdahl previsto | Verificado |",
              "|---|---:|---:|---:|---:|:---:|"]
    for group in groups.values():
        for r in group:
            processos = "1 (sequencial)" if r["processos"] == "1" else r["processos"]
            lines.append(f"| {LABELS[r['ambiente']]} | {processos} | {r['tempo_s'].replace('.', ',')} | "
                         f"{r['speedup'].replace('.', ',')} | {(r.get('speedup_amdahl_previsto') or '—').replace('.', ',')} | "
                         f"{r.get('verificado') or '—'} |")
    lines.append("")

    summaries = [s for s in (summarize_environment(g) for g in groups.values()) if s]
    if summaries:
        lines += ["## Resumo", "", *[f"- {s}" for s in summaries], ""]
    if charts:
        lines += ["## Gráficos", "", *[f"![{alt}]({path})\n" for alt, path in charts]]
    lines += ["## Como ler", "", CAVEAT, ""]
    return "\n".join(lines)


def write_charts(groups: dict[str, list[dict[str, str]]], out_dir: Path) -> list[tuple[str, str]]:
    """Grava os SVGs em out_dir/graficos/ e devolve (texto alternativo, caminho relativo ao .md)."""
    charts_dir = out_dir / CHARTS_DIR
    charts_dir.mkdir(parents=True, exist_ok=True)
    for old in charts_dir.glob("*.svg"):
        old.unlink()  # um grafico de uma execucao anterior nao pode sobrar no relatorio
    charts = []
    svgs = [("tempo.svg", "Tempo de processamento por ambiente", time_chart(groups, LABELS, COLORS, same_dataset(groups))),
            ("speedup.svg", "Speedup medido, ideal e previsto por Amdahl", speedup_chart(groups, LABELS, COLORS))]
    for name, alt, svg in svgs:
        if svg:
            (charts_dir / name).write_text(svg, encoding="utf-8")
            charts.append((alt, f"{CHARTS_DIR}/{name}"))
    return charts


def run(paths: dict[str, Path | None], out_dir: Path) -> list[dict[str, str]]:
    rows = merge_environments(paths)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(rows, out_dir / "comparison.csv")

    groups = group_by_environment(rows)
    charts = write_charts(groups, out_dir) if groups else []
    if groups and not same_dataset(groups):
        print("Aviso: ambientes com datasets diferentes; compare so o speedup, nao os segundos.")

    report = out_dir / "comparacao.md"
    report.write_text(render_markdown(rows, charts), encoding="utf-8")
    print(f"{len(rows)} linhas de {len(groups)} ambiente(s). Relatorio: {report}")
    return rows


INPUT_NAMES = {"local": "benchmark.csv", "aws": "benchmark-aws.csv", "actions": "benchmark-actions.csv", "web": "benchmark-web.csv"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara os resultados de local, aws, actions e web")
    parser.add_argument("--dir", type=Path, default=RESULTS_DIR / "comparacao",
                        help="Pasta com os CSVs de entrada (nomes padrao) e onde sai o relatorio")
    for ambiente, name in INPUT_NAMES.items():
        parser.add_argument(f"--{ambiente}", type=Path, help=f"CSV do ambiente (padrao: DIR/{name})")
    parser.add_argument("--out", type=Path, help="Pasta de saida (padrao: DIR)")
    args = parser.parse_args()

    paths = {a: getattr(args, a) or args.dir / name for a, name in INPUT_NAMES.items()}
    run(paths, args.out or args.dir)


if __name__ == "__main__":
    main()
