"""Test script for all search methods in ObsidianConscierge.

This script tests all search methods to verify they are working correctly.
"""

import sys
from pathlib import Path

import click

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.search import SearchService
from app.services.embedding_service import EmbeddingService
from app.services.vector_db_service import VectorDBService


def test_semantic_search(search_service: SearchService) -> bool:
    """セマンティック検索のテスト"""
    click.echo("\n" + "=" * 60)
    click.echo("1. セマンティック検索 (Semantic Search)")
    click.echo("=" * 60)
    
    try:
        results = search_service.search(query="Pythonでデータ分析", limit=5)
        click.echo(f"✅ 成功: {len(results)}件の結果を取得")
        if results:
            click.echo(f"   最初の結果: {results[0].get('title', 'N/A')}")
        return True
    except Exception as exc:
        click.echo(f"❌ 失敗: {exc}")
        return False


def test_tag_search(search_service: SearchService) -> bool:
    """タグ検索のテスト"""
    click.echo("\n" + "=" * 60)
    click.echo("2. タグ検索 (Tag Search)")
    click.echo("=" * 60)
    
    try:
        # まず、利用可能なタグを確認するために全記事を取得
        all_articles = search_service.vector_db_service.get_all_articles()
        if not all_articles:
            click.echo("⚠️  警告: データベースに記事がありません")
            return True  # エラーではない
        
        # タグが含まれている記事を探す
        test_tags = ["python", "coding", "test", "ai", "obsidian"]
        found_tags = []
        for article in all_articles[:10]:  # 最初の10件をチェック
            tags = article.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            for tag in test_tags:
                if tag in tags and tag not in found_tags:
                    found_tags.append(tag)
                    break
        
        if not found_tags:
            click.echo("⚠️  警告: テスト用のタグが見つかりませんでした")
            click.echo("   利用可能なタグで検索を試行します...")
            # 最初の記事のタグを使用
            first_article = all_articles[0]
            tags = first_article.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            if tags:
                found_tags = [tags[0]]
        
        if found_tags:
            results = search_service.search_by_tags(tags=found_tags, limit=5)
            click.echo(f"✅ 成功: タグ '{', '.join(found_tags)}' で {len(results)}件の結果を取得")
            if results:
                click.echo(f"   最初の結果: {results[0].get('title', 'N/A')}")
        else:
            click.echo("⚠️  警告: タグ検索をスキップ（タグが見つかりません）")
        
        return True
    except Exception as exc:
        click.echo(f"❌ 失敗: {exc}")
        return False


def test_keyword_search(search_service: SearchService) -> bool:
    """キーワード検索のテスト"""
    click.echo("\n" + "=" * 60)
    click.echo("3. キーワード検索 (Keyword Search)")
    click.echo("=" * 60)
    
    try:
        results = search_service.search_by_keyword(keyword="Python", limit=5)
        click.echo(f"✅ 成功: キーワード 'Python' で {len(results)}件の結果を取得")
        if results:
            click.echo(f"   最初の結果: {results[0].get('title', 'N/A')}")
        return True
    except Exception as exc:
        click.echo(f"❌ 失敗: {exc}")
        return False


def test_date_range_search(search_service: SearchService) -> bool:
    """日付範囲検索のテスト"""
    click.echo("\n" + "=" * 60)
    click.echo("4. 日付範囲検索 (Date Range Search)")
    click.echo("=" * 60)
    
    try:
        # 2024年以降の記事を検索
        results = search_service.search_by_date_range(
            from_date="2024-01-01", to_date=None, limit=5
        )
        click.echo(f"✅ 成功: 2024-01-01以降で {len(results)}件の結果を取得")
        if results:
            click.echo(f"   最初の結果: {results[0].get('title', 'N/A')}")
            click.echo(f"   更新日: {results[0].get('modified', 'N/A')}")
        return True
    except Exception as exc:
        click.echo(f"❌ 失敗: {exc}")
        return False


def test_word_count_search(search_service: SearchService) -> bool:
    """文字数範囲検索のテスト"""
    click.echo("\n" + "=" * 60)
    click.echo("5. 文字数範囲検索 (Word Count Search)")
    click.echo("=" * 60)
    
    try:
        # 100文字以上1000文字以下の記事を検索
        results = search_service.search_by_word_count(
            min_words=100, max_words=1000, limit=5
        )
        click.echo(f"✅ 成功: 100-1000文字の範囲で {len(results)}件の結果を取得")
        if results:
            click.echo(f"   最初の結果: {results[0].get('title', 'N/A')}")
            click.echo(f"   文字数: {results[0].get('word_count', 'N/A')}")
        return True
    except Exception as exc:
        click.echo(f"❌ 失敗: {exc}")
        return False


