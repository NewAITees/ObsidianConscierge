"""MOC generator - automatically generates Maps of Contents from Atomic notes.

02_Atomic → 03_MOC の自動生成を行う。
関連するアトミック・ノートをタグやベクトル類似度でグループ化し、
知識マップ（MOC: Map of Contents）を作成する。
"""

import logging
import re
from pathlib import Path
from typing import Any
from datetime import datetime

from app.core.config import Settings
from app.core.analysis import AnalysisService, cosine_similarity
from app.services.embedding_service import EmbeddingService
from app.services.vector_db_service import VectorDBService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class MOCGenerator:
    """MOC（Map of Contents）自動生成サービス.

    アトミック・ノートをグループ化して、知識マップを作成する。
    フォルダ階層ではなく、リンクベースで関連性を表現する。
    """

    def __init__(
        self,
        vector_db_service: VectorDBService,
        llm_service: LLMService,
        embedding_service: EmbeddingService,
        settings: Settings
    ) -> None:
        """MOCGenerator を初期化.

        Args:
            vector_db_service: ベクトルDBサービス
            llm_service: LLM呼び出しサービス
            embedding_service: Embeddingサービス
            settings: 設定
        """
        self.vector_db_service = vector_db_service
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

        # AnalysisService を内部で使用
        self.analysis_service = AnalysisService(
            vector_db_service=vector_db_service,
            settings=settings
        )

    def generate_moc_from_tag(
        self,
        tag: str,
        min_notes: int = 3
    ) -> Path | None:
        """指定されたタグを持つノートから MOC を生成.

        Args:
            tag: 対象タグ
            min_notes: 最小ノート数（この数未満の場合は生成しない）

        Returns:
            Path | None: 生成された MOC ファイルのパス、生成しなかった場合は None
        """
        try:
            logger.info(f"MOC 生成開始: タグ '{tag}'")

            # タグを持つノートを検索
            notes = self._get_notes_by_tag(tag)

            if len(notes) < min_notes:
                logger.info(
                    f"ノート数不足: {len(notes)}件（最小: {min_notes}件）"
                )
                return None

            # MOC コンテンツを生成（LLM使用、失敗時は例外）
            moc_content = self._build_moc_content(
                moc_type="tag",
                name=tag,
                notes=notes,
            )

            # MOC を保存
            moc_file = self._save_moc(f"MOC_{tag}", moc_content)

            logger.info(f"MOC 生成完了: {moc_file.name}（{len(notes)}件）")
            return moc_file

        except RuntimeError as exc:
            logger.error(f"LLMによるMOC生成に失敗: {exc}")
            return None
        except Exception as exc:
            logger.error(f"MOC 生成に失敗（予期しないエラー）: {exc}")
            return None

    def generate_moc_from_concept(
        self,
        concept: str,
        min_notes: int = 3
    ) -> Path | None:
        """指定された概念に関連するノートから MOC を生成.

        Args:
            concept: 対象概念（検索クエリ）
            min_notes: 最小ノート数

        Returns:
            Path | None: 生成された MOC ファイルのパス
        """
        try:
            logger.info(f"MOC 生成開始: 概念 '{concept}'")

            # 概念に関連するノートを検索（セマンティック検索）
            notes = self._get_notes_by_concept(concept, top_k=20)

            if len(notes) < min_notes:
                logger.info(
                    f"ノート数不足: {len(notes)}件（最小: {min_notes}件）"
                )
                return None

            # MOC コンテンツを生成（LLM使用、失敗時は例外）
            moc_content = self._build_moc_content(
                moc_type="concept",
                name=concept,
                notes=notes,
            )

            # MOC を保存
            safe_name = re.sub(r'[<>:"/\\|?*]', '', concept)
            moc_file = self._save_moc(f"MOC_{safe_name}", moc_content)

            logger.info(f"MOC 生成完了: {moc_file.name}（{len(notes)}件）")
            return moc_file

        except RuntimeError as exc:
            logger.error(f"LLMによるMOC生成に失敗: {exc}")
            return None
        except Exception as exc:
            logger.error(f"MOC 生成に失敗（予期しないエラー）: {exc}")
            return None

    def generate_all_mocs(
        self,
        min_notes: int = 3,
        max_mocs: int = 10
    ) -> list[Path]:
        """全てのタグから MOC を自動生成.

        Args:
            min_notes: 最小ノート数
            max_mocs: 最大生成数

        Returns:
            list[Path]: 生成された MOC ファイルのリスト
        """
        try:
            logger.info("全 MOC 自動生成開始")

            # MOC 候補を取得（AnalysisService を使用）
            candidates = self.analysis_service.find_moc_candidates(
                min_articles=min_notes,
                max_articles=50
            )

            if not candidates:
                logger.info("MOC 候補が見つかりませんでした")
                return []

            moc_files: list[Path] = []

            # タグベースの候補のみ処理（最大 max_mocs 件）
            tag_candidates = [c for c in candidates if c["type"] == "tag"]

            for candidate in tag_candidates[:max_mocs]:
                tag = candidate["name"]
                moc_file = self.generate_moc_from_tag(tag, min_notes)

                if moc_file:
                    moc_files.append(moc_file)

            logger.info(f"全 MOC 自動生成完了: {len(moc_files)}件")
            return moc_files

        except Exception as exc:
            logger.error(f"全 MOC 自動生成に失敗: {exc}")
            return []

    def _get_notes_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """タグを持つノートを取得.

        Args:
            tag: 対象タグ

        Returns:
            list[dict[str, Any]]: ノートのリスト
        """
        try:
            # 全記事を取得
            all_articles = self.vector_db_service.get_all_articles()

            # 02_Atomic フォルダのファイルのみ
            notes = [
                article
                for article in all_articles
                if "02_Atomic" in article.get("file_path", "")
                and tag in article.get("tags", [])
            ]

            return notes

        except Exception as exc:
            logger.error(f"タグ検索に失敗: {exc}")
            return []

    def _get_notes_by_concept(
        self,
        concept: str,
        top_k: int = 20
    ) -> list[dict[str, Any]]:
        """概念に関連するノートを検索.

        Args:
            concept: 検索クエリ
            top_k: 取得件数

        Returns:
            list[dict[str, Any]]: ノートのリスト
        """
        try:
            # セマンティック検索
            query_embedding = self.embedding_service.embed(concept)
            results = self.vector_db_service.search(
                query_embedding=query_embedding,
                limit=top_k,
            )

            # 02_Atomic フォルダのファイルのみ
            notes = [
                result
                for result in results
                if "02_Atomic" in result.get("file_path", "")
            ]

            return notes

        except Exception as exc:
            logger.error(f"概念検索に失敗: {exc}")
            return []

    def _build_moc_content(
        self,
        moc_type: str,
        name: str,
        notes: list[dict[str, Any]],
    ) -> str:
        """MOC の Markdown コンテンツを生成.

        Args:
            moc_type: MOC のタイプ（tag/concept）
            name: MOC の名前
            notes: 含まれるノートのリスト

        Returns:
            str: Markdown コンテンツ

        Raises:
            RuntimeError: LLMによるMOC生成に失敗した場合
        """
        created_date = datetime.now().strftime("%Y-%m-%d")
        all_tags = self._collect_tags(name, notes)

        # LLMでMOC本文を生成（失敗時は例外がraiseされる）
        question, body = self._build_llm_body(name, notes)

        title = f"MOC: {question}"
        frontmatter = self._build_frontmatter(
            title=title,
            created_date=created_date,
            tags=sorted(all_tags),
            moc_type=moc_type,
            note_count=len(notes),
        )

        body = self._ensure_link_coverage(body, notes)
        content = f"{frontmatter}\n\n{body}"

        return content

    def _build_frontmatter(
        self,
        title: str,
        created_date: str,
        tags: list[str],
        moc_type: str,
        note_count: int,
    ) -> str:
        """MOC Frontmatter を生成."""
        tags_str = "[" + ", ".join(tags) + "]" if tags else "[]"
        return f"""---
title: "{title}"
created: {created_date}
updated: {created_date}
tags: {tags_str}
pipeline_stage: "03_MOC"
moc_type: "{moc_type}"
note_count: {note_count}
---"""

    def _collect_tags(self, name: str, notes: list[dict[str, Any]]) -> set[str]:
        """MOC用のタグを集約."""
        all_tags = {"moc", name}
        for note in notes:
            all_tags.update(note.get("tags", []))
        return all_tags

    def _build_rule_based_body(
        self,
        name: str,
        notes: list[dict[str, Any]],
    ) -> str:
        """ルールベースのMOC本文を生成.

        注: このメソッドは現在未使用です（LLMフォールバックを削除したため）。
        将来的なフォールバック実装のために残しています。
        """
        lines = [
            f"# 【問い】{name}に共通する要素は何か",
            "",
            "## この問いの背景",
            "関連ノートを俯瞰するための出発点として整理する。",
            "",
            "## 関連するAtomicノート",
            "",
        ]
        lines.extend(self._build_rule_based_links(notes))
        lines.append("")
        lines.append("## 現時点での暫定的な答え")
        lines.append("（未記入）")
        lines.append("")
        lines.append("## 未解決の疑問")
        lines.append("- （未記入）")
        return "\n".join(lines)

    def _build_rule_based_links(self, notes: list[dict[str, Any]]) -> list[str]:
        """ルールベースのリンク一覧を作成."""
        sorted_notes = self._sort_notes_by_similarity(notes)
        lines: list[str] = []
        for note in sorted_notes:
            file_path = Path(note.get("file_path", ""))
            note_name = file_path.stem or note.get("title", "Untitled")
            atomic_concept = note.get("atomic_concept", "")
            if atomic_concept:
                lines.append(f"- [[{note_name}]]：{atomic_concept}")
            else:
                lines.append(f"- [[{note_name}]]：関連ノート")
        return lines

    def _sort_notes_by_similarity(self, notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """類似度でノートをソート."""
        if len(notes) <= 1:
            return notes
        base_embedding = notes[0].get("body_embedding")
        if not base_embedding:
            return notes
        return sorted(
            notes,
            key=lambda n: cosine_similarity(
                base_embedding,
                n.get("body_embedding", []),
            ),
            reverse=True,
        )

    def _build_llm_body(
        self,
        name: str,
        notes: list[dict[str, Any]],
    ) -> tuple[str, str]:
        """LLMでMOC本文を生成（QUESTION行付き）.

        Args:
            name: MOC の名前
            notes: 含まれるノートのリスト

        Returns:
            tuple[str, str]: (問い, 本文)

        Raises:
            RuntimeError: LLM生成に失敗した場合
        """
        notes_list = "\n".join(
            f"- {Path(note.get('file_path', '')).stem}: {note.get('atomic_concept', '')}"
            for note in notes
        )
        prompt = f"""以下の関連ノートを使ってMOC本文を作成してください。

【必須ルール】
1. 出力の1行目は必ず `QUESTION: ...` で開始する
2. 各リンクには文脈コメントを付ける（例: `- [[ノート名]]：...`）
3. 必ず以下の見出し構成を含める
   - # 【問い】...
   - ## この問いの背景
   - ## 関連するAtomicノート
   - ## 現時点での暫定的な答え
   - ## 未解決の疑問
4. リンクに含めるノートは下記一覧のものだけを使う

【対象ノート一覧】
{notes_list}

【出力形式】
QUESTION: ここに問いを書く
# 【問い】ここに問いを書く

## この問いの背景
（2-3文）

## 関連するAtomicノート
- [[ノート名]]：文脈コメント

## 現時点での暫定的な答え
（数文）

## 未解決の疑問
- 疑問1
"""
        try:
            response = self.llm_service._generate_with_retry(prompt)
        except Exception as exc:
            logger.error(f"LLMによるMOC本文生成に失敗: {exc}")
            raise RuntimeError(f"LLMによるMOC本文生成に失敗: {exc}") from exc

        if not response.strip():
            raise RuntimeError("LLMが空のレスポンスを返しました")

        question_match = re.search(r"^QUESTION:\s*(.+)", response, re.MULTILINE)
        if not question_match:
            raise RuntimeError(
                "LLMレスポンスにQUESTION行が含まれていません"
            )

        question = question_match.group(1).strip()
        body = re.sub(r"^QUESTION:\s*.+\n?", "", response, flags=re.MULTILINE)

        return question, body.strip()

    def _ensure_link_coverage(self, body: str, notes: list[dict[str, Any]]) -> str:
        """LLM出力に不足リンクがある場合、ルールベースで補完."""
        missing: list[dict[str, Any]] = []
        for note in notes:
            note_name = Path(note.get("file_path", "")).stem
            if note_name and f"[[{note_name}]]" not in body:
                missing.append(note)

        if not missing:
            return body

        lines = [body, "", "## 関連するAtomicノート（補完）", ""]
        lines.extend(self._build_rule_based_links(missing))
        return "\n".join(lines)

    def _save_moc(self, moc_name: str, content: str) -> Path:
        """MOC を保存.

        Args:
            moc_name: MOC ファイル名（拡張子なし）
            content: Markdown コンテンツ

        Returns:
            Path: 保存されたファイルのパス
        """
        try:
            moc_dir = self.vault_path / "03_MOC"
            moc_dir.mkdir(parents=True, exist_ok=True)

            date_str = datetime.now().strftime("%Y%m%d")

            # ファイル名を生成（MOC名_YYYYMMDD.md）
            safe_name = re.sub(r'[<>:"/\\|?*]', '', moc_name)
            file_path = moc_dir / f"{safe_name}_{date_str}.md"

            # 重複チェック（同名ファイルがある場合は連番を追加）
            counter = 1
            while file_path.exists():
                file_path = moc_dir / f"{safe_name}_{date_str}_{counter}.md"
                counter += 1

            # ファイルを保存
            file_path.write_text(content, encoding="utf-8")

            logger.info(f"MOC 保存: {file_path.name}")
            return file_path

        except Exception as exc:
            logger.error(f"MOC 保存に失敗: {exc}")
            raise
