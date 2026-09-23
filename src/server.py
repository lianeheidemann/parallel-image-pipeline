"""Painel de resultados: servico HTTP so de leitura com o ultimo benchmark da maquina.

E a "porta do servico" da instancia na nuvem (ver cloud/user-data.sh e o README).
Rotas fixas, so GET:
- /               pagina com a tabela de results/benchmark.csv e dados da maquina
- /benchmark.csv  o CSV bruto
Nao serve nenhum outro arquivo: todo texto lido do disco e escapado antes de ir para a pagina.
"""

import argparse
import csv
import functools
import html
import os
import platform
import urllib.request
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from common import DATASET_DIR, RESULTS_DIR, list_images

BENCHMARK_CSV = "benchmark.csv"
SETUP_LOG = "setup.log"
# Criado por cloud/user-data.sh enquanto gera o dataset e roda o benchmark.
RUNNING_MARKER = "setup.running"
LOG_LINES = 15


@functools.lru_cache(maxsize=1)
def instance_metadata() -> dict[str, str]:
    """Tipo de instancia e zona pela metadata da EC2 (IMDSv2); vazio fora da AWS."""
    base = "http://169.254.169.254/latest"
    # Endereco local da EC2: nunca passar por proxy configurado no ambiente.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        token_request = urllib.request.Request(
            f"{base}/api/token", method="PUT", headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"})
        token = opener.open(token_request, timeout=0.5).read().decode()
        info = {}
        for key, path in [("tipo", "instance-type"), ("zona", "placement/availability-zone")]:
            request = urllib.request.Request(f"{base}/meta-data/{path}", headers={"X-aws-ec2-metadata-token": token})
            info[key] = opener.open(request, timeout=0.5).read().decode()
        return info
    except OSError:
        return {}


def read_benchmark(results_dir: Path) -> list[dict[str, str]]:
    path = results_dir / BENCHMARK_CSV
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parallel_fraction(rows: list[dict[str, str]]) -> float | None:
    # Mesma estimativa do benchmark.py: p a partir da primeira contagem de processos.
    from benchmark import estimate_parallel_fraction

    try:
        seq = next(float(r["tempo_s"]) for r in rows if r["processos"] == "1")
        first = next(r for r in rows if r["processos"] != "1")
        return estimate_parallel_fraction(seq, float(first["tempo_s"]), int(first["processos"]))
    except (StopIteration, KeyError, ValueError):
        return None


def dataset_summary(dataset_dir: Path) -> str:
    images = list_images(dataset_dir)
    if not images:
        return "nenhuma imagem"
    try:
        from PIL import Image

        with Image.open(images[0]) as first:
            return f"{len(images)} imagens {first.width}×{first.height}"
    except OSError:
        return f"{len(images)} imagens"


def last_lines(path: Path, count: int) -> str:
    if not path.exists():
        return ""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-count:])


def pt(value: str, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}".replace(".", ",")
    except ValueError:
        return value


def render_page(results_dir: Path, dataset_dir: Path) -> str:
    esc = html.escape
    rows = read_benchmark(results_dir)
    running = (results_dir / RUNNING_MARKER).exists()
    meta = instance_metadata()
    machine = [
        ("Núcleos lógicos", str(os.cpu_count())),
        ("Tipo de instância", meta.get("tipo", "—")),
        ("Zona", meta.get("zona", "—")),
        ("Sistema", f"{platform.system()} {platform.release()} · Python {platform.python_version()}"),
        ("Entrada", dataset_summary(dataset_dir)),
    ]

    if rows:
        csv_path = results_dir / BENCHMARK_CSV
        when = datetime.fromtimestamp(csv_path.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
        body_rows = "".join(
            "<tr>"
            f"<td>{esc(r.get('processos', ''))}{' (sequencial)' if r.get('processos') == '1' else ''}</td>"
            f"<td>{esc(pt(r.get('tempo_s', ''), 2))} s</td>"
            f"<td>{esc(pt(r.get('speedup', '')))}×</td>"
            f"<td>{esc(pt(r.get('speedup_amdahl_previsto', '')))}×</td>"
            f"<td>{esc(r.get('verificado') or '—')}</td>"
            "</tr>"
            for r in rows)
        p = parallel_fraction(rows)
        fraction = f"<p>Fração paralelizável estimada (Amdahl): <b>{pt(str(p))}</b></p>" if p is not None else ""
        results = (
            f"<p class='muted'>Medido em {esc(when)} · mediana das rodadas · "
            f"<a href='/{BENCHMARK_CSV}'>baixar CSV</a></p>"
            "<div class='table-wrap'><table><thead><tr><th>Processos</th><th>Tempo</th><th>Speedup</th>"
            "<th>Previsto (Amdahl)</th><th>Verificado</th></tr></thead>"
            f"<tbody>{body_rows}</tbody></table></div>{fraction}")
    else:
        results = "<p class='muted'>Nenhum resultado ainda. Rode <code>python src/benchmark.py</code>.</p>"

    status = "<p class='running'>Benchmark em andamento…</p>" if running else ""
    log = last_lines(results_dir / SETUP_LOG, LOG_LINES)
    log_block = f"<h2>Últimas linhas de setup.log</h2><pre>{esc(log)}</pre>" if log else ""
    machine_rows = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in machine)

    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{'<meta http-equiv="refresh" content="15">' if running else ''}
