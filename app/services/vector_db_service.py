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
