"""Summarizer - converts Raw notes to Summary format."""

import logging
from pathlib import Path
from datetime import datetime

from app.services.llm_service import LLMService
from app.core.config import Settings

logger = logging.getLogger(__name__)


class Summarizer:
    """00_Raw → 01_Summary 変換サービス

    殴り書きメモを整形し、構造化されたサマリーを生成する。
    """

    def __init__(
        self,
        llm_service: LLMService,
        settings: Settings
    ) -> None:
        """
        Summarizerを初期化

        Args:
            llm_service: LLM呼び出しサービス
            settings: 設定
        """
        self.llm_service = llm_service
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

    def generate_summary_prompt(
        self,
        raw_content: str,
        file_path: str
    ) -> str:
        """
        00_Raw → 01_Summary 要約プロンプトを生成

        Args:
            raw_content: Rawファイルの内容
            file_path: ファイルパス（相対パス）

        Returns:
            str: 要約プロンプト
        """
        return f"""以下の殴り書きメモを整形し、構造化されたサマリーを作成してください。

【ルール】
1. タイトルを付ける（ファイル名: {file_path}）
2. サマリーセクション: 全体を3-5文で要約
3. 主要トピックを観点ごとにセクション分け
4. アクションアイテムを抽出（あれば）
5. Frontmatterメタデータを生成（YAML形式）
   - title: タイトル
   - created: 作成日（YYYY-MM-DD形式）
   - tags: 関連タグ（3-7個）
   - pipeline_stage: "01_Summary"
   - source_file: 元ファイルパス

【入力】
{raw_content}

【出力形式】
---
title: "タイトル"
created: {datetime.now().strftime("%Y-%m-%d")}
tags: [タグ1, タグ2, タグ3]
pipeline_stage: "01_Summary"
source_file: "{file_path}"
---

# タイトル

## サマリー
[3-5文の要約]

## 観点1
- 要点
- 要点

## 観点2
- 要点
- 要点

## 次のアクション
- [ ] アクションアイテム1
"""

    def summarize_raw_file(self, raw_file_path: Path) -> str:
        """
        Rawファイルを要約してSummary形式のMarkdownを生成

        Args:
            raw_file_path: Rawファイルのパス

        Returns:
            str: Summary形式のMarkdownコンテンツ

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        try:
            if not raw_file_path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {raw_file_path}")

            # ファイルを読み込み
            raw_content = raw_file_path.read_text(encoding="utf-8")

            # プロンプトを生成
            relative_path = raw_file_path.relative_to(self.vault_path)
            prompt = self.generate_summary_prompt(
                raw_content,
                str(relative_path)
            )

            # LLMで要約
            summary_content = self.llm_service._generate_with_retry(prompt)

            logger.info(f"要約完了: {raw_file_path.name}")
            return summary_content

        except Exception as exc:
            logger.error(f"要約に失敗: {exc}")
            return ""

    def save_summary(
        self,
        summary_content: str,
        raw_file_path: Path
    ) -> Path:
        """
        Summaryを保存

        Args:
            summary_content: Summary形式のMarkdownコンテンツ
            raw_file_path: 元のRawファイルパス

        Returns:
            Path: 保存されたSummaryファイルのパス
        """
        try:
            summary_dir = self.vault_path / "01_Summary"
            summary_dir.mkdir(parents=True, exist_ok=True)

            # ファイル名を生成（テーマ_YYYYMMDD_Summary.md）
            date_str = datetime.now().strftime("%Y%m%d")

            # Rawファイル名から日付部分を除去してテーマを抽出
            # 形式: テーマ_YYYYMMDD.md → テーマ
            raw_stem = raw_file_path.stem
            if "_" in raw_stem and raw_stem.split("_")[-1].isdigit():
                # 末尾が日付の場合、それを除去
                theme = "_".join(raw_stem.split("_")[:-1])
            else:
                theme = raw_stem

            summary_file_path = summary_dir / f"{theme}_{date_str}_Summary.md"

            # ファイルを保存
            summary_file_path.write_text(summary_content, encoding="utf-8")

            logger.info(f"Summary保存: {summary_file_path.name}")
            return summary_file_path

        except Exception as exc:
            logger.error(f"Summary保存に失敗: {exc}")
            raise
