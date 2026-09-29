import csv

from charts import time_chart
from compare_environments import (
    COLORS,
    FIELDS,
    LABELS,
    dataset_of,
    group_by_environment,
    load_environment,
    merge_environments,
    run,
    same_dataset,
    summarize_environment,
    write_csv,
)

HEADER = "processos,tempo_s,speedup,speedup_amdahl_previsto,verificado,imagens,resolucao\n"


def write_benchmark(path, body):
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def local_csv(tmp_path):
    return write_benchmark(tmp_path / "local.csv", "1,10.0,1.0,1.0,,100,1920x1080\n"
                                                   "2,5.5,1.818,1.818,sim,100,1920x1080\n"
                                                   "4,3.2,3.125,3.077,sim,100,1920x1080\n")


def web_csv(tmp_path, dataset="100,1920x1080"):
    return write_benchmark(tmp_path / "web.csv", f"1,20,1,1,,{dataset}\n2,11,1.818,1.818,sim,{dataset}\n")


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


def test_dataset_is_compared_between_environments(tmp_path):
    same = group_by_environment(merge_environments({"local": local_csv(tmp_path), "web": web_csv(tmp_path)}))
    assert dataset_of(same["local"]) == "100 imagens 1920x1080"
    assert same_dataset(same)

    different = group_by_environment(merge_environments({"local": local_csv(tmp_path), "web": web_csv(tmp_path, "200,1024x768")}))
    assert not same_dataset(different)


def test_old_csv_without_dataset_columns_is_not_comparable(tmp_path):
    old = tmp_path / "old.csv"
    old.write_text("processos,tempo_s,speedup,speedup_amdahl_previsto,verificado\n1,10,1,1,\n2,5,2,2,sim\n", encoding="utf-8")
    groups = group_by_environment(merge_environments({"local": old, "web": web_csv(tmp_path)}))
    assert dataset_of(groups["local"]) == "desconhecido"
    assert not same_dataset(groups)


def test_time_chart_scale_depends_on_dataset(tmp_path):
    groups = group_by_environment(merge_environments({"local": local_csv(tmp_path), "web": web_csv(tmp_path)}))
    assert "mesma escala" in time_chart(groups, LABELS, COLORS, shared_scale=True)
    assert "escala própria" in time_chart(groups, LABELS, COLORS, shared_scale=False)


def test_summary_uses_fastest_parallel_run(tmp_path):
    summary = summarize_environment(load_environment(local_csv(tmp_path), "local"))
    assert "sequencial 10,00 s" in summary
    assert "3,20 s com 4 processos" in summary


def test_summary_is_none_without_parallel_rows(tmp_path):
    only_sequential = write_benchmark(tmp_path / "seq.csv", "1,10.0,1.0,1.0,,100,1920x1080\n")
    assert summarize_environment(load_environment(only_sequential, "local")) is None


def test_run_writes_report_and_charts_folder(tmp_path):
    out = tmp_path / "results"
    run({"local": local_csv(tmp_path), "aws": None, "web": web_csv(tmp_path)}, out)

    report = (out / "comparacao.md").read_text(encoding="utf-8")
    assert "Sem dados ainda: aws (EC2), actions (GitHub)." in report
    assert "- **local (PC)**: 100 imagens 1920x1080" in report
    assert "Todos os ambientes processaram o mesmo dataset" in report
    assert "| local (PC) | 4 | 3,2 | 3,125 | 3,077 | sim |" in report
    assert "![Speedup medido, ideal e previsto por Amdahl](graficos/speedup.svg)" in report
    assert (out / "comparison.csv").exists()
    assert (out / "graficos" / "tempo.svg").read_text(encoding="utf-8").startswith("<svg")
    assert "aws (EC2)" not in (out / "graficos" / "speedup.svg").read_text(encoding="utf-8")


def test_run_warns_when_datasets_differ(tmp_path):
    out = tmp_path / "results"
    run({"local": local_csv(tmp_path), "web": web_csv(tmp_path, "200,1024x768")}, out)
    report = (out / "comparacao.md").read_text(encoding="utf-8")
    assert "processaram datasets diferentes" in report
    assert "escala própria" in (out / "graficos" / "tempo.svg").read_text(encoding="utf-8")


def test_run_without_any_data(tmp_path):
    out = tmp_path / "results"
    rows = run({"local": None, "aws": None, "web": None}, out)
    assert rows == []
    assert "Nenhum resultado encontrado" in (out / "comparacao.md").read_text(encoding="utf-8")
    assert not (out / "graficos").exists()
