""" Tools for Git versioned projects. """

from __future__ import annotations

from typing import Optional, Sequence, cast

from kraken.core.api import Project

from .tasks.const import DEFAULT_GITIGNORE_TOKENS, GITIGNORE_TASK_NAME
from .tasks.gitignore_check_task import GitignoreCheckTask
from .tasks.gitignore_sync_task import GitignoreSyncTask
from .version import GitVersion, git_describe

__all__ = [
    "git_describe",
    "GitVersion",
    "GitignoreSyncTask",
    "GitignoreCheckTask",
    "gitignore",
    "GITIGNORE_TASK_NAME",
    "DEFAULT_GITIGNORE_TOKENS",
]


def gitignore(
    tokens: Sequence[str] = DEFAULT_GITIGNORE_TOKENS,
    project: Project | None = None,
) -> GitignoreSyncTask:
    project = project or Project.current()
    task = cast(Optional[GitignoreSyncTask], project.tasks().get(GITIGNORE_TASK_NAME))
    if task is None:
        task = project.do(GITIGNORE_TASK_NAME, GitignoreSyncTask, group="apply", tokens=tokens)
        project.do(f"{GITIGNORE_TASK_NAME}.check", GitignoreCheckTask, group="check", tokens=tokens)
    else:
        raise ValueError("cannot add gitignore task: task can only be added once")
    return task
