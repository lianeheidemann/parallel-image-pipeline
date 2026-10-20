import threading

import pytest

import comparar
import medicao
import server
from cenarios import POR_CHAVE
from dados import carregar, mesmo_dataset
from relatorio import gerar

HEADER = "processos,tempo_s,speedup,speedup_amdahl_previsto,verificado,imagens,resolucao\n"
TEMPOS = {  # cenario -> (sequencial, paralelo com 2, paralelo com 4)
    "local": ("10.0", "5.5", "3.2"),
    "aws": ("15.0", "8.0", None),
    "web": ("20.0", "11.0", None),
}


def benchmark_csv(seq, par2, par4=None, dataset="100,1920x1080"):
    body = f"1,{seq},1.0,1.0,,{dataset}\n2,{par2},{float(seq) / float(par2):.3f},1.8,sim,{dataset}\n"
    if par4:
        body += f"4,{par4},{float(seq) / float(par4):.3f},3.0,sim,{dataset}\n"
    return HEADER + body


def write_results(results, chaves=("local", "aws", "web"), **datasets):
    for chave in chaves:
        cenario = POR_CHAVE[chave]
        cenario.pasta(results).mkdir(parents=True, exist_ok=True)
        cenario.csv(results).write_text(
            benchmark_csv(*TEMPOS[chave], dataset=datasets.get(chave, "100,1920x1080")), encoding="utf-8")
    return results


def test_carregar_keeps_order_and_zeroes_pending_aws(tmp_path):
    medicoes = carregar(write_results(tmp_path, ("web", "local")))
    assert [m.cenario.chave for m in medicoes] == ["local", "aws", "web"]
    local, aws, _ = medicoes
    assert local.dataset == "100 imagens 1920x1080" and not local.pendente
    assert local.melhor_paralelo["processos"] == "4"
    assert aws.pendente and [(r["processos"], r["tempo_s"]) for r in aws.linhas] == [("1", "0"), ("2", "0"), ("4", "0"), ("8", "0")]
    assert mesmo_dataset(medicoes)  # o cenario zerado nao conta


def test_labels_say_language_and_parallel_unit():
    local, aws, web = (POR_CHAVE[k] for k in ("local", "aws", "web"))
    assert local.titulo == "Local (Python)" and web.titulo == "GitHub Pages (JavaScript)"
    assert local.rotulo(1) == "sequencial (1 processo)" and local.rotulo(8) == "8 processos"
    assert web.rotulo(1) == "sequencial (thread principal)" and web.rotulo(8) == "8 Web Workers"
    assert aws.rotulo_curto(2) == "2 proc." and web.rotulo_curto(4) == "4 workers"


def test_machine_cores_are_read():
    from dados import Medicao
    assert Medicao(POR_CHAVE["local"], [], "maquina: i7\nnucleos: 20 logicos").nucleos == "20"


def test_report_compares_the_three_scenarios(tmp_path):
    out, dados = tmp_path / "doc", tmp_path / "results" / "dados.csv"
    gerar(carregar(write_results(tmp_path / "results")), out, dados=dados)

    report = (out / "comparacao.md").read_text(encoding="utf-8")
    assert "| Local (Python) | 10,00 | mais rápido | 3,20 | 4 processos | mais rápido |" in report
    assert "| AWS EC2 (Python) | 15,00 | 1,50× mais lento | 8,00 | 2 processos | 2,50× mais lento |" in report
    assert "| GitHub Pages (JavaScript) | 20,00 | 2,00× mais lento | 11,00 | 2 Web Workers | 3,44× mais lento |" in report
    assert "| GitHub Pages | JavaScript | sequencial (thread principal) | 20,00 | 1,00× | — |" in report
    assert "![Sequencial e paralelo mais rápido de cada cenário](graficos/cenarios.svg)" in report
    assert "pendente" not in report

    for name in ("cenarios.svg", "tempo.svg"):
        svg = (out / "graficos" / name).read_text(encoding="utf-8")
        assert svg.startswith("<svg") and "Local (Python)" in svg and "GitHub Pages (JavaScript)" in svg
        assert "JavaScript · Web Workers" in svg and "Python · processos" in svg
    assert dados.read_text(encoding="utf-8").splitlines()[1] == "local,1,10.0,1.0,,100,1920x1080"
    assert not (out / "dados.csv").exists()


