"""Unit tests for AtomicSplitter."""

from pathlib import Path

import pytest

from app.core.atomic_splitter import AtomicSplitter
from app.core.config import Settings


class DummyLLMService:
    """LLMサービスのダミー."""

    def _generate_with_retry(self, _prompt: str) -> str:
        return ""


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """テスト用 Settings を作成."""
    return Settings(
        obsidian_vault_path=str(tmp_path),
        obsidian_vault_name="test_vault",
        github_token="test_token",
    )


def test_parse_atomic_notes(settings: Settings, tmp_path: Path) -> None:
    """LLMレスポンスを正しくパースできるか."""
    splitter = AtomicSplitter(DummyLLMService(), settings)

    response = """
---ATOMIC_NOTE---
タイトル: AI動画集客戦略
タグ: マーケティング, AI動画
概念: AI動画を使った集客施策
詳細:
費用: 月50万円

応用例:
- YouTube shortsでの活用

関連リンク:
- [[test]]
---END---
"""

    notes = splitter._parse_atomic_notes(response, tmp_path / "test.md")

    assert len(notes) == 1
    assert notes[0]["title"] == "AI動画集客戦略"
    assert "マーケティング" in notes[0]["tags"]
    assert "AI動画" in notes[0]["tags"]
