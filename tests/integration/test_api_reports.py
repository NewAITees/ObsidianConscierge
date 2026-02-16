"""Integration tests for reports API endpoints."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def mock_settings() -> Settings:
    """モック設定を返す"""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        return Settings(
            github_token="test_token",
            obsidian_vault_name="test_vault",
            chroma_db_path=Path(tmpdir) / "chroma_db",
        )


@pytest.fixture
def mock_vector_db_service() -> MagicMock:
    """モックベクトルDBサービスを返す"""
    service = MagicMock()
    # get_all_articles()のモック
    service.get_all_articles.return_value = [
        {
            "id": "test/article1.md",
            "title": "テスト記事1",
            "summary": "テスト記事1の要約",
            "tags": ["test", "python"],
            "file_path": "test/article1.md",
            "modified": (datetime.now() - timedelta(days=1)).isoformat(),
            "created": (datetime.now() - timedelta(days=2)).isoformat(),
            "word_count": 100,
            "body": "テスト記事1の本文",
            "body_embedding": [0.1] * 512,
        },
        {
            "id": "test/article2.md",
            "title": "テスト記事2",
            "summary": "テスト記事2の要約",
            "tags": ["test", "javascript"],
            "file_path": "test/article2.md",
            "modified": (datetime.now() - timedelta(days=1)).isoformat(),
            "created": (datetime.now() - timedelta(days=3)).isoformat(),
            "word_count": 200,
            "body": "テスト記事2の本文",
            "body_embedding": [0.2] * 512,
        },
        {
            "id": "category/article3.md",
            "title": "カテゴリ記事",
            "summary": "カテゴリ記事の要約",
            "tags": ["category", "example"],
            "file_path": "category/article3.md",
            "modified": (datetime.now() - timedelta(days=2)).isoformat(),
            "created": (datetime.now() - timedelta(days=4)).isoformat(),
            "word_count": 150,
            "body": "カテゴリ記事の本文",
            "body_embedding": [0.3] * 512,
        },
        {
            "id": "04CODING/mcp1.md",
            "title": "MCP入門",
            "summary": "MCPの概要",
            "tags": ["MCP", "2025-01-10"],
            "file_path": "04CODING/mcp1.md",
            "modified": (datetime.now() - timedelta(days=1)).isoformat(),
            "created": (datetime.now() - timedelta(days=5)).isoformat(),
            "word_count": 120,
            "body": "MCP本文1",
            "body_embedding": [0.25] * 512,
        },
        {
            "id": "04CODING/mcp2.md",
            "title": "MCP実装",
            "summary": "MCPの実装",
            "tags": ["MCP"],
            "file_path": "04CODING/mcp2.md",
            "modified": (datetime.now() - timedelta(days=1)).isoformat(),
            "created": (datetime.now() - timedelta(days=6)).isoformat(),
            "word_count": 130,
            "body": "MCP本文2",
            "body_embedding": [0.26] * 512,
        },
        {
            "id": "05MATH/mcp3.md",
            "title": "MCP応用",
            "summary": "MCPの応用",
            "tags": ["MCP"],
            "file_path": "05MATH/mcp3.md",
            "modified": (datetime.now() - timedelta(days=2)).isoformat(),
            "created": (datetime.now() - timedelta(days=7)).isoformat(),
            "word_count": 110,
            "body": "MCP本文3",
            "body_embedding": [0.27] * 512,
        },
        {
            "id": "01DIARY/2025-01-10.md",
            "title": "前後リンク：[[DiaryMOC_2025]]",
            "summary": "日記テンプレ",
            "tags": ["MCP", "2025-01-10"],
            "file_path": "01DIARY/2025-01-10.md",
            "modified": (datetime.now() - timedelta(days=1)).isoformat(),
            "created": (datetime.now() - timedelta(days=1)).isoformat(),
            "word_count": 50,
            "body": "日記本文",
            "body_embedding": [0.28] * 512,
        },
    ]
    return service


@pytest.fixture
def client(
    mock_settings: Settings,
    mock_vector_db_service: MagicMock,
) -> TestClient:
    """テスト用のFastAPIクライアントを返す"""
    with patch("app.main.get_settings", return_value=mock_settings), patch(
        "app.services.vector_db_service.VectorDBService",
        return_value=mock_vector_db_service,
    ):
        app = create_app()

        # テスト用にサービスを直接設定
        app.state.vector_db_service = mock_vector_db_service

        return TestClient(app)


class TestReportsAPI:
    """レポートAPIのテストクラス"""

    def test_get_daily_report_success(self, client: TestClient) -> None:
        """デイリーレポート取得成功テスト"""
        # Arrange
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Act
        response = client.get(f"/api/v1/reports/daily/{date_str}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "generated_at" in data
        assert "statistics" in data
        assert "duplicates" in data
        assert "pickups" in data
        assert "moc_candidates" in data
        assert data["date"] == date_str

    def test_get_yesterday_report(self, client: TestClient) -> None:
        """昨日のレポート取得テスト（日付指定なし）"""
        # Act
        response = client.get("/api/v1/reports/daily")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "statistics" in data

    def test_get_daily_report_invalid_date_format(self, client: TestClient) -> None:
        """無効な日付形式のテスト"""
        # Act
        response = client.get("/api/v1/reports/daily/invalid-date")

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "Invalid date format" in data["detail"]

    def test_get_daily_report_with_duplicate_threshold(
        self, client: TestClient
    ) -> None:
        """重複閾値パラメータのテスト"""
        # Arrange
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Act
        response = client.get(
            f"/api/v1/reports/daily/{date_str}?duplicate_threshold=0.9"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "duplicates" in data

    def test_daily_report_statistics(self, client: TestClient) -> None:
        """レポート統計情報のテスト"""
        # Arrange
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Act
        response = client.get(f"/api/v1/reports/daily/{date_str}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        stats = data["statistics"]
        assert "new_count" in stats
        assert "updated_count" in stats
        assert "total_word_count" in stats
        assert "total_articles" in stats
        assert isinstance(stats["new_count"], int)
        assert isinstance(stats["updated_count"], int)
        assert isinstance(stats["total_word_count"], int)
        assert isinstance(stats["total_articles"], int)

    def test_daily_report_pickups(self, client: TestClient) -> None:
        """レポートピックアップ記事のテスト"""
        # Arrange
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Act
        response = client.get(f"/api/v1/reports/daily/{date_str}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        pickups = data["pickups"]
        assert isinstance(pickups, list)
        # ピックアップ記事が存在する場合、各記事に必要なフィールドがあることを確認
        for pickup in pickups:
            assert "id" in pickup
            assert "title" in pickup
            assert "file_path" in pickup

    def test_daily_report_moc_candidates(self, client: TestClient) -> None:
        """レポートMOC候補のテスト"""
        # Arrange
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Act
        response = client.get(f"/api/v1/reports/daily/{date_str}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        moc_candidates = data["moc_candidates"]
        assert isinstance(moc_candidates, list)
        # MOC候補が存在する場合、各候補に必要なフィールドがあることを確認
        for candidate in moc_candidates:
            assert "type" in candidate
            assert "name" in candidate
            assert "articles" in candidate
            assert "count" in candidate

    def test_daily_report_moc_candidates_exclude_noise(self, client: TestClient) -> None:
        """MOC候補から日付タグ・日記テンプレノイズが除外されることを確認."""
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        response = client.get(f"/api/v1/reports/daily/{date_str}")

        assert response.status_code == 200
        moc_candidates = response.json()["moc_candidates"]
        candidate_names = {candidate["name"] for candidate in moc_candidates}

        assert "MCP" in candidate_names
        assert "2025-01-10" not in candidate_names
        for candidate in moc_candidates:
            for article in candidate["articles"]:
                assert "01DIARY/" not in article["file_path"]
                assert "前後リンク" not in article["title"]
