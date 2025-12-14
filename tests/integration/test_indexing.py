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
            test_file = vault_path / "test.md"
            test_file.write_text("# Test")
            repo.index.add([str(test_file)])
            repo.index.commit("Initial commit")

            mock_settings.obsidian_vault_path = vault_path

            with patch("app.core.indexing.get_settings", return_value=mock_settings):
                service = IndexingService(
                    vector_db_service=MagicMock(),
                    embedding_service=MagicMock(),
                    llm_service=MagicMock(),
                    content_extractor=MagicMock(),
                    settings=mock_settings,
                )

                # Act
                changes = service.detect_changes()

                # Assert
                assert isinstance(changes, list)

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

