"""Automatic pipeline - Raw → Summary → Atomic の全自動化.

00_Raw 内の全ファイルを自動的に処理し、Summary と Atomic ノートを生成する。
"""

import logging
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import Settings
from app.core.summarizer import Summarizer
from app.core.atomic_splitter import AtomicSplitter
from app.core.daily_note_linker import DailyNoteLinker
from app.services.llm_service import LLMService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """自動パイプラインのメイン処理."""
    try:
        logger.info("=== 自動パイプライン開始 ===")

        # 設定とサービスの初期化
        settings = Settings()
        llm_service = LLMService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_llm_model,
        )

        # コアサービスの初期化
        summarizer = Summarizer(llm_service, settings)
        atomic_splitter = AtomicSplitter(llm_service, settings)
        daily_linker = DailyNoteLinker(settings)

        vault_path = Path(settings.obsidian_vault_path)
        raw_dir = vault_path / "00_Raw"

        if not raw_dir.exists():
            logger.warning(f"00_Raw ディレクトリが存在しません: {raw_dir}")
            logger.info("ディレクトリを作成します")
            raw_dir.mkdir(parents=True, exist_ok=True)
            return

        # 00_Raw 内の全 .md ファイルを取得
        raw_files = list(raw_dir.glob("*.md"))

        if not raw_files:
            logger.info("処理対象のファイルがありません")
            return

        logger.info(f"処理対象: {len(raw_files)}ファイル")

        # 統計情報
        stats = {
            "processed": 0,
            "summaries_created": 0,
            "atomic_notes_created": 0,
            "diary_links_added": 0,
            "errors": 0,
        }

        # 各ファイルを処理
        for raw_file in raw_files:
            try:
                logger.info(f"\n--- 処理開始: {raw_file.name} ---")

                # Step 1: Raw → Summary
                logger.info("Step 1: Summary 生成中...")
                summary_content = summarizer.summarize_raw_file(raw_file)

                if not summary_content:
                    logger.warning(f"Summary 生成に失敗: {raw_file.name}")
                    stats["errors"] += 1
                    continue

                summary_file = summarizer.save_summary(summary_content, raw_file)
                stats["summaries_created"] += 1
                logger.info(f"✅ Summary 保存: {summary_file.name}")

                # Step 2: Summary → Atomic
                logger.info("Step 2: Atomic ノート分解中...")
                atomic_notes = atomic_splitter.split_into_atomic_notes(summary_file)

                if not atomic_notes:
                    logger.warning(f"Atomic ノート生成に失敗: {summary_file.name}")
                    stats["errors"] += 1
                    # Summary は作成できたので、日記リンクは追加
                    daily_linker.add_to_daily_note(summary_file)
                    stats["diary_links_added"] += 1
                    continue

                atomic_files = atomic_splitter.save_atomic_notes(atomic_notes)
                stats["atomic_notes_created"] += len(atomic_files)
                logger.info(f"✅ Atomic ノート保存: {len(atomic_files)}個")

                # Step 3: 日記ファイル連携
                logger.info("Step 3: 日記ファイル連携中...")

                # Raw ファイルをリンク
                if daily_linker.add_to_daily_note(raw_file):
                    stats["diary_links_added"] += 1

                # Summary ファイルをリンク
                if daily_linker.add_to_daily_note(summary_file):
                    stats["diary_links_added"] += 1

                # 全 Atomic ファイルをリンク
                for atomic_file in atomic_files:
                    if daily_linker.add_to_daily_note(atomic_file):
                        stats["diary_links_added"] += 1

                logger.info(f"✅ 日記リンク追加: {1 + len(atomic_files)}個")

                stats["processed"] += 1
                logger.info(f"--- 処理完了: {raw_file.name} ---\n")

            except Exception as exc:
                logger.error(f"ファイル処理中にエラー: {raw_file.name} - {exc}")
                stats["errors"] += 1
                continue

        # 最終レポート
        logger.info("\n=== 自動パイプライン完了 ===")
        logger.info(f"処理ファイル数: {stats['processed']}/{len(raw_files)}")
        logger.info(f"Summary 作成: {stats['summaries_created']}個")
        logger.info(f"Atomic ノート作成: {stats['atomic_notes_created']}個")
        logger.info(f"日記リンク追加: {stats['diary_links_added']}個")

        if stats["errors"] > 0:
            logger.warning(f"エラー発生: {stats['errors']}件")

    except Exception as exc:
        logger.error(f"自動パイプラインに失敗: {exc}")
        raise


if __name__ == "__main__":
    main()
