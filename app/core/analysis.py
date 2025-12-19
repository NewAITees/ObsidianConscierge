"""Analysis service for article analysis (duplicates, MOC candidates, etc.)."""

import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import Settings, get_settings
from app.services.vector_db_service import VectorDBService

logger = logging.getLogger(__name__)


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

    def find_moc_candidates(
        self, min_articles: int = 3, max_articles: int = 20
    ) -> list[dict[str, Any]]:
        """
        MOC（Map of Contents）候補を抽出する

        タグやカテゴリが似ている記事をグループ化して、MOC候補として提案する

        Args:
            min_articles: 最小記事数（この数未満のグループは除外）
            max_articles: 最大記事数（この数を超えるグループは除外）

        Returns:
            List[Dict[str, Any]]: MOC候補のリスト（各要素は {category, articles, count} を含む）
        """
        try:
            # 全記事を取得
            articles = self.vector_db_service.get_all_articles()

            if not articles:
                return []

            # タグでグループ化
            tag_groups: dict[str, list[dict[str, Any]]] = {}
            for article in articles:
                tags = article.get("tags", [])
                if not tags:
                    continue

                for tag in tags:
                    if tag not in tag_groups:
                        tag_groups[tag] = []
                    tag_groups[tag].append(article)

            # カテゴリ（フォルダ）でグループ化
            category_groups: dict[str, list[dict[str, Any]]] = {}
            for article in articles:
                file_path = article.get("file_path", "")
                if not file_path:
                    continue

                # ファイルパスからカテゴリ（最初のフォルダ）を抽出
                path_parts = Path(file_path).parts
                if len(path_parts) > 1:
                    category = path_parts[0]
                    if category not in category_groups:
                        category_groups[category] = []
                    category_groups[category].append(article)

            # MOC候補を構築
            candidates: list[dict[str, Any]] = []

            # タグベースの候補
            for tag, group_articles in tag_groups.items():
                if min_articles <= len(group_articles) <= max_articles:
                    candidates.append(
                        {
                            "type": "tag",
                            "name": tag,
                            "articles": [
                                {
                                    "id": a["id"],
                                    "title": a["title"],
                                    "file_path": a["file_path"],
                                }
                                for a in group_articles[:10]  # 最大10件まで表示
                            ],
                            "count": len(group_articles),
                        }
                    )

            # カテゴリベースの候補
            for category, group_articles in category_groups.items():
                if min_articles <= len(group_articles) <= max_articles:
                    candidates.append(
                        {
                            "type": "category",
                            "name": category,
                            "articles": [
                                {
                                    "id": a["id"],
                                    "title": a["title"],
                                    "file_path": a["file_path"],
                                }
                                for a in group_articles[:10]  # 最大10件まで表示
                            ],
                            "count": len(group_articles),
                        }
                    )

            # 記事数の降順でソート
            candidates.sort(key=lambda x: x["count"], reverse=True)

            logger.info(f"MOC候補: {len(candidates)}件を抽出")
            return candidates

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

                    # ファイルパスからカテゴリ（最初のフォルダ）を抽出
                    path_parts = Path(file_path).parts
                    if len(path_parts) > 1:
                        category = path_parts[0]
                        if category not in category_groups:
                            category_groups[category] = []
                        category_groups[category].append(article)
                    else:
                        uncategorized.append(article)

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
                for category, group_articles in category_groups.items():
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

