"""FastAPI application main module."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import atomic, config, moc, pipeline, reports, search
from app.core.config import Settings, get_settings
from app.core.search import SearchService
from app.services.embedding_service import EmbeddingService
from app.services.vector_db_service import VectorDBService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    アプリケーションのライフサイクル管理

    Args:
        app: FastAPIアプリケーションインスタンス
    """
    # 起動時の初期化処理
    settings = get_settings()

    # サービス層の初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
    embedding_service = EmbeddingService()

    # 検索サービスの初期化
    search_service = SearchService(
        vector_db_service=vector_db_service,
        embedding_service=embedding_service,
    )

    # アプリケーションコンテキストに保存
    app.state.vector_db_service = vector_db_service
    app.state.embedding_service = embedding_service
    app.state.search_service = search_service

    yield

    # 終了時のクリーンアップ処理
    # （必要に応じて実装）


def create_app() -> FastAPI:
    """
    FastAPIアプリケーションを作成

    Returns:
        FastAPI: アプリケーションインスタンス
    """
    settings = get_settings()

    app = FastAPI(
        title="ObsidianConscierge",
        description="AI-driven knowledge management system for Obsidian",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS設定（必要に応じて）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 本番環境では適切なオリジンを指定
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ルーターを登録
    app.include_router(search.router)
    app.include_router(reports.router)
    app.include_router(config.router)
    app.include_router(atomic.router)
    app.include_router(moc.router)
    app.include_router(pipeline.router)

    # 静的ファイルの配信
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ルートエンドポイント（フロントエンドUI）
    @app.get("/")
    async def root() -> FileResponse:
        """
        ルートエンドポイント（フロントエンドUI）

        Returns:
            FileResponse: index.html
        """
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        # フォールバック: 静的ファイルが存在しない場合
        return {"message": "ObsidianConscierge API", "docs": "/docs"}

    # ヘルスチェックエンドポイント
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """
        ヘルスチェックエンドポイント

        Returns:
            dict: ステータス情報
        """
        return {"status": "ok"}

    return app


# アプリケーションインスタンス（uvicorn用）
# uvicorn app.main:app で実行する場合に必要
# 注意: モジュールインポート時に初期化されるため、.envファイルが存在しない場合はエラーになる
# テスト時は create_app() を直接呼び出すため、この変数は使用されない
try:
    app = create_app()
except Exception as exc:
    # 設定が不足している場合（テスト時など）は None にしておく
    # 実際の実行時は、.envファイルが存在することを前提とする
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(
        "Failed to create app at module level (this is OK for tests): %s",
        exc,
    )
    app = None  # type: ignore[assignment]
