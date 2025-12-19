"""Mock Embedding Service for testing."""

import hashlib
from typing import Any
from unittest.mock import MagicMock

from app.services.embedding_service import EmbeddingService


class MockEmbeddingService(EmbeddingService):
    """Embeddingサービスのモック"""

    def __init__(self, model_name: str = "mock-model") -> None:
        """
        モックEmbeddingサービスを初期化

        Args:
            model_name: モデル名（使用しない）
        """
        # 親クラスの初期化をスキップ（モデルロードを回避）
        self.model_name = model_name
        self.embedding_size = 512
        self._model = None
        self._use_fallback = True

    def embed(self, text: str) -> list[float]:
        """
        テキストからベクトルを生成する（決定論的フォールバック）

        Args:
            text: 埋め込みを生成するテキスト

        Returns:
            List[float]: ベクトル（512次元）
        """
        # 決定論的なフォールバックEmbeddingを使用
        return self._fallback_embedding(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        複数のテキストをバッチで処理してベクトルを生成する

        Args:
            texts: 埋め込みを生成するテキストのリスト

        Returns:
            List[List[float]]: ベクトルのリスト
        """
        return [self.embed(text) for text in texts]


def create_mock_embedding_service() -> MockEmbeddingService:
    """
    モックEmbeddingサービスを作成する

    Returns:
        MockEmbeddingService: モックサービス
    """
    return MockEmbeddingService()

