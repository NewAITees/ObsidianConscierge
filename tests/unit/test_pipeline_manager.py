"""Unit tests for PipelineManager."""

import pytest
from pathlib import Path
from datetime import datetime

from app.core.pipeline_manager import PipelineManager, PipelineStage
from app.core.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """テスト用の Settings を作成."""
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    # 各ステージのディレクトリを作成
    (vault_path / "00_Raw").mkdir()
    (vault_path / "01_Summary").mkdir()
    (vault_path / "02_Atomic").mkdir()
    (vault_path / "03_MOC").mkdir()

    return Settings(
        obsidian_vault_path=str(vault_path),
        github_repo_url="https://github.com/test/test",
        github_token="test_token",
    )


@pytest.fixture
def pipeline_manager(settings: Settings) -> PipelineManager:
    """PipelineManager のインスタンスを作成."""
    return PipelineManager(settings)


@pytest.fixture
def sample_file_with_frontmatter(settings: Settings) -> Path:
    """Frontmatter 付きのサンプルファイルを作成."""
    file_path = Path(settings.obsidian_vault_path) / "02_Atomic" / "test.md"

    content = """---
title: "Test Note"
created: 2025-01-15
pipeline_stage: "02_Atomic"
tags: [test, sample]
---

# Test Note

This is a test note.
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_file_without_frontmatter(settings: Settings) -> Path:
    """Frontmatter なしのサンプルファイルを作成."""
    file_path = Path(settings.obsidian_vault_path) / "00_Raw" / "test.md"

    content = """# Test Note

This is a test note without frontmatter.
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_get_current_stage_with_frontmatter(
    pipeline_manager: PipelineManager,
    sample_file_with_frontmatter: Path
) -> None:
    """Frontmatter からステージを取得できることを確認."""
    stage = pipeline_manager.get_current_stage(sample_file_with_frontmatter)
    assert stage == "02_Atomic"


def test_get_current_stage_without_frontmatter(
    pipeline_manager: PipelineManager,
    sample_file_without_frontmatter: Path
) -> None:
    """Frontmatter なしの場合は None を返すことを確認."""
    stage = pipeline_manager.get_current_stage(sample_file_without_frontmatter)
    assert stage is None


def test_get_current_stage_nonexistent_file(
    pipeline_manager: PipelineManager,
    settings: Settings
) -> None:
    """存在しないファイルの場合は None を返すことを確認."""
    nonexistent_file = Path(settings.obsidian_vault_path) / "nonexistent.md"
    stage = pipeline_manager.get_current_stage(nonexistent_file)
    assert stage is None


def test_update_stage_forward_transition(
    pipeline_manager: PipelineManager,
    sample_file_with_frontmatter: Path
) -> None:
    """前方遷移（02_Atomic → 03_MOC）が成功することを確認."""
    # 現在は 02_Atomic
    assert pipeline_manager.get_current_stage(sample_file_with_frontmatter) == "02_Atomic"

    # 03_MOC に更新
    success = pipeline_manager.update_stage(
        sample_file_with_frontmatter,
        "03_MOC"
    )

    assert success is True
    assert pipeline_manager.get_current_stage(sample_file_with_frontmatter) == "03_MOC"

    # updated フィールドが追加されていることを確認
    content = sample_file_with_frontmatter.read_text(encoding="utf-8")
    assert "updated:" in content


def test_update_stage_backward_transition_blocked(
    pipeline_manager: PipelineManager,
    sample_file_with_frontmatter: Path
) -> None:
    """後方遷移（02_Atomic → 01_Summary）がブロックされることを確認."""
    # 現在は 02_Atomic
    assert pipeline_manager.get_current_stage(sample_file_with_frontmatter) == "02_Atomic"

    # 01_Summary に更新しようとする（失敗するはず）
    success = pipeline_manager.update_stage(
        sample_file_with_frontmatter,
        "01_Summary",
        allow_backward=False
    )

    assert success is False
    # ステージは変更されていないはず
    assert pipeline_manager.get_current_stage(sample_file_with_frontmatter) == "02_Atomic"


