"""Link updater - automatically updates all links when file is renamed."""

import logging
from pathlib import Path

from app.core.config import Settings

logger = logging.getLogger(__name__)


class LinkUpdater:
    """リンク自動更新サービス

    ファイル名変更時にVault内の全リンクを自動更新する。
    """

    def __init__(self, settings: Settings) -> None:
        """
        LinkUpdaterを初期化

        Args:
            settings: 設定
        """
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

    def update_all_links(
        self,
        old_name: str,
        new_name: str
    ) -> int:
        """
        Vault内の全ファイルでリンクを更新

        Args:
            old_name: 旧ファイル名（拡張子なし）
            new_name: 新ファイル名（拡張子なし）

        Returns:
            int: 更新されたファイル数
        """
        updated_count = 0

        try:
            old_link = f"[[{old_name}]]"
            new_link = f"[[{new_name}]]"

            logger.info(f"リンク更新開始: {old_link} → {new_link}")

            for file in self.vault_path.rglob("*.md"):
                try:
                    content = file.read_text(encoding="utf-8")

                    if old_link in content:
                        updated = content.replace(old_link, new_link)
                        file.write_text(updated, encoding="utf-8")
                        updated_count += 1
                        logger.debug(f"リンク更新: {file.name}")

                except Exception as exc:
                    logger.warning(f"リンク更新失敗: {file.name} - {exc}")
                    continue

            logger.info(f"リンク自動更新完了: {updated_count}ファイル")
            return updated_count

        except Exception as exc:
            logger.error(f"リンク自動更新に失敗: {exc}")
            return 0

    def rename_file_and_update_links(
        self,
        file_path: Path,
        new_name: str
    ) -> Path:
        """
        ファイルをリネームし、全リンクを更新

        Args:
            file_path: 対象ファイルのパス
            new_name: 新しいファイル名（拡張子なし）

        Returns:
            Path: リネーム後のファイルパス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: 新しいファイル名が既に存在する場合
        """
        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        old_name = file_path.stem
        new_file_path = file_path.parent / f"{new_name}.md"

        if new_file_path.exists():
            raise ValueError(f"新しいファイル名が既に存在します: {new_file_path}")

        # ファイルをリネーム
        file_path.rename(new_file_path)
        logger.info(f"ファイルリネーム: {old_name} → {new_name}")

        # 全リンクを更新
        updated_count = self.update_all_links(old_name, new_name)
        logger.info(f"リンク更新完了: {updated_count}ファイル")

        return new_file_path
