"""Mock Ollama for testing."""

from typing import Any
from unittest.mock import MagicMock


class MockOllamaClient:
    """Ollamaクライアントのモック"""

    def __init__(self) -> None:
        """モッククライアントを初期化"""
        self._default_responses: dict[str, str] = {
            "summary": "これはテスト用のサマリーです。",
            "tags": "test, python, example",
        }

    def generate(
        self,
        model: str,
        prompt: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        テキスト生成をモック

        Args:
            model: モデル名（使用しない）
            prompt: プロンプト
            **kwargs: その他の引数

        Returns:
            Dict: 生成結果
        """
        # プロンプトの内容に応じて適切なレスポンスを返す
        if "要約" in prompt or "summary" in prompt.lower():
            response_text = self._default_responses.get("summary", "テスト用のサマリー")
        elif "タグ" in prompt or "tag" in prompt.lower():
            response_text = self._default_responses.get("tags", "test, example")
        else:
            response_text = "テスト用のレスポンス"

        return {
            "model": model,
            "response": response_text,
            "done": True,
        }

    def set_default_response(self, key: str, value: str) -> None:
        """
        デフォルトレスポンスを設定する

        Args:
            key: レスポンスキー（summary, tags等）
            value: レスポンス値
        """
        self._default_responses[key] = value


def create_mock_ollama_client() -> MagicMock:
    """
    モックOllamaクライアントを作成する

    Returns:
        MagicMock: モッククライアント
    """
    mock_client = MagicMock()
    mock_ollama = MockOllamaClient()

    # generateメソッドをモック
    mock_client.generate = mock_ollama.generate

    return mock_client

