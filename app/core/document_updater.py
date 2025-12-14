"""Document updater with AI-managed sections.

このモジュールは、Obsidianドキュメント内の====バーで囲まれた
AI自動生成セクションを安全に管理します。

【重要ルール】
- ====セクション内のみを編集対象とする
- ====セクション外は絶対に編集しない
- セクションが存在しない場合のみ、ファイル末尾に追加する
"""

import re
from datetime import datetime
from pathlib import Path


class DocumentUpdater:
    """Obsidianドキュメントの====セクション管理クラス"""

    # セクション境界マーカー（偶然の一致を防ぐため、明確な文字列を使用）
    SECTION_START = "=" * 10 + " AI AUTO-GENERATED SECTION START " + "=" * 10
    SECTION_END = "=" * 10 + " AI AUTO-GENERATED SECTION END " + "=" * 10
    SECTION_HEADER = "## 🤖 AI自動生成セクション"

    @classmethod
    def extract_ai_section(cls, content: str) -> tuple[str, str, str]:
        """
        ドキュメントからAI自動生成セクションを抽出

        Args:
            content: ドキュメント全文

        Returns:
            tuple[str, str, str]: (セクション前部分, AI生成セクション, セクション後部分)
                - AI生成セクションが存在しない場合は、中央が空文字列
        """
        # 明確なマーカーで囲まれたセクションを検索
        pattern = re.compile(
            rf"{re.escape(cls.SECTION_START)}\n"
            rf"{re.escape(cls.SECTION_HEADER)}\n"
            r"(.*?)\n"
            rf"{re.escape(cls.SECTION_END)}",
            re.DOTALL,
        )

        match = pattern.search(content)
        if match:
            # セクションが見つかった場合
            before = content[: match.start()]
            section = match.group(0)
            after = content[match.end() :]
            return before, section, after
        else:
            # セクションが見つからない場合
            return content, "", ""

    @classmethod
    def create_ai_section(
        cls,
        similar_links: list[dict] | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """
        AI自動生成セクションを作成

        Args:
            similar_links: 類似ドキュメントのリスト
                [{"title": "ドキュメント名", "similarity": 0.85}, ...]
            tags: タグのリスト ["python", "fastapi", ...]

        Returns:
            str: 完全なセクション文字列
        """
        lines = [cls.SECTION_START, cls.SECTION_HEADER, ""]

        # 類似ドキュメントセクション
        if similar_links:
            lines.append("### 🔗 類似ドキュメント")
            for link in similar_links:
                title = link["title"]
                similarity = link["similarity"]

                # 類似度に応じたアイコン
                if similarity >= 0.8:
                    icon = "🔗"
                elif similarity >= 0.6:
                    icon = "📎"
                else:
                    icon = "🔍"

                lines.append(f"- {icon} [[{title}]] (類似度: {similarity:.3f})")
            lines.append("")

        # タグセクション
        if tags:
            lines.append("### 🏷️ 自動タグ")
            tag_line = " ".join(f"#{tag}" for tag in tags)
            lines.append(tag_line)
            lines.append("")

        # 最終更新時刻
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"最終更新: {now}")

        lines.append(cls.SECTION_END)

        return "\n".join(lines)

    @classmethod
    def update_document(
        cls,
        file_path: Path,
        similar_links: list[dict] | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """
        ドキュメントのAI自動生成セクションを更新

        【重要】
        - 既存のセクションがある場合は、その内容のみを置き換える
        - セクションが存在しない場合は、ファイル末尾に追加する
        - セクション外の内容は絶対に変更しない

        Args:
            file_path: 更新対象のファイルパス
            similar_links: 類似ドキュメントのリスト
            tags: タグのリスト

        Returns:
            bool: 更新成功時True
        """
        try:
            # ファイル読み込み
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            # AI生成セクションを抽出
            before, old_section, after = cls.extract_ai_section(original_content)

            # 新しいセクションを作成
            new_section = cls.create_ai_section(similar_links, tags)

            # コンテンツを再構築
            if old_section:
                # 既存セクションがある場合は置き換え
                new_content = before + new_section + after
            else:
                # セクションがない場合は末尾に追加
                # 既存コンテンツの末尾に改行を追加してからセクションを追加
                new_content = original_content.rstrip() + "\n\n" + new_section + "\n"

            # ファイル書き込み
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return True

        except Exception as e:
            print(f"❌ ファイル更新エラー ({file_path}): {e}")
            return False

    @classmethod
    def is_file_excluded(
        cls,
        file_path: Path,
        excluded_folders: list[str],
        vault_path: Path | None = None,
        exclude_root: bool = True,
    ) -> bool:
        """
        ファイルが除外対象かどうかを判定

        Args:
            file_path: チェック対象のファイルパス
            excluded_folders: 除外フォルダのリスト
            vault_path: Vaultのルートパス（ルート判定に使用）
            exclude_root: ルートディレクトリのファイルを除外するか

        Returns:
            bool: 除外対象の場合True
        """
        # ルートディレクトリのファイルをチェック
        if exclude_root and vault_path:
            try:
                # vault_pathからの相対パスを取得
                relative_path = file_path.relative_to(vault_path)
                # ルートディレクトリに直接配置されているファイルかチェック
                # （サブディレクトリに含まれていない場合）
                if len(relative_path.parts) == 1:
                    return True
            except ValueError:
                # vault_pathの外にある場合はスキップ
                pass

        # パスの各部分をチェック
        parts = file_path.parts
        for folder in excluded_folders:
            if folder in parts:
                return True
        return False
