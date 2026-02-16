"""Indexing pipeline for processing articles."""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from subprocess import TimeoutExpired
from typing import Any

from app.core.config import Settings, get_settings
from app.core.content_extractor import ContentExtractor
from app.core.git_sync import GitChangeDetector
from app.models.article import Article, ArticleContent, FileChange
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService

logger = logging.getLogger(__name__)


@dataclass
class _PreparedArticle:
    """埋め込み生成前の準備済み記事データ"""

    id: str
    title: str
    body: str
    summary: str
    tags: list[str]
    created: datetime | None
    modified: datetime | None
    file_path: str
    word_count: int


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
            prepared = self._prepare_article(file_path)
            if prepared is None:
                return None

            body_embedding = self.embedding_service.embed(prepared.body)
            summary_embedding = self.embedding_service.embed(prepared.summary)

            return self._build_article(
                prepared,
                body_embedding=body_embedding,
                summary_embedding=summary_embedding,
            )

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

            prepared_batch: list[_PreparedArticle] = []
            for file_path in batch:
                prepared = self._prepare_article(file_path)
                if prepared is not None:
                    prepared_batch.append(prepared)

            if not prepared_batch:
                continue

            bodies = [prepared.body for prepared in prepared_batch]
            summaries = [prepared.summary for prepared in prepared_batch]

            body_embeddings = self.embed_batch_with_worker(bodies)
            summary_embeddings = self.embed_batch_with_worker(summaries)

            for prepared, body_embedding, summary_embedding in zip(
                prepared_batch, body_embeddings, summary_embeddings, strict=True
            ):
                articles.append(
                    self._build_article(
                        prepared,
                        body_embedding=body_embedding,
                        summary_embedding=summary_embedding,
                    )
                )

        return articles

    def _prepare_article(self, file_path: Path) -> "_PreparedArticle | None":
        """
        記事のメタ情報と本文を準備する（埋め込み生成は行わない）

        Args:
            file_path: 処理対象のファイルパス（相対パスまたは絶対パス）

        Returns:
            _PreparedArticle | None: 準備済みデータ。失敗時はNone。
        """
        try:
            # 絶対パスに変換（パス重複を防ぐ）
            if not file_path.is_absolute():
                file_path = self.vault_path / file_path

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            content: ArticleContent = self.content_extractor.extract_content(file_path)

            summary = self.llm_service.generate_summary(content.body)

            existing_tags = content.metadata.get("tags", [])
            if isinstance(existing_tags, str):
                existing_tags = [existing_tags]
            elif not isinstance(existing_tags, list):
                existing_tags = []

            # リスト内の全要素を文字列に変換（datetime.date等のオブジェクト対策）
            existing_tags = [str(tag) for tag in existing_tags]

            tags = (
                self.llm_service.generate_tags(content.body, existing_tags=existing_tags)
                if self.settings.enable_auto_tagging
                else existing_tags
            )

            created = self._parse_datetime(content.metadata.get("created"))
            modified = self._parse_datetime(content.metadata.get("modified")) or datetime.now()

            relative_path = file_path.relative_to(self.vault_path)
            article_id = str(relative_path).replace("\\", "/")

            return _PreparedArticle(
                id=article_id,
                title=content.title,
                body=content.body,
                summary=summary,
                tags=tags,
                created=created,
                modified=modified,
                file_path=article_id,
                word_count=content.word_count,
            )
        except Exception as exc:
            logger.error(f"記事の処理に失敗しました: {file_path}, エラー: {exc}")
            return None

    def _build_article(
        self,
        prepared: "_PreparedArticle",
        body_embedding: list[float],
        summary_embedding: list[float],
    ) -> Article:
        """
        準備済みデータと埋め込みからArticleを構築する。
        """
        return Article(
            id=prepared.id,
            title=prepared.title,
            body=prepared.body,
            summary=prepared.summary,
            tags=prepared.tags,
            created=prepared.created,
            modified=prepared.modified,
            file_path=prepared.file_path,
            body_embedding=body_embedding,
            summary_embedding=summary_embedding,
            word_count=prepared.word_count,
        )

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
            value: 日時文字列、datetimeオブジェクト、またはdateオブジェクト

        Returns:
            datetime | None: 変換されたdatetimeオブジェクト（変換できない場合はNone）
        """
        if value is None:
            return None

        # datetime.datetimeオブジェクトの場合
        if isinstance(value, datetime):
            return value

        # datetime.dateオブジェクトの場合（Frontmatterが自動変換する可能性あり）
        # dateをdatetimeに変換（時刻は00:00:00）
        from datetime import date
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())

        # 文字列の場合
        if isinstance(value, str):
            # ISO形式の日時文字列をパース
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

        # その他の型の場合は文字列に変換してパースを試みる
        try:
            value_str = str(value)
            return datetime.fromisoformat(value_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

        return None

    def embed_batch_with_worker(
        self, texts: list[str], timeout: int = 1800
    ) -> list[list[float]]:
        """
        ワーカープロセス経由でバッチembeddingを実行（より堅牢）

        別プロセスでembedding処理を実行することで、ハング時でも
        親プロセスから強制終了してGPUリソースを確実に解放できる。

        Args:
            texts: 埋め込みを生成するテキストのリスト
            timeout: タイムアウト秒数（デフォルト: 30分）

        Returns:
            List[List[float]]: 埋め込みベクトルのリスト

        Raises:
            TimeoutExpired: タイムアウトした場合
            RuntimeError: ワーカープロセスがエラーを返した場合
        """
        worker_script = Path(__file__).parent.parent.parent / "scripts" / "embedding_worker.py"

        if not worker_script.exists():
            logger.warning(
                f"Embedding worker script not found: {worker_script}, falling back to direct call"
            )
            # フォールバック: 直接呼び出し
            return self.embedding_service.embed_batch(texts)

        # 入力データをJSON化
        input_data = {"texts": texts}
        input_json = json.dumps(input_data)

        logger.info(f"Starting embedding worker process (timeout: {timeout}s)")

        proc: subprocess.Popen[str] | None = None

        try:
            # ワーカープロセスを起動
            proc = subprocess.Popen(
                [sys.executable, str(worker_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # タイムアウト付きで実行
            stdout, stderr = proc.communicate(input=input_json, timeout=timeout)

            # ワーカーのログ出力（stderr）を記録
            if stderr:
                logger.debug(f"Worker stderr: {stderr}")

            if not stdout.strip():
                raise RuntimeError(
                    f"Worker returned empty output (rc={proc.returncode}): {stderr.strip()}"
                )

            # 結果をパース
            result = json.loads(stdout)

            if result.get("status") == "error":
                error_msg = result.get("error", "Unknown error")
                error_type = result.get("type", "UnknownError")
                raise RuntimeError(f"Worker process failed ({error_type}): {error_msg}")

            embeddings = result.get("embeddings", [])
            logger.info(f"Successfully received {len(embeddings)} embeddings from worker")

            return embeddings

        except TimeoutExpired:
            logger.error(f"Embedding worker timed out after {timeout}s, killing process")
            if proc is not None:
                proc.kill()
                proc.wait()  # zombie回避
            raise

        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse worker output: {exc}")
            logger.error(f"Worker stdout: {stdout}")
            raise RuntimeError(f"Invalid worker output: {exc}") from exc

        except Exception as exc:
            logger.error(f"Embedding worker failed: {exc}")
            # プロセスがまだ動いている場合は終了
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait()
            raise
