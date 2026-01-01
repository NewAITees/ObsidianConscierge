"""Atomic note splitter - splits summarized notes into atomic concepts."""

import logging
import re
from pathlib import Path
from typing import Any
from datetime import datetime

from app.services.llm_service import LLMService
from app.core.config import Settings

logger = logging.getLogger(__name__)


class AtomicSplitter:
    """01_Summary から 02_Atomic への分解を行うサービス

    1つのSummaryファイルから独立した概念（アトミック・ノート）を抽出する。
    """

    def __init__(
        self,
        llm_service: LLMService,
        settings: Settings
    ) -> None:
        """
        AtomicSplitterを初期化

        Args:
            llm_service: LLM呼び出しサービス
            settings: 設定
        """
        self.llm_service = llm_service
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

    def generate_split_prompt(
        self,
        summary_content: str,
        file_path: str
    ) -> str:
        """
        01_Summary → 02_Atomic 分解プロンプトを生成

        Args:
            summary_content: Summary形式のMarkdownコンテンツ
            file_path: ファイルパス（相対パス）

        Returns:
            str: 分解プロンプト
        """
        return f"""以下の文章から、独立した概念（アトミック・ノート）を抽出してください。

【ルール】
1. **1つの概念 = 1つのノート**
2. 各ノートは「1ファイル1テーマ」
3. 他のノートと組み合わせて使える「レゴブロック」として設計
4. 各ノートは以下の形式で出力:

---ATOMIC_NOTE---
タイトル: [概念名（問い形式推奨）]
タグ: [関連タグをカンマ区切り]
概念: [1文での概念定義]
詳細:
[詳細説明（200〜800字）]

応用例:
- [具体的な使用場面1]
- [具体的な使用場面2]

関連リンク:
- [[元ファイル名]]
---END---

【抽出基準】
- 独立して理解できる概念
- 再利用可能な知識
- 他の文脈でも適用可能
- 過度に具体的すぎない（例: 「2025-01-01の会議」ではなく「AI動画集客戦略」）
- 本文が200字未満になる場合は分割しない

【入力文章】
元ファイル: {file_path}

{summary_content}

【出力例】
---ATOMIC_NOTE---
タイトル: なぜAI動画は集客に効果的なのか
タグ: マーケティング, AI動画, 集客
概念: AI動画を使ったYouTube shorts/TikTokでの集客施策
詳細:
AI動画は短尺フォーマットでの展開により、若年層へのリーチを拡大する。
プラットフォーム: YouTube shorts、TikTok
費用: 月50万円、ROI: 3ヶ月で回収見込み。
短尺動画は視聴完了率が高く、アルゴリズムに好まれるため、
オーガニックリーチが期待できる。

応用例:
- YouTube shortsでの商品PR
- TikTokでのブランド認知施策
- Instagram Reelsでのエンゲージメント向上

関連リンク:
- [[プロジェクトX進捗会議 2025-01-01]]
---END---
"""

    def split_into_atomic_notes(
        self,
        summary_file_path: Path
    ) -> list[dict[str, Any]]:
        """
        01_Summaryファイルを複数の02_Atomicノートに分解

        Args:
            summary_file_path: 01_Summaryファイルのパス

        Returns:
            List[Dict[str, Any]]: 生成されたアトミック・ノートのリスト
                各要素は {title, content, tags, atomic_concept} を含む

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        try:
            if not summary_file_path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {summary_file_path}")

            # ファイルを読み込み
            summary_content = summary_file_path.read_text(encoding="utf-8")

            # 分解プロンプトを生成
            relative_path = summary_file_path.relative_to(self.vault_path)
            prompt = self.generate_split_prompt(
                summary_content,
                str(relative_path)
            )

            # LLMで分解
            response = self.llm_service._generate_with_retry(prompt)

            # レスポンスをパース
            atomic_notes = self._parse_atomic_notes(response, summary_file_path)

            logger.info(
                f"分解完了: {summary_file_path.name} → {len(atomic_notes)}個のアトミック・ノート"
            )
            return atomic_notes

        except Exception as exc:
            logger.error(f"アトミック・ノート分解に失敗: {exc}")
            return []

    def _parse_atomic_notes(
        self,
        response: str,
        source_file: Path
    ) -> list[dict[str, Any]]:
        """
        LLMレスポンスをパースしてアトミック・ノートのリストを生成

        Args:
            response: LLMのレスポンス
            source_file: 元ファイルのパス

        Returns:
            List[Dict[str, Any]]: パースされたアトミック・ノートのリスト
        """
        notes: list[dict[str, Any]] = []

        # ---ATOMIC_NOTE--- ... ---END--- のパターンで分割
        pattern = r"---ATOMIC_NOTE---(.*?)---END---"
        matches = re.findall(pattern, response, re.DOTALL)

        for match in matches:
            try:
                # タイトル抽出
                title_match = re.search(r"タイトル:\s*(.+)", match)
                title = title_match.group(1).strip() if title_match else "Untitled"

                # タグ抽出
                tags_match = re.search(r"タグ:\s*(.+)", match)
                tags = []
                if tags_match:
                    tags = [
                        tag.strip()
                        for tag in tags_match.group(1).split(",")
                    ]

                # 概念抽出
                concept_match = re.search(r"概念:\s*(.+)", match)
                atomic_concept = (
                    concept_match.group(1).strip()
                    if concept_match
                    else title
                )

                # 詳細抽出
                details_match = re.search(
                    r"詳細:(.*?)(?:応用例:|関連リンク:|$)",
                    match,
                    re.DOTALL
                )
                details = (
                    details_match.group(1).strip()
                    if details_match
                    else ""
                )

                # 応用例抽出
                examples_match = re.search(
                    r"応用例:(.*?)(?:関連リンク:|$)",
                    match,
                    re.DOTALL
                )
                examples = (
                    examples_match.group(1).strip()
                    if examples_match
                    else ""
                )

                # Frontmatter付きMarkdownコンテンツを生成
                content = self._build_atomic_note_content(
                    title=title,
                    tags=tags,
                    atomic_concept=atomic_concept,
                    details=details,
                    examples=examples,
                    source_file=source_file
                )

                notes.append({
                    "title": title,
                    "content": content,
                    "tags": tags,
                    "atomic_concept": atomic_concept,
                })

            except Exception as exc:
                logger.warning(f"アトミック・ノートのパースに失敗: {exc}")
                continue

        return notes

    def _build_atomic_note_content(
        self,
        title: str,
        tags: list[str],
        atomic_concept: str,
        details: str,
        examples: str,
        source_file: Path
    ) -> str:
        """
        アトミック・ノートのMarkdownコンテンツを生成

        Args:
            title: タイトル
            tags: タグリスト
            atomic_concept: 概念の1文説明
            details: 詳細説明
            examples: 応用例
            source_file: 元ファイルのパス

        Returns:
            str: Frontmatter付きMarkdownコンテンツ
        """
        created_date = datetime.now().strftime("%Y-%m-%d")
        tags_str = "[" + ", ".join(tags) + "]" if tags else "[]"
        source_link = f"[[{source_file.stem}]]"

        content = f"""---
