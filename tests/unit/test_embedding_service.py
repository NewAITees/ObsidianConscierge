"""Tests for embedding service."""

from app.services.embedding_service import EmbeddingService


class TestEmbeddingService:
    """Embedding生成サービスのテストクラス"""

    def test_embed_text_generates_embedding(self) -> None:
        """テキストからベクトルを生成できるかテスト"""
        # Arrange
        service = EmbeddingService()
        text = "これはテスト用のテキストです。"

        # Act
        embedding = service.embed(text)

        # Assert
        assert isinstance(embedding, list)
        assert len(embedding) == 512  # distiluse-base-multilingual-cased-v2は512次元
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_empty_text(self) -> None:
        """空のテキストでもベクトルを生成できるかテスト"""
        # Arrange
        service = EmbeddingService()
        text = ""

        # Act
        embedding = service.embed(text)

        # Assert
        assert isinstance(embedding, list)
        assert len(embedding) == 512

    def test_embed_multiple_texts(self) -> None:
        """複数のテキストをバッチで処理できるかテスト"""
        # Arrange
        service = EmbeddingService()
        texts = [
            "これは最初のテキストです。",
            "これは2番目のテキストです。",
            "これは3番目のテキストです。",
        ]

        # Act
        embeddings = service.embed_batch(texts)

        # Assert
        assert len(embeddings) == 3
        for embedding in embeddings:
            assert isinstance(embedding, list)
            assert len(embedding) == 512

    def test_embed_different_texts_produce_different_embeddings(self) -> None:
        """異なるテキストは異なるベクトルを生成するかテスト"""
        # Arrange
        service = EmbeddingService()
        text1 = "Pythonはプログラミング言語です。"
        text2 = "今日は良い天気です。"

        # Act
        embedding1 = service.embed(text1)
        embedding2 = service.embed(text2)

        # Assert
        # 異なるテキストなので、ベクトルも異なるはず
        assert embedding1 != embedding2

    def test_embed_same_text_produces_same_embedding(self) -> None:
        """同じテキストは同じベクトルを生成するかテスト"""
        # Arrange
        service = EmbeddingService()
        text = "これは同じテキストです。"

        # Act
        embedding1 = service.embed(text)
        embedding2 = service.embed(text)

        # Assert
        # 同じテキストなので、ベクトルも同じ（または非常に近い）はず
        assert embedding1 == embedding2




