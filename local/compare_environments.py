"""Junta os resultados dos 3 ambientes (local, aws, web) e gera a comparacao.

Entrada: um CSV por ambiente, no formato de results/benchmark.csv (local/benchmark.py
no PC e na EC2; botao "Baixar CSV" da pagina web/). Ambiente sem arquivo e pulado,
entao da para comparar so os que ja foram medidos.

Saida (em --out, padrao results/):
- comparison.csv: todas as linhas, com a coluna "ambiente";
- comparacao.md: tabela, resumo por ambiente e graficos;
- comparacao-tempo.svg e comparacao-speedup.svg: os graficos do .md.

Ao contrario de benchmark.py, aqui as maquinas sao diferentes por definicao: o
speedup de cada ambiente vale dentro dele; os tempos absolutos entre ambientes, nao.

    python local/compare_environments.py --web results/benchmark-web.csv
"""

import argparse
import csv
from datetime import datetime
from html import escape
from pathlib import Path

from common import DATASET_DIR, RESULTS_DIR, list_images, read_csv_rows

# "actions" e o mesmo codigo Python de local/ numa maquina do GitHub Actions
# (.github/workflows/benchmark.yml): um ambiente remoto enquanto a AWS nao existe.
ENVIRONMENTS = ["local", "aws", "actions", "web"]
LABELS = {"local": "local (PC)", "aws": "aws (EC2)", "actions": "actions (GitHub)", "web": "web (navegador)"}
COLORS = {"local": "#3776AB", "aws": "#FF9900", "actions": "#8250DF", "web": "#2EA44F"}
FIELDS = ["ambiente", "processos", "tempo_s", "speedup", "speedup_amdahl_previsto", "verificado"]
TIME_CHART = "comparacao-tempo.svg"
SPEEDUP_CHART = "comparacao-speedup.svg"
CAVEAT = (
    "Os tempos entre ambientes não são diretamente comparáveis: mudam o hardware, a "
    "implementação dos filtros (OpenCV em local/aws/actions, JavaScript em web), a granularidade "
    "da paralelização (uma imagem por processo em Python, faixas horizontais por Web "
    "Worker em web) e, em geral, a quantidade de imagens processadas. Compare sequencial "
    "× paralelo dentro de cada ambiente; entre ambientes, compare o speedup, não os segundos."
)
FONT = "font-family:Segoe UI,Arial,sans-serif"


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


def pt(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


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


def svg_document(width: int, height: int, title: str, body: list[str]) -> str:
    # Fundo branco proprio: o .md pode ser aberto em tema escuro (GitHub, VS Code).
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        f'<rect width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#d0d7de"/>',
        f'<text x="20" y="28" style="{FONT};font-size:16px;font-weight:600" fill="#1f2328">{escape(title)}</text>',
        *body,
        "</svg>",
    ])


def time_chart(groups: dict[str, list[dict[str, str]]]) -> str:
    """Barras horizontais de tempo, um painel por ambiente, cada um na propria escala."""
    width, left, right, bar_h, gap = 720, 140, 110, 22, 8
    y, body = 52, []
    for ambiente, rows in groups.items():
        body.append(f'<text x="20" y="{y + 4}" style="{FONT};font-size:14px;font-weight:600" '
                    f'fill="{COLORS[ambiente]}">{escape(LABELS[ambiente])}</text>')
        y += 14
        longest = max(float(r["tempo_s"]) for r in rows) or 1.0
        for r in rows:
            seconds = float(r["tempo_s"])
            bar_w = (width - left - right) * seconds / longest
            label = "1 (sequencial)" if r["processos"] == "1" else f"{r['processos']} processos"
            opacity = "0.55" if r["processos"] == "1" else "1"
            text_y = y + bar_h * 0.7
            body += [
                f'<text x="{left - 8}" y="{text_y:.1f}" text-anchor="end" style="{FONT};font-size:12px" fill="#59636e">{label}</text>',
                f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="3" fill="{COLORS[ambiente]}" fill-opacity="{opacity}"/>',
                f'<text x="{left + bar_w + 6:.1f}" y="{text_y:.1f}" style="{FONT};font-size:12px" fill="#1f2328">{pt(seconds, 2)} s</text>',
            ]
            y += bar_h + gap
        y += 16
    return svg_document(width, y, "Tempo de processamento (escala própria em cada ambiente)", body)


