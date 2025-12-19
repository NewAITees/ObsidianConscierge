"""ChromaDB statistics viewer for ObsidianConscierge."""

import sys
from pathlib import Path

import click

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.services.vector_db_service import VectorDBService


@click.command()
@click.option(
    "--sample-size",
    "-s",
    default=5,
    help="表示するサンプルデータの件数（デフォルト: 5）",
)
@click.option(
    "--show-samples/--no-samples",
    default=True,
    help="サンプルデータを表示するかどうか",
)
def main(sample_size: int, show_samples: bool) -> None:
    """
    ChromaDB統計情報表示ツール

    例:
        python scripts/db_stats.py
        python scripts/db_stats.py -s 10
        python scripts/db_stats.py --no-samples
    """
    # 設定を読み込む
    settings = get_settings()

    # サービスを初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())

    click.echo("=" * 60)
    click.echo("ChromaDB 統計情報")
    click.echo("=" * 60)
    click.echo()

    # コレクション情報を取得
    try:
        collection = vector_db_service.collection
        count = collection.count()

        click.echo(f"📊 総ドキュメント数: {count:,}件")
        click.echo(f"📁 データベースパス: {settings.chroma_db_path}")
        click.echo(f"📦 コレクション名: {collection.name}")
        click.echo()

        # TargetObsidianVaultのマークダウンファイル数をカウント
        vault_path = settings.obsidian_vault_path
        if vault_path.exists():
            md_files = list(vault_path.rglob("*.md"))
            click.echo(f"📝 Vault内のマークダウンファイル数: {len(md_files):,}件")
            click.echo(f"   Vaultパス: {vault_path}")

            # 比較
            if count == len(md_files):
                click.echo("✅ すべてのファイルがインデックス化されています")
            elif count < len(md_files):
                missing = len(md_files) - count
                click.echo(
                    f"⚠️  {missing}件のファイルがインデックス化されていません"
                )
            else:
                extra = count - len(md_files)
                click.echo(f"⚠️  {extra}件の余分なドキュメントがDBに存在します")
        else:
            click.echo(f"⚠️  Vaultパスが存在しません: {vault_path}")

        click.echo()

        # サンプルデータを表示
        if show_samples and count > 0:
            click.echo("=" * 60)
            click.echo(f"サンプルデータ（最初の{sample_size}件）")
            click.echo("=" * 60)
            click.echo()

            # 最初のN件を取得
            results = collection.get(
                limit=sample_size,
                include=["metadatas"],
            )

            if results["ids"]:
                for i, doc_id in enumerate(results["ids"], 1):
                    metadata = results["metadatas"][i - 1] if results["metadatas"] else {}
                    title = metadata.get("title", "（タイトルなし）")
                    file_path = metadata.get("file_path", "")
                    tags = metadata.get("tags", "")
                    word_count = metadata.get("word_count", 0)
                    summary = metadata.get("summary", "")

                    click.echo(f"{i}. {title}")
                    click.echo(f"   ID: {doc_id}")
                    click.echo(f"   ファイル: {file_path}")
                    click.echo(f"   文字数: {word_count}")
                    if tags:
                        click.echo(f"   タグ: {tags}")
                    if summary:
                        # サマリーは最初の100文字のみ表示
                        summary_short = (
                            summary[:100] + "..." if len(summary) > 100 else summary
                        )
                        click.echo(f"   サマリー: {summary_short}")
                    click.echo()

    except Exception as e:
        click.echo(f"❌ エラーが発生しました: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