title: "{title}"
created: {created_date}
tags: {tags_str}
pipeline_stage: "02_Atomic"
source_file: "{source_file.relative_to(self.vault_path)}"
atomic_concept: "{atomic_concept}"
---

# {title}

## 概念
{atomic_concept}

## 詳細
{details}
"""

        if examples:
            content += f"""
## 応用例
{examples}
"""

        content += f"""
## 関連リンク
- {source_link}
"""

        return content

    def save_atomic_notes(
        self,
        atomic_notes: list[dict[str, Any]]
    ) -> list[Path]:
        """
        アトミック・ノートをファイルとして保存

        Args:
            atomic_notes: アトミック・ノートのリスト

        Returns:
            List[Path]: 保存されたファイルパスのリスト
        """
        saved_files: list[Path] = []
        atomic_dir = self.vault_path / "02_Atomic"
        atomic_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y%m%d")

        for note in atomic_notes:
            try:
                title = note["title"]
                content = note["content"]

                # ファイル名を生成（タイトル_YYYYMMDD.md）
                safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
                file_path = atomic_dir / f"{safe_title}_{date_str}.md"

                # 重複チェック（同名ファイルがある場合は連番を追加）
                counter = 1
                original_file_path = file_path
                while file_path.exists():
                    file_path = atomic_dir / f"{safe_title}_{date_str}_{counter}.md"
                    counter += 1

                # ファイルを保存
                file_path.write_text(content, encoding="utf-8")

                saved_files.append(file_path)
                logger.info(f"アトミック・ノート保存: {file_path.name}")

            except Exception as exc:
                logger.error(f"アトミック・ノート保存に失敗: {exc}")
                continue

        return saved_files
