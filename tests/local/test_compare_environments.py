import csv

from compare_environments import (
    FIELDS,
    load_environment,
    merge_environments,
    run,
    summarize_environment,
    write_csv,
)

HEADER = "processos,tempo_s,speedup,speedup_amdahl_previsto,verificado\n"


def write_benchmark(path, body):
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def local_csv(tmp_path):
    return write_benchmark(tmp_path / "local.csv", "1,10.0,1.0,1.0,\n2,5.5,1.818,1.818,sim\n4,3.2,3.125,3.077,sim\n")


def web_csv(tmp_path):
    return write_benchmark(tmp_path / "web.csv", "1,2,1,1,\n2,1.2,1.667,1.667,sim\n")


def test_load_environment_adds_ambiente(tmp_path):
    rows = load_environment(local_csv(tmp_path), "local")
    assert [r["ambiente"] for r in rows] == ["local"] * 3
    assert rows[1]["tempo_s"] == "5.5"


def test_missing_environment_is_skipped(tmp_path, capsys):
    assert load_environment(None, "aws") == []
    assert load_environment(tmp_path / "nao-existe.csv", "aws") == []
    assert "pulando" in capsys.readouterr().out


def test_merge_keeps_order_and_skips_missing(tmp_path):
    rows = merge_environments({"web": web_csv(tmp_path), "aws": None, "local": local_csv(tmp_path)})
    assert [r["ambiente"] for r in rows] == ["local"] * 3 + ["web"] * 2


def test_actions_environment_sits_between_aws_and_web(tmp_path):
    rows = merge_environments({"web": web_csv(tmp_path), "actions": local_csv(tmp_path), "local": tmp_path})
    assert [r["ambiente"] for r in rows] == ["actions"] * 3 + ["web"] * 2  # pasta no lugar de arquivo: pulada


def test_write_csv_roundtrip(tmp_path):
    rows = merge_environments({"local": local_csv(tmp_path)})
    out = tmp_path / "out" / "comparison.csv"
    write_csv(rows, out)
    with open(out, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDS
        assert list(reader) == rows


def test_summary_uses_fastest_parallel_run(tmp_path):
    summary = summarize_environment(load_environment(local_csv(tmp_path), "local"))
    assert "sequencial 10,00 s" in summary
    assert "3,20 s com 4 processos" in summary


def test_summary_is_none_without_parallel_rows(tmp_path):
    only_sequential = write_benchmark(tmp_path / "seq.csv", "1,10.0,1.0,1.0,\n")
    assert summarize_environment(load_environment(only_sequential, "local")) is None


def test_run_writes_report_and_charts(tmp_path):
    out = tmp_path / "results"
    run({"local": local_csv(tmp_path), "aws": None, "web": web_csv(tmp_path)}, out, dataset_dir=None)

    report = (out / "comparacao.md").read_text(encoding="utf-8")
    assert "local (PC)" in report and "web (navegador)" in report
    assert "Sem dados ainda: aws (EC2), actions (GitHub)." in report
    assert "| local (PC) | 4 | 3,2 | 3,125 | 3,077 | sim |" in report
    assert "não são diretamente comparáveis" in report
    assert "![Speedup medido, ideal e previsto por Amdahl](comparacao-speedup.svg)" in report
    assert (out / "comparison.csv").exists()
    assert (out / "comparacao-tempo.svg").read_text(encoding="utf-8").startswith("<svg")
    assert "aws (EC2)" not in (out / "comparacao-speedup.svg").read_text(encoding="utf-8")


def test_run_without_any_data(tmp_path):
    out = tmp_path / "results"
    rows = run({"local": None, "aws": None, "web": None}, out, dataset_dir=None)
    assert rows == []
    assert "Nenhum resultado encontrado" in (out / "comparacao.md").read_text(encoding="utf-8")
    assert not (out / "comparacao-tempo.svg").exists()
