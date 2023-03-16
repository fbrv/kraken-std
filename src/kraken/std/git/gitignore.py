from __future__ import annotations

import enum
import hashlib
import io
import re
from itertools import islice
from os import PathLike
from pathlib import Path
from typing import Iterable, NamedTuple, Optional, Sequence, TextIO

import httpx

GITIGNORE_API_URL = "https://www.toptal.com/developers/gitignore/api/"
GENERATED_GUARD_START_TEMPLATE = "### START-GENERATED-CONTENT [HASH: {hash}]"
GENERATED_GUARD_START_REGEX = r"^### START-GENERATED-CONTENT \[HASH: (.*)\]$"
PARAMETER_HASH_TEMPLATE = "### [PARAMETERS_HASH: {hash}]"
PARAMETER_HASH_REGEX = r"^### \[PARAMETERS_HASH: (.*)\]$"
GENERATED_GUARD_DESCRIPTION = """\
# -------------------------------------------------------------------------------------------------
# THIS SECTION WAS AUTOMATICALLY GENERATED BY KRAKEN; DO NOT MODIFY OR YOUR CHANGES WILL BE LOST.
# If you need to define custom gitignore rules, add them below
# -------------------------------------------------------------------------------------------------"""
GENERATED_GUARD_END = "### END-GENERATED-CONTENT"


class GitignoreException(Exception):
    """Raise for a gitignore parsing/generation exception"""


class GitignoreEntryType(enum.Enum):
    COMMENT = enum.auto()
    BLANK = enum.auto()
    PATH = enum.auto()


class GitignoreEntry(NamedTuple):
    type: GitignoreEntryType
    value: str

    def __str__(self) -> str:
        if self.is_comment():
            return f"# {self.value}"
        return self.value

    def is_comment(self) -> bool:
        return self.type == GitignoreEntryType.COMMENT

    def is_blank(self) -> bool:
        return self.type == GitignoreEntryType.BLANK

    def is_path(self) -> bool:
        return self.type == GitignoreEntryType.PATH


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def hash_parameters(tokens: Sequence[str], extra_paths: Sequence[str]) -> str:
    return hash_content(",".join([*tokens, *extra_paths]))


