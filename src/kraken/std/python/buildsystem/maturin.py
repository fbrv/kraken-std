""" Implements Maturin as a build system for kraken-std. """

from __future__ import annotations

import logging
import shutil
import subprocess as sp
from pathlib import Path

from kraken.common.path import is_relative_to

from ...cargo.manifest import CargoMetadata
from ..pyproject import Pyproject
from ..settings import PythonSettings
from . import ManagedEnvironment
from .poetry import PoetryManagedEnvironment, PoetryPythonBuildSystem

logger = logging.getLogger(__name__)


class MaturinPythonBuildSystem(PoetryPythonBuildSystem):
    """A maturin-backed version of the Poetry build system, that invokes the maturin build-backend.
    Can be enabled by adding the following to the local pyproject.yaml:
    ```toml
    [tool.poetry.dev-dependencies]
    maturin = "0.13.7"

    [build-system]
    requires = ["maturin>=0.13,<0.14"]
    build-backend = "maturin"
    ```
    """

    name = "Maturin"

    def get_managed_environment(self) -> ManagedEnvironment:
        return MaturinManagedEnvironment(self.project_directory)

    def update_pyproject(self, settings: PythonSettings, pyproject: Pyproject) -> None:
        super().update_pyproject(settings, pyproject)
        pyproject.synchronize_project_section_to_poetry_state()

    def build(self, output_directory: Path, as_version: str | None = None) -> list[Path]:
        old_poetry_version = None
        old_project_version = None
        pyproject_path = self.project_directory / "pyproject.toml"
        if as_version is not None:
            pyproject = Pyproject.read(pyproject_path)
            old_poetry_version = pyproject.set_poetry_version(as_version)
            old_project_version = pyproject.set_core_metadata_version(as_version)
            pyproject.save()

        metadata = CargoMetadata.read(self.project_directory)
        dist_dir = metadata.target_directory / "wheels"
        if dist_dir.exists():
            shutil.rmtree(dist_dir)

        command = ["poetry", "run", "maturin", "build", "--release"]
        logger.info("%s", command)
        sp.check_call(command, cwd=self.project_directory)
        src_files = list(dist_dir.iterdir())
        dst_files = [output_directory / path.name for path in src_files]
        for src, dst in zip(src_files, dst_files):
            shutil.move(str(src), dst)

        # Unless the output directory is a subdirectory of the dist_dir, we remove the dist dir again.
        if not is_relative_to(output_directory, dist_dir):
            shutil.rmtree(dist_dir)

        if as_version is not None:
            # We roll back the version
            pyproject = Pyproject.read(pyproject_path)
            pyproject.set_poetry_version(old_poetry_version)
            pyproject.set_core_metadata_version(old_project_version)
            pyproject.save()

        return dst_files


class MaturinManagedEnvironment(PoetryManagedEnvironment):
    def install(self, settings: PythonSettings) -> None:
        super().install(settings)
        command = ["poetry", "run", "maturin", "develop"]
        logger.info("%s", command)
        sp.check_call(command, cwd=self.project_directory)
