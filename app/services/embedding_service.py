"""Embedding generation service using sentence-transformers."""

import hashlib
import logging
from contextlib import contextmanager

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

FALLBACK_DIMENSIONS = 512

# torch のインポート（オプショナル: GPU管理用）
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available, GPU management disabled")


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
        self._gpu_loaded = False

    def _get_or_load_model(self) -> SentenceTransformer | None:
        """モデルを取得し、失敗した場合はフォールバックを有効化"""
        if self._use_fallback:
            return None

        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name)
                # デフォルトはCPUに配置
                if TORCH_AVAILABLE and torch.cuda.is_available():
                    self._model = self._model.to("cpu")
                    logger.info("Model loaded to CPU (GPU will be used on-demand)")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to load embedding model '%s', using deterministic fallback: %s",
                    self.model_name,
                    exc,
                )
                self._use_fallback = True
                self._model = None
        return self._model

    @contextmanager
    def use_gpu(self):
        """
        GPU使用のコンテキストマネージャー

        使用例:
            with embedding_service.use_gpu() as model:
                embeddings = model.encode(texts)
            # ← ここでGPUから自動解放される
        """
        model = self._get_or_load_model()
        if model is None:
            # フォールバックモード時はNoneを返す
            yield None
            return

        try:
            # GPUが利用可能ならGPUに転送
            if TORCH_AVAILABLE and torch.cuda.is_available():
                model = model.to("cuda")
                self._gpu_loaded = True
                logger.debug("Model moved to GPU")
            yield model
        finally:
            # 必ずGPUから解放
            if TORCH_AVAILABLE and torch.cuda.is_available() and self._gpu_loaded:
                if self._model is not None:
                    self._model = self._model.to("cpu")
                    self._gpu_loaded = False
                torch.cuda.empty_cache()
                logger.debug("Model moved to CPU, GPU cache cleared")

    def embed(self, text: str) -> list[float]:
        """
        テキストからベクトル（埋め込み）を生成する

        GPU使用後は自動的に解放される。

        Args:
            text: 埋め込みを生成するテキスト

        Returns:
            List[float]: ベクトル（512次元）
        """
        # use_gpu() コンテキストマネージャーでGPU使用を管理
        with self.use_gpu() as model:
            if model is not None:
                embedding = model.encode(text, show_progress_bar=False)
                return embedding.tolist()

        # フォールバックモード
        return self._fallback_embedding(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        複数のテキストをバッチで処理してベクトルを生成する

        GPU使用後は自動的に解放される。

        Args:
            texts: 埋め込みを生成するテキストのリスト

        Returns:
            List[List[float]]: ベクトルのリスト
        """
        # use_gpu() コンテキストマネージャーでGPU使用を管理
        with self.use_gpu() as model:
            if model is not None:
                embeddings = model.encode(texts, show_progress_bar=False)
                return [embedding.tolist() for embedding in embeddings]

        # フォールバックモード
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

    def cleanup(self) -> None:
        """
        明示的なクリーンアップ処理

        GPUメモリを解放し、モデルを削除する。
        """
        if self._model is not None:
            logger.info("Cleaning up EmbeddingService resources")
            if TORCH_AVAILABLE and torch.cuda.is_available():
                # GPUから退避
                self._model = self._model.to("cpu")
                self._gpu_loaded = False
                # GPUキャッシュをクリア
                torch.cuda.empty_cache()
                logger.debug("GPU cache cleared")
            # モデルを削除
            del self._model
            self._model = None

    def __del__(self) -> None:
        """
        デストラクタ

        オブジェクト破棄時に念のためクリーンアップを実行。
        """
        try:
            self.cleanup()
        except Exception:
            # デストラクタでは例外を無視
            pass




