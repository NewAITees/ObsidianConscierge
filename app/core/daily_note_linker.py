"""Daily note linker - automatically links created files to daily note."""

import logging
from pathlib import Path
from datetime import datetime

from app.core.config import Settings

logger = logging.getLogger(__name__)


class DailyNoteLinker:
    """日記ファイル連携サービス

    作成したファイルをその日の日記ファイルに自動リンクする。
    """

    def __init__(self, settings: Settings) -> None:
        """
        DailyNoteLinkerを初期化

        Args:
            settings: 設定
        """
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)
        self.diary_dir = self.vault_path / "01DIARY"

    def add_to_daily_note(
        self,
        created_file: Path,
        created_date: str | None = None
    ) -> bool:
        """
        その日の日記ファイルにリンクを追加

        Args:
            created_file: 作成されたファイルのパス
            created_date: 作成日（YYYY-MM-DD形式、Noneの場合は今日）

        Returns:
            bool: 成功/失敗
        """
        try:
            # 作成日を取得
            if created_date is None:
                created_date = datetime.now().strftime("%Y-%m-%d")

            # 日記ファイルパス
            diary_file = self.diary_dir / f"{created_date}.md"

            # 日記ファイルがなければ作成
            if not diary_file.exists():
                self._create_daily_note(created_date)

            # リンクを追加
            link = f"- [[{created_file.stem}]]\n"
            content = diary_file.read_text(encoding="utf-8")

            # 「## 今日作成したファイル」セクションを探す
            section_header = "## 今日作成したファイル"

            if section_header in content:
                # セクションの後に追加（重複チェック）
                if link.strip() not in content:
                    # セクションヘッダーの直後に挿入
                    content = content.replace(
                        f"{section_header}\n",
                        f"{section_header}\n{link}",
                        1  # 最初の1回のみ置換
                    )
                else:
                    logger.info(f"リンク既存: {created_file.name}")
                    return True
            else:
                # セクションを新規作成
                content += f"\n{section_header}\n{link}"

            # ファイルに書き戻し
            diary_file.write_text(content, encoding="utf-8")
            logger.info(f"日記ファイルにリンク追加: {diary_file.name} ← {created_file.name}")
            return True

        except Exception as exc:
            logger.error(f"日記ファイル連携に失敗: {exc}")
            return False

    def _create_daily_note(self, date: str) -> None:
        """
        日記ファイルを作成

        Args:
            date: 作成日（YYYY-MM-DD形式）
        """
        try:
            self.diary_dir.mkdir(parents=True, exist_ok=True)
            diary_file = self.diary_dir / f"{date}.md"

            template = f"""---
title: "{date}"
created: {date}
tags: [日記]
---

# {date}

## 今日作成したファイル

"""

            diary_file.write_text(template, encoding="utf-8")
            logger.info(f"日記ファイル作成: {diary_file.name}")

        except Exception as exc:
            logger.error(f"日記ファイル作成に失敗: {exc}")
            raise

    def get_daily_note_path(self, date: str | None = None) -> Path:
        """
        日記ファイルのパスを取得

        Args:
            date: 日付（YYYY-MM-DD形式、Noneの場合は今日）

        Returns:
            Path: 日記ファイルのパス
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        return self.diary_dir / f"{date}.md"
