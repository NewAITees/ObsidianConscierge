"""Git change detection functionality."""

from pathlib import Path

from git import Repo

from app.models.article import FileChange


class GitChangeDetector:
    """Gitリポジトリの変更を検知するクラス"""

    def __init__(self, repo_path: Path) -> None:
        """
        GitChangeDetectorを初期化

        Args:
            repo_path: Gitリポジトリのパス
        """
        self.repo_path = repo_path
        self._repo: Repo | None = None

    @property
    def repo(self) -> Repo:
        """
        Gitリポジトリを取得（遅延初期化）

        Returns:
            Repo: GitPythonのRepoオブジェクト

        Raises:
            ValueError: リポジトリが存在しない場合
        """
        if self._repo is None:
            if not self.repo_path.exists():
                raise ValueError(f"Repository not found: {self.repo_path}")
            self._repo = Repo(self.repo_path)
        return self._repo

    def detect_changes(
        self,
        since_commit: str | None = None,
    ) -> list[FileChange]:
        """
        指定されたコミット以降の変更を検知する

        Args:
            since_commit: 検知開始コミットID（Noneの場合は全コミット）

        Returns:
            List[FileChange]: 検出されたファイル変更のリスト
        """
        changes: list[FileChange] = []

        # コミットを取得
        if since_commit:
            # 指定されたコミット以降を検索
            commits = self.repo.iter_commits(f"{since_commit}..HEAD")
        else:
            # 全コミットを検索
            commits = self.repo.iter_commits()

        for commit in commits:
            # 親コミットとの差分を取得
            if commit.parents:
                # 親コミットがある場合
                parent = commit.parents[0]
                diffs = commit.diff(parent)
            else:
                # 初回コミットの場合
                diffs = commit.diff(None)

            for diff in diffs:
                # Markdownファイルのみを対象
                file_path = diff.b_path if diff.b_path else diff.a_path
                if not file_path.endswith(".md"):
                    continue

                # 変更タイプをマッピング
                change_type_map = {
                    "A": "added",  # Added
                    "M": "modified",  # Modified
                    "D": "deleted",  # Deleted
                    "R": "modified",  # Renamed (modifiedとして扱う)
                }

                change_type = change_type_map.get(diff.change_type, "modified")

                changes.append(
                    FileChange(
                        file_path=file_path,
                        change_type=change_type,
                        commit_id=commit.hexsha,
                    )
                )

        return changes

    def get_latest_commit_id(self) -> str:
        """
        最新のコミットIDを取得する

        Returns:
            str: 最新のコミットID
        """
        return self.repo.head.commit.hexsha


