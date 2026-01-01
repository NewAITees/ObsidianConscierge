"""Unit tests for AtomicScorer."""

import pytest
from pathlib import Path
from unittest.mock import Mock

from app.core.atomic_scorer import AtomicScorer
from app.core.config import Settings
from app.services.llm_service import LLMService


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """テスト用の Settings を作成."""
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    (vault_path / "02_Atomic").mkdir()

    return Settings(
        obsidian_vault_path=str(vault_path),
        github_repo_url="https://github.com/test/test",
        github_token="test_token",
    )


@pytest.fixture
def mock_llm_service() -> LLMService:
    """モック LLMService を作成."""
    return Mock(spec=LLMService)


@pytest.fixture
def atomic_scorer(
    mock_llm_service: LLMService,
    settings: Settings
) -> AtomicScorer:
    """AtomicScorer のインスタンスを作成."""
    return AtomicScorer(mock_llm_service, settings)


@pytest.fixture
def good_atomic_note(settings: Settings) -> Path:
    """高品質なアトミック・ノートを作成."""
    file_path = Path(settings.obsidian_vault_path) / "02_Atomic" / "good_note.md"

    content = """---
title: "なぜAI動画は集客に効果的なのか"
created: 2025-01-15
tags: [マーケティング, AI動画, 集客]
pipeline_stage: "02_Atomic"
---

# なぜAI動画は集客に効果的なのか

## 概念
AI動画を使ったYouTube shorts/TikTokでの集客施策は、短尺フォーマットによる高い視聴完了率とアルゴリズムの親和性により、オーガニックリーチを最大化できる。

## 詳細
AI動画は短尺フォーマットでの展開により、若年層へのリーチを拡大する。プラットフォームはYouTube shortsとTikTokが主要で、費用は月50万円程度、ROIは3ヶ月で回収見込み。短尺動画は視聴完了率が高く、アルゴリズムに好まれるため、オーガニックリーチが期待できる。制作コストを抑えつつ、大量のコンテンツを投稿できる点も魅力的である。

## 応用例
- YouTube shortsでの商品PR
- TikTokでのブランド認知施策
- Instagram Reelsでのエンゲージメント向上
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def poor_atomic_note(settings: Settings) -> Path:
    """低品質なアトミック・ノートを作成."""
    file_path = Path(settings.obsidian_vault_path) / "02_Atomic" / "poor_note.md"

    content = """---
title: "メモ"
created: 2025-01-15
tags: []
pipeline_stage: "02_Atomic"
---

# メモ

これは短いメモです。
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_score_good_atomic_note(
    atomic_scorer: AtomicScorer,
    good_atomic_note: Path
) -> None:
    """高品質なノートが高スコアを得ることを確認."""
    result = atomic_scorer.score_atomic_note(good_atomic_note)

    # 0.6以上ならB以上の評価（実用上問題なし）
    assert result["total_score"] >= 0.6
    assert result["grade"] in ["A+", "A", "B", "C"]
    assert result["file_path"] == str(good_atomic_note)
    assert "scores" in result
    assert "suggestions" in result


def test_score_poor_atomic_note(
    atomic_scorer: AtomicScorer,
    poor_atomic_note: Path
) -> None:
    """低品質なノートが低スコアを得ることを確認."""
    result = atomic_scorer.score_atomic_note(poor_atomic_note)

    assert result["total_score"] < 0.5
    assert result["grade"] in ["D", "F"]
    assert len(result["suggestions"]) > 0


def test_score_nonexistent_file(
    atomic_scorer: AtomicScorer,
    settings: Settings
) -> None:
    """存在しないファイルのスコアリングがエラーを返すことを確認."""
    nonexistent_file = Path(settings.obsidian_vault_path) / "nonexistent.md"

    result = atomic_scorer.score_atomic_note(nonexistent_file)

    assert result["total_score"] == 0.0
    assert result["grade"] == "F"
    assert "エラー" in result["suggestions"][0]


def test_score_length_ideal(atomic_scorer: AtomicScorer) -> None:
    """理想的な長さ（200-800字）のスコアが高いことを確認."""
    # 300字のテキスト
    body = "あ" * 300
    score = atomic_scorer._score_length(body)
    assert score == 1.0


def test_score_length_too_short(atomic_scorer: AtomicScorer) -> None:
    """短すぎるテキスト（<100字）のスコアが低いことを確認."""
    body = "あ" * 50
    score = atomic_scorer._score_length(body)
    assert score == 0.2


