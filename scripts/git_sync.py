"""Git synchronization script for ObsidianConscierge."""

import logging
import subprocess
import sys
from pathlib import Path

import click

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.git_sync import GitChangeDetector
from app.core.indexing import IndexingService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--pull-only",
    is_flag=True,
    help="Git pullのみ実行（インデックス更新はスキップ）",
)
@click.option(
    "--use-sh-script",
    is_flag=True,
    help="Git操作をshスクリプトで実行（推奨）",
)
def main(pull_only: bool, use_sh_script: bool) -> None:
    """
    ObsidianConscierge Git同期スクリプト

    Git pullを実行し、変更を検知してインデックスを更新します。

    例:
        uv run python scripts/git_sync.py
        uv run python scripts/git_sync.py --use-sh-script
    """
    try:
        # 設定を読み込む
        settings = get_settings()
        vault_path = Path(settings.obsidian_vault_path)

        if not vault_path.exists():
            logger.error(f"Vaultパスが存在しません: {vault_path}")
            sys.exit(1)

        logger.info(f"Vaultパス: {vault_path}")

        # Git pullを実行
        if use_sh_script:
            # shスクリプトを使用
            script_path = Path(__file__).parent / "git_sync.sh"
            if not script_path.exists():
                logger.error(f"Git同期スクリプトが見つかりません: {script_path}")
                sys.exit(1)

            logger.info("Git同期スクリプトを実行中...")
            result = subprocess.run(
                ["bash", str(script_path)],
                cwd=str(Path(__file__).parent.parent),
                check=False,
            )

            if result.returncode != 0:
                logger.error("Git同期スクリプトの実行に失敗しました")
                sys.exit(1)
        else:
            # Pythonで直接Git操作（シンプルなpullのみ）
            logger.info("Git pullを実行中...")
            try:
                from git import Repo

                repo = Repo(vault_path)
                origin = repo.remotes.origin
                origin.pull()
                logger.info("Git pull完了")
            except Exception as exc:
                logger.error(f"Git pullに失敗しました: {exc}")
                sys.exit(1)

        if pull_only:
            logger.info("Git pullのみ実行しました（インデックス更新はスキップ）")
            return

        # 変更を検知
        logger.info("変更を検知中...")
        detector = GitChangeDetector(vault_path)
        last_commit = None

        # 前回コミットを読み込む
        data_dir = Path("data")
        last_commit_file = data_dir / "last_commit.txt"
        if last_commit_file.exists():
            with open(last_commit_file, encoding="utf-8") as f:
                last_commit = f.read().strip() or None

        changes = detector.detect_changes(since_commit=last_commit)

        if not changes:
            logger.info("変更は検出されませんでした")
            return

        logger.info(f"検出された変更: {len(changes)}件")

        # サービスを初期化
        logger.info("サービスを初期化中...")
        vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
        embedding_service = EmbeddingService()
        llm_service = LLMService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_llm_model,
        )

        indexing_service = IndexingService(
            vector_db_service=vector_db_service,
            embedding_service=embedding_service,
            llm_service=llm_service,
            settings=settings,
        )

        # 変更を処理
        added_files: list[Path] = []
        modified_files: list[Path] = []
        deleted_files: list[str] = []

        for change in changes:
            if change.change_type == "added":
                added_files.append(vault_path / change.file_path)
            elif change.change_type == "modified":
                modified_files.append(vault_path / change.file_path)
            elif change.change_type == "deleted":
                deleted_files.append(change.file_path)

        # 削除されたファイルを処理
        if deleted_files:
            logger.info(f"削除されたファイルを処理中: {len(deleted_files)}件")
            indexing_service.delete_articles(deleted_files)

        # 追加・更新されたファイルを処理
        all_files = added_files + modified_files
        if all_files:
            logger.info(f"追加・更新されたファイルを処理中: {len(all_files)}件")
            articles = indexing_service.process_batch(all_files)
            success_count = indexing_service.index_articles(articles)
            logger.info(f"インデックス更新完了: {success_count}/{len(articles)}件を格納")

        # 最新コミットを保存
        latest_commit = detector.get_latest_commit_id()
        indexing_service.save_last_commit(latest_commit)
        logger.info(f"最新コミットを保存: {latest_commit}")

        click.echo(f"✅ Git同期が完了しました: {len(changes)}件の変更を処理")

    except KeyboardInterrupt:
        logger.info("処理が中断されました")
        sys.exit(1)
    except Exception as exc:
        logger.error(f"エラーが発生しました: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