class GitignoreFile:
    entries: list[GitignoreEntry]
    generated_content: str = ""
    generated_content_hash: Optional[str] = None
    parameters_hash: Optional[str] = None

    def __init__(self, entries: list[GitignoreEntry]):
        self.entries = entries

    def find_comment(self, comment: str) -> int | None:
        return next(
            (i for i, e in enumerate(self.entries) if e.is_comment() and e.value.lstrip("#").strip() == comment), None
        )

    def paths(self, start: int | None = None, stop: int | None = None) -> Iterable[str]:
        return (entry.value for entry in islice(self.entries, start, stop) if entry.is_path())

    def add_comment(self, comment: str, index: int | None = None) -> None:
        entry = GitignoreEntry(GitignoreEntryType.COMMENT, comment)
        self.entries.insert(len(self.entries) if index is None else index, entry)

    def add_blank(self, index: int | None = None) -> None:
        entry = GitignoreEntry(GitignoreEntryType.BLANK, "")
        self.entries.insert(len(self.entries) if index is None else index, entry)

    def add_path(self, path: str, index: int | None = None) -> None:
        entry = GitignoreEntry(GitignoreEntryType.PATH, path)
        self.entries.insert(len(self.entries) if index is None else index, entry)

    def remove_path(self, path: str) -> None:
        removed = 0
        while True:
            index = next((i for i, e in enumerate(self.entries) if e.is_path() and e.value == path), None)
            if index is None:
                break
            del self.entries[index]
            removed += 1
        if removed == 0:
            raise ValueError(f'"{path}" not in GitignoreFile')

    def render(self) -> str:
        guarded_section = [
            GENERATED_GUARD_START_TEMPLATE.format(hash=self.generated_content_hash),
            self.generated_content,
            GENERATED_GUARD_END,
        ]
        user_content = map(str, self.entries)
        return "\n".join(guarded_section) + "\n" + "\n".join(user_content) + "\n"

    def refresh_generated_content(self, tokens: Sequence[str], extra_paths: Sequence[str]) -> None:
        result = httpx.get(GITIGNORE_API_URL + ",".join(tokens))
        if result.status_code != 200:
            raise GitignoreException(f"Error status code returned from {GITIGNORE_API_URL}")

        # MacOS's Icon file ends with a double \r, but this is removed by vscode upon saving.
        # To avoid a constant back and forth between user and sync tasks,
        # all \r chars are removed proactively
        fetched_content = result.text.replace("\r", "")

        self.parameters_hash = hash_parameters(tokens, extra_paths)

        self.generated_content = "\n".join(
            [
                GENERATED_GUARD_DESCRIPTION,
                PARAMETER_HASH_TEMPLATE.format(hash=self.parameters_hash),
                "",
                fetched_content,
                "# Extra paths",  # todo(daviud): name
                *extra_paths,
                "# -------------------------------------------------------------------------------------------------",
            ]
        )

    def refresh_generated_content_hash(self) -> None:
        self.generated_content_hash = hash_content(self.generated_content)

    def check_generation_parameters(self, tokens: Sequence[str], extra_paths: Sequence[str]) -> bool:
        return self.parameters_hash == hash_parameters(tokens, extra_paths)

    def check_generated_content_hash(self) -> bool:
        return self.generated_content_hash == hash_content(self.generated_content)

    def sort_gitignore(self, sort_paths: bool = True, sort_groups: bool = False) -> None:
        """Sorts the entries in the specified gitignore file, keeping paths under a common comment block grouped.
        Will also get rid of any extra blanks.

        :param gitignore: The input to sort.
        :param sort_paths: Whether to sort paths (default: True).
        :param sort_groups: Whether to sort groups among themselves, not just paths within groups (default: False).
        :return: A new, sorted gitignore file.
        """

        class Group(NamedTuple):
            comments: list[str]
            paths: list[str]

        # List of (comments, paths).
        groups: list[Group] = [Group([], [])]

        for entry in self.entries:
            if entry.is_path():
                groups[-1].paths.append(entry.value)
            elif entry.is_comment():
                # If we already have paths in the current group, we open a new group.
                if groups[-1].paths:
                    groups.append(Group([entry.value], []))
                # Otherwise we append the comment to the group.
                else:
                    groups[-1].comments.append(entry.value)

        if sort_groups:
            groups.sort(key=lambda g: "\n".join(g.comments).lower())

        self.entries = []
        self.add_blank()  # separate GENERATED from USER content
        for group in groups:
            if sort_paths:
                group.paths.sort(key=str.lower)
            for comment in group.comments:
                self.add_comment(comment)
            for path in group.paths:
                self.add_path(path)
            self.add_blank()

        if self.entries and self.entries[-1].is_blank():
            self.entries.pop()

    @staticmethod
    def parse(file: TextIO | Path | str) -> GitignoreFile:
        if isinstance(file, str):
            return GitignoreFile.parse(io.StringIO(file))
        elif isinstance(file, PathLike):
            with file.open() as fp:
                return GitignoreFile.parse(fp)

        class State(enum.Enum):
            USER = enum.auto()
            GENERATED = enum.auto()

        gitignore = GitignoreFile([])

        state = State.USER
        generated_content: list[str] = []
        for line in file:
            line = line.rstrip("\n")
            if state == State.USER:
                match = re.match(GENERATED_GUARD_START_REGEX, line)
                if match:
                    gitignore.generated_content_hash = match.group(1)
                    state = State.GENERATED
                elif line.startswith("#"):
                    gitignore.entries.append(GitignoreEntry(GitignoreEntryType.COMMENT, line[1:].lstrip()))
                elif not line.strip():
                    gitignore.entries.append(GitignoreEntry(GitignoreEntryType.BLANK, ""))
                else:
                    gitignore.entries.append(GitignoreEntry(GitignoreEntryType.PATH, line))
            else:  # state == State.GENERATED
                if line == GENERATED_GUARD_END:
                    state = State.USER
                    gitignore.generated_content = "\n".join(generated_content)
                else:
                    generated_content += [line]
                    match = re.match(PARAMETER_HASH_REGEX, line)
                    if match:
                        gitignore.parameters_hash = match.group(1)

        if state == State.GENERATED:
            raise GitignoreException("Generated section never closed")
        return gitignore
