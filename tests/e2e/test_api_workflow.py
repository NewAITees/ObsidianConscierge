"""End-to-end tests for API workflow."""

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
タイトル: AIノート設計の要点
タグ: AI, ノート
概念: アトミック化の重要性
詳細:
ノートを小さな単位にすると再利用しやすい。

応用例:
- 研究メモの整理

関連リンク:
- [[元ノート]]
---END---
"""
        else:
            response = "テスト用のレスポンス"

        return {"response": response}


@pytest.fixture
def mock_settings(tmp_path: Path) -> Settings:
    """テスト用 Settings."""
    return Settings(
        github_token="test_token",
        obsidian_vault_name="test_vault",
        obsidian_vault_path=tmp_path,
        chroma_db_path=tmp_path / "chroma_db",
    )


@pytest.fixture
def client(mock_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """FastAPIのTestClient."""
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


def test_api_split_workflow(client: TestClient, mock_settings: Settings) -> None:
    """POST /api/v1/atomic/split のE2E."""
    vault_path = Path(mock_settings.obsidian_vault_path)
    summary_dir = vault_path / "01_Summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary_file = summary_dir / "test.md"
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
        json={"summary_file_path": "01_Summary/test.md"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["atomic_notes_count"] >= 1


def test_api_pipeline_status(client: TestClient, mock_settings: Settings) -> None:
    """GET /api/v1/pipeline/status のE2E."""
    vault_path = Path(mock_settings.obsidian_vault_path)
    raw_dir = vault_path / "00_Raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "raw.md").write_text("test", encoding="utf-8")

    response = client.get("/api/v1/pipeline/status")

    assert response.status_code == 200
    data = response.json()
    assert "pipeline_stages" in data
    assert "00_Raw" in data["pipeline_stages"]
