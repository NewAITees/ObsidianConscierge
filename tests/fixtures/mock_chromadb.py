"""Mock ChromaDB for testing."""

from typing import Any
from unittest.mock import MagicMock

import chromadb


class MockChromaCollection:
    """ChromaDBコレクションのモック"""

    def __init__(self) -> None:
        """モックコレクションを初期化"""
        self._data: dict[str, dict[str, Any]] = {}
        self._embeddings: dict[str, list[float]] = {}
        self._metadatas: dict[str, dict[str, Any]] = {}
        self._documents: dict[str, str] = {}

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        """
        データを追加/更新する

        Args:
            ids: ドキュメントIDのリスト
            embeddings: 埋め込みベクトルのリスト
            metadatas: メタデータのリスト
            documents: ドキュメントテキストのリスト
        """
        for i, doc_id in enumerate(ids):
            self._data[doc_id] = {
                "id": doc_id,
                "embedding": embeddings[i] if embeddings else None,
                "metadata": metadatas[i] if metadatas else {},
                "document": documents[i] if documents else "",
            }
            if embeddings:
                self._embeddings[doc_id] = embeddings[i]
            if metadatas:
                self._metadatas[doc_id] = metadatas[i]
            if documents:
                self._documents[doc_id] = documents[i]

    def query(
        self,
        query_embeddings: list[list[float]] | None = None,
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        クエリを実行する（簡易実装）

        Args:
            query_embeddings: クエリの埋め込みベクトル
            n_results: 取得件数
            where: フィルタ条件
            include: 含める情報

        Returns:
            Dict: 検索結果
        """
        include = include or ["documents", "distances", "metadatas"]

        # 簡易実装: 全データを返す（実際の類似度計算は行わない）
        results: dict[str, Any] = {
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
            "documents": [[]],
        }

        if "ids" in include:
            results["ids"] = [[doc_id for doc_id in self._data.keys()][:n_results]]
        if "distances" in include:
            # ダミーの距離（0.0 = 完全一致）
            results["distances"] = [[0.0] * min(n_results, len(self._data))]
        if "metadatas" in include:
            results["metadatas"] = [
                [
                    self._metadatas.get(doc_id, {})
                    for doc_id in list(self._data.keys())[:n_results]
                ]
            ]
        if "documents" in include:
            results["documents"] = [
                [
                    self._documents.get(doc_id, "")
                    for doc_id in list(self._data.keys())[:n_results]
                ]
            ]

        return results

    def get(
        self,
        ids: list[str] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        データを取得する

        Args:
            ids: 取得するIDのリスト（Noneの場合は全件）
            include: 含める情報

        Returns:
            Dict: 取得結果
        """
        include = include or ["documents", "metadatas", "embeddings"]

        target_ids = ids if ids else list(self._data.keys())

        results: dict[str, Any] = {
            "ids": [],
            "metadatas": [],
            "documents": [],
            "embeddings": [],
        }

        for doc_id in target_ids:
            if doc_id in self._data:
                results["ids"].append(doc_id)
                if "metadatas" in include:
                    results["metadatas"].append(self._metadatas.get(doc_id, {}))
                if "documents" in include:
                    results["documents"].append(self._documents.get(doc_id, ""))
                if "embeddings" in include:
                    results["embeddings"].append(self._embeddings.get(doc_id, []))

        return results

    def delete(self, ids: list[str]) -> None:
        """
        データを削除する

        Args:
            ids: 削除するIDのリスト
        """
        for doc_id in ids:
            if doc_id in self._data:
                del self._data[doc_id]
            if doc_id in self._embeddings:
                del self._embeddings[doc_id]
            if doc_id in self._metadatas:
                del self._metadatas[doc_id]
            if doc_id in self._documents:
                del self._documents[doc_id]


class MockChromaClient:
    """ChromaDBクライアントのモック"""

    def __init__(self, path: str | None = None) -> None:
        """
        モッククライアントを初期化

        Args:
            path: データ保存パス（使用しない）
        """
        self._collections: dict[str, MockChromaCollection] = {}

    def get_or_create_collection(
        self,
        name: str,
        embedding_function: Any | None = None,
    ) -> MockChromaCollection:
        """
        コレクションを取得または作成する

        Args:
            name: コレクション名
            embedding_function: 埋め込み関数（使用しない）

        Returns:
            MockChromaCollection: モックコレクション
        """
        if name not in self._collections:
            self._collections[name] = MockChromaCollection()
        return self._collections[name]


def create_mock_chroma_client() -> MagicMock:
    """
    モックChromaDBクライアントを作成する

    Returns:
        MagicMock: モッククライアント
    """
    mock_client = MagicMock(spec=chromadb.PersistentClient)
    mock_collection = MockChromaCollection()

    # get_or_create_collectionをモック
    mock_client.get_or_create_collection.return_value = mock_collection

    return mock_client

