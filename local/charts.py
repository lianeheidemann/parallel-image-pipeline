"""Graficos SVG da comparacao entre ambientes (usados por compare_environments.py).

SVG escrito a mao, sem dependencia nova (nada de matplotlib): abre no navegador, no
VS Code e no GitHub, dentro do .md. Cada funcao recebe as linhas ja agrupadas por
ambiente ({ambiente: [linhas do CSV]}) e devolve o texto do SVG.
"""

from html import escape

FONT = "font-family:Segoe UI,Arial,sans-serif"


def pt(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


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


def time_chart(groups: dict[str, list[dict[str, str]]], labels: dict[str, str], colors: dict[str, str],
               shared_scale: bool) -> str:
    """Barras horizontais de tempo, um bloco por ambiente.

    shared_scale=True (todos processaram o mesmo dataset): uma escala para todos, e o
    tamanho das barras compara os ambientes. False: cada bloco na propria escala, e o
    titulo avisa que so vale comparar dentro do bloco.
    """
    width, left, right, bar_h, gap = 720, 140, 110, 22, 8
    overall = max(float(r["tempo_s"]) for rows in groups.values() for r in rows) or 1.0
    y, body = 52, []
    for ambiente, rows in groups.items():
        body.append(f'<text x="20" y="{y + 4}" style="{FONT};font-size:14px;font-weight:600" '
                    f'fill="{colors[ambiente]}">{escape(labels[ambiente])}</text>')
        y += 14
        longest = overall if shared_scale else (max(float(r["tempo_s"]) for r in rows) or 1.0)
        for r in rows:
            seconds = float(r["tempo_s"])
            bar_w = (width - left - right) * seconds / longest
            label = "1 (sequencial)" if r["processos"] == "1" else f"{r['processos']} processos"
            opacity = "0.55" if r["processos"] == "1" else "1"
            text_y = y + bar_h * 0.7
            body += [
                f'<text x="{left - 8}" y="{text_y:.1f}" text-anchor="end" style="{FONT};font-size:12px" fill="#59636e">{label}</text>',
                f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="3" fill="{colors[ambiente]}" fill-opacity="{opacity}"/>',
                f'<text x="{left + bar_w + 6:.1f}" y="{text_y:.1f}" style="{FONT};font-size:12px" fill="#1f2328">{pt(seconds, 2)} s</text>',
            ]
            y += bar_h + gap
        y += 16
    title = ("Tempo de processamento (mesmo dataset, mesma escala)" if shared_scale
             else "Tempo de processamento (datasets diferentes: escala própria por ambiente)")
    return svg_document(width, y, title, body)


def speedup_chart(groups: dict[str, list[dict[str, str]]], labels: dict[str, str], colors: dict[str, str]) -> str | None:
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
        body += [f'<rect x="{legend_x}" y="40" width="12" height="12" rx="2" fill="{colors[ambiente]}"/>',
                 f'<text x="{legend_x + 18}" y="50" style="{FONT};font-size:12px" fill="#1f2328">{escape(labels[ambiente])}</text>']
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
                     f'rx="2" fill="{colors[ambiente]}"/>',
                     f'<text x="{x + bar_w / 2 - 1:.1f}" y="{y_of(value) - 10:.1f}" text-anchor="middle" '
                     f'style="{FONT};font-size:11px" fill="#1f2328">{pt(value, 2)}×</text>']
            if runs[n].get("speedup_amdahl_previsto"):
                body.append(f'<circle cx="{x + bar_w / 2 - 1:.1f}" cy="{y_of(float(runs[n]["speedup_amdahl_previsto"])):.1f}" '
                            f'r="4" fill="#ffffff" stroke="#1f2328" stroke-width="1.5"/>')
        body.append(f'<text x="{left + (i + 0.5) * group_w:.1f}" y="{height - 20}" text-anchor="middle" '
                    f'style="{FONT};font-size:12px" fill="#1f2328">{n} processos</text>')
    return svg_document(width, height, "Speedup medido × ideal × Amdahl", body)
