"""Indexing pipeline for processing articles."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.core.content_extractor import ContentExtractor
from app.core.git_sync import GitChangeDetector
from app.models.article import Article, ArticleContent, FileChange
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService

logger = logging.getLogger(__name__)


class IndexingService:
    """記事のインデックス作成サービス"""

    def __init__(
        self,
        vector_db_service: VectorDBService,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        content_extractor: ContentExtractor | None = None,
        settings: Settings | None = None,
    ) -> None:
        """
        IndexingServiceを初期化

        Args:
            vector_db_service: ベクトルDBサービス
            embedding_service: Embeddingサービス
            llm_service: LLMサービス
            content_extractor: コンテンツ抽出サービス（Noneの場合は新規作成）
            settings: 設定（Noneの場合はget_settings()で取得）
        """
        self.settings = settings or get_settings()
        self.vector_db_service = vector_db_service
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        self.content_extractor = content_extractor or ContentExtractor()
        # vault_pathを絶対パスに解決（相対パスの場合、現在の作業ディレクトリからの相対パスとして解決）
        self.vault_path = Path(self.settings.obsidian_vault_path).resolve()
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.last_commit_file = self.data_dir / "last_commit.txt"

    def detect_changes(
        self, since_commit: str | None = None
    ) -> list[FileChange]:
        """
        Git変更を検知する

        Args:
            since_commit: 検知開始コミットID（Noneの場合は前回保存されたコミットを使用）

        Returns:
            List[FileChange]: 検出されたファイル変更のリスト
        """
        if since_commit is None:
            since_commit = self.load_last_commit()

        detector = GitChangeDetector(self.vault_path)
        changes = detector.detect_changes(since_commit=since_commit)

        logger.info(f"検出された変更: {len(changes)}件")
        return changes

    def process_article(self, file_path: Path) -> Article | None:
        """
        単一記事を処理してArticleオブジェクトを作成

        Args:
            file_path: 処理対象のファイルパス（相対パスまたは絶対パス）

        Returns:
            Article: 処理されたArticleオブジェクト。処理に失敗した場合はNone
        """
        try:
            # 絶対パスに変換
            if not file_path.is_absolute():
                # 相対パスの場合、vault_pathからの相対パスとして扱う
                file_path = self.vault_path / file_path
            else:
                # 絶対パスの場合、vault_pathに含まれているかチェック
                try:
                    # vault_pathからの相対パスを取得（vault_pathに含まれている場合）
                    file_path.relative_to(self.vault_path)
                except ValueError:
                    # vault_pathに含まれていない場合は、そのまま使用
                    pass

            # コンテンツ抽出
            content: ArticleContent = self.content_extractor.extract_content(
                file_path
            )

            # サマリー生成
            summary = self.llm_service.generate_summary(content.body)

            # タグ生成（既存タグがある場合は統合）
            existing_tags = content.metadata.get("tags", [])
            if isinstance(existing_tags, str):
                existing_tags = [existing_tags]
            elif not isinstance(existing_tags, list):
                existing_tags = []

            tags = self.llm_service.generate_tags(
                content.body, existing_tags=existing_tags
            ) if self.settings.enable_auto_tagging else existing_tags

            # 埋め込み生成
            body_embedding = self.embedding_service.embed(content.body)
            summary_embedding = self.embedding_service.embed(summary)

            # 日時を取得
            created = self._parse_datetime(content.metadata.get("created"))
            modified = self._parse_datetime(
                content.metadata.get("modified")
            ) or datetime.now()

            # 相対パスを取得
            relative_path = file_path.relative_to(self.vault_path)
            article_id = str(relative_path).replace("\\", "/")

            # Articleオブジェクトを作成
            article = Article(
                id=article_id,
                title=content.title,
                body=content.body,
                summary=summary,
                tags=tags,
                created=created,
                modified=modified,
                file_path=article_id,
                body_embedding=body_embedding,
                summary_embedding=summary_embedding,
                word_count=content.word_count,
            )

            return article

        except Exception as exc:
            logger.error(f"記事の処理に失敗しました: {file_path}, エラー: {exc}")
            return None

    def process_batch(
        self, file_paths: list[Path], batch_size: int = 100
    ) -> list[Article]:
        """
        複数記事をバッチ処理する

        Args:
            file_paths: 処理対象のファイルパスのリスト
            batch_size: バッチサイズ

        Returns:
            List[Article]: 処理されたArticleオブジェクトのリスト
        """
        articles: list[Article] = []

        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i : i + batch_size]
            logger.info(f"バッチ処理: {i + 1}-{min(i + batch_size, len(file_paths))}/{len(file_paths)}")

            for file_path in batch:
                article = self.process_article(file_path)
                if article:
                    articles.append(article)

        return articles

    def index_articles(self, articles: list[Article]) -> int:
        """
        記事をベクトルDBに格納する

        Args:
            articles: 格納するArticleオブジェクトのリスト

        Returns:
            int: 格納に成功した記事数
        """
        success_count = 0

        for article in articles:
            try:
                if self.vector_db_service.store(article):
                    success_count += 1
            except Exception as exc:
                logger.error(f"記事の格納に失敗しました: {article.id}, エラー: {exc}")

        logger.info(f"記事の格納完了: {success_count}/{len(articles)}件")
        return success_count

    def delete_articles(self, file_paths: list[str]) -> int:
        """
        削除された記事をベクトルDBから削除する

        Args:
            file_paths: 削除するファイルパスのリスト（相対パス）

        Returns:
            int: 削除に成功した記事数
        """
        success_count = 0

        for file_path in file_paths:
            try:
                # パスを正規化（Windows/Unix対応）
                article_id = file_path.replace("\\", "/")
                if self.vector_db_service.delete(article_id):
                    success_count += 1
            except Exception as exc:
                logger.error(f"記事の削除に失敗しました: {file_path}, エラー: {exc}")

        logger.info(f"記事の削除完了: {success_count}/{len(file_paths)}件")
        return success_count

    def save_last_commit(self, commit_id: str) -> None:
        """
        前回処理したコミットIDを保存する

        Args:
            commit_id: コミットID
        """
        try:
            self.last_commit_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.last_commit_file, "w", encoding="utf-8") as f:
                f.write(commit_id)
            logger.info(f"前回コミットを保存: {commit_id}")
        except Exception as exc:
            logger.error(f"前回コミットの保存に失敗しました: {exc}")

    def load_last_commit(self) -> str | None:
        """
        前回処理したコミットIDを読み込む

        Returns:
            str | None: コミットID（存在しない場合はNone）
        """
        try:
            if self.last_commit_file.exists():
                with open(self.last_commit_file, encoding="utf-8") as f:
                    commit_id = f.read().strip()
                    if commit_id:
                        logger.info(f"前回コミットを読み込み: {commit_id}")
                        return commit_id
        except Exception as exc:
            logger.error(f"前回コミットの読み込みに失敗しました: {exc}")

        return None

    def _parse_datetime(self, value: Any) -> datetime | None:
        """
        日時文字列をdatetimeオブジェクトに変換する

        Args:
            value: 日時文字列またはdatetimeオブジェクト

        Returns:
            datetime | None: 変換されたdatetimeオブジェクト（変換できない場合はNone）
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            # ISO形式の日時文字列をパース
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

        return None