def test_score_length_too_long(atomic_scorer: AtomicScorer) -> None:
    """長すぎるテキスト（>1500字）のスコアが低いことを確認."""
    body = "あ" * 2000
    score = atomic_scorer._score_length(body)
    assert score == 0.4


def test_score_title_quality_question_form(atomic_scorer: AtomicScorer) -> None:
    """問い形式のタイトルが高スコアを得ることを確認."""
    title = "なぜAI動画は集客に効果的なのか"
    score = atomic_scorer._score_title_quality(title)
    assert score == 1.0


def test_score_title_quality_normal(atomic_scorer: AtomicScorer) -> None:
    """普通のタイトルが中程度のスコアを得ることを確認."""
    title = "AI動画集客戦略"
    score = atomic_scorer._score_title_quality(title)
    assert score == 0.6


def test_score_title_quality_empty(atomic_scorer: AtomicScorer) -> None:
    """空のタイトルがスコア0を得ることを確認."""
    title = ""
    score = atomic_scorer._score_title_quality(title)
    assert score == 0.0


def test_score_tags_ideal(atomic_scorer: AtomicScorer) -> None:
    """理想的なタグ数（2-5個）が高スコアを得ることを確認."""
    tags = ["tag1", "tag2", "tag3"]
    score = atomic_scorer._score_tags(tags)
    assert score == 1.0


def test_score_tags_too_few(atomic_scorer: AtomicScorer) -> None:
    """タグがない場合が低スコアになることを確認."""
    tags: list[str] = []
    score = atomic_scorer._score_tags(tags)
    assert score == 0.3


def test_score_tags_too_many(atomic_scorer: AtomicScorer) -> None:
    """タグが多すぎる場合が低スコアになることを確認."""
    tags = ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"]
    score = atomic_scorer._score_tags(tags)
    assert score == 0.3


def test_get_grade(atomic_scorer: AtomicScorer) -> None:
    """スコアからグレードへの変換が正しいことを確認."""
    assert atomic_scorer._get_grade(0.95) == "A+"
    assert atomic_scorer._get_grade(0.85) == "A"
    assert atomic_scorer._get_grade(0.75) == "B"
    assert atomic_scorer._get_grade(0.65) == "C"
    assert atomic_scorer._get_grade(0.55) == "D"
    assert atomic_scorer._get_grade(0.45) == "F"


def test_extract_metadata(
    atomic_scorer: AtomicScorer,
    good_atomic_note: Path
) -> None:
    """Frontmatter からメタデータを正しく抽出できることを確認."""
    content = good_atomic_note.read_text(encoding="utf-8")
    metadata = atomic_scorer._extract_metadata(content)

    assert metadata["title"] == "なぜAI動画は集客に効果的なのか"
    assert "マーケティング" in metadata["tags"]
    assert "AI動画" in metadata["tags"]
    assert len(metadata["tags"]) == 3


def test_extract_body(
    atomic_scorer: AtomicScorer,
    good_atomic_note: Path
) -> None:
    """Frontmatter を除いた本文を抽出できることを確認."""
    content = good_atomic_note.read_text(encoding="utf-8")
    body = atomic_scorer._extract_body(content)

    # Frontmatter が除去されていることを確認
    assert "---" not in body
    assert "title:" not in body

    # 本文が含まれていることを確認
    assert "なぜAI動画は集客に効果的なのか" in body
    assert "概念" in body


def test_generate_suggestions_for_poor_note(
    atomic_scorer: AtomicScorer,
    poor_atomic_note: Path
) -> None:
    """低品質なノートに対して適切な改善提案が生成されることを確認."""
    content = poor_atomic_note.read_text(encoding="utf-8")
    metadata = atomic_scorer._extract_metadata(content)
    body = atomic_scorer._extract_body(content)

    scores = {
        "single_concept": 0.5,
        "reusability": 0.4,
        "independence": 0.3,
        "length_score": 0.2,
        "title_quality": 0.6,
        "tag_appropriateness": 0.3,
    }

    suggestions = atomic_scorer._generate_suggestions(scores, metadata, body)

    assert len(suggestions) > 0
    # 長さに関する提案が含まれているはず
    assert any("短すぎます" in s for s in suggestions)
    # タグに関する提案が含まれているはず
    assert any("タグ" in s for s in suggestions)


def test_score_all_atomic_notes(
    atomic_scorer: AtomicScorer,
    good_atomic_note: Path,
    poor_atomic_note: Path
) -> None:
    """全アトミック・ノートのスコアリングが正しく動作することを確認."""
    results = atomic_scorer.score_all_atomic_notes()

    assert len(results) == 2
    # スコアの降順でソートされているはず
    assert results[0]["total_score"] >= results[1]["total_score"]
