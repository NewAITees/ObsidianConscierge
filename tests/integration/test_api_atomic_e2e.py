"""End-to-end tests for atomic pipeline APIs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.article import Article
from tests.fixtures.mock_chromadb import MockChromaClient


class MockOllamaClient:
    """Mock Ollama client with prompt-aware responses."""

    def generate(self, model: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
        if "---ATOMIC_NOTE---" in prompt:
            response = """
---ATOMIC_NOTE---
タイトル: なぜAIノートは再利用性が高いのか
タグ: AI, ナレッジ
概念: AIノートを再利用可能な単位に分解する意義
詳細:
AIノートを最小単位に分解することで、再利用性が高まり異なる文脈でも使える。

応用例:
- ナレッジ共有のテンプレ化

関連リンク:
- [[元ノート]]
---END---
"""
        elif "QUESTION:" in prompt:
            response = """
QUESTION: なぜAIノートは価値が高いのか
# 【問い】なぜAIノートは価値が高いのか

## この問いの背景
AIノートは再利用可能な知識の単位として重要である。
知識の再構成を容易にする。

## 関連するAtomicノート
- [[AI_note_1]]：AIの知識粒度を示す。

## 現時点での暫定的な答え
再利用性と検索性が高いため価値がある。

## 未解決の疑問
- 具体的な評価基準は何か
"""
        else:
            response = "テスト用のレスポンス"

        return {"response": response}


@pytest.fixture
def mock_settings(tmp_path: Path) -> Settings:
    """テスト用Settingsを返す."""
    return Settings(
        github_token="test_token",
        obsidian_vault_name="test_vault",
        obsidian_vault_path=tmp_path,
        chroma_db_path=tmp_path / "chroma_db",
    )


@pytest.fixture
def client(mock_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """FastAPIのTestClientを返す."""
    # Settings のモック（全モジュールで統一）
    monkeypatch.setattr("app.main.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.core.config.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.api.atomic.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.api.moc.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.api.pipeline.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.core.atomic_splitter.Settings", lambda **kwargs: mock_settings)
    monkeypatch.setattr("app.core.atomic_scorer.Settings", lambda **kwargs: mock_settings)
    monkeypatch.setattr("app.core.moc_generator.Settings", lambda **kwargs: mock_settings)
    monkeypatch.setattr("app.core.pipeline_manager.Settings", lambda **kwargs: mock_settings)
    monkeypatch.setattr("app.core.daily_note_linker.Settings", lambda **kwargs: mock_settings)

    monkeypatch.setattr(
        "app.services.vector_db_service.chromadb.PersistentClient",
        MockChromaClient,
    )

    class DummyEmbeddingService:
        """埋め込みを固定値で返すモック."""

        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def embed(self, _text: str) -> list[float]:
            return [0.1, 0.2, 0.3]

    monkeypatch.setattr(
        "app.services.embedding_service.EmbeddingService",
        DummyEmbeddingService,
    )
    monkeypatch.setattr(
        "app.services.llm_service.ollama.Client",
        lambda *args, **kwargs: MockOllamaClient(),
    )

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _seed_atomic_articles(client: TestClient) -> None:
    """02_Atomic用のダミー記事をベクトルDBに登録."""
    vector_db_service = client.app.state.vector_db_service
    now = datetime.now()

    articles = [
        Article(
            id="02_Atomic/AI_note_1.md",
            title="AI note 1",
            body="AI note content 1",
            summary="summary 1",
            tags=["AI"],
            created=now,
            modified=now,
            file_path="02_Atomic/AI_note_1.md",
            body_embedding=[0.1, 0.2, 0.3],
            summary_embedding=[0.1, 0.2, 0.3],
            word_count=10,
        ),
        Article(
            id="02_Atomic/AI_note_2.md",
            title="AI note 2",
            body="AI note content 2",
            summary="summary 2",
            tags=["AI", "ナレッジ"],
            created=now,
            modified=now,
            file_path="02_Atomic/AI_note_2.md",
            body_embedding=[0.2, 0.3, 0.4],
            summary_embedding=[0.2, 0.3, 0.4],
            word_count=12,
        ),
    ]

    for article in articles:
        vector_db_service.store(article)


def test_atomic_split_e2e(client: TestClient, mock_settings: Settings) -> None:
    """POST /api/v1/atomic/split のE2Eテスト."""
    vault_path = Path(mock_settings.obsidian_vault_path)
    summary_dir = vault_path / "01_Summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary_file = summary_dir / "test_summary.md"
    summary_file.write_text(
        """---
title: テスト
pipeline_stage: "01_Summary"
---

# テスト

## サマリー
AIノートの要点
""",
        encoding="utf-8",
    )

    response = client.post(
        "/api/v1/atomic/split",
        json={"summary_file_path": "01_Summary/test_summary.md"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["atomic_notes_count"] == 1

    atomic_path = vault_path / payload["atomic_notes"][0]["file_path"]
    assert atomic_path.exists()
    assert 'pipeline_stage: "02_Atomic"' in atomic_path.read_text(encoding="utf-8")


def test_moc_generate_e2e(client: TestClient, mock_settings: Settings) -> None:
    """POST /api/v1/moc/generate のE2Eテスト."""
    _seed_atomic_articles(client)

    response = client.post(
        "/api/v1/moc/generate",
        json={
            "moc_type": "tag",
            "name": "AI",
            "min_notes": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["moc_count"] >= 1

    vault_path = Path(mock_settings.obsidian_vault_path)
    moc_path = vault_path / payload["moc_files"][0]
    assert moc_path.exists()
    content = moc_path.read_text(encoding="utf-8")
    assert "# 【問い】" in content
    assert "[[AI_note_1]]" in content


def test_pipeline_stats_e2e(client: TestClient, mock_settings: Settings) -> None:
    """GET /api/v1/pipeline/stats のE2Eテスト."""
    vault_path = Path(mock_settings.obsidian_vault_path)
    stages = ["00_Raw", "01_Summary", "02_Atomic", "03_MOC"]

    for stage in stages:
        stage_dir = vault_path / stage
        stage_dir.mkdir(parents=True, exist_ok=True)
        (stage_dir / f"{stage}_test.md").write_text("test", encoding="utf-8")

    response = client.get("/api/v1/pipeline/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_files"] == 4
    for stage in stages:
        assert payload["stages"][stage] == 1
