"""Unit tests for scripts.git_sync helpers."""

from scripts.git_sync import _normalize_extensions, _stage_safe_changes


class _DummyGit:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def add(self, *args: str) -> None:
        self.calls.append(args)


class _DummyRepo:
    def __init__(self, untracked_files: list[str]) -> None:
        self.git = _DummyGit()
        self.untracked_files = untracked_files


def test_normalize_extensions_adds_dot_and_lowercases() -> None:
    """拡張子正規化で大文字・ドットなしを統一する."""
    normalized = _normalize_extensions(["md", ".Canvas", "  .TXT  ", ""])
    assert normalized == {".md", ".canvas", ".txt"}


def test_stage_safe_changes_only_stages_allowed_extensions() -> None:
    """許可拡張子のみ新規ファイルがステージングされる."""
    repo = _DummyRepo(
        untracked_files=[
            "note1.md",
            "board.canvas",
            "image.png",
            "README.MD",
        ]
    )

    staged_count = _stage_safe_changes(repo, [".md", "canvas"])

    assert staged_count == 3
    assert repo.git.calls[0] == ("--update",)
    assert ("--", "note1.md") in repo.git.calls
    assert ("--", "board.canvas") in repo.git.calls
    assert ("--", "README.MD") in repo.git.calls
    assert ("--", "image.png") not in repo.git.calls
