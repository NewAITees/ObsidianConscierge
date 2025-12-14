"""Smart tag inserter with exception pattern detection.

タグ自動挿入機能を提供します。
コードブロック、リンク、既存タグなどの例外パターンを適切に回避します。
"""

import re
from pathlib import Path
from typing import NamedTuple

from app.core.config import Settings, get_settings
from app.core.document_updater import DocumentUpdater


class TextPosition(NamedTuple):
    """テキスト位置の情報"""

    start: int
    end: int
    context: str
    priority: int  # 優先度（低い値ほど高優先）


class TagInserter:
    """タグ自動挿入サービス"""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        TagInserterを初期化

        Args:
            settings: 設定（Noneの場合はget_settings()で取得）
        """
        self.settings = settings or get_settings()
        self.vault_path = Path(self.settings.obsidian_vault_path).resolve()

    def find_exception_positions(self, content: str) -> list[TextPosition]:
        """
        例外パターンの位置を検出

        以下のパターンを検出し、タグ化を回避します：
        1. YAMLフロントマター
        2. コードブロック
        3. インラインコード
        4. Obsidianリンク
        5. Markdownリンク
        6. 画像リンク
        7. URL
        8. 既存のタグ
        9. HTMLコメント
        10. 見出し

        Args:
            content: ドキュメント全文

        Returns:
            list[TextPosition]: 例外位置のリスト
        """
        positions = []

        # 1. YAMLフロントマター（最高優先度）
        yaml_match = re.search(r"^---\s*\n([\s\S]*?)\n---\s*\n", content)
        if yaml_match:
            positions.append(
                TextPosition(
                    yaml_match.start(), yaml_match.end(), "yaml_frontmatter", 1
                )
            )

        # 2. コードブロック（高優先度）
        for match in re.finditer(r"```[\s\S]*?```", content):
            positions.append(
                TextPosition(match.start(), match.end(), "code_block", 2)
            )

        # 3. インラインコード
        for match in re.finditer(r"`[^`\n]+`", content):
            positions.append(
                TextPosition(match.start(), match.end(), "inline_code", 2)
            )

        # 4. Obsidianリンク系
        # 基本リンク [[リンク名]]
        for match in re.finditer(r"\[\[[^\]]+\]\]", content):
            positions.append(
                TextPosition(match.start(), match.end(), "obsidian_link", 3)
            )

        # エンベッド ![[ファイル名]]
        for match in re.finditer(r"!\[\[[^\]]+\]\]", content):
            positions.append(
                TextPosition(match.start(), match.end(), "obsidian_embed", 3)
            )

        # 5. Markdownリンク [テキスト](URL)
        for match in re.finditer(r"\[([^\]]+)\]\([^\)]+\)", content):
            positions.append(
                TextPosition(match.start(), match.end(), "markdown_link", 3)
            )

        # 6. 画像リンク ![alt](URL)
        for match in re.finditer(r"!\[[^\]]*\]\([^\)]+\)", content):
            positions.append(
                TextPosition(match.start(), match.end(), "image_link", 3)
            )

        # 7. URL（http/https）
        for match in re.finditer(r"https?://[^\s\)\]\}\'"]+", content):
            positions.append(TextPosition(match.start(), match.end(), "url", 3))

        # 8. 既存のタグ
        for match in re.finditer(r"#[\w\-/]+", content):
            positions.append(
                TextPosition(match.start(), match.end(), "existing_tag", 1)
            )

        # 9. HTMLコメント
        for match in re.finditer(r"<!--[\s\S]*?-->", content):
            positions.append(
                TextPosition(match.start(), match.end(), "html_comment", 2)
            )

        # 10. 見出し
        for match in re.finditer(r"^#+\s+.*$", content, re.MULTILINE):
            positions.append(
                TextPosition(match.start(), match.end(), "heading", 5)
            )

        return positions

    def is_safe_to_tag(
        self, start: int, end: int, exception_positions: list[TextPosition]
    ) -> bool:
        """
        指定位置にタグを挿入しても安全かチェック

        Args:
            start: 開始位置
            end: 終了位置
            exception_positions: 例外位置のリスト

        Returns:
            bool: 安全な場合True
        """
        for pos in exception_positions:
            # 例外範囲と重複していないかチェック
            if not (end <= pos.start or start >= pos.end):
                return False
        return True

    def extract_tags_from_llm_response(self, llm_tags: list[str]) -> list[str]:
        """
        LLM応答からタグを抽出・正規化

        Args:
            llm_tags: LLMから生成されたタグリスト

        Returns:
            list[str]: 正規化されたタグリスト
        """
        normalized_tags = []
        for tag in llm_tags:
            # タグの正規化
            # - 先頭の#を除去
            # - 空白を除去
            # - 小文字に統一（オプション）
            tag = tag.strip().lstrip("#").strip()

            # 無効なタグをスキップ
            if not tag or len(tag) < 2:
                continue

            # スペースを含むタグはハイフンに置換
            tag = tag.replace(" ", "-")

            # 使用可能な文字のみを許可（英数字、ハイフン、アンダースコア）
            if re.match(r"^[\w\-]+$", tag):
                normalized_tags.append(tag)

        return normalized_tags

    def insert_tags_to_file(
        self, file_path: Path, tags: list[str], similar_links: list[dict] | None = None
    ) -> bool:
        """
        ファイルにタグを挿入

        Args:
            file_path: 対象ファイルのパス
            tags: 挿入するタグのリスト
            similar_links: 類似リンク（同時に挿入する場合）

        Returns:
            bool: 挿入成功時True
        """
        # 除外フォルダチェック
        if DocumentUpdater.is_file_excluded(
            file_path,
            self.settings.excluded_folders,
            self.vault_path,
            self.settings.exclude_root_files,
        ):
            return False

        # タグの正規化
        normalized_tags = self.extract_tags_from_llm_response(tags)

        if not normalized_tags:
            # 有効なタグがない場合は何もしない
            return False

        # ドキュメントを更新（AIセクションを使用）
        return DocumentUpdater.update_document(
            file_path=file_path,
            similar_links=similar_links,
            tags=normalized_tags,
        )

    def batch_insert_tags(
        self,
        file_paths: list[Path],
        tags_per_file: dict[str, list[str]],
        links_per_file: dict[str, list[dict]] | None = None,
    ) -> dict:
        """
        複数ファイルに一括でタグを挿入

        Args:
            file_paths: 対象ファイルパスのリスト
            tags_per_file: {ファイルパス: タグリスト} の辞書
            links_per_file: {ファイルパス: 類似リンクリスト} の辞書（オプション）

        Returns:
            dict: 処理統計
                {
                    "processed": 処理ファイル数,
                    "successful": 成功数,
                    "excluded": 除外数,
                    "no_tags": タグなし数,
                    "failed": 失敗数
                }
        """
        stats = {
            "processed": 0,
            "successful": 0,
            "excluded": 0,
            "no_tags": 0,
            "failed": 0,
        }

        links_per_file = links_per_file or {}

        for file_path in file_paths:
            stats["processed"] += 1

            # 除外フォルダチェック
            if DocumentUpdater.is_file_excluded(
                file_path,
                self.settings.excluded_folders,
                self.vault_path,
                self.settings.exclude_root_files,
            ):
                stats["excluded"] += 1
                continue

            # タグを取得
            file_key = str(file_path)
            if file_key not in tags_per_file:
                stats["no_tags"] += 1
                continue

            tags = tags_per_file[file_key]
            links = links_per_file.get(file_key)

            # タグ挿入
            success = self.insert_tags_to_file(file_path, tags, links)

            if success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1

        return stats
