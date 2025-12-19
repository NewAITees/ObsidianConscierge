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


@click.group()
def cli() -> None:
    """ObsidianConscierge CLI検索ツール"""
    pass


@cli.command()
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
def semantic(query: str, limit: int, tags: tuple[str, ...]) -> None:
    """
    セマンティック検索（自然言語ベクトル検索）

    例:
        python scripts/search_cli.py semantic -q "Pythonでデータ分析"
        python scripts/search_cli.py semantic -q "テスト" -l 10 -t python -t testing
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
    _display_results(results, query, "セマンティック検索")


@cli.command()
@click.option(
    "--tags",
    "-t",
    multiple=True,
    required=True,
    help="検索対象のタグ（複数指定可能）",
)
@click.option(
    "--limit",
    "-l",
    default=20,
    help="表示する結果の最大数（デフォルト: 20）",
)
def tags(tags: tuple[str, ...], limit: int) -> None:
    """
    タグ検索

    例:
        python scripts/search_cli.py tags -t python
        python scripts/search_cli.py tags -t python -t fastapi -l 10
    """
    # 設定を読み込む
    settings = get_settings()

    # サービスを初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
    search_service = SearchService(vector_db_service=vector_db_service)

    # 検索実行
    tag_list = list(tags)
    results = search_service.search_by_tags(tags=tag_list, limit=limit)

    # 結果を表示
    query_str = f"タグ: {', '.join(tag_list)}"
    _display_results(results, query_str, "タグ検索")


@cli.command()
@click.option(
    "--keyword",
    "-k",
    required=True,
    help="検索キーワード",
)
@click.option(
    "--limit",
    "-l",
    default=20,
    help="表示する結果の最大数（デフォルト: 20）",
)
def keyword(keyword: str, limit: int) -> None:
    """
    キーワード検索（タイトルまたは本文に含まれるもの）

    例:
        python scripts/search_cli.py keyword -k "ObsidianConscierge"
        python scripts/search_cli.py keyword -k "Python" -l 10
    """
    # 設定を読み込む
    settings = get_settings()

    # サービスを初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
    search_service = SearchService(vector_db_service=vector_db_service)

    # 検索実行
    results = search_service.search_by_keyword(keyword=keyword, limit=limit)

    # 結果を表示
    _display_results(results, keyword, "キーワード検索")


@cli.command()
@click.option(
    "--from-date",
    "--from",
    help="開始日（ISO形式、例: 2024-01-01）",
)
@click.option(
    "--to-date",
    "--to",
    help="終了日（ISO形式、例: 2024-12-31）",
)
@click.option(
    "--limit",
    "-l",
    default=20,
    help="表示する結果の最大数（デフォルト: 20）",
)
def date(from_date: str | None, to_date: str | None, limit: int) -> None:
    """
    日付範囲検索

    例:
        python scripts/search_cli.py date --from 2024-01-01 --to 2024-12-31
        python scripts/search_cli.py date --from 2024-01-01 -l 10
    """
    # 設定を読み込む
    settings = get_settings()

    # サービスを初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
    search_service = SearchService(vector_db_service=vector_db_service)

    # 検索実行
    results = search_service.search_by_date_range(
        from_date=from_date, to_date=to_date, limit=limit
    )

    # 結果を表示
    query_parts = []
    if from_date:
        query_parts.append(f"{from_date}以降")
    if to_date:
        query_parts.append(f"{to_date}以前")
    query_str = " ".join(query_parts) if query_parts else "全期間"
    _display_results(results, query_str, "日付範囲検索")


@cli.command()
@click.option(
    "--min-words",
    "--min",
    type=int,
    help="最小文字数",
)
@click.option(
    "--max-words",
    "--max",
    type=int,
    help="最大文字数",
)
@click.option(
    "--limit",
    "-l",
    default=20,
    help="表示する結果の最大数（デフォルト: 20）",
)
def wordcount(min_words: int | None, max_words: int | None, limit: int) -> None:
    """
    文字数範囲検索

    例:
        python scripts/search_cli.py wordcount --min 100 --max 1000
        python scripts/search_cli.py wordcount --min 500 -l 10
    """
    # 設定を読み込む
    settings = get_settings()

    # サービスを初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
    search_service = SearchService(vector_db_service=vector_db_service)

    # 検索実行
    results = search_service.search_by_word_count(
        min_words=min_words, max_words=max_words, limit=limit
    )

    # 結果を表示
    query_parts = []
    if min_words:
        query_parts.append(f"{min_words}文字以上")
    if max_words:
        query_parts.append(f"{max_words}文字以下")
    query_str = " ".join(query_parts) if query_parts else "全範囲"
    _display_results(results, query_str, "文字数範囲検索")


@cli.command()
@click.option(
    "--doc-id",
    "--id",
    required=True,
    help="基準となるドキュメントのID（ファイルパス）",
)
@click.option(
    "--limit",
    "-l",
    default=5,
    help="表示する結果の最大数（デフォルト: 5）",
)
def similar(doc_id: str, limit: int) -> None:
    """
    類似ドキュメント検索

    例:
        python scripts/search_cli.py similar --doc-id "path/to/article.md"
        python scripts/search_cli.py similar --id "00CreatedFiles/coeiroink.md" -l 10
    """
    # 設定を読み込む
    settings = get_settings()

    # サービスを初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
    search_service = SearchService(vector_db_service=vector_db_service)

    # 検索実行
    results = search_service.get_similar_documents(doc_id=doc_id, limit=limit)

    # 結果を表示
    _display_results(results, doc_id, "類似ドキュメント検索")


@cli.command()
@click.option(
    "--query",
    "-q",
    help="検索クエリ（自然文、オプション）",
)
@click.option(
    "--tags",
    "-t",
    multiple=True,
    help="タグフィルタ（複数指定可能）",
)
@click.option(
    "--from-date",
    "--from",
    help="開始日（ISO形式、例: 2024-01-01）",
)
@click.option(
    "--to-date",
    "--to",
    help="終了日（ISO形式、例: 2024-12-31）",
)
@click.option(
    "--min-words",
    "--min",
    type=int,
    help="最小文字数",
)
@click.option(
    "--max-words",
    "--max",
    type=int,
    help="最大文字数",
)
@click.option(
    "--limit",
    "-l",
    default=20,
    help="表示する結果の最大数（デフォルト: 20）",
)
def hybrid(
    query: str | None,
    tags: tuple[str, ...],
    from_date: str | None,
    to_date: str | None,
    min_words: int | None,
    max_words: int | None,
    limit: int,
) -> None:
    """
    ハイブリッド検索（複数の条件を組み合わせて検索）

    例:
        python scripts/search_cli.py hybrid -q "Python" -t coding --min 500
        python scripts/search_cli.py hybrid --from 2024-01-01 --to 2024-12-31 -t python
    """
    # 設定を読み込む
    settings = get_settings()

    # サービスを初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
    embedding_service = EmbeddingService() if query else None
    search_service = SearchService(
        vector_db_service=vector_db_service,
        embedding_service=embedding_service,
    )

    # 検索実行
    tag_list = list(tags) if tags else None
    results = search_service.hybrid_search(
        query=query,
        tags=tag_list,
        from_date=from_date,
        to_date=to_date,
        min_words=min_words,
        max_words=max_words,
        limit=limit,
    )

    # 結果を表示
    query_parts = []
    if query:
        query_parts.append(f"クエリ: {query}")
    if tags:
        query_parts.append(f"タグ: {', '.join(tags)}")
    if from_date:
        query_parts.append(f"{from_date}以降")
    if to_date:
        query_parts.append(f"{to_date}以前")
    if min_words:
        query_parts.append(f"{min_words}文字以上")
    if max_words:
        query_parts.append(f"{max_words}文字以下")
    query_str = " / ".join(query_parts) if query_parts else "全条件"
    _display_results(results, query_str, "ハイブリッド検索")


def _display_results(
    results: list[dict],
    query_str: str,
    search_type: str,
) -> None:
    """検索結果を表示する"""
    if not results:
        click.echo(f"'{query_str}' に一致する記事は見つかりませんでした。", err=True)
        sys.exit(1)

    click.echo(f"{search_type}結果 ({len(results)}件):")
    click.echo(f"検索条件: {query_str}\n")

    for i, result in enumerate(results, 1):
        click.echo(f"{i}. {result['title']}")
        click.echo(f"   ファイル: {result['file_path']}")

        if "similarity" in result:
            click.echo(f"   類似度: {result['similarity']:.3f}")

        if result.get("summary"):
            click.echo(f"   サマリー: {result['summary']}")

        if result.get("tags"):
            click.echo(f"   タグ: {', '.join(result['tags'])}")

        if result.get("word_count"):
            click.echo(f"   文字数: {result['word_count']}")

        if result.get("modified"):
            click.echo(f"   更新日: {result['modified']}")

        click.echo()


if __name__ == "__main__":
    cli()
