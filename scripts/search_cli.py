"""CLI search tool for ObsidianConscierge."""

import sys
from pathlib import Path

import click

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.search import SearchService
from app.services.embedding_service import EmbeddingService
from app.services.vector_db_service import VectorDBService


@click.command()
@click.option(
    "--query",
    "-q",
    required=True,
    help="検索クエリ（自然文）",
)
@click.option(
    "--limit",
    "-l",
    default=5,
    help="表示する結果の最大数（デフォルト: 5）",
)
@click.option(
    "--tags",
    "-t",
    multiple=True,
    help="タグフィルタ（複数指定可能）",
)
def main(query: str, limit: int, tags: tuple[str, ...]) -> None:
    """
    ObsidianConscierge CLI検索ツール

    例:
        python scripts/search_cli.py -q "Pythonでデータ分析"
        python scripts/search_cli.py -q "テスト" -l 10 -t python -t testing
    """
    # 設定を読み込む
    settings = get_settings()

    # サービスを初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
    embedding_service = EmbeddingService()
    search_service = SearchService(
        vector_db_service=vector_db_service,
        embedding_service=embedding_service,
    )

    # 検索実行
    tag_list = list(tags) if tags else None
    results = search_service.search(query=query, limit=limit, tags=tag_list)

    # 結果を表示
    if not results:
        click.echo(f"'{query}' に一致する記事は見つかりませんでした。", err=True)
        sys.exit(1)

    click.echo(f"'{query}' の検索結果 ({len(results)}件):\n")

    for i, result in enumerate(results, 1):
        click.echo(f"{i}. {result['title']}")
        click.echo(f"   ファイル: {result['file_path']}")
        click.echo(f"   類似度: {result['similarity']:.3f}")
        if result.get("summary"):
            click.echo(f"   サマリー: {result['summary']}")
        if result.get("tags"):
            click.echo(f"   タグ: {', '.join(result['tags'])}")
        click.echo()


if __name__ == "__main__":
    main()



