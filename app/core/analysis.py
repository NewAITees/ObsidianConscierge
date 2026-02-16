"""Analysis service for article analysis (duplicates, MOC candidates, etc.)."""

import logging
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import Settings, get_settings
from app.services.vector_db_service import VectorDBService

logger = logging.getLogger(__name__)
DATE_TAG_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    2つのベクトルのコサイン類似度を計算する

    Args:
        vec1: 第1ベクトル
        vec2: 第2ベクトル

    Returns:
        float: コサイン類似度（0.0-1.0）
    """
    if not vec1 or not vec2:
        return 0.0

    try:
        v1 = np.array(vec1, dtype=np.float32)
        v2 = np.array(vec2, dtype=np.float32)

        # ベクトルのノルムを計算
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        # ゼロベクトルの場合は類似度0を返す
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        # コサイン類似度を計算
        dot_product = np.dot(v1, v2)
        similarity = dot_product / (norm1 * norm2)

        # 値を0.0-1.0の範囲にクランプ
        return float(max(0.0, min(1.0, similarity)))
    except Exception as exc:
        logger.warning(f"コサイン類似度の計算に失敗しました: {exc}")
        return 0.0


class AnalysisService:
    """記事分析サービス（重複検知、MOC候補抽出、ランダムピックアップ等）"""

    def __init__(
        self,
        vector_db_service: VectorDBService,
        settings: Settings | None = None,
    ) -> None:
        """
        AnalysisServiceを初期化

        Args:
            vector_db_service: ベクトルDBサービス
            settings: 設定（Noneの場合はget_settings()で取得）
        """
        self.vector_db_service = vector_db_service
        self.settings = settings or get_settings()

    def _get_category_from_path(self, file_path: str) -> str | None:
        """ファイルパスからカテゴリを取得する（パイプラインフォルダは除外）。

        Args:
            file_path: 対象ファイルのパス

        Returns:
            str | None: カテゴリ名（該当なしの場合はNone）
        """
        if not file_path:
            return None

        path_parts = Path(file_path).parts
        if len(path_parts) <= 1:
            return None

        category = path_parts[0]
        if category in self.settings.pipeline_folders:
            return None

        return category

    def detect_duplicates(
        self, threshold: float | None = None
    ) -> list[dict[str, Any]]:
        """
        重複記事を検知する（コサイン類似度計算）

        Args:
            threshold: 重複判定の閾値（0.0-1.0、Noneの場合は設定値を使用）

        Returns:
            List[Dict[str, Any]]: 重複ペアのリスト（各要素は {article1, article2, similarity} を含む）
        """
        threshold_value = threshold or self.settings.duplicate_threshold

        try:
            # 全記事を取得
            articles = self.vector_db_service.get_all_articles()

            if len(articles) < 2:
                return []

            duplicates: list[dict[str, Any]] = []

            # 全ペアで類似度を計算
            for i in range(len(articles)):
                article1 = articles[i]
                embedding1 = article1.get("body_embedding")

                if not embedding1:
                    continue

                for j in range(i + 1, len(articles)):
                    article2 = articles[j]
                    embedding2 = article2.get("body_embedding")

                    if not embedding2:
                        continue

                    # コサイン類似度を計算
                    similarity = cosine_similarity(embedding1, embedding2)

                    # 閾値以上の場合は重複として記録
                    if similarity >= threshold_value:
                        duplicates.append(
                            {
                                "article1": {
                                    "id": article1["id"],
                                    "title": article1["title"],
                                    "file_path": article1["file_path"],
                                },
                                "article2": {
                                    "id": article2["id"],
                                    "title": article2["title"],
                                    "file_path": article2["file_path"],
                                },
                                "similarity": similarity,
                            }
                        )

            # 類似度の降順でソート
            duplicates.sort(key=lambda x: x["similarity"], reverse=True)

            logger.info(f"重複検知: {len(duplicates)}件のペアを検出（閾値: {threshold_value}）")
            return duplicates

        except Exception as exc:
            logger.error(f"重複検知に失敗しました: {exc}")
            return []

    def _matches_excluded_path(self, file_path: str) -> bool:
        """MOC候補から除外すべきパスかどうかを判定する."""
        if not file_path:
            return True

        normalized_file_path = file_path.replace("\\", "/")
        for excluded_path in self.settings.moc_exclude_paths:
            normalized_excluded = excluded_path.replace("\\", "/").strip()
            if not normalized_excluded:
                continue
            if normalized_excluded in normalized_file_path:
                return True

        return False

    def _matches_excluded_title(self, title: str) -> bool:
        """MOC候補から除外すべきタイトルかどうかを判定する."""
        if not title:
            return True

        lower_title = title.lower()
        for keyword in self.settings.moc_exclude_title_keywords:
            if keyword and keyword.lower() in lower_title:
                return True

        return False

    def _is_excluded_tag(self, tag: str) -> bool:
        """MOC候補から除外すべきタグかどうかを判定する."""
        if not tag:
            return True

        normalized_tag = str(tag).strip()
        if not normalized_tag:
            return True

        if self.settings.moc_exclude_date_tags and DATE_TAG_PATTERN.fullmatch(normalized_tag):
            return True

        excluded_tags = {t.lower().strip() for t in self.settings.moc_exclude_tags if t.strip()}
        return normalized_tag.lower() in excluded_tags

    def _get_modified_datetime(self, article: dict[str, Any]) -> datetime | None:
        """記事の更新日時をdatetimeで取得する."""
        modified = article.get("modified")
        if not modified:
            return None

        try:
            if isinstance(modified, datetime):
                return modified
            if isinstance(modified, str):
                return datetime.fromisoformat(modified.replace("Z", "+00:00"))
        except Exception:
            return None

        return None

    def _calculate_candidate_score(
        self,
        candidate_type: str,
        candidate_name: str,
        group_articles: list[dict[str, Any]],
    ) -> float:
        """MOC候補のスコアを計算する."""
        count = len(group_articles)
        if count == 0:
            return 0.0

        category_set: set[str] = set()
        recent_count = 0
        noise_count = 0
        recent_threshold = datetime.now() - timedelta(days=180)

        for article in group_articles:
            file_path = str(article.get("file_path", ""))
            title = str(article.get("title", ""))
            category = self._get_category_from_path(file_path)
            if category:
                category_set.add(category)

            modified_at = self._get_modified_datetime(article)
            if modified_at and modified_at >= recent_threshold:
                recent_count += 1

            if self._matches_excluded_path(file_path) or self._matches_excluded_title(title):
                noise_count += 1

        # タグ候補側でのみ、タグ名自体のノイズもペナルティ対象にする
        if candidate_type == "tag" and self._is_excluded_tag(candidate_name):
            noise_count += count

        diversity_ratio = len(category_set) / count
        recency_ratio = recent_count / count
        noise_ratio = noise_count / count

        base_score = float(count)
        bonus = (diversity_ratio * 3.0) + (recency_ratio * 2.0)
        penalty = noise_ratio * 2.0
        return base_score + bonus - penalty

    def _article_to_candidate_item(self, article: dict[str, Any]) -> dict[str, str]:
        """候補内の記事表示用の辞書に変換する."""
        return {
            "id": str(article.get("id", "")),
            "title": str(article.get("title", "")),
            "file_path": str(article.get("file_path", "")),
        }

    def _build_candidates_from_groups(
        self,
        candidate_type: str,
        groups: dict[str, list[dict[str, Any]]],
        min_articles: int,
    ) -> list[dict[str, Any]]:
        """グループ化済み記事から候補を構築する."""
        candidates: list[dict[str, Any]] = []

        for name, group_articles in groups.items():
            if len(group_articles) < min_articles:
                continue

            score = self._calculate_candidate_score(candidate_type, name, group_articles)
            candidates.append(
                {
                    "type": candidate_type,
                    "name": name,
                    "articles": [self._article_to_candidate_item(a) for a in group_articles[:10]],
                    "count": len(group_articles),
                    "_score": score,
                }
            )

        return candidates

    def find_moc_candidates(
        self,
        min_articles: int = 3,
        top_n: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        MOC（Map of Contents）候補を抽出する

        タグやカテゴリが似ている記事をグループ化して、MOC候補として提案する

        Args:
            min_articles: 最小記事数（この数未満のグループは除外）
            top_n: 返却する候補件数（Noneの場合は設定値を使用）

        Returns:
            List[Dict[str, Any]]: MOC候補のリスト（各要素は {category, articles, count} を含む）
        """
        try:
            # 全記事を取得
            articles = self.vector_db_service.get_all_articles()

            if not articles:
                return []

            candidate_limit = top_n if top_n is not None else self.settings.moc_candidate_top_n
            candidate_limit = max(1, candidate_limit)

            filtered_articles = [
                article
                for article in articles
                if not self._matches_excluded_path(str(article.get("file_path", "")))
                and not self._matches_excluded_title(str(article.get("title", "")))
            ]

            if not filtered_articles:
                return []

            # タグでグループ化
            tag_groups: dict[str, list[dict[str, Any]]] = {}
            for article in filtered_articles:
                tags = article.get("tags", [])
                if not tags:
                    continue

                for tag in tags:
                    normalized_tag = str(tag).strip()
                    if self._is_excluded_tag(normalized_tag):
                        continue
                    if normalized_tag not in tag_groups:
                        tag_groups[normalized_tag] = []
                    tag_groups[normalized_tag].append(article)

            # カテゴリ（フォルダ）でグループ化
            category_groups: dict[str, list[dict[str, Any]]] = {}
            for article in filtered_articles:
                file_path = article.get("file_path", "")
                category = self._get_category_from_path(file_path)
                if not category:
                    continue
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(article)

            candidates = self._build_candidates_from_groups(
                "tag", tag_groups, min_articles
            ) + self._build_candidates_from_groups("category", category_groups, min_articles)

            candidates.sort(
                key=lambda x: (
                    float(x.get("_score", 0.0)),
                    int(x["count"]),
                ),
                reverse=True,
            )

            limited_candidates = candidates[:candidate_limit]
            for candidate in limited_candidates:
                candidate.pop("_score", None)

            logger.info(
                "MOC候補: %d件を抽出（フィルタ後記事数: %d件, top_n: %d）",
                len(limited_candidates),
                len(filtered_articles),
                candidate_limit,
            )
            return limited_candidates

        except Exception as exc:
            logger.error(f"MOC候補の抽出に失敗しました: {exc}")
            return []

    def get_random_pickups(
        self, count: int = 3, prefer_different_categories: bool = True
    ) -> list[dict[str, Any]]:
        """
        ランダムピックアップ記事を取得する（異分野優先）

        Args:
            count: 取得する記事数（デフォルト: 3）
            prefer_different_categories: 異分野優先フラグ（Trueの場合は異なるカテゴリから選択）

        Returns:
            List[Dict[str, Any]]: ピックアップ記事のリスト
        """
        try:
            # 全記事を取得
            articles = self.vector_db_service.get_all_articles()

            if not articles:
                return []

            if prefer_different_categories:
                # カテゴリでグループ化
                category_groups: dict[str, list[dict[str, Any]]] = {}
                uncategorized: list[dict[str, Any]] = []

                for article in articles:
                    file_path = article.get("file_path", "")
                    if not file_path:
                        uncategorized.append(article)
                        continue

                    category = self._get_category_from_path(file_path)
                    if not category:
                        uncategorized.append(article)
                        continue

                    if category not in category_groups:
                        category_groups[category] = []
                    category_groups[category].append(article)

                # 各カテゴリから1件ずつ選択
                pickups: list[dict[str, Any]] = []
                categories = list(category_groups.keys())
                random.shuffle(categories)  # カテゴリをランダムにシャッフル

                for category in categories:
                    if len(pickups) >= count:
                        break

                    group_articles = category_groups[category]
                    if group_articles:
                        selected = random.choice(group_articles)
                        pickups.append(
                            {
                                "id": selected["id"],
                                "title": selected["title"],
                                "file_path": selected["file_path"],
                                "summary": selected.get("summary", ""),
                                "tags": selected.get("tags", []),
                                "category": category,
                            }
                        )

                # まだ足りない場合は、残りのカテゴリからランダムに選択
                remaining_articles: list[dict[str, Any]] = []
                for _category, group_articles in category_groups.items():
                    for article in group_articles:
                        # 既に選択された記事は除外
                        if not any(p["id"] == article["id"] for p in pickups):
                            remaining_articles.append(article)

                # 未分類の記事も追加
                remaining_articles.extend(uncategorized)

                # ランダムに選択
                while len(pickups) < count and remaining_articles:
                    selected = random.choice(remaining_articles)
                    remaining_articles.remove(selected)
                    pickups.append(
                        {
                            "id": selected["id"],
                            "title": selected["title"],
                            "file_path": selected["file_path"],
                            "summary": selected.get("summary", ""),
                            "tags": selected.get("tags", []),
                            "category": None,
                        }
                    )

                logger.info(f"ランダムピックアップ: {len(pickups)}件を取得（異分野優先）")
                return pickups
            else:
                # 単純にランダムに選択
                selected = random.sample(articles, min(count, len(articles)))
                pickups = [
                    {
                        "id": a["id"],
                        "title": a["title"],
                        "file_path": a["file_path"],
                        "summary": a.get("summary", ""),
                        "tags": a.get("tags", []),
                        "category": None,
                    }
                    for a in selected
                ]

                logger.info(f"ランダムピックアップ: {len(pickups)}件を取得")
                return pickups

        except Exception as exc:
            logger.error(f"ランダムピックアップの取得に失敗しました: {exc}")
            return []

    def get_writing_statistics(
        self, since_date: datetime | None = None
    ) -> dict[str, Any]:
        """
        執筆統計を取得する

        Args:
            since_date: 開始日時（Noneの場合は昨日）

        Returns:
            Dict[str, Any]: 統計情報（new_count, updated_count, total_word_count等）
        """
        try:
            # 全記事を取得
            articles = self.vector_db_service.get_all_articles()

            if not articles:
                return {
                    "new_count": 0,
                    "updated_count": 0,
                    "total_word_count": 0,
                    "total_articles": 0,
                }

            # 開始日時を設定（デフォルトは昨日）
            if since_date is None:
                since_date = datetime.now() - timedelta(days=1)
                # 時刻を00:00:00に設定
                since_date = since_date.replace(hour=0, minute=0, second=0, microsecond=0)

            new_count = 0
            updated_count = 0
            total_word_count = 0

            for article in articles:
                word_count = article.get("word_count", 0)
                total_word_count += word_count

                # 作成日時を確認
                created_str = article.get("created")
                if created_str:
                    try:
                        if isinstance(created_str, str):
                            created = datetime.fromisoformat(
                                created_str.replace("Z", "+00:00")
                            )
                        else:
                            created = created_str

                        if created >= since_date:
                            new_count += 1
                    except Exception:
                        pass

                # 更新日時を確認
                modified_str = article.get("modified")
                if modified_str:
                    try:
                        if isinstance(modified_str, str):
                            modified = datetime.fromisoformat(
                                modified_str.replace("Z", "+00:00")
                            )
                        else:
                            modified = modified_str

                        if modified >= since_date:
                            # 作成日時が開始日時より前の場合は更新としてカウント
                            if created_str:
                                try:
                                    if isinstance(created_str, str):
                                        created = datetime.fromisoformat(
                                            created_str.replace("Z", "+00:00")
                                        )
                                    else:
                                        created = created_str

                                    if created < since_date:
                                        updated_count += 1
                                except Exception:
                                    pass
                            else:
                                updated_count += 1
                    except Exception:
                        pass

            return {
                "new_count": new_count,
                "updated_count": updated_count,
                "total_word_count": total_word_count,
                "total_articles": len(articles),
            }

        except Exception as exc:
            logger.error(f"執筆統計の取得に失敗しました: {exc}")
            return {
                "new_count": 0,
                "updated_count": 0,
                "total_word_count": 0,
                "total_articles": 0,
            }
