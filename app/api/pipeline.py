"""Pipeline API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.pipeline_manager import PipelineManager
from app.models.atomic import PipelineStatsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


def get_pipeline_manager() -> PipelineManager:
    """PipelineManager を取得（依存性注入）."""
    settings = get_settings()
    return PipelineManager(settings)


@router.get("/status")
async def get_pipeline_status(
    pipeline_manager: PipelineManager = Depends(get_pipeline_manager),
) -> dict[str, object]:
    """パイプライン全体のステータスを取得."""
    try:
        status: dict[str, dict[str, object]] = {}
        total_files = 0

        for stage in pipeline_manager.stage_order:
            files = pipeline_manager.get_stage_files(stage)
            file_count = len(files)
            total_files += file_count

            latest_file = None
            if files:
                latest_file = max(files, key=lambda f: f.stat().st_mtime).name

            status[stage] = {
                "file_count": file_count,
                "latest_file": latest_file,
            }

        return {
            "pipeline_stages": status,
            "total_files": total_files,
        }

    except Exception as exc:
        logger.error(f"Pipeline status retrieval failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline status retrieval failed: {str(exc)}",
        ) from exc


@router.get("/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats(
    pipeline_manager: PipelineManager = Depends(get_pipeline_manager),
) -> PipelineStatsResponse:
    """パイプライン統計情報を取得."""
    try:
        stats = pipeline_manager.get_pipeline_statistics()
        total_files = sum(stats.values())

        return PipelineStatsResponse(
            stages=stats,
            total_files=total_files,
        )

    except Exception as exc:
        logger.error(f"Pipeline stats retrieval failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline stats retrieval failed: {str(exc)}",
        ) from exc
