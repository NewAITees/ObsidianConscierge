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
        クエリで記事を検索する（セマンティック検索）

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

    def search_by_tags(
        self, tags: list[str], limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        タグで記事を検索する

        Args:
            tags: 検索対象のタグリスト
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        return self.vector_db_service.search_by_tags(tags=tags, limit=limit)

    def search_by_keyword(
        self, keyword: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        キーワードで記事を検索する

        Args:
            keyword: 検索キーワード
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        return self.vector_db_service.search_by_keyword(keyword=keyword, limit=limit)

    def search_by_date_range(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        日付範囲で記事を検索する

        Args:
            from_date: 開始日（ISO形式、例: 2024-01-01）
            to_date: 終了日（ISO形式、例: 2024-12-31）
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        return self.vector_db_service.search_by_date_range(
            from_date=from_date, to_date=to_date, limit=limit
        )

    def search_by_word_count(
        self,
        min_words: int | None = None,
        max_words: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        文字数範囲で記事を検索する

        Args:
            min_words: 最小文字数
            max_words: 最大文字数
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        return self.vector_db_service.search_by_word_count(
            min_words=min_words, max_words=max_words, limit=limit
        )

    def get_similar_documents(
        self, doc_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        指定されたドキュメントに類似したドキュメントを検索する

        Args:
            doc_id: 基準となるドキュメントのID
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 類似ドキュメントのリスト
        """
        return self.vector_db_service.get_similar_documents(doc_id=doc_id, limit=limit)

    def hybrid_search(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        min_words: int | None = None,
        max_words: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        ハイブリッド検索（複数の条件を組み合わせて検索）

        Args:
            query: 検索クエリ（自然文、オプション）
            tags: タグフィルタ（オプション）
            from_date: 開始日（ISO形式、オプション）
            to_date: 終了日（ISO形式、オプション）
            min_words: 最小文字数（オプション）
            max_words: 最大文字数（オプション）
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        # セマンティック検索を実行
        if query:
            results = self.search(query=query, limit=limit * 2, tags=tags)  # 多めに取得してフィルタ
        else:
            # クエリがない場合は全件取得
            results = self.vector_db_service.get_all_articles()

        # 日付範囲でフィルタ
        if from_date or to_date:
            filtered_results = []
            for result in results:
                modified = result.get("modified")
                if modified:
                    if from_date and modified < from_date:
                        continue
                    if to_date and modified > to_date:
                        continue
                    filtered_results.append(result)
            results = filtered_results

        # 文字数範囲でフィルタ
        if min_words is not None or max_words is not None:
            filtered_results = []
            for result in results:
                word_count = result.get("word_count", 0)
                if min_words is not None and word_count < min_words:
                    continue
                if max_words is not None and word_count > max_words:
                    continue
                filtered_results.append(result)
            results = filtered_results

        # limitまで絞り込む
        return results[:limit]




