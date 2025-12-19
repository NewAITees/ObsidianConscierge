"""Report response models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WritingStatistics(BaseModel):
    """執筆統計モデル"""

    new_count: int = Field(..., description="新規記事数", ge=0)
    updated_count: int = Field(..., description="更新記事数", ge=0)
    total_word_count: int = Field(..., description="総文字数", ge=0)
    total_articles: int = Field(..., description="総記事数", ge=0)


class DuplicatePair(BaseModel):
    """重複ペアモデル"""

    article1: dict[str, str] = Field(..., description="記事1（id, title, file_path）")
    article2: dict[str, str] = Field(..., description="記事2（id, title, file_path）")
    similarity: float = Field(..., description="類似度（0.0-1.0）", ge=0.0, le=1.0)


class PickupArticle(BaseModel):
    """ピックアップ記事モデル"""

    id: str = Field(..., description="記事ID（ファイルパス）")
    title: str = Field(..., description="記事タイトル")
    file_path: str = Field(..., description="ファイルパス")
    summary: str = Field(default="", description="サマリーテキスト")
    tags: list[str] = Field(default_factory=list, description="タグリスト")
    category: str | None = Field(default=None, description="カテゴリ（フォルダ名）")


class MOCCandidate(BaseModel):
    """MOC候補モデル"""

    type: str = Field(..., description="候補タイプ（tag or category）")
    name: str = Field(..., description="候補名（タグ名またはカテゴリ名）")
    articles: list[dict[str, str]] = Field(
        ..., description="記事リスト（id, title, file_path）"
    )
    count: int = Field(..., description="記事数", ge=0)


class DailyReportResponse(BaseModel):
    """デイリーレポートレスポンスモデル"""

    date: str = Field(..., description="レポート対象日（YYYY-MM-DD形式）")
    generated_at: str = Field(..., description="生成日時（ISO形式）")
    statistics: WritingStatistics = Field(..., description="執筆統計")
    duplicates: list[DuplicatePair] = Field(
        default_factory=list, description="重複ペアのリスト"
    )
    pickups: list[PickupArticle] = Field(
        default_factory=list, description="ランダムピックアップ記事のリスト"
    )
    moc_candidates: list[MOCCandidate] = Field(
        default_factory=list, description="MOC候補のリスト"
    )

    @classmethod
    def from_analysis(
        cls,
        date: datetime,
        stats: dict[str, Any],
        duplicates: list[dict[str, Any]],
        pickups: list[dict[str, Any]],
        moc_candidates: list[dict[str, Any]],
    ) -> "DailyReportResponse":
        """
        分析結果からDailyReportResponseを作成

        Args:
            date: レポート対象日
            stats: 執筆統計
            duplicates: 重複ペアのリスト
            pickups: ピックアップ記事のリスト
            moc_candidates: MOC候補のリスト

        Returns:
            DailyReportResponse: レスポンスモデル
        """
        return cls(
            date=date.strftime("%Y-%m-%d"),
            generated_at=datetime.now().isoformat(),
            statistics=WritingStatistics(
                new_count=stats.get("new_count", 0),
                updated_count=stats.get("updated_count", 0),
                total_word_count=stats.get("total_word_count", 0),
                total_articles=stats.get("total_articles", 0),
            ),
            duplicates=[
                DuplicatePair(
                    article1=dup["article1"],
                    article2=dup["article2"],
                    similarity=dup["similarity"],
                )
                for dup in duplicates
            ],
            pickups=[
                PickupArticle(
                    id=pickup["id"],
                    title=pickup["title"],
                    file_path=pickup["file_path"],
                    summary=pickup.get("summary", ""),
                    tags=pickup.get("tags", []),
                    category=pickup.get("category"),
                )
                for pickup in pickups
            ],
            moc_candidates=[
                MOCCandidate(
                    type=candidate["type"],
                    name=candidate["name"],
                    articles=candidate["articles"],
                    count=candidate["count"],
                )
                for candidate in moc_candidates
            ],
        )