<title>Pipeline de Imagens · Resultados</title>
<style>
body {{ margin:0; font-family:system-ui,sans-serif; color:#101b36; background:#f7f8fc; }}
main {{ max-width:760px; margin:0 auto; padding:32px 16px; }}
h1 {{ font-size:1.6rem; margin:0 0 4px; }} h2 {{ font-size:1.1rem; margin:28px 0 10px; }}
.muted {{ color:#68758e; }} .running {{ color:#3151d4; font-weight:600; }}
section {{ background:#fff; border:1px solid #dfe4ef; border-radius:12px; padding:20px; margin-top:18px; min-width:0; }}
section > h2:first-child {{ margin-top:0; }}
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }}
th,td {{ text-align:left; padding:8px 6px; border-bottom:1px solid #e7eaf2; white-space:nowrap; }}
@media (max-width:480px) {{ section {{ padding:16px 14px; }} th,td {{ padding:8px 4px; font-size:.85rem; }} dl div {{ grid-template-columns:7.5rem 1fr; }} }}
th {{ font-size:.85rem; color:#5a6981; }}
dl {{ display:grid; gap:6px; margin:0; }} dl div {{ display:grid; grid-template-columns:9rem 1fr; gap:10px; }}
dt {{ color:#68758e; }} dd {{ margin:0; overflow-wrap:anywhere; }}
pre {{ background:#101b36; color:#e7ecf6; padding:12px; border-radius:8px; overflow-x:auto; font-size:.8rem; }}
</style></head>
<body><main>
<h1>Pipeline de Imagens</h1>
<p class="muted">Resultados do benchmark sequencial × paralelo nesta máquina</p>
<section><h2>Máquina</h2><dl>{machine_rows}</dl></section>
<section><h2>Benchmark</h2>{status}{results}</section>
{f'<section>{log_block}</section>' if log_block else ''}
</main></body></html>"""


def make_server(port: int, results_dir: Path, dataset_dir: Path, host: str = "0.0.0.0") -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def send_body(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/":
                page = render_page(results_dir, dataset_dir).encode("utf-8")
                self.send_body(HTTPStatus.OK, "text/html; charset=utf-8", page)
            elif path == f"/{BENCHMARK_CSV}" and (results_dir / BENCHMARK_CSV).exists():
                self.send_body(HTTPStatus.OK, "text/csv; charset=utf-8", (results_dir / BENCHMARK_CSV).read_bytes())
            else:
                self.send_body(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", "Nao encontrado.".encode())

        def not_allowed(self) -> None:
            self.send_body(HTTPStatus.METHOD_NOT_ALLOWED, "text/plain; charset=utf-8", "Somente leitura.".encode())

        do_POST = do_PUT = do_DELETE = do_PATCH = not_allowed

    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Painel de resultados (HTTP, somente leitura)")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--results", type=Path, default=RESULTS_DIR)
    parser.add_argument("--dataset", type=Path, default=DATASET_DIR)
    args = parser.parse_args()

    server = make_server(args.port, args.results, args.dataset)
    print(f"Painel em http://0.0.0.0:{args.port}/ (Ctrl+C para parar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
