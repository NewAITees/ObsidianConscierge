"""Search request and response models."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    """検索リクエストモデル"""

    q: str = Field(..., description="検索クエリ（自然文）", min_length=1)
    tags: str | None = Field(
        default=None,
        description="タグフィルタ（カンマ区切り）",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="取得件数（1-100）",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="オフセット（ページネーション用）",
    )

    @field_validator("q")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """クエリのバリデーション"""
        if not v or not v.strip():
            msg = "Query cannot be empty"
            raise ValueError(msg)
        return v.strip()

    def get_tags_list(self) -> list[str] | None:
        """タグ文字列をリストに変換"""
        if not self.tags:
            return None
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]


class SearchResultItem(BaseModel):
    """検索結果の1件を表現するモデル"""

    id: str = Field(..., description="記事ID（ファイルパス）")
    title: str = Field(..., description="記事タイトル")
    summary: str = Field(..., description="サマリーテキスト")
    similarity: float = Field(..., description="類似度スコア（0.0-1.0）", ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list, description="タグリスト")
    file_path: str = Field(..., description="ファイルパス")
    modified: str | None = Field(default=None, description="更新日時（ISO形式）")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchResultItem":
        """辞書からSearchResultItemを作成"""
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            similarity=data.get("similarity", 0.0),
            tags=data.get("tags", []),
            file_path=data.get("file_path", ""),
            modified=data.get("modified"),
        )


class SearchResponse(BaseModel):
    """検索レスポンスモデル"""

    results: list[SearchResultItem] = Field(..., description="検索結果リスト")
    total: int = Field(..., description="総件数", ge=0)
    page: int = Field(..., description="現在のページ番号（1始まり）", ge=1)
    limit: int = Field(..., description="1ページあたりの件数", ge=1)

    @classmethod
    def from_results(
        cls,
        results: list[dict[str, Any]],
        limit: int,
        offset: int,
    ) -> "SearchResponse":
        """検索結果からSearchResponseを作成"""
        total = len(results)
        page = (offset // limit) + 1 if limit > 0 else 1

        result_items = [SearchResultItem.from_dict(r) for r in results]

        return cls(
            results=result_items,
            total=total,
            page=page,
            limit=limit,
        )

