"""Reports API endpoints."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.analysis import AnalysisService
from app.core.config import Settings, get_settings
from app.models.report import DailyReportResponse
from app.services.vector_db_service import VectorDBService

router = APIRouter(prefix="/api/v1", tags=["reports"])


def get_analysis_service(request: Request) -> AnalysisService:
    """
    分析サービスを取得（依存性注入）

    Args:
        request: FastAPI Requestオブジェクト

    Returns:
        AnalysisService: 分析サービスインスタンス
    """
    settings = get_settings()
    vector_db_service = request.app.state.vector_db_service
    return AnalysisService(
        vector_db_service=vector_db_service,
        settings=settings,
    )


@router.get("/reports/daily/{date}", response_model=DailyReportResponse)
async def get_daily_report(
    date: str,
    duplicate_threshold: float | None = None,
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> DailyReportResponse:
    """
    デイリーレポートを取得する

    Args:
        date: レポート対象日（YYYY-MM-DD形式）
        duplicate_threshold: 重複検知の閾値（0.0-1.0、オプション）
        analysis_service: 分析サービス（依存性注入）

    Returns:
        DailyReportResponse: デイリーレポート

    Raises:
        HTTPException: バリデーションエラー（422）またはサーバーエラー（500）時
    """
    try:
        # 日付文字列をパース
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d")
            report_date = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid date format: {date}. Expected YYYY-MM-DD format.",
            ) from exc

        # 執筆統計を取得
        stats = analysis_service.get_writing_statistics(since_date=report_date)

        # 重複検知
        duplicates = analysis_service.detect_duplicates(threshold=duplicate_threshold)

        # ランダムピックアップ
        pickups = analysis_service.get_random_pickups(
            count=3, prefer_different_categories=True
        )

        # MOC候補
        moc_candidates = analysis_service.find_moc_candidates(
            min_articles=3, max_articles=20
        )

        # レスポンスを作成
        response = DailyReportResponse.from_analysis(
            date=report_date,
            stats=stats,
            duplicates=duplicates,
            pickups=pickups,
            moc_candidates=moc_candidates,
        )

        return response

    except HTTPException:
        raise
    except Exception as exc:
        # その他のエラー（サーバーエラー）
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate daily report: {str(exc)}",
        ) from exc


@router.get("/reports/daily", response_model=DailyReportResponse)
async def get_yesterday_report(
    duplicate_threshold: float | None = None,
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> DailyReportResponse:
    """
    昨日のデイリーレポートを取得する（日付指定なしの場合）

    Args:
        duplicate_threshold: 重複検知の閾値（0.0-1.0、オプション）
        analysis_service: 分析サービス（依存性注入）

    Returns:
        DailyReportResponse: デイリーレポート

    Raises:
        HTTPException: サーバーエラー（500）時
    """
    # 昨日の日付を計算
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    # 日付指定エンドポイントにリダイレクト
    return await get_daily_report(
        date=yesterday_str,
        duplicate_threshold=duplicate_threshold,
        analysis_service=analysis_service,
    )

