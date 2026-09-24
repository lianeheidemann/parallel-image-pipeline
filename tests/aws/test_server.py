import threading
import urllib.error
import urllib.request

import pytest

import server
from generate_dataset import generate_dataset


@pytest.fixture
def panel(tmp_path, monkeypatch):
    # Fora da AWS a metadata nao responde; evita esperar o timeout nos testes.
    monkeypatch.setattr(server, "instance_metadata", lambda: {})
    results, dataset = tmp_path / "results", tmp_path / "dataset"
    results.mkdir()
    httpd = server.make_server(0, results, dataset, host="127.0.0.1")
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", results, dataset
    httpd.shutdown()
    httpd.server_close()


def get(url, method="GET"):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=method), timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def write_benchmark(results):
    (results / "benchmark.csv").write_text(
        "processos,tempo_s,speedup,speedup_amdahl_previsto,verificado\n"
        "1,10.0,1.0,1.0,\n"
        "2,5.5,1.818,1.818,sim\n",
        encoding="utf-8",
    )


def test_page_without_results(panel):
    url, _, _ = panel
    status, body = get(url + "/")
    assert status == 200
    assert "Nenhum resultado ainda" in body
    assert "nenhuma imagem" in body


def test_page_shows_benchmark_and_dataset(panel):
    url, results, dataset = panel
    write_benchmark(results)
    generate_dataset(dataset, count=3, size=(64, 48))

    status, body = get(url + "/")

    assert status == 200
    assert "10,00 s" in body and "5,50 s" in body and "1,818×" in body
    assert ">sim<" in body
    assert "3 imagens 64×48" in body
    assert "Fração paralelizável estimada (Amdahl): <b>0,900</b>" in body  # 1 - 1/1.818 = 0.45 -> p = 0.9


def test_running_marker_and_log_are_shown_escaped(panel):
    url, results, _ = panel
    (results / "setup.running").touch()
    (results / "setup.log").write_text("linha 1\n<script>alert(1)</script>\n", encoding="utf-8")

    _, body = get(url + "/")

    assert "Benchmark em andamento" in body
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body


def test_csv_download(panel):
    url, results, _ = panel
    assert get(url + "/benchmark.csv")[0] == 404
    write_benchmark(results)
    status, body = get(url + "/benchmark.csv")
    assert status == 200 and body.startswith("processos,tempo_s")


@pytest.mark.parametrize("path", ["/nada", "/results/benchmark.csv", "/../README.md", "/setup.log"])
def test_other_paths_are_not_served(panel, path):
    url, results, _ = panel
    write_benchmark(results)
    (results / "setup.log").write_text("x", encoding="utf-8")
    assert get(url + path)[0] == 404


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_read_only(panel, method):
    url, _, _ = panel
    assert get(url + "/", method=method)[0] == 405
