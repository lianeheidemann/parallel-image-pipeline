"""Graficos SVG do tempo de processamento de cada cenario.

SVG escrito a mao, sem dependencia nova: abre no navegador, no VS Code e no GitHub,
dentro do .md. So e chamado com o mesmo dataset em todos os cenarios medidos, entao
todos usam uma escala unica e o tamanho das barras compara os cenarios. Cada cenario
diz a linguagem (Python ou JavaScript), a unidade paralela (processos ou Web Workers)
e os nucleos da maquina; um cenario pendente aparece zerado.
"""

from html import escape

from dados import Medicao, tempo

FONT = "font-family:Segoe UI,Arial,sans-serif"
TEXT, MUTED, GRID = "#1f2328", "#59636e", "#eaeef2"


def pt(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def svg_document(width: int, height: int, title: str, body: list[str]) -> str:
    # Fundo branco proprio: o .md pode ser aberto em tema escuro (GitHub, VS Code).
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        '<style>@media (prefers-color-scheme: dark){rect[fill="#ffffff"]{fill:#0d1117;stroke:#30363d} '
        'text[fill="#1f2328"]{fill:#f0f3f6} text[fill="#59636e"]{fill:#9da7b3} '
        'line[stroke="#eaeef2"],line[stroke="#d0d7de"]{stroke:#30363d}}</style>',
        f'<rect width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#d0d7de"/>',
        f'<text x="20" y="28" style="{FONT};font-size:16px;font-weight:600" fill="{TEXT}">{escape(title)}</text>',
        *body,
        "</svg>",
    ])


def text(x: float, y: float, content: str, size: int = 12, fill: str = TEXT, anchor: str = "start",
         weight: str = "normal") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'style="{FONT};font-size:{size}px;font-weight:{weight}" fill="{fill}">{escape(content)}</text>')


def grid_step(top_value: float) -> float:
    """Passo da grade com no maximo 8 linhas: 1, 2, 5, 10, 20, 50..."""
    step = 1.0
    while top_value / step > 8:
        for factor in (2, 2.5, 2):
            step *= factor
            if top_value / step <= 8:
                break
    return step


def hardware(m: Medicao) -> str:
    """"Python · processos · 20 núcleos", ou "... · pendente" sem resultado."""
    partes = [m.cenario.linguagem, m.cenario.unidade[1]]
    if m.pendente:
        partes.append("pendente")
    elif m.nucleos:
        partes.append(f"{m.nucleos} núcleos")
    return " · ".join(partes)


def segundos(m: Medicao, row: dict[str, str]) -> str:
    return f"{pt(tempo(row), 2)} s" + (" (pendente)" if m.pendente else "")


def grafico_cenarios(medicoes: list[Medicao]) -> str:
    """Colunas: sequencial x paralelo mais rapido de cada cenario, lado a lado."""
    width, height, left, right, top, bottom = 720, 400, 60, 20, 76, 84
    plot_w, plot_h = width - left - right, height - top - bottom
    top_value = max(tempo(r) for m in medicoes for r in (m.sequencial, m.melhor_paralelo) if r) * 1.15 or 1.0

    def y_of(value: float) -> float:
        return top + plot_h - value / top_value * plot_h

    body = [f'<rect x="20" y="40" width="12" height="12" rx="2" fill="{MUTED}" fill-opacity="0.55"/>',
            text(38, 50, "sequencial (1 processo / thread principal)"),
            f'<rect x="320" y="40" width="12" height="12" rx="2" fill="{MUTED}"/>',
            text(338, 50, "paralelo mais rápido (processos / Web Workers)")]
    step, tick = grid_step(top_value), 0.0
    while tick <= top_value:
        body += [f'<line x1="{left}" y1="{y_of(tick):.1f}" x2="{width - right}" y2="{y_of(tick):.1f}" stroke="{GRID}"/>',
                 text(left - 6, y_of(tick) + 4, f"{pt(tick, 0)} s", 11, MUTED, "end")]
        tick += step

    group_w = plot_w / len(medicoes)
    bar_w = min(group_w * 0.35, 90)
    for i, m in enumerate(medicoes):
        center = left + (i + 0.5) * group_w
        for j, (row, opacity) in enumerate([(m.sequencial, "0.55"), (m.melhor_paralelo, "1")]):
            if row is None:
                continue
            x = center - bar_w - 2 + j * (bar_w + 4)
            body += [f'<rect x="{x:.1f}" y="{y_of(tempo(row)):.1f}" width="{bar_w:.1f}" '
                     f'height="{top + plot_h - y_of(tempo(row)):.1f}" rx="3" fill="{m.cenario.cor}" fill-opacity="{opacity}"/>',
                     text(x + bar_w / 2, y_of(tempo(row)) - 6, f"{pt(tempo(row), 2)} s", 11, anchor="middle"),
                     text(x + bar_w / 2, top + plot_h + 14, m.cenario.rotulo_curto(row["processos"]), 10, MUTED, "middle")]
        body += [text(center, height - 40, m.cenario.titulo, 12, m.cenario.cor, "middle", "600"),
                 text(center, height - 22, hardware(m), 11, MUTED, "middle")]
    return svg_document(width, height, "Tempo para processar o mesmo dataset em cada cenário", body)


def grafico_tempo(medicoes: list[Medicao]) -> str:
    """Barras horizontais: tempo com cada contagem de processos/workers, um bloco por cenario."""
    width, left, right, bar_h, gap = 720, 230, 120, 22, 8
    longest = max(tempo(r) for m in medicoes for r in m.linhas) or 1.0
    y, body = 52, []
    for m in medicoes:
        body.append(text(20, y + 4, f"{m.cenario.titulo} — {m.cenario.paralelismo}", 13, m.cenario.cor, weight="600"))
        body.append(text(20, y + 20, hardware(m), 11, MUTED))
        y += 30
        for r in m.linhas:
            bar_w = (width - left - right) * tempo(r) / longest
            opacity = "0.55" if r["processos"] == "1" else "1"
            body += [text(left - 8, y + bar_h * 0.7, m.cenario.rotulo(r["processos"]), 12, MUTED, "end"),
                     f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="3" '
                     f'fill="{m.cenario.cor}" fill-opacity="{opacity}"/>',
                     text(left + bar_w + 6, y + bar_h * 0.7, segundos(m, r))]
            y += bar_h + gap
        y += 16
    return svg_document(width, y, "Tempo por número de processos ou Web Workers (mesmo dataset)", body)
