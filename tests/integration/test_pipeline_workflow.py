"""Integration tests for pipeline workflow."""

from pathlib import Path

import pytest

from app.core.atomic_splitter import AtomicSplitter
from app.core.config import Settings


class DummyLLMService:
    """LLMサービスのダミー."""

    def _generate_with_retry(self, _prompt: str) -> str:
        return """
---ATOMIC_NOTE---
タイトル: なぜAI動画は集客に効果的なのか
タグ: マーケティング, AI動画, 集客
概念: AI動画を使った短尺集客施策
詳細:
短尺動画は視聴完了率が高く、拡散されやすい。

応用例:
- YouTube shortsでの商品PR

関連リンク:
- [[test_summary]]
---END---
"""


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """テスト用 Settings を作成."""
    return Settings(
        obsidian_vault_path=str(tmp_path),
        obsidian_vault_name="test_vault",
        github_token="test_token",
    )


def test_summary_to_atomic_workflow(settings: Settings, tmp_path: Path) -> None:
    """01_Summary → 02_Atomic の基本フローを検証."""
    summary_dir = tmp_path / "01_Summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary_file = summary_dir / "test_summary.md"
    summary_file.write_text(
        """---
title: テスト
pipeline_stage: "01_Summary"
---

# テスト

## サマリー
AI動画とレコメンデーションの提案
""",
        encoding="utf-8",
    )

    splitter = AtomicSplitter(DummyLLMService(), settings)
    atomic_notes = splitter.split_into_atomic_notes(summary_file)
    assert len(atomic_notes) == 1

    saved_files = splitter.save_atomic_notes(atomic_notes)
    assert len(saved_files) == 1
    assert saved_files[0].exists()
