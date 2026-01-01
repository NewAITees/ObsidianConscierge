"""MOC API endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.core.moc_generator import MOCGenerator
from app.models.atomic import MOCGenerateRequest, MOCGenerateResponse
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/moc", tags=["moc"])


def get_vector_db_service(request: Request) -> VectorDBService:
    """VectorDBService を取得（依存性注入）."""
    return request.app.state.vector_db_service


def get_embedding_service(request: Request) -> EmbeddingService:
    """EmbeddingService を取得（依存性注入）."""
    return request.app.state.embedding_service


def get_llm_service() -> LLMService:
    """LLMService を取得（依存性注入）."""
    settings = get_settings()
    return LLMService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_llm_model,
    )


def get_moc_generator(
    vector_db_service: VectorDBService = Depends(get_vector_db_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> MOCGenerator:
    """MOCGenerator を取得（依存性注入）."""
    settings = get_settings()
    return MOCGenerator(vector_db_service, llm_service, embedding_service, settings)


@router.post("/generate", response_model=MOCGenerateResponse)
async def generate_moc(
    request: MOCGenerateRequest,
    moc_generator: MOCGenerator = Depends(get_moc_generator),
) -> MOCGenerateResponse:
    """MOC (Map of Contents) を生成する."""
    try:
        settings = get_settings()
        vault_path = Path(settings.obsidian_vault_path)

        moc_files: list[Path] = []

        if request.moc_type == "tag":
            if not request.name:
                raise HTTPException(
                    status_code=422,
                    detail="Tag name is required for moc_type='tag'",
                )

            moc_file = moc_generator.generate_moc_from_tag(
                tag=request.name,
                min_notes=request.min_notes,
            )

            if moc_file:
                moc_files.append(moc_file)

        elif request.moc_type == "concept":
            if not request.name:
                raise HTTPException(
                    status_code=422,
                    detail="Concept name is required for moc_type='concept'",
                )

            moc_file = moc_generator.generate_moc_from_concept(
                concept=request.name,
                min_notes=request.min_notes,
            )

            if moc_file:
                moc_files.append(moc_file)

        elif request.moc_type == "auto":
            moc_files = moc_generator.generate_all_mocs(
                min_notes=request.min_notes,
                max_mocs=request.max_mocs,
            )

        else:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid moc_type: {request.moc_type}. Must be 'tag', 'concept', or 'auto'",
            )

        if not moc_files:
            return MOCGenerateResponse(
                success=False,
                message="No MOC files were generated (insufficient notes or no candidates found)",
                moc_files=[],
                moc_count=0,
            )

        return MOCGenerateResponse(
            success=True,
            message=f"Successfully generated {len(moc_files)} MOC file(s)",
            moc_files=[
                str(Path(file).relative_to(vault_path))
                for file in moc_files
            ],
            moc_count=len(moc_files),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"MOC generation failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"MOC generation failed: {str(exc)}",
        ) from exc
