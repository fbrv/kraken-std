from .settings import PythonSettings, python_settings
from .tasks.black_task import BlackTask, black
from .tasks.build_task import BuildTask, build
from .tasks.flake8_task import Flake8Task, flake8
from .tasks.install_task import InstallTask, install
from .tasks.isort_task import IsortTask, isort
from .tasks.login_task import login
from .tasks.mypy_subtest_task import MypyStubtestTask, mypy_subtest
from .tasks.mypy_task import MypyTask, mypy
from .tasks.publish_task import PublishTask, publish
from .tasks.pycln_task import PyclnTask, pycln
from .tasks.pylint_task import PylintTask, pylint
from .tasks.pytest_task import PytestTask, pytest
from .tasks.pyupgrade_task import PyUpgradeCheckTask, PyUpgradeTask, pyupgrade
from .tasks.update_lockfile_task import update_lockfile_task
from .tasks.update_pyproject_task import update_pyproject_task

# Backwards compatibilty
from .version import git_version_to_python_version, git_version_to_python_version as git_version_to_python

__all__ = [
    "black",
    "BlackTask",
    "build",
    "BuildTask",
    "flake8",
    "Flake8Task",
    "git_version_to_python_version",
    "git_version_to_python",
    "install",
    "InstallTask",
    "isort",
    "IsortTask",
    "login",
    "mypy",
    "MypyTask",
    "mypy_subtest",
    "MypyStubtestTask",
    "publish",
    "PublishTask",
    "pycln",
    "PyclnTask",
    "pylint",
    "PylintTask",
    "pytest",
    "PytestTask",
    "python_settings",
    "PythonSettings",
    "pyupgrade",
    "PyUpgradeTask",
    "PyUpgradeCheckTask",
    "update_lockfile_task",
    "update_pyproject_task",
]
