"""Python build system helper functions """

from __future__ import annotations

import logging
import re
from pathlib import Path

from kraken.std.python.pyproject import Pyproject

logger = logging.getLogger(__name__)


def update_python_version_str_in_source_files(as_version: str, project_directory: Path) -> None:
    FILENAMES = ["__init__.py", "__about__.py", "_version.py"]
    VERSION_REGEX = r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]'
    replace_with = f'__version__ = "{as_version}"'

    for source_file_path in project_directory.rglob("*.py"):
        if source_file_path.name not in FILENAMES:
            continue
        source_file_path_ = Path(source_file_path)
        content = source_file_path_.read_text()
        (content, n_replaces) = re.subn(VERSION_REGEX, replace_with, content, flags=re.M)
        if n_replaces > 0:
            source_file_path_.write_text(content)


def update_python_version_str(as_version: str | None, project_directory: Path) -> str | None:
    old_version = None
    if as_version is not None:
        pyproject_path = project_directory / "pyproject.toml"
        pyproject = Pyproject.read(pyproject_path)
        old_version = pyproject.set_poetry_version(as_version)
        pyproject.save()
        update_python_version_str_in_source_files(as_version, project_directory)
    return old_version