def test_similar_documents_search(search_service: SearchService) -> bool:
    """類似ドキュメント検索のテスト"""
    click.echo("\n" + "=" * 60)
    click.echo("6. 類似ドキュメント検索 (Similar Documents Search)")
    click.echo("=" * 60)
    
    try:
        # まず、データベースから最初の記事を取得
        all_articles = search_service.vector_db_service.get_all_articles()
        if not all_articles:
            click.echo("⚠️  警告: データベースに記事がありません")
            return True  # エラーではない
        
        # 最初の記事のIDを使用
        first_article_id = all_articles[0].get("id")
        if not first_article_id:
            click.echo("⚠️  警告: 記事IDが見つかりません")
            return True
        
        results = search_service.get_similar_documents(doc_id=first_article_id, limit=5)
        click.echo(f"✅ 成功: 記事 '{first_article_id}' に類似した {len(results)}件の結果を取得")
        if results:
            click.echo(f"   最初の結果: {results[0].get('title', 'N/A')}")
            if "similarity" in results[0]:
                click.echo(f"   類似度: {results[0]['similarity']:.3f}")
        return True
    except Exception as exc:
        click.echo(f"❌ 失敗: {exc}")
        return False


def test_hybrid_search(search_service: SearchService) -> bool:
    """ハイブリッド検索のテスト"""
    click.echo("\n" + "=" * 60)
    click.echo("7. ハイブリッド検索 (Hybrid Search)")
    click.echo("=" * 60)
    
    try:
        # 複数の条件を組み合わせて検索
        results = search_service.hybrid_search(
            query="Python",
            min_words=100,
            limit=5
        )
        click.echo(f"✅ 成功: ハイブリッド検索で {len(results)}件の結果を取得")
        click.echo("   条件: クエリ='Python', 最小文字数=100")
        if results:
            click.echo(f"   最初の結果: {results[0].get('title', 'N/A')}")
        return True
    except Exception as exc:
        click.echo(f"❌ 失敗: {exc}")
        return False


@click.command()
@click.option(
    "--method",
    "-m",
    type=click.Choice([
        "all", "semantic", "tags", "keyword", "date", "wordcount", "similar", "hybrid"
    ]),
    default="all",
    help="テストする検索方法（デフォルト: all）",
)
def main(method: str) -> None:
    """
    検索機能のテストスクリプト
    
    各検索方法が正しく動作するかテストします。
    
    例:
        python scripts/test_search_methods.py
        python scripts/test_search_methods.py -m semantic
        python scripts/test_search_methods.py -m tags
    """
    click.echo("🔍 ObsidianConscierge 検索機能テスト")
    click.echo("=" * 60)
    
    # 設定を読み込む
    try:
        settings = get_settings()
    except Exception as exc:
        click.echo(f"❌ 設定の読み込みに失敗しました: {exc}")
        click.echo("   .envファイルが存在し、正しく設定されているか確認してください。")
        sys.exit(1)
    
    # サービスを初期化
    try:
        vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
        embedding_service = EmbeddingService()
        search_service = SearchService(
            vector_db_service=vector_db_service,
            embedding_service=embedding_service,
        )
    except Exception as exc:
        click.echo(f"❌ サービスの初期化に失敗しました: {exc}")
        sys.exit(1)
    
    # データベースに記事があるか確認
    try:
        all_articles = vector_db_service.get_all_articles()
        click.echo(f"📊 データベース内の記事数: {len(all_articles)}件")
        if not all_articles:
            click.echo("⚠️  警告: データベースに記事がありません。")
            click.echo("   先に 'uv run python scripts/initial_index.py' を実行してインデックスを作成してください。")
            sys.exit(1)
    except Exception as exc:
        click.echo(f"❌ データベースへのアクセスに失敗しました: {exc}")
        sys.exit(1)
    
    # テスト実行
    results: dict[str, bool] = {}
    
    if method == "all" or method == "semantic":
        results["semantic"] = test_semantic_search(search_service)
    
    if method == "all" or method == "tags":
        results["tags"] = test_tag_search(search_service)
    
    if method == "all" or method == "keyword":
        results["keyword"] = test_keyword_search(search_service)
    
    if method == "all" or method == "date":
        results["date"] = test_date_range_search(search_service)
    
    if method == "all" or method == "wordcount":
        results["wordcount"] = test_word_count_search(search_service)
    
    if method == "all" or method == "similar":
        results["similar"] = test_similar_documents_search(search_service)
    
    if method == "all" or method == "hybrid":
        results["hybrid"] = test_hybrid_search(search_service)
    
    # 結果サマリー
    click.echo("\n" + "=" * 60)
    click.echo("📊 テスト結果サマリー")
    click.echo("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        click.echo(f"  {name:15s}: {status}")
    
    click.echo(f"\n合計: {passed}/{total} テストが成功しました")
    
    if passed == total:
        click.echo("\n🎉 すべての検索機能が正常に動作しています！")
        sys.exit(0)
    else:
        click.echo(f"\n⚠️  {total - passed}個のテストが失敗しました。")
        sys.exit(1)


if __name__ == "__main__":
    main()

