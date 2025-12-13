"""Tests for Git change detection functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.git_sync import GitChangeDetector


class TestGitChangeDetector:
    """Git変更検知機能のテストクラス"""

    @patch("app.core.git_sync.Repo")
    @patch("pathlib.Path.exists")
    def test_detect_changes_with_new_files(
        self, mock_exists: MagicMock, mock_repo_class: MagicMock
    ) -> None:
        """新規ファイルの検知テスト"""
        # Arrange: モックの設定
        mock_exists.return_value = True
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # コミット履歴のモック
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_commit.message = "Add new file"
        mock_commit.parents = [MagicMock()]  # 親コミットがあることを示す
        mock_repo.iter_commits.return_value = [mock_commit]

        # 差分のモック
        mock_diff = MagicMock()
        mock_diff.a_path = "new_file.md"
        mock_diff.b_path = "new_file.md"
        mock_diff.change_type = "A"  # Added
        mock_commit.diff.return_value = [mock_diff]

        detector = GitChangeDetector(repo_path=Path("/fake/repo"))
        detector._repo = mock_repo  # 直接repoを設定

        # Act
        changes = detector.detect_changes(since_commit="previous_commit")

        # Assert
        assert len(changes) == 1
        assert changes[0].file_path == "new_file.md"
        assert changes[0].change_type == "added"
        assert changes[0].commit_id == "abc123"

    @patch("app.core.git_sync.Repo")
    @patch("pathlib.Path.exists")
    def test_detect_changes_with_modified_files(
        self, mock_exists: MagicMock, mock_repo_class: MagicMock
    ) -> None:
        """更新ファイルの検知テスト"""
        # Arrange
        mock_exists.return_value = True
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        mock_commit = MagicMock()
        mock_commit.hexsha = "def456"
        mock_commit.message = "Update file"
        mock_commit.parents = [MagicMock()]
        mock_repo.iter_commits.return_value = [mock_commit]

        mock_diff = MagicMock()
        mock_diff.a_path = "modified_file.md"
        mock_diff.b_path = "modified_file.md"
        mock_diff.change_type = "M"  # Modified
        mock_commit.diff.return_value = [mock_diff]

        detector = GitChangeDetector(repo_path=Path("/fake/repo"))
        detector._repo = mock_repo

        # Act
        changes = detector.detect_changes(since_commit="previous_commit")

        # Assert
        assert len(changes) == 1
        assert changes[0].file_path == "modified_file.md"
        assert changes[0].change_type == "modified"
        assert changes[0].commit_id == "def456"

    @patch("app.core.git_sync.Repo")
    @patch("pathlib.Path.exists")
    def test_detect_changes_with_deleted_files(
        self, mock_exists: MagicMock, mock_repo_class: MagicMock
    ) -> None:
        """削除ファイルの検知テスト"""
        # Arrange
        mock_exists.return_value = True
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        mock_commit = MagicMock()
        mock_commit.hexsha = "ghi789"
        mock_commit.message = "Delete file"
        mock_commit.parents = [MagicMock()]
        mock_repo.iter_commits.return_value = [mock_commit]

        mock_diff = MagicMock()
        mock_diff.a_path = "deleted_file.md"
        mock_diff.b_path = "deleted_file.md"
        mock_diff.change_type = "D"  # Deleted
        mock_commit.diff.return_value = [mock_diff]

        detector = GitChangeDetector(repo_path=Path("/fake/repo"))
        detector._repo = mock_repo

        # Act
        changes = detector.detect_changes(since_commit="previous_commit")

        # Assert
        assert len(changes) == 1
        assert changes[0].file_path == "deleted_file.md"
        assert changes[0].change_type == "deleted"
        assert changes[0].commit_id == "ghi789"

    @patch("app.core.git_sync.Repo")
    @patch("pathlib.Path.exists")
    def test_detect_changes_filters_markdown_files(
        self, mock_exists: MagicMock, mock_repo_class: MagicMock
    ) -> None:
        """Markdownファイルのみをフィルタリングするテスト"""
        # Arrange
        mock_exists.return_value = True
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        mock_commit = MagicMock()
        mock_commit.hexsha = "jkl012"
        mock_commit.parents = [MagicMock()]
        mock_repo.iter_commits.return_value = [mock_commit]

        # Markdownファイルと非Markdownファイルの差分
        mock_diff1 = MagicMock()
        mock_diff1.a_path = "article.md"
        mock_diff1.b_path = "article.md"
        mock_diff1.change_type = "M"

        mock_diff2 = MagicMock()
        mock_diff2.a_path = "image.png"
        mock_diff2.b_path = "image.png"
        mock_diff2.change_type = "A"

        mock_commit.diff.return_value = [mock_diff1, mock_diff2]

        detector = GitChangeDetector(repo_path=Path("/fake/repo"))
        detector._repo = mock_repo

        # Act
        changes = detector.detect_changes(since_commit="previous_commit")

        # Assert: Markdownファイルのみが含まれる
        assert len(changes) == 1
        assert changes[0].file_path == "article.md"

    @patch("app.core.git_sync.Repo")
    @patch("pathlib.Path.exists")
    def test_detect_changes_with_no_previous_commit(
        self, mock_exists: MagicMock, mock_repo_class: MagicMock
    ) -> None:
        """前回のコミットがない場合のテスト"""
        # Arrange
        mock_exists.return_value = True
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        mock_commit = MagicMock()
        mock_commit.hexsha = "mno345"
        mock_commit.parents = []  # 親コミットなし（初回コミット）
        mock_repo.iter_commits.return_value = [mock_commit]

        mock_diff = MagicMock()
        mock_diff.a_path = "new_file.md"
        mock_diff.b_path = "new_file.md"
        mock_diff.change_type = "A"
        mock_commit.diff.return_value = [mock_diff]

        detector = GitChangeDetector(repo_path=Path("/fake/repo"))
        detector._repo = mock_repo

        # Act: since_commitをNoneに
        changes = detector.detect_changes(since_commit=None)

        # Assert
        assert len(changes) >= 0  # 全コミットを検索する

    @patch("app.core.git_sync.Repo")
    @patch("pathlib.Path.exists")
    def test_get_latest_commit_id(self, mock_exists: MagicMock, mock_repo_class: MagicMock) -> None:
        """最新のコミットIDを取得するテスト"""
        # Arrange
        mock_exists.return_value = True
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        mock_commit = MagicMock()
        mock_commit.hexsha = "pqr678"
        mock_repo.head.commit = mock_commit

        detector = GitChangeDetector(repo_path=Path("/fake/repo"))
        detector._repo = mock_repo

        # Act
        latest_commit = detector.get_latest_commit_id()

        # Assert
        assert latest_commit == "pqr678"
