"""Similar document link inserter.

類似ドキュメントへのリンクを自動挿入する機能を提供します。
"""

import re
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.document_updater import DocumentUpdater
from app.services.vector_db_service import VectorDBService


class LinkInserter:
    """類似リンク挿入サービス"""

    def __init__(
        self,
        vector_db_service: VectorDBService,
        settings: Settings | None = None,
    ) -> None:
        """
        LinkInserterを初期化

        Args:
            vector_db_service: ベクトルDBサービス
            settings: 設定（Noneの場合はget_settings()で取得）
        """
        self.settings = settings or get_settings()
        self.vector_db_service = vector_db_service
        self.vault_path = Path(self.settings.obsidian_vault_path).resolve()

    def is_duplicate_file(self, file1: Path, file2: Path) -> bool:
        """
        ファイル名が実質的に同じかチェック（重複ファイル検出）

        Args:
            file1: ファイル1のパス
            file2: ファイル2のパス

        Returns:
            bool: 重複ファイルの場合True
        """
        name1 = file1.stem.lower()
        name2 = file2.stem.lower()

        # 完全一致
        if name1 == name2:
            return True

        # 数字違いのみ (例: file.md と file 2.md)
        name1_clean = re.sub(r"\s*\d+\s*$", "", name1)
        name2_clean = re.sub(r"\s*\d+\s*$", "", name2)

        return name1_clean == name2_clean and name1_clean != ""

    def get_similar_documents(
        self, file_path: Path, embedding: list[float]
    ) -> list[dict]:
        """
        類似ドキュメントを取得

        Args:
            file_path: 対象ファイルのパス
            embedding: ファイルのベクトル表現

        Returns:
            list[dict]: 類似ドキュメントのリスト
                [{"title": "ドキュメント名", "similarity": 0.85, "file_path": "..."}, ...]
        """
        # 設定値を取得
        min_similarity = self.settings.min_similarity_for_link
        max_links = self.settings.max_similar_links

        # ベクトル検索を実行（多めに取得してフィルタリング）
        search_results = self.vector_db_service.search(
            query_embedding=embedding,
            limit=max_links * 3,  # フィルタリング後に十分な数が残るように
        )

        similar_docs = []
        for result in search_results:
            result_path = Path(result["file_path"])
            similarity = result["similarity"]

            # 自己参照をスキップ
            if result_path.resolve() == file_path.resolve():
                continue

            # 類似度チェック
            if similarity < min_similarity:
                continue

            # 重複ファイルチェック
            if self.is_duplicate_file(file_path, result_path):
                continue

            # タイトルを取得（拡張子なし）
            title = result_path.stem

            similar_docs.append(
                {
                    "title": title,
                    "similarity": similarity,
                    "file_path": str(result_path),
                }
            )

        # 類似度でソートして上位N件を返す
        similar_docs.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_docs[:max_links]

    def insert_links_to_file(
        self, file_path: Path, embedding: list[float]
    ) -> bool:
        """
        ファイルに類似リンクを挿入

        Args:
            file_path: 対象ファイルのパス
            embedding: ファイルのベクトル表現

        Returns:
            bool: 挿入成功時True
        """
        # 除外フォルダチェック
        if DocumentUpdater.is_file_excluded(
            file_path,
            self.settings.excluded_folders,
            self.vault_path,
            self.settings.exclude_root_files,
        ):
            return False

        # 類似ドキュメントを取得
        similar_docs = self.get_similar_documents(file_path, embedding)

        if not similar_docs:
            # 類似ドキュメントがない場合は何もしない
            return False

        # ドキュメントを更新（AIセクションを使用）
        return DocumentUpdater.update_document(
            file_path=file_path,
            similar_links=similar_docs,
            tags=None,  # タグは別のサービスで処理
        )

    def batch_insert_links(
        self, file_paths: list[Path], embeddings: dict[str, list[float]]
    ) -> dict:
        """
        複数ファイルに一括でリンクを挿入

        Args:
            file_paths: 対象ファイルパスのリスト
            embeddings: {ファイルパス: ベクトル} の辞書

        Returns:
            dict: 処理統計
                {
                    "processed": 処理ファイル数,
                    "successful": 成功数,
                    "excluded": 除外数,
                    "no_similar": 類似なし数,
                    "failed": 失敗数
                }
        """
        stats = {
            "processed": 0,
            "successful": 0,
            "excluded": 0,
            "no_similar": 0,
            "failed": 0,
        }

        for file_path in file_paths:
            stats["processed"] += 1

            # 除外フォルダチェック
            if DocumentUpdater.is_file_excluded(
                file_path,
                self.settings.excluded_folders,
                self.vault_path,
                self.settings.exclude_root_files,
            ):
                stats["excluded"] += 1
                continue

            # ベクトルを取得
            file_key = str(file_path)
            if file_key not in embeddings:
                stats["failed"] += 1
                continue

            embedding = embeddings[file_key]

            # 類似ドキュメントを取得
            similar_docs = self.get_similar_documents(file_path, embedding)

            if not similar_docs:
                stats["no_similar"] += 1
                continue

            # リンク挿入
            success = DocumentUpdater.update_document(
                file_path=file_path,
                similar_links=similar_docs,
                tags=None,
            )

            if success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1

        return stats
