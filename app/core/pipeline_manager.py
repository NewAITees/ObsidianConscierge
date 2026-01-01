"""Pipeline manager - tracks file stage transitions in the 4-stage pipeline.

00_Raw → 01_Summary → 02_Atomic → 03_MOC
"""

import logging
import re
from pathlib import Path
from typing import Literal
from datetime import datetime

from app.core.config import Settings

logger = logging.getLogger(__name__)

PipelineStage = Literal["00_Raw", "01_Summary", "02_Atomic", "03_MOC"]


class PipelineManager:
    """パイプラインステージ管理サービス.

    各ファイルの pipeline_stage を追跡し、Frontmatter を更新する。
    """

    def __init__(self, settings: Settings) -> None:
        """PipelineManager を初期化.

        Args:
            settings: 設定
        """
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

        # ステージの順序（前方への遷移のみ許可）
        self.stage_order: list[PipelineStage] = [
            "00_Raw",
            "01_Summary",
            "02_Atomic",
            "03_MOC",
        ]

    def get_current_stage(self, file_path: Path) -> PipelineStage | None:
        """ファイルの現在のステージを Frontmatter から取得.

        Args:
            file_path: 対象ファイルのパス

        Returns:
            PipelineStage | None: 現在のステージ、取得できない場合は None
        """
        try:
            if not file_path.exists():
                logger.warning(f"ファイルが存在しません: {file_path}")
                return None

            content = file_path.read_text(encoding="utf-8")

            # Frontmatter から pipeline_stage を抽出
            frontmatter_match = re.search(
                r"^---\n(.*?)\n---",
                content,
                re.DOTALL | re.MULTILINE
            )

            if not frontmatter_match:
                logger.debug(f"Frontmatter なし: {file_path.name}")
                return None

            frontmatter = frontmatter_match.group(1)

            # pipeline_stage フィールドを探す
            stage_match = re.search(
                r'pipeline_stage:\s*["\']?(00_Raw|01_Summary|02_Atomic|03_MOC)["\']?',
                frontmatter
            )

            if stage_match:
                return stage_match.group(1)  # type: ignore

            logger.debug(f"pipeline_stage フィールドなし: {file_path.name}")
            return None

        except Exception as exc:
            logger.error(f"ステージ取得に失敗: {file_path.name} - {exc}")
            return None

    def update_stage(
        self,
        file_path: Path,
        new_stage: PipelineStage,
        allow_backward: bool = False
    ) -> bool:
        """ファイルの pipeline_stage を更新.

        Args:
            file_path: 対象ファイルのパス
            new_stage: 新しいステージ
            allow_backward: 後方への遷移を許可するか（デフォルト: False）

        Returns:
            bool: 更新成功/失敗
        """
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

            # 現在のステージを取得
            current_stage = self.get_current_stage(file_path)

            # ステージの妥当性チェック
            if current_stage and not allow_backward:
                current_idx = self.stage_order.index(current_stage)
                new_idx = self.stage_order.index(new_stage)

                if new_idx < current_idx:
                    logger.warning(
                        f"後方遷移は許可されていません: "
                        f"{current_stage} → {new_stage} ({file_path.name})"
                    )
                    return False

            content = file_path.read_text(encoding="utf-8")

            # Frontmatter を更新
            updated_content = self._update_frontmatter(
                content,
                new_stage,
                file_path
            )

            if updated_content == content:
                logger.debug(f"変更なし: {file_path.name}")
                return True

            # ファイルに書き戻し
            file_path.write_text(updated_content, encoding="utf-8")
            logger.info(
                f"ステージ更新: {file_path.name} "
                f"({current_stage or '不明'} → {new_stage})"
            )
            return True

        except Exception as exc:
            logger.error(f"ステージ更新に失敗: {file_path.name} - {exc}")
            return False

    def _update_frontmatter(
        self,
        content: str,
        new_stage: PipelineStage,
        file_path: Path
    ) -> str:
        """Frontmatter の pipeline_stage を更新.

        Args:
            content: ファイルコンテンツ
            new_stage: 新しいステージ
            file_path: ファイルパス（ログ用）

        Returns:
            str: 更新されたコンテンツ
        """
        # Frontmatter の存在チェック
        frontmatter_match = re.search(
            r"^(---\n)(.*?)(\n---)",
            content,
            re.DOTALL | re.MULTILINE
        )

        if not frontmatter_match:
            # Frontmatter がない場合は新規作成
            logger.debug(f"Frontmatter 新規作成: {file_path.name}")
            new_frontmatter = self._create_frontmatter(
                file_path,
                new_stage
            )
            return f"{new_frontmatter}\n\n{content}"

        # 既存の Frontmatter を更新
        frontmatter_start = frontmatter_match.group(1)
        frontmatter_body = frontmatter_match.group(2)
        frontmatter_end = frontmatter_match.group(3)

        # pipeline_stage フィールドを更新または追加
        if "pipeline_stage:" in frontmatter_body:
            # 既存フィールドを更新
            updated_body = re.sub(
                r'pipeline_stage:\s*["\']?.*?["\']?(?=\n|$)',
                f'pipeline_stage: "{new_stage}"',
                frontmatter_body
            )
        else:
            # フィールドを追加（最後に）
            updated_body = frontmatter_body.rstrip() + f'\npipeline_stage: "{new_stage}"'

        # updated フィールドを更新または追加
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if "updated:" in updated_body:
            updated_body = re.sub(
                r'updated:\s*["\']?.*?["\']?(?=\n|$)',
                f'updated: "{current_time}"',
                updated_body
            )
        else:
            updated_body = updated_body.rstrip() + f'\nupdated: "{current_time}"'

        # コンテンツを再構築
        updated_frontmatter = frontmatter_start + updated_body + frontmatter_end
        rest_of_content = content[frontmatter_match.end():]

        return updated_frontmatter + rest_of_content

    def _create_frontmatter(
        self,
        file_path: Path,
        stage: PipelineStage
    ) -> str:
        """新規 Frontmatter を作成.

        Args:
            file_path: ファイルパス
            stage: パイプラインステージ

        Returns:
            str: Frontmatter 文字列
        """
        title = file_path.stem
        created_date = datetime.now().strftime("%Y-%m-%d")

        return f"""---
title: "{title}"
created: {created_date}
pipeline_stage: "{stage}"
---"""

    def get_stage_files(self, stage: PipelineStage) -> list[Path]:
        """指定されたステージのファイルを全て取得.

        Args:
            stage: パイプラインステージ

        Returns:
            list[Path]: ファイルパスのリスト
        """
        try:
            # ステージに対応するディレクトリ
            stage_dir = self.vault_path / stage

            if not stage_dir.exists():
                logger.warning(f"ディレクトリが存在しません: {stage_dir}")
                return []

            # .md ファイルを全て取得
            files = list(stage_dir.glob("*.md"))

            logger.info(f"{stage} のファイル数: {len(files)}")
            return files

        except Exception as exc:
            logger.error(f"ファイル取得に失敗: {stage} - {exc}")
            return []

    def get_pipeline_statistics(self) -> dict[PipelineStage, int]:
        """各ステージのファイル数を取得.

        Returns:
            dict[PipelineStage, int]: ステージごとのファイル数
        """
        stats: dict[PipelineStage, int] = {}

        for stage in self.stage_order:
            files = self.get_stage_files(stage)
            stats[stage] = len(files)

        return stats

    def validate_stage_transition(
        self,
        from_stage: PipelineStage,
        to_stage: PipelineStage
    ) -> bool:
        """ステージ遷移の妥当性を検証.

        Args:
            from_stage: 遷移元ステージ
            to_stage: 遷移先ステージ

        Returns:
            bool: 妥当な遷移かどうか
        """
        try:
            from_idx = self.stage_order.index(from_stage)
            to_idx = self.stage_order.index(to_stage)

            # 前方への遷移のみ許可（同一ステージも可）
            return to_idx >= from_idx

        except ValueError:
            logger.error(f"不正なステージ: {from_stage} または {to_stage}")
            return False
