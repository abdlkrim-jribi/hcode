import shutil
from pathlib import Path
from typing import Iterable, List


def read_file(file_path: Path) -> str:
    """Read the entire contents of *file_path* and return as a string."""
    return file_path.read_text()


def write_file(file_path: Path, data: str, overwrite: bool = True) -> None:
    """Write *data* to *file_path*.

    If *overwrite* is ``False`` and the file already exists, a ``FileExistsError``
    is raised.  By default the file is overwritten.
    """
    if not overwrite and file_path.exists():
        raise FileExistsError(f"File {file_path} already exists and overwrite is False")
    file_path.write_text(data)


def append_file(file_path: Path, data: str) -> None:
    """Append *data* to the end of *file_path* (creating the file if needed)."""
    with file_path.open("a", encoding="utf-8") as f:
        f.write(data)


def delete_file(file_path: Path) -> None:
    """Delete *file_path* if it exists."""
    if file_path.exists():
        file_path.unlink()


def list_files(directory: Path, pattern: str, recursive: bool = False) -> List[Path]:
    """Return a list of ``Path`` objects matching *pattern* in *directory*.

    * If *recursive* is ``False`` (default) a non‑recursive ``glob`` is used.
    * If *recursive* is ``True`` a ``rglob`` search is performed.
    """
    if recursive:
        return list(directory.rglob(pattern))
    return list(directory.glob(pattern))


def copy_file(src: Path, dst: Path) -> None:
    """Copy *src* to *dst* preserving file contents."""
    shutil.copy2(src, dst)


def move_file(src: Path, dst: Path) -> None:
    """Move *src* to *dst* (equivalent to ``shutil.move``)."""
    shutil.move(str(src), str(dst))


def get_file_size(file_path: Path) -> int:
    """Return the size of *file_path* in bytes."""
    return file_path.stat().st_size


def file_exists(file_path: Path) -> bool:
    """Return ``True`` if *file_path* exists, otherwise ``False``."""
    return file_path.exists()
