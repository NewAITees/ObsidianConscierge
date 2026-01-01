"""Migrate existing files to atomic notes pipeline.

00CreatedFiles → 01_Summary の移行を行う.
"""

import logging
from pathlib import Path

from app.core.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_files() -> None:
    """00CreatedFiles → 01_Summary 移行."""
    settings = Settings()
    vault_path = Path(settings.obsidian_vault_path)
    old_dir = vault_path / "00CreatedFiles"
    new_dir = vault_path / "01_Summary"

    if not old_dir.exists():
        logger.error(f"ソースディレクトリが見つかりません: {old_dir}")
        return

    new_dir.mkdir(parents=True, exist_ok=True)

    for file in old_dir.glob("*.md"):
        new_file = new_dir / file.name

        if new_file.exists():
            logger.info(f"スキップ（既存）: {file.name}")
            continue

        new_file.write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info(f"移行完了: {file.name}")


if __name__ == "__main__":
    migrate_files()
