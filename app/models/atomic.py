"""Atomic notes API request/response models."""

from pydantic import BaseModel, Field


class AtomicSplitRequest(BaseModel):
    """Summary を Atomic notes に分解するリクエスト."""

    summary_file_path: str = Field(
        ...,
        description="Summary ファイルのパス（Vault からの相対パス）",
        examples=["01_Summary/VTuber配信メモ_20250115_Summary.md"],
    )


class AtomicSplitResponse(BaseModel):
    """Atomic notes 分解のレスポンス."""

    success: bool = Field(..., description="処理成功/失敗")
    message: str = Field(..., description="メッセージ")
    atomic_notes_count: int = Field(
        ..., description="生成されたアトミック・ノートの数"
    )
    atomic_notes: list[dict] = Field(
        default_factory=list, description="生成されたアトミック・ノートのリスト"
    )


class AtomicScoreResponse(BaseModel):
    """アトミック性評価のレスポンス."""

    file_path: str = Field(..., description="ファイルパス")
    total_score: float = Field(..., description="総合スコア（0.0-1.0）")
    scores: dict[str, float] = Field(..., description="各基準のスコア")
    grade: str = Field(..., description="評価グレード（A-F）")
    suggestions: list[str] = Field(..., description="改善提案")


class MOCGenerateRequest(BaseModel):
    """MOC 生成リクエスト."""

    moc_type: str = Field(
        ...,
        description="MOC のタイプ（tag/concept/auto）",
        examples=["tag", "concept", "auto"],
    )
    name: str | None = Field(
        None,
        description="対象名（tag の場合はタグ名、concept の場合は概念名）",
        examples=["マーケティング", "AI動画集客戦略"],
    )
    min_notes: int = Field(
        3, description="最小ノート数（この数未満の場合は生成しない）"
    )
    max_mocs: int = Field(
        10, description="最大生成数（auto モードの場合のみ有効）"
    )


class MOCGenerateResponse(BaseModel):
    """MOC 生成のレスポンス."""

    success: bool = Field(..., description="処理成功/失敗")
    message: str = Field(..., description="メッセージ")
    moc_files: list[str] = Field(
        default_factory=list, description="生成された MOC ファイルのパス"
    )
    moc_count: int = Field(0, description="生成された MOC の数")


class PipelineStatsResponse(BaseModel):
    """パイプライン統計情報のレスポンス."""

    stages: dict[str, int] = Field(..., description="各ステージのファイル数")
    total_files: int = Field(..., description="全ファイル数")
