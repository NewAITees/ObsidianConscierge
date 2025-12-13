"""Search service for semantic search."""

from typing import Any

from app.services.embedding_service import EmbeddingService
from app.services.vector_db_service import VectorDBService


class SearchService:
    """セマンティック検索サービス"""

    def __init__(
        self,
        vector_db_service: VectorDBService,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """
        SearchServiceを初期化

        Args:
            vector_db_service: ベクトルDBサービス
            embedding_service: Embeddingサービス（Noneの場合は新規作成）
        """
        self.vector_db_service = vector_db_service
        self.embedding_service = embedding_service or EmbeddingService()

    def search(
        self,
        query: str,
        limit: int = 20,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        クエリで記事を検索する

        Args:
            query: 検索クエリ（自然文）
            limit: 取得件数
            tags: タグフィルタ（オプション）

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        # クエリをベクトル化
        query_embedding = self.embedding_service.embed(query)

        # フィルタを準備
        filters: dict[str, Any] | None = None
        if tags:
            filters = {"tags": ",".join(tags)}

        # ベクトルDBで検索
        results = self.vector_db_service.search(
            query_embedding=query_embedding,
            limit=limit,
            filters=filters,
        )

        return results


