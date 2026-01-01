"""Atomic scorer - evaluates how "atomic" a note is.

アトミック・ノートの品質を評価し、1ファイル1テーマの原則に従っているか判定する。
"""

import logging
import re
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AtomicScorer:
    """アトミック性評価サービス.

    以下の基準でノートを評価し、スコアを算出する:
    1. 単一概念性（single_concept）: 1つのテーマに集中しているか
    2. 再利用可能性（reusability）: 他の文脈でも使えるか
    3. 独立性（independence）: 単体で理解できるか
    4. 長さの適切性（length_score）: 200〜800字が理想
    5. タイトル品質（title_quality）: 問い形式が推奨
    6. タグの適切性（tag_appropriateness）: 関連タグが付いているか
    """

    def __init__(
        self,
        llm_service: LLMService,
        settings: Settings
    ) -> None:
        """AtomicScorer を初期化.

        Args:
            llm_service: LLM呼び出しサービス
            settings: 設定
        """
        self.llm_service = llm_service
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

        # スコアリングの重み（合計 = 1.0）
        self.weights = {
            "single_concept": 0.30,  # 最重要
            "reusability": 0.20,
            "independence": 0.20,
            "length_score": 0.15,
            "title_quality": 0.10,
            "tag_appropriateness": 0.05,
        }

    def score_atomic_note(self, file_path: Path) -> dict[str, Any]:
        """アトミック・ノートをスコアリング.

        Args:
            file_path: 対象ファイルのパス

        Returns:
            dict[str, Any]: スコアリング結果（total_score, 各基準のスコア、改善提案等）
        """
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

            # ファイルを読み込み
            content = file_path.read_text(encoding="utf-8")

            # メタデータを抽出
            metadata = self._extract_metadata(content)
            body = self._extract_body(content)

            # 各基準でスコアリング
            scores = {
                "single_concept": self._score_single_concept(body),
                "reusability": self._score_reusability(body),
                "independence": self._score_independence(body),
                "length_score": self._score_length(body),
                "title_quality": self._score_title_quality(metadata.get("title", "")),
                "tag_appropriateness": self._score_tags(metadata.get("tags", [])),
            }

            # 総合スコアを計算（重み付き平均）
            total_score = sum(
                scores[key] * self.weights[key]
                for key in scores
            )

            # 改善提案を生成
            suggestions = self._generate_suggestions(scores, metadata, body)

            result = {
                "file_path": str(file_path),
                "total_score": round(total_score, 2),
                "scores": {k: round(v, 2) for k, v in scores.items()},
                "grade": self._get_grade(total_score),
                "suggestions": suggestions,
            }

            logger.info(
                f"スコアリング完了: {file_path.name} - "
                f"総合スコア: {result['total_score']:.2f} ({result['grade']})"
            )
            return result

        except Exception as exc:
            logger.error(f"スコアリングに失敗: {file_path.name} - {exc}")
            return {
                "file_path": str(file_path),
                "total_score": 0.0,
                "scores": {},
                "grade": "F",
                "suggestions": ["エラーが発生しました"],
            }

    def _extract_metadata(self, content: str) -> dict[str, Any]:
        """Frontmatter からメタデータを抽出.

        Args:
            content: ファイルコンテンツ

        Returns:
            dict[str, Any]: メタデータ（title, tags等）
        """
        metadata: dict[str, Any] = {}

        # Frontmatter を抽出
        frontmatter_match = re.search(
            r"^---\n(.*?)\n---",
            content,
            re.DOTALL | re.MULTILINE
        )

        if not frontmatter_match:
            return metadata

        frontmatter = frontmatter_match.group(1)

        # title を抽出
        title_match = re.search(r'title:\s*["\']?(.+?)["\']?(?=\n|$)', frontmatter)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        # tags を抽出
        tags_match = re.search(r'tags:\s*\[(.+?)\]', frontmatter)
        if tags_match:
            tags_str = tags_match.group(1)
            metadata["tags"] = [
                tag.strip().strip('"\'')
                for tag in tags_str.split(",")
            ]
        else:
            metadata["tags"] = []

        return metadata

    def _extract_body(self, content: str) -> str:
        """Frontmatter を除いた本文を抽出.

        Args:
            content: ファイルコンテンツ

        Returns:
            str: 本文テキスト
        """
        # Frontmatter を除去
        body = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL | re.MULTILINE)

        # Markdown 記法を除去（簡易版）
        body = re.sub(r"#+ ", "", body)  # 見出し
        body = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", body)  # リンク
        body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)  # ウィキリンク

        return body.strip()

    def _score_single_concept(self, body: str) -> float:
        """単一概念性をスコアリング（ルールベース）.

        Args:
            body: 本文テキスト

        Returns:
            float: スコア（0.0-1.0）
        """
        # 簡易版: セクション数でスコアリング
        # 理想は2-4セクション（概念、詳細、応用例程度）
        sections = re.findall(r"^##\s+", body, re.MULTILINE)
        section_count = len(sections)

        if 2 <= section_count <= 4:
            return 1.0
        elif section_count == 1 or section_count == 5:
            return 0.7
        elif section_count == 0 or section_count >= 6:
            return 0.4
        else:
            return 0.5

    def _score_reusability(self, body: str) -> float:
        """再利用可能性をスコアリング.

        Args:
            body: 本文テキスト

        Returns:
            float: スコア（0.0-1.0）
        """
        # 簡易版: 汎用的なキーワードの存在でスコアリング
        generic_keywords = [
            "応用例", "使用例", "パターン", "原則", "手法",
            "方法", "戦略", "アプローチ", "フレームワーク"
        ]

        score = 0.5  # ベーススコア

        for keyword in generic_keywords:
            if keyword in body:
                score += 0.1

        return min(1.0, score)

    def _score_independence(self, body: str) -> float:
        """独立性をスコアリング.

        Args:
            body: 本文テキスト

        Returns:
            float: スコア（0.0-1.0）
        """
        # 簡易版: 本文の長さと構造でスコアリング
        char_count = len(body)

        # 200字未満は独立性が低い
        if char_count < 200:
            return 0.3

        # 概念、詳細、応用例のセクションがあるか
        has_concept = "## 概念" in body
        has_details = "## 詳細" in body
        has_examples = "## 応用例" in body or "## 例" in body

        score = 0.5

        if has_concept:
            score += 0.2
        if has_details:
            score += 0.2
        if has_examples:
            score += 0.1

        return min(1.0, score)

    def _score_length(self, body: str) -> float:
        """長さの適切性をスコアリング.

        Args:
            body: 本文テキスト

        Returns:
            float: スコア（0.0-1.0）
        """
        char_count = len(body)

        # 理想は200〜800字
        if 200 <= char_count <= 800:
            return 1.0
        elif 150 <= char_count < 200 or 800 < char_count <= 1000:
            return 0.8
        elif 100 <= char_count < 150 or 1000 < char_count <= 1500:
            return 0.6
        elif char_count < 100:
            return 0.2
        else:  # 1500字超
            return 0.4

    def _score_title_quality(self, title: str) -> float:
        """タイトル品質をスコアリング.

        Args:
            title: タイトル

        Returns:
            float: スコア（0.0-1.0）
        """
        if not title:
            return 0.0

        # 問い形式が推奨
        question_markers = ["なぜ", "どう", "何が", "いつ", "どこで", "誰が"]

        for marker in question_markers:
            if marker in title:
                return 1.0

        # 疑問符がある
        if "？" in title or "?" in title:
            return 1.0

        # 普通のタイトル
        return 0.6

    def _score_tags(self, tags: list[str]) -> float:
        """タグの適切性をスコアリング.

        Args:
            tags: タグリスト

        Returns:
            float: スコア（0.0-1.0）
        """
        tag_count = len(tags)

        # 理想は2-5個
        if 2 <= tag_count <= 5:
            return 1.0
        elif tag_count == 1 or tag_count == 6:
            return 0.7
        elif tag_count == 0 or tag_count >= 7:
            return 0.3
        else:
            return 0.5

    def _get_grade(self, score: float) -> str:
        """スコアから評価グレードを取得.

        Args:
            score: 総合スコア（0.0-1.0）

        Returns:
            str: グレード（A-F）
        """
        if score >= 0.9:
            return "A+"
        elif score >= 0.8:
            return "A"
        elif score >= 0.7:
            return "B"
        elif score >= 0.6:
            return "C"
        elif score >= 0.5:
            return "D"
        else:
            return "F"

    def _generate_suggestions(
        self,
        scores: dict[str, float],
        metadata: dict[str, Any],
        body: str
    ) -> list[str]:
        """改善提案を生成.

        Args:
            scores: 各基準のスコア
            metadata: メタデータ
            body: 本文

        Returns:
            list[str]: 改善提案のリスト
        """
        suggestions: list[str] = []

        # 単一概念性が低い
        if scores["single_concept"] < 0.6:
            suggestions.append(
                "複数の概念が混在している可能性があります。"
                "1ノート1概念に分割することを検討してください。"
            )

        # 再利用可能性が低い
        if scores["reusability"] < 0.6:
            suggestions.append(
                "具体的すぎる内容になっていませんか？"
                "より汎用的な知識として抽出できないか検討してください。"
            )

        # 独立性が低い
        if scores["independence"] < 0.6:
            suggestions.append(
                "単体で理解できる内容にしましょう。"
                "概念、詳細、応用例のセクションを追加してください。"
            )

        # 長さが不適切
        char_count = len(body)
        if char_count < 200:
            suggestions.append(
                f"本文が短すぎます（{char_count}字）。"
                "詳細説明や応用例を追加してください。"
            )
        elif char_count > 1000:
            suggestions.append(
                f"本文が長すぎます（{char_count}字）。"
                "複数のアトミック・ノートに分割することを検討してください。"
            )

        # タイトルが問い形式でない
        if scores["title_quality"] < 0.8:
            suggestions.append(
                "タイトルを問い形式にすると良いでしょう。"
                "例: 「なぜ○○は△△なのか」"
            )

        # タグが少ない
        if len(metadata.get("tags", [])) < 2:
            suggestions.append(
                "タグを2-5個追加して、検索性を向上させましょう。"
            )

        return suggestions

    def score_all_atomic_notes(self) -> list[dict[str, Any]]:
        """全アトミック・ノートをスコアリング.

        Returns:
            list[dict[str, Any]]: スコアリング結果のリスト
        """
        try:
            atomic_dir = self.vault_path / "02_Atomic"

            if not atomic_dir.exists():
                logger.warning("02_Atomic ディレクトリが存在しません")
                return []

            # 全 .md ファイルを取得
            files = list(atomic_dir.glob("*.md"))

            if not files:
                logger.info("対象ファイルがありません")
                return []

            results: list[dict[str, Any]] = []

            for file_path in files:
                result = self.score_atomic_note(file_path)
                results.append(result)

            # スコアの降順でソート
            results.sort(key=lambda x: x["total_score"], reverse=True)

            logger.info(f"全スコアリング完了: {len(results)}件")
            return results

        except Exception as exc:
            logger.error(f"全スコアリングに失敗: {exc}")
            return []
