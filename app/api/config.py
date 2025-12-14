"""Configuration API endpoints."""

from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["config"])


@router.get("/config")
async def get_config(request: Request) -> dict[str, str]:
    """
    フロントエンド用の設定を取得

    Returns:
        dict: フロントエンドで使用する設定値
    """
    settings = get_settings()
    return {
        "obsidian_vault_name": settings.obsidian_vault_name,
    }

