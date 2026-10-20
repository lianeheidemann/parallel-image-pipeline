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


def write_compare(results, resolucao="1920x1080"):
    compare = results / "analysis" / "aws"
    compare.mkdir(parents=True)
    (compare / "benchmark.csv").write_text(
        "processos,tempo_s,speedup,speedup_amdahl_previsto,verificado,imagens,resolucao\n"
        f"1,20.0,1.0,1.0,,100,{resolucao}\n"
        f"2,11.0,1.818,1.818,sim,100,{resolucao}\n",
        encoding="utf-8",
    )
    (compare / "maquina.txt").write_text("maquina: Xeon\nnucleos: 2 logicos\n", encoding="utf-8")


def test_compare_csv_and_machine_download(panel):
    url, results, _ = panel
    assert get(url + "/comparacao.csv")[0] == 404
    assert get(url + "/comparacao-maquina.txt")[0] == 404
    write_compare(results)
    status, body = get(url + "/comparacao.csv")
    assert status == 200 and body.startswith("processos,tempo_s") and "100,1920x1080" in body
    status, body = get(url + "/comparacao-maquina.txt")
    assert status == 200 and body.splitlines() == ["maquina: Xeon", "nucleos: 2 logicos"]


def test_page_shows_compare_section(panel):
    url, results, _ = panel
    assert "Ainda não medido" in get(url + "/")[1]
    write_compare(results, resolucao="<b>x</b>")
    _, body = get(url + "/")
    assert "20,00 s" in body and "11,00 s" in body
    assert "&lt;b&gt;x&lt;/b&gt;" in body and "<b>x</b>" not in body


@pytest.mark.parametrize("path", ["/analysis/aws/benchmark.csv", "/nada", "/results/benchmark.csv", "/../README.md", "/setup.log"])
def test_other_paths_are_not_served(panel, path):
    url, results, _ = panel
    write_benchmark(results)
    (results / "setup.log").write_text("x", encoding="utf-8")
    assert get(url + path)[0] == 404


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_read_only(panel, method):
    url, _, _ = panel
    assert get(url + "/", method=method)[0] == 405
