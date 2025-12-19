"""Vector database service using ChromaDB."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from app.models.article import Article

COLLECTION_NAME = "articles"


class VectorDBService:
    """ChromaDBを使用したベクトルDBサービス"""

    def __init__(
        self,
        db_path: Path,
        embedding_function: embedding_functions.EmbeddingFunction | None = None,
    ) -> None:
        """
        VectorDBServiceを初期化

        Args:
            db_path: ChromaDBのデータ保存パス
            embedding_function: ChromaDBに渡すEmbedding関数（Noneで自前ベクトルのみ使用）
        """
        self.db_path = db_path
        self.embedding_function = embedding_function
        self._client: chromadb.PersistentClient | None = None
        self._collection: chromadb.Collection | None = None

    @property
    def client(self) -> chromadb.PersistentClient:
        """
        ChromaDBクライアントを取得（遅延初期化）

        Returns:
            chromadb.PersistentClient: ChromaDBクライアント
        """
        if self._client is None:
            self._client = chromadb.PersistentClient(path=str(self.db_path))
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        """
        ChromaDBコレクションを取得（遅延初期化）

        Returns:
            chromadb.Collection: ChromaDBコレクション
        """
        if self._collection is None:
            kwargs: dict[str, Any] = {"name": COLLECTION_NAME}
            if self.embedding_function is not None:
                kwargs["embedding_function"] = self.embedding_function

            self._collection = self.client.get_or_create_collection(**kwargs)
        return self._collection

    def store(self, article: Article) -> bool:
        """
        記事をベクトルDBに格納する

        Args:
            article: 格納する記事

        Returns:
            bool: 格納成功時True
        """
        try:
            # メタデータを準備
            metadata: dict[str, Any] = {
                "title": article.title,
                "summary": article.summary,
                "tags": ",".join(article.tags),
                "file_path": article.file_path,
                "word_count": article.word_count,
            }

            if article.created:
                metadata["created"] = article.created.isoformat()
            if article.modified:
                metadata["modified"] = article.modified.isoformat()

            # ChromaDBに格納（既存のIDがある場合は上書き）
            self.collection.upsert(
                ids=[article.id],
                embeddings=[article.body_embedding],
                metadatas=[metadata],
                documents=[article.body],  # 検索用に本文も保存
            )

            return True
        except Exception:
            return False

    def search(
        self,
        query_embedding: list[float],
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        ベクトル検索を実行する

        Args:
            query_embedding: クエリのベクトル
            limit: 取得件数
            filters: フィルタ条件（オプション）

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        try:
            # where句を構築
            where: dict[str, Any] | None = None
            if filters:
                where = {}
                if "tags" in filters:
                    # タグフィルタ（カンマ区切りのタグ文字列から検索）
                    # 複数のタグがある場合は、いずれかが含まれていればOK
                    tag_filter = filters["tags"]
                    if isinstance(tag_filter, str):
                        where["tags"] = {"$contains": tag_filter}
                    elif isinstance(tag_filter, list) and tag_filter:
                        # 最初のタグでフィルタ（ChromaDBの制約により単一条件のみ）
                        where["tags"] = {"$contains": tag_filter[0]}

            # 検索実行
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where,
                include=["documents", "distances", "metadatas"],
            )

            # 結果を整形
            search_results: list[dict[str, Any]] = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][i]
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]

                    # 距離を類似度に変換（L2距離を想定）
                    similarity = max(0.0, 1.0 - (distance / 2.0))

                    search_results.append(
                        {
                            "id": doc_id,
                            "title": metadata.get("title", ""),
                            "summary": metadata.get("summary", ""),
                            "similarity": similarity,
                            "tags": metadata.get("tags", "").split(",")
                            if metadata.get("tags")
                            else [],
                            "file_path": metadata.get("file_path", ""),
                            "modified": metadata.get("modified"),
                        }
                    )

            return search_results
        except Exception:
            return []

    def delete(self, article_id: str) -> bool:
        """
        記事をベクトルDBから削除する

        Args:
            article_id: 削除する記事のID

        Returns:
            bool: 削除成功時True
        """
        try:
            self.collection.delete(ids=[article_id])
            return True
        except Exception:
            return False

    def update(self, article: Article) -> bool:
        """
        記事を更新する（storeと同じ処理）

        Args:
            article: 更新する記事

        Returns:
            bool: 更新成功時True
        """
        return self.store(article)

    def get_all_articles(self) -> list[dict[str, Any]]:
        """
        ChromaDBから全記事を取得する

        Returns:
            List[Dict[str, Any]]: 全記事のリスト（id, title, summary, tags, file_path, modified, created, word_count, body_embeddingを含む）
        """
        try:
            # ChromaDBから全件取得（where句なしで全件取得）
            # embeddingsは大きいので、必要に応じてのみ取得
            results = self.collection.get(
                include=["documents", "metadatas"],
            )

            articles: list[dict[str, Any]] = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc_id = results["ids"][i]
                    metadata = results["metadatas"][i] if results["metadatas"] else {}
                    document = results["documents"][i] if results["documents"] else ""

                    # タグをリストに変換
                    tags_str = metadata.get("tags", "")
                    tags = tags_str.split(",") if tags_str else []
                    # 空文字列を除去
                    tags = [tag.strip() for tag in tags if tag.strip()]

                    articles.append(
                        {
                            "id": doc_id,
                            "title": metadata.get("title", ""),
                            "summary": metadata.get("summary", ""),
                            "tags": tags,
                            "file_path": metadata.get("file_path", ""),
                            "modified": metadata.get("modified"),
                            "created": metadata.get("created"),
                            "word_count": metadata.get("word_count", 0),
                            "body": document,
                        }
                    )

            return articles
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"get_all_articles() failed: {exc}")
            return []

    def search_by_tags(
        self, tags: list[str], limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        タグで検索する

        Args:
            tags: 検索対象のタグリスト
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        try:
            if not tags:
                return []

            # 最初のタグでフィルタ（ChromaDBの制約により単一条件のみ）
            where = {"tags": {"$contains": tags[0]}}

            results = self.collection.get(
                where=where,
                limit=limit,
                include=["documents", "metadatas"],
            )

            search_results: list[dict[str, Any]] = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc_id = results["ids"][i]
                    metadata = results["metadatas"][i] if results["metadatas"] else {}

                    # 他のタグでもフィルタリング（複数タグ対応）
                    tags_str = metadata.get("tags", "")
                    doc_tags = tags_str.split(",") if tags_str else []

                    # すべてのタグが含まれているかチェック
                    if all(tag in doc_tags for tag in tags):
                        search_results.append(
                            {
                                "id": doc_id,
                                "title": metadata.get("title", ""),
                                "summary": metadata.get("summary", ""),
                                "tags": doc_tags,
                                "file_path": metadata.get("file_path", ""),
                                "modified": metadata.get("modified"),
                                "word_count": metadata.get("word_count", 0),
                            }
                        )

            return search_results
        except Exception:
            return []

    def search_by_keyword(
        self, keyword: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        キーワードで検索する（タイトルまたは本文に含まれるもの）

        Args:
            keyword: 検索キーワード
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        try:
            # ChromaDBから全件取得して、キーワードでフィルタリング
            results = self.collection.get(
                include=["documents", "metadatas"],
            )

            search_results: list[dict[str, Any]] = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc_id = results["ids"][i]
                    metadata = results["metadatas"][i] if results["metadatas"] else {}
                    document = results["documents"][i] if results["documents"] else ""

                    # タイトルまたは本文にキーワードが含まれているかチェック
                    title = metadata.get("title", "")
                    if keyword.lower() in title.lower() or keyword.lower() in document.lower():
                        tags_str = metadata.get("tags", "")
                        tags = tags_str.split(",") if tags_str else []

                        search_results.append(
                            {
                                "id": doc_id,
                                "title": title,
                                "summary": metadata.get("summary", ""),
                                "tags": tags,
                                "file_path": metadata.get("file_path", ""),
                                "modified": metadata.get("modified"),
                                "word_count": metadata.get("word_count", 0),
                            }
                        )

                        if len(search_results) >= limit:
                            break

            return search_results
        except Exception:
            return []

    def search_by_date_range(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        日付範囲で検索する

        Args:
            from_date: 開始日（ISO形式、例: 2024-01-01）
            to_date: 終了日（ISO形式、例: 2024-12-31）
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        try:
            # ChromaDBから全件取得して、日付でフィルタリング
            results = self.collection.get(
                include=["documents", "metadatas"],
            )

            search_results: list[dict[str, Any]] = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc_id = results["ids"][i]
                    metadata = results["metadatas"][i] if results["metadatas"] else {}
                    modified = metadata.get("modified")

                    # 日付範囲チェック
                    if modified:
                        if from_date and modified < from_date:
                            continue
                        if to_date and modified > to_date:
                            continue

                        tags_str = metadata.get("tags", "")
                        tags = tags_str.split(",") if tags_str else []

                        search_results.append(
                            {
                                "id": doc_id,
                                "title": metadata.get("title", ""),
                                "summary": metadata.get("summary", ""),
                                "tags": tags,
                                "file_path": metadata.get("file_path", ""),
                                "modified": modified,
                                "word_count": metadata.get("word_count", 0),
                            }
                        )

                        if len(search_results) >= limit:
                            break

            return search_results
        except Exception:
            return []

    def search_by_word_count(
        self,
        min_words: int | None = None,
        max_words: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        文字数範囲で検索する

        Args:
            min_words: 最小文字数
            max_words: 最大文字数
            limit: 取得件数

        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        try:
            # ChromaDBから全件取得して、文字数でフィルタリング
            results = self.collection.get(
                include=["documents", "metadatas"],
            )

            search_results: list[dict[str, Any]] = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc_id = results["ids"][i]
                    metadata = results["metadatas"][i] if results["metadatas"] else {}
                    word_count = metadata.get("word_count", 0)

                    # 文字数範囲チェック
                    if min_words is not None and word_count < min_words:
                        continue
                    if max_words is not None and word_count > max_words:
                        continue

                    tags_str = metadata.get("tags", "")
                    tags = tags_str.split(",") if tags_str else []

                    search_results.append(
                        {
                            "id": doc_id,
                            "title": metadata.get("title", ""),
                            "summary": metadata.get("summary", ""),
                            "tags": tags,
                            "file_path": metadata.get("file_path", ""),
                            "modified": metadata.get("modified"),
                            "word_count": word_count,
                        }
                    )

                    if len(search_results) >= limit:
                        break

            return search_results
        except Exception:
            return []

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
        try:
            # 指定されたドキュメントを取得
            results = self.collection.get(
                ids=[doc_id],
                include=["embeddings"],
            )

            if not results["ids"] or not results["embeddings"]:
                return []

            # ドキュメントのベクトルを使って類似検索
            embedding = results["embeddings"][0]
            similar_results = self.collection.query(
                query_embeddings=[embedding],
                n_results=limit + 1,  # 自分自身も含まれるため+1
                include=["documents", "distances", "metadatas"],
            )

            # 結果を整形（自分自身を除外）
            search_results: list[dict[str, Any]] = []
            if similar_results["ids"] and similar_results["ids"][0]:
                for i in range(len(similar_results["ids"][0])):
                    result_id = similar_results["ids"][0][i]

                    # 自分自身は除外
                    if result_id == doc_id:
                        continue

                    metadata = similar_results["metadatas"][0][i]
                    distance = similar_results["distances"][0][i]

                    # 距離を類似度に変換
                    similarity = max(0.0, 1.0 - (distance / 2.0))

                    tags_str = metadata.get("tags", "")
                    tags = tags_str.split(",") if tags_str else []

                    search_results.append(
                        {
                            "id": result_id,
                            "title": metadata.get("title", ""),
                            "summary": metadata.get("summary", ""),
                            "similarity": similarity,
                            "tags": tags,
                            "file_path": metadata.get("file_path", ""),
                            "modified": metadata.get("modified"),
                        }
                    )

            return search_results
        except Exception:
            return []
