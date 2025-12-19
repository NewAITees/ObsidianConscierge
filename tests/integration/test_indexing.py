"""Integration tests for indexing pipeline."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.indexing import IndexingService
from app.models.article import Article, FileChange


@pytest.fixture
def mock_settings() -> Settings:
    """モック設定を返す"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        return Settings(
            github_token="test_token",
            obsidian_vault_name="test_vault",
            chroma_db_path=Path(tmpdir) / "chroma_db",
            obsidian_vault_path=Path(tmpdir) / "vault",
        )


@pytest.fixture
def mock_services() -> dict:
    """モックサービスを返す"""
    return {
        "vector_db": MagicMock(),
        "embedding": MagicMock(),
        "llm": MagicMock(),
        "content_extractor": MagicMock(),
    }


class TestIndexingService:
    """インデックスサービスのテストクラス"""

    def test_process_article_success(
        self, mock_settings: Settings, mock_services: dict
    ) -> None:
        """記事処理の成功テスト"""
        # Arrange
        import tempfile
        from app.models.article import ArticleContent

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()
            test_file = vault_path / "test.md"
            test_file.write_text("# テスト記事\n\nテスト本文")

            mock_settings.obsidian_vault_path = vault_path

            with patch("app.core.indexing.get_settings", return_value=mock_settings):
                service = IndexingService(
                    vector_db_service=mock_services["vector_db"],
                    embedding_service=mock_services["embedding"],
                    llm_service=mock_services["llm"],
                    content_extractor=mock_services["content_extractor"],
                    settings=mock_settings,
                )

                # モックの設定
                mock_services["content_extractor"].extract_content.return_value = (
                    ArticleContent(
                        title="テスト記事",
                        body="テスト本文",
                        metadata={},
                        file_path=str(test_file),
                        word_count=10,
                    )
                )
                mock_services["llm"].generate_summary.return_value = "テストサマリー"
                mock_services["llm"].generate_tags.return_value = ["test", "python"]
                mock_services["embedding"].embed.side_effect = [
                    [0.1] * 512,  # body embedding
                    [0.2] * 512,  # summary embedding
                ]

                # Act
                result = service.process_article(test_file)

                # Assert
                assert result is not None
                assert result.title == "テスト記事"
                # storeはprocess_articleでは呼ばれない（index_articlesで呼ばれる）

    def test_detect_changes(self, mock_settings: Settings) -> None:
        """変更検知のテスト"""
        # Arrange
        import tempfile
        from git import Repo

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            # Gitリポジトリを初期化
            repo = Repo.init(vault_path)
            
            # 初期コミットを作成（READMEファイルを追加）
            readme_file = vault_path / "README.md"
            readme_file.write_text("# Vault")
            repo.index.add([str(readme_file)])
            repo.index.commit("Initial commit")
            initial_commit = repo.head.commit.hexsha
            
            # テストファイルを追加してコミット
            test_file = vault_path / "test.md"
            test_file.write_text("# Test")
            repo.index.add([str(test_file)])
            repo.index.commit("Add test file")
            
            # 2つ目のファイルを追加してコミット
            test_file2 = vault_path / "test2.md"
            test_file2.write_text("# Test 2")
            repo.index.add([str(test_file2)])
            repo.index.commit("Add test file 2")

            mock_settings.obsidian_vault_path = vault_path

            with patch("app.core.indexing.get_settings", return_value=mock_settings):
                service = IndexingService(
                    vector_db_service=MagicMock(),
                    embedding_service=MagicMock(),
                    llm_service=MagicMock(),
                    content_extractor=MagicMock(),
                    settings=mock_settings,
                )

                # Act: 初期コミット以降の変更を検知
                changes = service.detect_changes(since_commit=initial_commit)

                # Assert
                assert isinstance(changes, list)
                # 2つのファイルが追加されているはず
                assert len(changes) >= 2

    def test_save_and_load_last_commit(
        self, mock_settings: Settings, mock_services: dict
    ) -> None:
        """前回コミットの保存/読み込みテスト"""
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            with patch("app.core.indexing.get_settings", return_value=mock_settings), patch(
                "app.core.indexing.Path", return_value=data_dir / "last_commit.txt"
            ):
                service = IndexingService(
                    vector_db_service=mock_services["vector_db"],
                    embedding_service=mock_services["embedding"],
                    llm_service=mock_services["llm"],
                    content_extractor=mock_services["content_extractor"],
                )

                # Act
                commit_id = "abc123"
                service.save_last_commit(commit_id)
                loaded_commit = service.load_last_commit()

                # Assert
                assert loaded_commit == commit_id

    def test_end_to_end_indexing_flow(
        self, mock_settings: Settings, mock_services: dict
    ) -> None:
        """エンドツーエンドのインデックスパイプラインフローのテスト"""
        # Arrange
        import tempfile
        from app.models.article import ArticleContent

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()
            test_file = vault_path / "test.md"
            test_file.write_text("# テスト記事\n\nこれはテスト記事の本文です。")

            mock_settings.obsidian_vault_path = vault_path

            # モックの設定
            mock_services["content_extractor"].extract_content.return_value = (
                ArticleContent(
                    title="テスト記事",
                    body="これはテスト記事の本文です。",
                    metadata={},
                    file_path=str(test_file),
                    word_count=20,
                )
            )
            mock_services["llm"].generate_summary.return_value = "テスト記事の要約"
            mock_services["llm"].generate_tags.return_value = ["test", "python"]
            mock_services["embedding"].embed.side_effect = [
                [0.1] * 512,  # body embedding
                [0.2] * 512,  # summary embedding
            ]
            mock_services["vector_db"].store.return_value = True

            with patch("app.core.indexing.get_settings", return_value=mock_settings):
                service = IndexingService(
                    vector_db_service=mock_services["vector_db"],
                    embedding_service=mock_services["embedding"],
                    llm_service=mock_services["llm"],
                    content_extractor=mock_services["content_extractor"],
                    settings=mock_settings,
                )

                # Act: 記事を処理してインデックスに追加
                article = service.process_article(test_file)
                assert article is not None

                # 記事をインデックスに追加
                success_count = service.index_articles([article])

                # Assert
                assert success_count == 1
                # モックが正しく呼ばれたことを確認
                mock_services["content_extractor"].extract_content.assert_called_once()
                mock_services["llm"].generate_summary.assert_called_once()
                mock_services["llm"].generate_tags.assert_called_once()
                assert mock_services["embedding"].embed.call_count == 2  # body + summary
                mock_services["vector_db"].store.assert_called_once()

    def test_batch_processing(
        self, mock_settings: Settings, mock_services: dict
    ) -> None:
        """バッチ処理のテスト"""
        # Arrange
        import tempfile
        from app.models.article import ArticleContent

        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir) / "vault"
            vault_path.mkdir()

            # 複数のテストファイルを作成
            test_files = []
            for i in range(3):
                test_file = vault_path / f"test{i}.md"
                test_file.write_text(f"# テスト記事{i}\n\n本文{i}")
                test_files.append(test_file)

            mock_settings.obsidian_vault_path = vault_path

            # モックの設定（複数回呼ばれることを想定）
            def extract_content_side_effect(file_path: Path) -> ArticleContent:
                return ArticleContent(
                    title=f"テスト記事{test_files.index(file_path)}",
                    body=f"本文{test_files.index(file_path)}",
                    metadata={},
                    file_path=str(file_path),
                    word_count=10,
                )

            mock_services["content_extractor"].extract_content.side_effect = (
                extract_content_side_effect
            )
            mock_services["llm"].generate_summary.return_value = "テストサマリー"
            mock_services["llm"].generate_tags.return_value = ["test"]
            mock_services["embedding"].embed.return_value = [0.1] * 512
            mock_services["vector_db"].store.return_value = True

            with patch("app.core.indexing.get_settings", return_value=mock_settings):
                service = IndexingService(
                    vector_db_service=mock_services["vector_db"],
                    embedding_service=mock_services["embedding"],
                    llm_service=mock_services["llm"],
                    content_extractor=mock_services["content_extractor"],
                    settings=mock_settings,
                )

                # Act: バッチ処理
                articles = service.process_batch(test_files, batch_size=2)

                # Assert
                assert len(articles) == 3
                assert mock_services["content_extractor"].extract_content.call_count == 3
                assert mock_services["llm"].generate_summary.call_count == 3

    def test_delete_articles(self, mock_settings: Settings, mock_services: dict) -> None:
        """記事削除のテスト"""
        # Arrange
        mock_services["vector_db"].delete.return_value = True

        with patch("app.core.indexing.get_settings", return_value=mock_settings):
            service = IndexingService(
                vector_db_service=mock_services["vector_db"],
                embedding_service=mock_services["embedding"],
                llm_service=mock_services["llm"],
                content_extractor=mock_services["content_extractor"],
                settings=mock_settings,
            )

            # Act
            file_paths = ["test/article1.md", "test/article2.md"]
            success_count = service.delete_articles(file_paths)

            # Assert
            assert success_count == 2
            assert mock_services["vector_db"].delete.call_count == 2

