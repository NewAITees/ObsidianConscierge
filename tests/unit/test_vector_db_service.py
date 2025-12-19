"""Tests for vector DB service (ChromaDB)."""

import tempfile
from pathlib import Path

from app.models.article import Article
from app.services.vector_db_service import VectorDBService


class TestVectorDBService:
    """ベクトルDBサービスのテストクラス"""

    def test_store_article_success(self) -> None:
        """記事の格納成功テスト"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorDBService(db_path=Path(tmpdir))

            article = Article(
                id="test/article.md",
                title="テスト記事",
                body="これはテスト記事です。",
                summary="テスト記事の要約",
                tags=["test", "python"],
                created=None,
                modified=None,
                file_path="test/article.md",
                body_embedding=[0.1] * 512,
                summary_embedding=[0.2] * 512,
                word_count=100,
            )

            # Act
            result = service.store(article)

            # Assert
            assert result is True

    def test_search_articles(self) -> None:
        """記事の検索テスト"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorDBService(db_path=Path(tmpdir))

            # 記事を格納
            article = Article(
                id="test/article.md",
                title="テスト記事",
                body="これはテスト記事です。",
                summary="テスト記事の要約",
                tags=["test"],
                created=None,
                modified=None,
                file_path="test/article.md",
                body_embedding=[0.1] * 512,
                summary_embedding=[0.2] * 512,
                word_count=100,
            )
            service.store(article)

            # Act: 検索
            query_embedding = [0.1] * 512
            results = service.search(query_embedding, limit=5)

            # Assert
            assert len(results) > 0
            assert results[0]["id"] == "test/article.md"

    def test_delete_article(self) -> None:
        """記事の削除テスト"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorDBService(db_path=Path(tmpdir))

            article = Article(
                id="test/article.md",
                title="テスト記事",
                body="これはテスト記事です。",
                summary="テスト記事の要約",
                tags=["test"],
                created=None,
                modified=None,
                file_path="test/article.md",
                body_embedding=[0.1] * 512,
                summary_embedding=[0.2] * 512,
                word_count=100,
            )
            service.store(article)

            # Act: 削除
            result = service.delete("test/article.md")

            # Assert
            assert result is True

            # 削除後は検索結果に含まれない
            query_embedding = [0.1] * 512
            results = service.search(query_embedding, limit=5)
            assert all(r["id"] != "test/article.md" for r in results)

    def test_update_article(self) -> None:
        """記事の更新テスト"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorDBService(db_path=Path(tmpdir))

            article = Article(
                id="test/article.md",
                title="テスト記事",
                body="これはテスト記事です。",
                summary="テスト記事の要約",
                tags=["test"],
                created=None,
                modified=None,
                file_path="test/article.md",
                body_embedding=[0.1] * 512,
                summary_embedding=[0.2] * 512,
                word_count=100,
            )
            service.store(article)

            # Act: 更新
            updated_article = Article(
                id="test/article.md",
                title="更新されたテスト記事",
                body="これは更新されたテスト記事です。",
                summary="更新された要約",
                tags=["test", "updated"],
                created=None,
                modified=None,
                file_path="test/article.md",
                body_embedding=[0.3] * 512,
                summary_embedding=[0.4] * 512,
                word_count=200,
            )
            result = service.update(updated_article)

            # Assert
            assert result is True

            # 更新後の内容を確認
            query_embedding = [0.3] * 512
            results = service.search(query_embedding, limit=5)
            assert results[0]["title"] == "更新されたテスト記事"