def test_pending_aws_is_shown_zeroed(tmp_path):
    out, dados = tmp_path / "doc", tmp_path / "results" / "dados.csv"
    gerar(carregar(write_results(tmp_path / "results", ("local", "web"))), out, dados=dados)
    report = (out / "comparacao.md").read_text(encoding="utf-8")
    assert "- **AWS EC2 (Python)**" in report and "**pendente**" in report
    assert "| AWS EC2 | Python | 2 processos | 0,00 (pendente) | — | — |" in report
    assert "| AWS EC2 (Python) | 15" not in report  # fora da comparacao direta
    assert "aws," not in dados.read_text(encoding="utf-8")
    cenarios = (out / "graficos" / "cenarios.svg").read_text(encoding="utf-8")
    tempo_svg = (out / "graficos" / "tempo.svg").read_text(encoding="utf-8")
    assert "AWS EC2 (Python)" in cenarios and "Python · processos · pendente" in cenarios
    assert "0,00 s (pendente)" in tempo_svg


def test_different_datasets_are_not_compared(tmp_path):
    out = tmp_path / "doc"
    (out / "graficos").mkdir(parents=True)
    (out / "graficos" / "antigo.svg").write_text("<svg/>", encoding="utf-8")
    gerar(carregar(write_results(tmp_path / "results", aws="2000,1920x1080")), out)
    report = (out / "comparacao.md").read_text(encoding="utf-8")
    assert "datasets diferentes" in report
    assert "Comparação direta" not in report
    assert not list((out / "graficos").glob("*.svg"))


def test_report_without_any_result(tmp_path):
    gerar([], tmp_path / "doc")
    assert "Nenhum cenário medido ainda" in (tmp_path / "doc" / "comparacao.md").read_text(encoding="utf-8")


@pytest.fixture
def aws_panel(tmp_path, monkeypatch):
    # O painel de verdade (code/aws/server.py), servindo um results/ de teste.
    monkeypatch.setattr(server, "instance_metadata", lambda: {})
    results = tmp_path / "ec2"
    (results / "analysis" / "aws").mkdir(parents=True)
    httpd = server.make_server(0, results, tmp_path / "ec2-dataset", host="127.0.0.1")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{httpd.server_address[1]}", results / "analysis" / "aws"
    httpd.shutdown()
    httpd.server_close()


def test_baixar_aws_gets_csv_and_machine(tmp_path, aws_panel):
    address, ec2 = aws_panel
    (ec2 / "benchmark.csv").write_text(benchmark_csv(*TEMPOS["aws"]), encoding="utf-8")
    (ec2 / "maquina.txt").write_text("maquina: Xeon\n", encoding="utf-8")

    destino = medicao.baixar_aws(f"http://{address}/", tmp_path, timeout=5)

    assert destino == POR_CHAVE["aws"].csv(tmp_path)
    assert carregar(tmp_path)[0].maquina == "maquina: Xeon"


def test_baixar_aws_before_the_instance_finished(tmp_path, aws_panel):
    address, _ = aws_panel
    with pytest.raises(OSError):  # o painel responde 404 enquanto a EC2 ainda mede
        medicao.baixar_aws(address, tmp_path, timeout=5)
    assert not POR_CHAVE["aws"].csv(tmp_path).exists()


def test_cli_reuses_measurements_and_downloads_aws(tmp_path, aws_panel):
    address, ec2 = aws_panel
    (ec2 / "benchmark.csv").write_text(benchmark_csv(*TEMPOS["aws"]), encoding="utf-8")
    results, out = write_results(tmp_path / "results", ("local", "web")), tmp_path / "doc"

    charts = tmp_path / "output" / "graficos"
    comparar.main(["--skip-local", "--skip-web", "--aws-ip", address, "--results", str(results),
                   "--out", str(out), "--graficos", str(charts)])

    report = (out / "comparacao.md").read_text(encoding="utf-8")
    assert "| AWS EC2 (Python) | 15,00 | 1,50× mais lento |" in report
    assert (charts / "cenarios.svg").exists() and not (out / "graficos").exists()
    assert (results / "dados.csv").exists() and not (out / "dados.csv").exists()


def test_charts_in_another_folder_are_linked_relative_to_report(tmp_path):
    out, charts = tmp_path / "doc" / "analysis", tmp_path / "output" / "graficos"
    gerar(carregar(write_results(tmp_path / "results")), out, charts)
    report = (out / "comparacao.md").read_text(encoding="utf-8")
    assert "](../../output/graficos/cenarios.svg)" in report
    assert "](../../output/graficos/tempo.svg)" in report
    assert sorted(p.name for p in charts.glob("*.svg")) == ["cenarios.svg", "tempo.svg"]
