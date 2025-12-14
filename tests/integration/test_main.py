"""Integration tests for main FastAPI application."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def mock_settings() -> Settings:
    """モック設定を返す"""
    with tempfile.TemporaryDirectory() as tmpdir:
        return Settings(
            github_token="test_token",
            obsidian_vault_name="test_vault",
            chroma_db_path=Path(tmpdir) / "chroma_db",
        )


@pytest.fixture
def client(mock_settings: Settings) -> TestClient:
    """テスト用のFastAPIクライアントを返す"""
    with patch("app.main.get_settings", return_value=mock_settings), patch(
        "app.services.vector_db_service.VectorDBService"
    ) as mock_vdb, patch(
        "app.services.embedding_service.EmbeddingService"
    ) as mock_emb:
        # モックサービスの設定
        mock_vdb_instance = MagicMock()
        mock_vdb.return_value = mock_vdb_instance

        mock_emb_instance = MagicMock()
        mock_emb.return_value = mock_emb_instance

        app = create_app()
        return TestClient(app)


class TestMainApp:
    """メインアプリケーションのテストクラス"""

    def test_health_check(self, client: TestClient) -> None:
        """ヘルスチェックエンドポイントのテスト"""
        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_root_endpoint(self, client: TestClient) -> None:
        """ルートエンドポイントのテスト（オプション）"""
        # Act
        response = client.get("/")

        # Assert
        # ルートエンドポイントが実装されている場合
        assert response.status_code in [200, 404]

