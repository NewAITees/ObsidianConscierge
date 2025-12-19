"""Initial index creation script."""

import logging
import sys
from pathlib import Path

import click
from tqdm import tqdm

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.content_extractor import ContentExtractor
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
    "--vault-path",
    "-v",
    type=click.Path(exists=True, path_type=Path),
    help="Obsidian Vaultのパス（未指定の場合は設定から取得）",
)
@click.option(
    "--batch-size",
    "-b",
    default=100,
    help="バッチサイズ（デフォルト: 100）",
)
@click.option(
    "--skip-summary",
    is_flag=True,
    help="サマリー生成をスキップ（高速化）",
)
@click.option(
    "--skip-tags",
    is_flag=True,
    help="タグ生成をスキップ（高速化）",
)
def main(
    vault_path: Path | None,
    batch_size: int,
    skip_summary: bool,
    skip_tags: bool,
) -> None:
    """
    ObsidianConscierge 初期インデックス作成スクリプト

    全記事をベクトル化してChromaDBに格納します。

    例:
        uv run python scripts/initial_index.py
        uv run python scripts/initial_index.py --vault-path ./TargetObsidianVault
    """
    try:
        # 設定を読み込む
        settings = get_settings()

        # Vaultパスを決定（絶対パスに解決）
        if vault_path is None:
            vault_path = Path(settings.obsidian_vault_path)

        # 絶対パスに解決（相対パスの場合、現在の作業ディレクトリからの相対パスとして解決）
        vault_path = vault_path.resolve()

        if not vault_path.exists():
            logger.error(f"Vaultパスが存在しません: {vault_path}")
            sys.exit(1)

        logger.info(f"Vaultパス: {vault_path}")
        logger.info(f"バッチサイズ: {batch_size}")

        # サービスを初期化
        logger.info("サービスを初期化中...")
        vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
        embedding_service = EmbeddingService()
        llm_service = LLMService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_llm_model,
        )
        content_extractor = ContentExtractor()

        # タグ生成を無効化する場合
        if skip_tags:
            settings.enable_auto_tagging = False

        indexing_service = IndexingService(
            vector_db_service=vector_db_service,
            embedding_service=embedding_service,
            llm_service=llm_service,
            content_extractor=content_extractor,
            settings=settings,
        )

        # 全Markdownファイルを取得
        logger.info("Markdownファイルを検索中...")
        md_files = list(vault_path.rglob("*.md"))

        if not md_files:
            logger.warning("Markdownファイルが見つかりませんでした")
            sys.exit(0)

        logger.info(f"見つかったファイル数: {len(md_files)}")

        # バッチ処理で記事を処理
        logger.info("記事を処理中...")
        articles = []
        with tqdm(total=len(md_files), desc="処理中") as pbar:
            for i in range(0, len(md_files), batch_size):
                batch = md_files[i : i + batch_size]
                batch_articles = indexing_service.process_batch(
                    batch, batch_size=batch_size
                )
                articles.extend(batch_articles)
                pbar.update(len(batch))

        if not articles:
            logger.warning("処理された記事がありません")
            sys.exit(0)

        logger.info(f"処理された記事数: {len(articles)}")

        # ベクトルDBに格納
        logger.info("ベクトルDBに格納中...")
        success_count = indexing_service.index_articles(articles)

        logger.info(f"初期インデックス作成完了: {success_count}/{len(articles)}件を格納")

        # 最新コミットを保存（Gitリポジトリがある場合）
        try:
            from app.core.git_sync import GitChangeDetector

            detector = GitChangeDetector(vault_path)
            latest_commit = detector.get_latest_commit_id()
            indexing_service.save_last_commit(latest_commit)
            logger.info(f"最新コミットを保存: {latest_commit}")
        except Exception as exc:
            logger.warning(f"コミット情報の保存に失敗しました（無視）: {exc}")

        click.echo(f"✅ 初期インデックス作成が完了しました: {success_count}件")

    except KeyboardInterrupt:
        logger.info("処理が中断されました")
        sys.exit(1)
    except Exception as exc:
        logger.error(f"エラーが発生しました: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

