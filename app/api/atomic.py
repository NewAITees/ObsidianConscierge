"""Atomic notes API endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.core.atomic_splitter import AtomicSplitter
from app.core.atomic_scorer import AtomicScorer
from app.core.config import get_settings
from app.models.atomic import (
    AtomicSplitRequest,
    AtomicSplitResponse,
    AtomicScoreResponse,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["atomic"])


def get_llm_service() -> LLMService:
    """LLMService を取得（依存性注入）."""
    settings = get_settings()
    return LLMService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_llm_model,
        keep_alive=settings.ollama_keep_alive,
    )


def get_atomic_splitter(
    llm_service: LLMService = Depends(get_llm_service),
) -> AtomicSplitter:
    """AtomicSplitter を取得（依存性注入）."""
    settings = get_settings()
    return AtomicSplitter(llm_service, settings)


def get_atomic_scorer(
    llm_service: LLMService = Depends(get_llm_service),
) -> AtomicScorer:
    """AtomicScorer を取得（依存性注入）."""
    settings = get_settings()
    return AtomicScorer(llm_service, settings)


@router.post("/atomic/split", response_model=AtomicSplitResponse)
async def split_summary_to_atomic(
    request: AtomicSplitRequest,
    atomic_splitter: AtomicSplitter = Depends(get_atomic_splitter),
) -> AtomicSplitResponse:
    """Summary ファイルを Atomic notes に分解する.

    Args:
        request: 分解リクエスト
        atomic_splitter: AtomicSplitter（依存性注入）

    Returns:
        AtomicSplitResponse: 分解結果

    Raises:
        HTTPException: ファイルが見つからない場合（404）または処理失敗（500）
    """
    try:
        settings = get_settings()
        vault_path = Path(settings.obsidian_vault_path)
        summary_file = vault_path / request.summary_file_path

        if not summary_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Summary file not found: {request.summary_file_path}",
            )

        # Atomic notes に分解
        atomic_notes = atomic_splitter.split_into_atomic_notes(summary_file)

        if not atomic_notes:
            return AtomicSplitResponse(
                success=False,
                message="Failed to split into atomic notes",
                atomic_notes_count=0,
                atomic_notes=[],
            )

        # 保存
        saved_files = atomic_splitter.save_atomic_notes(atomic_notes)

        return AtomicSplitResponse(
            success=True,
            message=f"Successfully split into {len(atomic_notes)} atomic notes",
            atomic_notes_count=len(atomic_notes),
            atomic_notes=[
                {
                    "title": note["title"],
                    "file_path": str(
                        Path(file).relative_to(vault_path)
                    ),
                    "tags": note["tags"],
                    "atomic_concept": note["atomic_concept"],
                }
                for note, file in zip(atomic_notes, saved_files)
            ],
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Atomic split failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Atomic split failed: {str(exc)}",
        ) from exc


@router.get("/atomic/score/{file_path:path}", response_model=AtomicScoreResponse)
async def score_atomic_note(
    file_path: str,
    atomic_scorer: AtomicScorer = Depends(get_atomic_scorer),
) -> AtomicScoreResponse:
    """指定されたアトミック・ノートをスコアリング.

    Args:
        file_path: ファイルパス（Vault からの相対パス）
        atomic_scorer: AtomicScorer（依存性注入）

    Returns:
        AtomicScoreResponse: スコアリング結果

    Raises:
        HTTPException: ファイルが見つからない場合（404）または処理失敗（500）
    """
    try:
        settings = get_settings()
        vault_path = Path(settings.obsidian_vault_path)
        target_file = vault_path / file_path

        if not target_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {file_path}",
            )

        # スコアリング実行
        result = atomic_scorer.score_atomic_note(target_file)

        return AtomicScoreResponse(**result)

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Atomic scoring failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Atomic scoring failed: {str(exc)}",
        ) from exc


@router.get("/atomic/scores", response_model=list[AtomicScoreResponse])
async def score_all_atomic_notes(
    atomic_scorer: AtomicScorer = Depends(get_atomic_scorer),
) -> list[AtomicScoreResponse]:
    """全アトミック・ノートをスコアリング.

    Args:
        atomic_scorer: AtomicScorer（依存性注入）

    Returns:
        list[AtomicScoreResponse]: スコアリング結果のリスト

    Raises:
        HTTPException: 処理失敗（500）
    """
    try:
        # 全スコアリング実行
        results = atomic_scorer.score_all_atomic_notes()

        return [AtomicScoreResponse(**result) for result in results]

    except Exception as exc:
        logger.error(f"Atomic scoring failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Atomic scoring failed: {str(exc)}",
        ) from exc

