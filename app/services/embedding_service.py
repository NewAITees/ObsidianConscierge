"""Embedding generation service using sentence-transformers."""

import hashlib
import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

FALLBACK_DIMENSIONS = 512


class EmbeddingService:
    """sentence-transformersを使用したEmbedding生成サービス"""

    def __init__(
        self,
        model_name: str = "distiluse-base-multilingual-cased-v2",
        embedding_size: int = FALLBACK_DIMENSIONS,
    ) -> None:
        """
        EmbeddingServiceを初期化

        Args:
            model_name: 使用するsentence-transformersモデル名
            embedding_size: フォールバック時に使用する次元数
        """
        self.model_name = model_name
        self.embedding_size = embedding_size
        self._model: SentenceTransformer | None = None
        self._use_fallback = False

    def _get_or_load_model(self) -> SentenceTransformer | None:
        """モデルを取得し、失敗した場合はフォールバックを有効化"""
        if self._use_fallback:
            return None

        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to load embedding model '%s', using deterministic fallback: %s",
                    self.model_name,
                    exc,
                )
                self._use_fallback = True
                self._model = None
        return self._model

    def embed(self, text: str) -> list[float]:
        """
        テキストからベクトル（埋め込み）を生成する

        Args:
            text: 埋め込みを生成するテキスト

        Returns:
            List[float]: ベクトル（512次元）
        """
        model = self._get_or_load_model()
        if model:
            embedding = model.encode(text, show_progress_bar=False)
            return embedding.tolist()
        return self._fallback_embedding(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        複数のテキストをバッチで処理してベクトルを生成する

        Args:
            texts: 埋め込みを生成するテキストのリスト

        Returns:
            List[List[float]]: ベクトルのリスト
        """
        model = self._get_or_load_model()
        if model:
            embeddings = model.encode(texts, show_progress_bar=False)
            return [embedding.tolist() for embedding in embeddings]
        return [self._fallback_embedding(text) for text in texts]

    def _fallback_embedding(self, text: str) -> list[float]:
        """
        モデルロード失敗時のフォールバックEmbedding生成（決定論的）

        Args:
            text: 埋め込みを生成するテキスト

        Returns:
            List[float]: 次元数固定の疑似ベクトル
        """
        if not text:
            text = " "

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector: list[float] = []
        while len(vector) < self.embedding_size:
            for byte in digest:
                normalized = (byte / 255.0) * 2 - 1
                vector.append(float(normalized))
                if len(vector) >= self.embedding_size:
                    break
            digest = hashlib.sha256(digest).digest()
        return vector




