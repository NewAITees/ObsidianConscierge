"""Search API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.search import SearchService
from app.models.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/api/v1", tags=["search"])


def get_search_service(request: Request) -> SearchService:
    """
    検索サービスを取得（依存性注入）

    Args:
        request: FastAPI Requestオブジェクト

    Returns:
        SearchService: 検索サービスインスタンス
    """
    return request.app.state.search_service


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str,
    tags: str | None = None,
    limit: int = 20,
    offset: int = 0,
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """
    セマンティック検索を実行する

    Args:
        q: 検索クエリ（自然文、必須）
        tags: タグフィルタ（カンマ区切り、オプション）
        limit: 取得件数（デフォルト: 20）
        offset: オフセット（ページネーション用、デフォルト: 0）
        search_service: 検索サービス（依存性注入）

    Returns:
        SearchResponse: 検索結果

    Raises:
        HTTPException: バリデーションエラー（422）またはサーバーエラー（500）時
    """
    try:
        # リクエストモデルを作成（バリデーションも実行される）
        request_model = SearchRequest(q=q, tags=tags, limit=limit, offset=offset)

        # タグリストを取得
        tags_list = request_model.get_tags_list()

        # 検索実行
        results = search_service.search(
            query=request_model.q,
            limit=request_model.limit,
            tags=tags_list,
        )

        # レスポンスを作成
        response = SearchResponse.from_results(
            results=results,
            limit=request_model.limit,
            offset=request_model.offset,
        )

        return response

    except ValueError as exc:
        # バリデーションエラー（Pydanticのバリデーションエラー）
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(exc)}",
        ) from exc
    except Exception as exc:
        # その他のエラー（サーバーエラー）
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(exc)}",
        ) from exc