def test_update_stage_backward_transition_allowed(
    pipeline_manager: PipelineManager,
    sample_file_with_frontmatter: Path
) -> None:
    """allow_backward=True の場合は後方遷移が許可されることを確認."""
    # 現在は 02_Atomic
    assert pipeline_manager.get_current_stage(sample_file_with_frontmatter) == "02_Atomic"

    # 01_Summary に更新（allow_backward=True）
    success = pipeline_manager.update_stage(
        sample_file_with_frontmatter,
        "01_Summary",
        allow_backward=True
    )

    assert success is True
    assert pipeline_manager.get_current_stage(sample_file_with_frontmatter) == "01_Summary"


def test_update_stage_creates_frontmatter_if_missing(
    pipeline_manager: PipelineManager,
    sample_file_without_frontmatter: Path
) -> None:
    """Frontmatter がない場合は新規作成されることを確認."""
    # 現在はステージなし
    assert pipeline_manager.get_current_stage(sample_file_without_frontmatter) is None

    # 00_Raw に設定
    success = pipeline_manager.update_stage(
        sample_file_without_frontmatter,
        "00_Raw"
    )

    assert success is True
    assert pipeline_manager.get_current_stage(sample_file_without_frontmatter) == "00_Raw"

    # Frontmatter が作成されていることを確認
    content = sample_file_without_frontmatter.read_text(encoding="utf-8")
    assert "---" in content
    assert "pipeline_stage:" in content


def test_get_stage_files(
    pipeline_manager: PipelineManager,
    settings: Settings
) -> None:
    """各ステージのファイルを取得できることを確認."""
    # サンプルファイルを作成
    raw_dir = Path(settings.obsidian_vault_path) / "00_Raw"
    (raw_dir / "file1.md").write_text("# File 1", encoding="utf-8")
    (raw_dir / "file2.md").write_text("# File 2", encoding="utf-8")

    atomic_dir = Path(settings.obsidian_vault_path) / "02_Atomic"
    (atomic_dir / "file3.md").write_text("# File 3", encoding="utf-8")

    # 各ステージのファイル数を確認
    raw_files = pipeline_manager.get_stage_files("00_Raw")
    assert len(raw_files) == 2

    summary_files = pipeline_manager.get_stage_files("01_Summary")
    assert len(summary_files) == 0

    atomic_files = pipeline_manager.get_stage_files("02_Atomic")
    assert len(atomic_files) == 1


def test_get_pipeline_statistics(
    pipeline_manager: PipelineManager,
    settings: Settings
) -> None:
    """パイプライン統計を取得できることを確認."""
    # サンプルファイルを作成
    raw_dir = Path(settings.obsidian_vault_path) / "00_Raw"
    (raw_dir / "file1.md").write_text("# File 1", encoding="utf-8")

    summary_dir = Path(settings.obsidian_vault_path) / "01_Summary"
    (summary_dir / "file2.md").write_text("# File 2", encoding="utf-8")
    (summary_dir / "file3.md").write_text("# File 3", encoding="utf-8")

    # 統計を取得
    stats = pipeline_manager.get_pipeline_statistics()

    assert stats["00_Raw"] == 1
    assert stats["01_Summary"] == 2
    assert stats["02_Atomic"] == 0
    assert stats["03_MOC"] == 0


def test_validate_stage_transition(pipeline_manager: PipelineManager) -> None:
    """ステージ遷移の妥当性検証が正しく動作することを確認."""
    # 前方遷移は有効
    assert pipeline_manager.validate_stage_transition("00_Raw", "01_Summary") is True
    assert pipeline_manager.validate_stage_transition("01_Summary", "02_Atomic") is True
    assert pipeline_manager.validate_stage_transition("02_Atomic", "03_MOC") is True

    # 同一ステージも有効
    assert pipeline_manager.validate_stage_transition("02_Atomic", "02_Atomic") is True

    # 後方遷移は無効
    assert pipeline_manager.validate_stage_transition("02_Atomic", "01_Summary") is False
    assert pipeline_manager.validate_stage_transition("03_MOC", "00_Raw") is False
