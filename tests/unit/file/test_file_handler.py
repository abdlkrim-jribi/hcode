import os
import shutil
from pathlib import Path

import pytest

from utils.file_handler import (
    read_file,
    write_file,
    append_file,
    delete_file,
    list_files,
    copy_file,
    move_file,
    get_file_size,
    file_exists,
)

def test_write_and_read_file(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    data = "Hello, world!"
    write_file(file_path, data)
    assert file_path.read_text() == data
    assert read_file(file_path) == data

def test_write_overwrite_flag(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    write_file(file_path, "first")
    # Overwrite default True
    write_file(file_path, "second")
    assert read_file(file_path) == "second"
    # Overwrite=False should raise
    with pytest.raises(FileExistsError):
        write_file(file_path, "third", overwrite=False)

def test_append_file(tmp_path: Path):
    file_path = tmp_path / "log.txt"
    write_file(file_path, "line1\n")
    append_file(file_path, "line2\n")
    assert read_file(file_path) == "line1\nline2\n"

def test_delete_file(tmp_path: Path):
    file_path = tmp_path / "to_delete.txt"
    write_file(file_path, "data")
    delete_file(file_path)
    assert not file_path.exists()

def test_list_files(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.log").write_text("b")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_text("c")
    flat = list_files(tmp_path, "*.txt")
    assert len(flat) == 1 and flat[0].name == "a.txt"
    recursive = list_files(tmp_path, "*.txt", recursive=True)
    assert {p.name for p in recursive} == {"a.txt", "c.txt"}

def test_copy_and_move_file(tmp_path: Path):
    src = tmp_path / "src.txt"
    write_file(src, "content")
    dst_copy = tmp_path / "copy.txt"
    copy_file(src, dst_copy)
    assert dst_copy.read_text() == "content"
    dst_move = tmp_path / "moved.txt"
    move_file(src, dst_move)
    assert not src.exists()
    assert dst_move.read_text() == "content"

def test_get_file_size_and_exists(tmp_path: Path):
    file_path = tmp_path / "size.txt"
    data = "12345"
    write_file(file_path, data)
    assert get_file_size(file_path) == len(data)
    assert file_exists(file_path) is True
    delete_file(file_path)
    assert file_exists(file_path) is False