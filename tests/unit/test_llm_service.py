"""Tests for LLM service (Ollama)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.llm_service import LLMService


class TestLLMService:
    """LLMサービスのテストクラス"""

    @patch("app.services.llm_service.ollama")
    def test_generate_summary_success(self, mock_ollama: MagicMock) -> None:
        """サマリー生成の成功テスト"""
        # Arrange
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "response": "これは記事の要約です。重要なポイントが含まれています。"
        }
        mock_ollama.Client.return_value = mock_client

        service = LLMService(base_url="http://localhost:11434", model="llama3")

        # Act
        summary = service.generate_summary("これは長い記事の内容です。")

        # Assert
        assert summary == "これは記事の要約です。重要なポイントが含まれています。"
        mock_client.generate.assert_called_once()

    @patch("app.services.llm_service.ollama")
    def test_generate_summary_with_retry(self, mock_ollama: MagicMock) -> None:
        """リトライロジックのテスト"""
        # Arrange: 最初の2回はエラー、3回目で成功
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            Exception("Connection error"),
            Exception("Timeout error"),
            {"response": "サマリー"},
        ]
        mock_ollama.Client.return_value = mock_client

        service = LLMService(base_url="http://localhost:11434", model="llama3")

        # Act
        summary = service.generate_summary("記事内容")

        # Assert
        assert summary == "サマリー"
        assert mock_client.generate.call_count == 3

    @patch("app.services.llm_service.ollama")
    def test_generate_summary_max_retries_exceeded(self, mock_ollama: MagicMock) -> None:
        """最大リトライ回数を超えた場合のテスト"""
        # Arrange: 常にエラーを返す
        mock_client = MagicMock()
        mock_client.generate.side_effect = Exception("Connection error")
        mock_ollama.Client.return_value = mock_client

        service = LLMService(base_url="http://localhost:11434", model="llama3")

        # Act & Assert: 例外が発生する（元の例外が再発生される）
        with pytest.raises(Exception, match="Connection error"):
            service.generate_summary("記事内容")

    @patch("app.services.llm_service.ollama")
    def test_generate_tags_success(self, mock_ollama: MagicMock) -> None:
        """タグ生成の成功テスト"""
        # Arrange
        mock_client = MagicMock()
        mock_client.generate.return_value = {"response": "python, testing, automation"}
        mock_ollama.Client.return_value = mock_client

        service = LLMService(base_url="http://localhost:11434", model="llama3")

        # Act
        tags = service.generate_tags("Pythonでテストを自動化する方法", existing_tags=[])

        # Assert
        assert isinstance(tags, list)
        assert len(tags) > 0
        assert "python" in tags or "testing" in tags or "automation" in tags
        mock_client.generate.assert_called_once()

    @patch("app.services.llm_service.ollama")
    def test_generate_tags_with_existing_tags(self, mock_ollama: MagicMock) -> None:
        """既存タグがある場合のタグ生成テスト"""
        # Arrange
        mock_client = MagicMock()
        mock_client.generate.return_value = {"response": "python, testing"}
        mock_ollama.Client.return_value = mock_client

        service = LLMService(base_url="http://localhost:11434", model="llama3")

        # Act
        tags = service.generate_tags("記事内容", existing_tags=["python", "automation"])

        # Assert
        assert isinstance(tags, list)
        # 既存タグと新規タグが統合されている
        assert "python" in tags or "testing" in tags