def speedup_chart(groups: dict[str, list[dict[str, str]]]) -> str | None:
    """Speedup medido por numero de processos, lado a lado, com o ideal (N) e o previsto por Amdahl."""
    parallel = {a: {int(r["processos"]): r for r in rows if r["processos"] != "1"} for a, rows in groups.items()}
    parallel = {a: runs for a, runs in parallel.items() if runs}
    counts = sorted({n for runs in parallel.values() for n in runs})
    if not counts:
        return None

    width, height, left, right, top, bottom = 720, 400, 50, 20, 92, 50
    plot_w, plot_h = width - left - right, height - top - bottom
    measured = [float(r["speedup"]) for runs in parallel.values() for r in runs.values()]
    predicted = [float(r["speedup_amdahl_previsto"]) for runs in parallel.values() for r in runs.values()
                 if r.get("speedup_amdahl_previsto")]
    top_value = max(measured + predicted + counts) * 1.12
    step = 1 if top_value <= 10 else int(top_value // 8) + 1

    def y_of(value: float) -> float:
        return top + plot_h - value / top_value * plot_h

    body = []
    legend_x = 20
    for ambiente in parallel:
        body += [f'<rect x="{legend_x}" y="40" width="12" height="12" rx="2" fill="{COLORS[ambiente]}"/>',
                 f'<text x="{legend_x + 18}" y="50" style="{FONT};font-size:12px" fill="#1f2328">{escape(LABELS[ambiente])}</text>']
        legend_x += 140
    body += ['<line x1="20" y1="66" x2="42" y2="66" stroke="#8c959f" stroke-width="2" stroke-dasharray="5 4"/>',
             f'<text x="48" y="70" style="{FONT};font-size:12px" fill="#1f2328">ideal (N×)</text>',
             '<circle cx="146" cy="66" r="4" fill="#ffffff" stroke="#1f2328" stroke-width="1.5"/>',
             f'<text x="156" y="70" style="{FONT};font-size:12px" fill="#1f2328">Amdahl previsto</text>']

    tick = 0
    while tick <= top_value:
        y = y_of(tick)
        body += [f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#eaeef2"/>',
                 f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end" style="{FONT};font-size:11px" fill="#59636e">{tick}×</text>']
        tick += step

    group_w = plot_w / len(counts)
    bar_w = group_w * 0.7 / len(parallel)
    for i, n in enumerate(counts):
        start = left + i * group_w + group_w * 0.15
        body.append(f'<line x1="{start - 4:.1f}" y1="{y_of(n):.1f}" x2="{start + group_w * 0.7 + 4:.1f}" y2="{y_of(n):.1f}" '
                    f'stroke="#8c959f" stroke-width="2" stroke-dasharray="5 4"/>')
        for j, (ambiente, runs) in enumerate(parallel.items()):
            if n not in runs:
                continue
            x = start + j * bar_w
            value = float(runs[n]["speedup"])
            body += [f'<rect x="{x:.1f}" y="{y_of(value):.1f}" width="{bar_w - 2:.1f}" height="{top + plot_h - y_of(value):.1f}" '
                     f'rx="2" fill="{COLORS[ambiente]}"/>',
                     f'<text x="{x + bar_w / 2 - 1:.1f}" y="{y_of(value) - 5:.1f}" text-anchor="middle" '
                     f'style="{FONT};font-size:11px" fill="#1f2328">{pt(value, 2)}×</text>']
            if runs[n].get("speedup_amdahl_previsto"):
                body.append(f'<circle cx="{x + bar_w / 2 - 1:.1f}" cy="{y_of(float(runs[n]["speedup_amdahl_previsto"])):.1f}" '
                            f'r="4" fill="#ffffff" stroke="#1f2328" stroke-width="1.5"/>')
        body.append(f'<text x="{left + (i + 0.5) * group_w:.1f}" y="{height - 20}" text-anchor="middle" '
                    f'style="{FONT};font-size:12px" fill="#1f2328">{n} processos</text>')
    return svg_document(width, height, "Speedup medido × ideal × Amdahl", body)


def render_markdown(rows: list[dict[str, str]], image_count: int | None, charts: list[tuple[str, str]]) -> str:
    groups = group_by_environment(rows)
    missing = [LABELS[a] for a in ENVIRONMENTS if a not in groups]
    lines = [
        "# Comparação de desempenho entre ambientes",
        "",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} por `local/compare_environments.py`.",
    ]
    if image_count is not None:
        lines.append(f"Dataset local (`dataset/`): {image_count} imagens.")
    if missing:
        lines.append(f"Sem dados ainda: {', '.join(missing)}.")
    lines.append("")

    if not rows:
        lines += ["Nenhum resultado encontrado. Gere os CSVs com `local/benchmark.py`, o painel da AWS "
                  "(`/benchmark.csv`) ou o botão \"Baixar CSV\" da página web.", ""]
        return "\n".join(lines)

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
        lines += ["## Gráficos", "", *[f"![{alt}]({name})\n" for alt, name in charts]]
    lines += ["## Como ler", "", CAVEAT, ""]
    return "\n".join(lines)


def run(paths: dict[str, Path | None], out_dir: Path, dataset_dir: Path | None = DATASET_DIR) -> list[dict[str, str]]:
    rows = merge_environments(paths)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(rows, out_dir / "comparison.csv")

    charts = []
    groups = group_by_environment(rows)
    if groups:
        (out_dir / TIME_CHART).write_text(time_chart(groups), encoding="utf-8")
        charts.append(("Tempo de processamento por ambiente", TIME_CHART))
        speedup = speedup_chart(groups)
        if speedup:
            (out_dir / SPEEDUP_CHART).write_text(speedup, encoding="utf-8")
            charts.append(("Speedup medido, ideal e previsto por Amdahl", SPEEDUP_CHART))

    image_count = len(list_images(dataset_dir)) if dataset_dir and dataset_dir.exists() else None
    report = out_dir / "comparacao.md"
    report.write_text(render_markdown(rows, image_count, charts), encoding="utf-8")
    print(f"{len(rows)} linhas de {len(groups)} ambiente(s). Relatorio: {report}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara os resultados de local, aws e web")
    parser.add_argument("--local", type=Path, default=RESULTS_DIR / "benchmark.csv")
    parser.add_argument("--aws", type=Path, default=RESULTS_DIR / "benchmark-aws.csv")
    parser.add_argument("--actions", type=Path, default=RESULTS_DIR / "benchmark-actions.csv")
    parser.add_argument("--web", type=Path, default=RESULTS_DIR / "benchmark-web.csv")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR)
    parser.add_argument("--dataset", type=Path, default=DATASET_DIR)
    args = parser.parse_args()

    run({"local": args.local, "aws": args.aws, "actions": args.actions, "web": args.web}, args.out, args.dataset)


if __name__ == "__main__":
    main()
