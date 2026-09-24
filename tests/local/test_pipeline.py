import csv

import parallel
import sequential
from generate_dataset import generate_dataset
from verify import verify


def test_sequential_equals_parallel(tmp_path):
    dataset = tmp_path / "dataset"
    generate_dataset(dataset, count=6, size=(64, 48))

    seq_out, par_out = tmp_path / "seq", tmp_path / "par"
    sequential.run(dataset, seq_out, tmp_path / "seq.csv")
    parallel.run(dataset, par_out, tmp_path / "par.csv", workers=2)

    assert verify(seq_out, par_out)
    with open(tmp_path / "par.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert sorted(row["arquivo"] for row in rows) == [p.name for p in sorted(dataset.glob("*.jpg"))]
    assert all(row["processo"].startswith("P") for row in rows)


def test_stale_outputs_are_removed(tmp_path):
    dataset = tmp_path / "dataset"
    generate_dataset(dataset, count=2, size=(32, 32))
    out = tmp_path / "out"
    out.mkdir()
    (out / "velho.png").write_bytes(b"sobra de outra execucao")

    sequential.run(dataset, out, tmp_path / "seq.csv")

    assert sorted(p.name for p in out.glob("*.png")) == ["img1.png", "img2.png"]
