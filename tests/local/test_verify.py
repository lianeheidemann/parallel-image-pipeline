from verify import verify


def write(folder, name, data):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)


def test_identical_folders(tmp_path):
    for side in ("a", "b"):
        write(tmp_path / side, "img1.png", b"x")
        write(tmp_path / side, "img2.png", b"y")
    assert verify(tmp_path / "a", tmp_path / "b")


def test_different_content(tmp_path):
    write(tmp_path / "a", "img1.png", b"x")
    write(tmp_path / "b", "img1.png", b"z")
    assert not verify(tmp_path / "a", tmp_path / "b")


def test_different_file_sets(tmp_path):
    write(tmp_path / "a", "img1.png", b"x")
    write(tmp_path / "b", "img2.png", b"x")
    assert not verify(tmp_path / "a", tmp_path / "b")


def test_empty_folders_fail(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    assert not verify(tmp_path / "a", tmp_path / "b")
