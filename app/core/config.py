"""Configuration management using Pydantic Settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # GitHub設定
    github_repo_name: str | None = Field(
        default=None, description="GitHubリポジトリ名（owner/repo形式）"
    )
    github_repo_url: str | None = Field(
        default=None, description="GitHubリポジトリURL（repo_name未設定時に使用）"
    )
    github_token: str = Field(..., description="GitHubトークン")

    # Obsidian設定
    obsidian_vault_name: str = Field(..., description="Obsidian Vault名")
    obsidian_vault_path: Path = Field(
        default=Path("./TargetObsidianVault"),
        description="Obsidian Vaultのローカルパス",
    )

    # Ollama設定
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="OllamaサーバーのベースURL",
    )
    ollama_llm_model: str = Field(
        default="gpt-oss:20b",
        description="Ollama LLMモデル名（gpt-oss:20b, llama3.1:8b, qwen3:14b等）",
    )
    ollama_keep_alive: int = Field(
        default=60,
        ge=-1,
        description="Ollama モデルのGPU保持時間（秒）。0=即座にアンロード、-1=常駐",
    )

    # ベクトルDB設定
    chroma_db_path: Path = Field(
        default=Path("./data/chroma_db"),
        description="ChromaDBのデータ保存パス",
    )

    # 分析設定
    duplicate_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="重複検知の閾値（0.0-1.0）",
    )
    cluster_count: str = Field(
        default="auto",
        description="クラスター数（auto or 数値）",
    )
    enable_auto_tagging: bool = Field(
        default=True,
        description="タグ自動生成のON/OFF",
    )
    pipeline_folders: list[str] = Field(
        default_factory=lambda: [
            "00_Raw",
            "01_Summary",
            "02_Atomic",
            "03_MOC",
        ],
        description="アトミック運用のパイプライン用フォルダ（カテゴリ判定から除外）",
    )

    # ログ設定
    log_level: str = Field(
        default="INFO",
        description="ログレベル（DEBUG, INFO, WARNING, ERROR）",
    )
    log_file: Path = Field(
        default=Path("./logs/obsidian_conscierge.log"),
        description="ログファイルのパス",
    )

    # Web UI設定
    web_host: str = Field(
        default="0.0.0.0",
        description="Webサーバーのホスト",
    )
    web_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Webサーバーのポート",
    )

    # Git同期設定
    git_auto_sync_enabled: bool = Field(
        default=True,
        description="Git自動同期の有効/無効",
    )
    git_sync_interval_minutes: int = Field(
        default=30,
        ge=1,
        description="Git同期間隔（分）",
    )
    git_auto_push_enabled: bool = Field(
        default=False,
        description="Git同期時の自動コミット・プッシュの有効/無効",
    )
    git_auto_push_allowed_extensions: list[str] = Field(
        default_factory=lambda: [".md"],
        description="自動コミット時に許可する新規ファイル拡張子（例: .md,.canvas）",
    )

    # ドキュメント自動編集設定
    excluded_folders: list[str] = Field(
        default_factory=lambda: [
            "01DIARY",           # 日記フォルダ
            "02TEMPLATES",       # テンプレートフォルダ
            "06MOC",            # Map of Contents
            "10KANBAN",         # カンバンボード
            "11MEDIA",          # メディアファイル
            "Excalidraw",       # 図形ファイル
            "Maybe",            # 一時メモ
            "Omnivore",         # Omnivoreインポート
            "model_cache",      # モデルキャッシュ
            "PythonScripts",    # Pythonスクリプト
            "github",           # GitHub関連
            ".chroma_db",       # ChromaDBデータ
            ".claude",          # Claude設定
            ".devcontainer",    # DevContainer設定
            ".smtcmp_json_db",  # SMTCMPデータベース
            ".smtcmp_vector_db",# SMTCMPベクトルDB
        ],
        description="自動編集対象外のフォルダリスト",
    )
    exclude_root_files: bool = Field(
        default=True,
        description="ルートディレクトリのファイルを編集対象外にする",
    )
    enable_auto_link_insert: bool = Field(
        default=True,
        description="類似リンク自動挿入の有効/無効",
    )
    enable_auto_tag_insert: bool = Field(
        default=True,
        description="タグ自動挿入の有効/無効",
    )
    min_similarity_for_link: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="リンク挿入の最小類似度（0.0-1.0）",
    )
    max_similar_links: int = Field(
        default=3,
        ge=1,
        le=10,
        description="挿入する類似リンクの最大数",
    )

    def get_chroma_db_path(self) -> Path:
        """ChromaDBのパスを取得（存在しない場合は作成）"""
        path = Path(self.chroma_db_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_log_file_path(self) -> Path:
        """ログファイルのパスを取得（存在しない場合はディレクトリを作成）"""
        log_file = Path(self.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        return log_file

    def resolve_github_repo_url(self) -> str:
        """
        GitHubリポジトリURLを解決する（名前指定を優先）

        Returns:
            str: GitHubリポジトリURL（https://github.com/owner/repo.git形式）

        Raises:
            ValueError: 無効な形式または設定が不足している場合
        """
        # github_repo_nameが設定されている場合（短縮形式: owner/repo）
        if self.github_repo_name:
            # 既にURL形式の場合はそのまま返す
            if self.github_repo_name.startswith("http://") or self.github_repo_name.startswith(
                "https://"
            ):
                return self.github_repo_name
            # 短縮形式（owner/repo）をURLに変換
            if "/" in self.github_repo_name and len(self.github_repo_name.split("/")) == 2:
                return f"https://github.com/{self.github_repo_name}.git"
            # 無効な形式
            msg = f"Invalid github_repo_name format: {self.github_repo_name}. Expected 'owner/repo' or full URL."
            raise ValueError(msg)

        # github_repo_urlが設定されている場合
        if self.github_repo_url:
            # 既にURL形式の場合はそのまま返す
            if self.github_repo_url.startswith("http://") or self.github_repo_url.startswith(
                "https://"
            ):
                # .gitが末尾にない場合は追加
                if not self.github_repo_url.endswith(".git"):
                    return f"{self.github_repo_url}.git"
                return self.github_repo_url
            # 短縮形式（owner/repo）をURLに変換
            if "/" in self.github_repo_url and len(self.github_repo_url.split("/")) == 2:
                return f"https://github.com/{self.github_repo_url}.git"
            # 無効な形式
            msg = f"Invalid github_repo_url format: {self.github_repo_url}. Expected 'owner/repo' or full URL."
            raise ValueError(msg)

        # どちらも設定されていない場合
        msg = "Either github_repo_name or github_repo_url must be set"
        raise ValueError(msg)


# グローバル設定インスタンス（後で初期化）
settings: Settings | None = None


def get_settings() -> Settings:
    """設定インスタンスを取得"""
    global settings
    if settings is None:
        settings = Settings()
    return settings
