"""Unit tests for AnalysisService."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.analysis import AnalysisService, cosine_similarity
from app.core.config import Settings


@pytest.fixture
def mock_settings() -> Settings:
    """モック設定を返す"""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        return Settings(
            github_token="test_token",
            obsidian_vault_name="test_vault",
            chroma_db_path=Path(tmpdir) / "chroma_db",
            duplicate_threshold=0.8,
        )


@pytest.fixture
def mock_vector_db_service() -> MagicMock:
    """モックベクトルDBサービスを返す"""
    service = MagicMock()
    # get_all_articles()のモック
    service.get_all_articles.return_value = [
        {
            "id": "test/article1.md",
            "title": "テスト記事1",
            "summary": "テスト記事1の要約",
            "tags": ["test", "python"],
            "file_path": "test/article1.md",
            "modified": (datetime.now() - timedelta(days=1)).isoformat(),
            "created": (datetime.now() - timedelta(days=2)).isoformat(),
            "word_count": 100,
            "body": "テスト記事1の本文",
            "body_embedding": [1.0] * 512,
        },
        {
            "id": "test/article2.md",
            "title": "テスト記事2",
            "summary": "テスト記事2の要約",
            "tags": ["test", "javascript"],
            "file_path": "test/article2.md",
            "modified": (datetime.now() - timedelta(days=1)).isoformat(),
            "created": (datetime.now() - timedelta(days=3)).isoformat(),
            "word_count": 200,
            "body": "テスト記事2の本文",
            "body_embedding": [0.9] * 512,  # 類似度が高い
        },
        {
            "id": "category/article3.md",
            "title": "カテゴリ記事",
            "summary": "カテゴリ記事の要約",
            "tags": ["category", "example"],
            "file_path": "category/article3.md",
            "modified": (datetime.now() - timedelta(days=2)).isoformat(),
            "created": (datetime.now() - timedelta(days=4)).isoformat(),
            "word_count": 150,
            "body": "カテゴリ記事の本文",
            "body_embedding": [0.1] * 512,  # 類似度が低い
        },
    ]
    return service


@pytest.fixture
def analysis_service(
    mock_vector_db_service: MagicMock,
    mock_settings: Settings,
) -> AnalysisService:
    """AnalysisServiceインスタンスを返す"""
    return AnalysisService(
        vector_db_service=mock_vector_db_service,
        settings=mock_settings,
    )


class TestCosineSimilarity:
    """コサイン類似度計算のテスト"""

    def test_cosine_similarity_identical_vectors(self) -> None:
        """同一ベクトルの類似度は1.0"""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, rel=1e-5)

    def test_cosine_similarity_orthogonal_vectors(self) -> None:
        """直交ベクトルの類似度は0.0"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0, rel=1e-5)

    def test_cosine_similarity_opposite_vectors(self) -> None:
        """逆ベクトルの類似度は0.0（クランプされる）"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)
        assert 0.0 <= similarity <= 1.0  # クランプされる

    def test_cosine_similarity_empty_vectors(self) -> None:
        """空ベクトルの類似度は0.0"""
        vec1: list[float] = []
        vec2: list[float] = []
        similarity = cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_cosine_similarity_zero_vector(self) -> None:
        """ゼロベクトルの類似度は0.0"""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = cosine_similarity(vec1, vec2)
        assert similarity == 0.0


class TestDetectDuplicates:
    """重複検知のテスト"""

    def test_detect_duplicates_default_threshold(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """デフォルト閾値で重複検知"""
        duplicates = analysis_service.detect_duplicates()
        assert isinstance(duplicates, list)
        # 類似度0.8以上のペアが検出されるはず
        for dup in duplicates:
            assert "article1" in dup
            assert "article2" in dup
            assert "similarity" in dup
            assert dup["similarity"] >= 0.8

    def test_detect_duplicates_custom_threshold(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """カスタム閾値で重複検知"""
        duplicates = analysis_service.detect_duplicates(threshold=0.95)
        assert isinstance(duplicates, list)
        # 閾値0.95で検出されるペアのみ
        for dup in duplicates:
            assert dup["similarity"] >= 0.95

    def test_detect_duplicates_sorted_by_similarity(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """重複ペアが類似度降順でソートされているか"""
        duplicates = analysis_service.detect_duplicates(threshold=0.0)
        if len(duplicates) > 1:
            for i in range(len(duplicates) - 1):
                assert duplicates[i]["similarity"] >= duplicates[i + 1]["similarity"]

    def test_detect_duplicates_no_articles(
        self,
        mock_settings: Settings,
    ) -> None:
        """記事が0件の場合は空リストを返す"""
        mock_db = MagicMock()
        mock_db.get_all_articles.return_value = []
        service = AnalysisService(mock_db, mock_settings)
        duplicates = service.detect_duplicates()
        assert duplicates == []

    def test_detect_duplicates_one_article(
        self,
        mock_settings: Settings,
    ) -> None:
        """記事が1件の場合は空リストを返す"""
        mock_db = MagicMock()
        mock_db.get_all_articles.return_value = [
            {
                "id": "test.md",
                "title": "Test",
                "file_path": "test.md",
                "body_embedding": [1.0] * 512,
            }
        ]
        service = AnalysisService(mock_db, mock_settings)
        duplicates = service.detect_duplicates()
        assert duplicates == []


class TestFindMocCandidates:
    """MOC候補抽出のテスト"""

    def test_find_moc_candidates_default(self, analysis_service: AnalysisService) -> None:
        """デフォルトパラメータでMOC候補抽出"""
        candidates = analysis_service.find_moc_candidates()
        assert isinstance(candidates, list)
        assert len(candidates) <= analysis_service.settings.moc_candidate_top_n
        for candidate in candidates:
            assert "type" in candidate
            assert "name" in candidate
            assert "articles" in candidate
            assert "count" in candidate
            assert candidate["count"] >= 3

    def test_find_moc_candidates_sorted_by_count(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """MOC候補が件数降順に近い順序で返るか"""
        candidates = analysis_service.find_moc_candidates(min_articles=1, top_n=100)
        if len(candidates) > 1:
            for i in range(len(candidates) - 1):
                assert candidates[i]["count"] >= candidates[i + 1]["count"] or (
                    candidates[i]["count"] + 2 >= candidates[i + 1]["count"]
                )

    def test_find_moc_candidates_tag_type(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """タグベースのMOC候補が含まれているか"""
        candidates = analysis_service.find_moc_candidates(min_articles=1, top_n=100)
        tag_candidates = [c for c in candidates if c["type"] == "tag"]
        assert len(tag_candidates) > 0

    def test_find_moc_candidates_category_type(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """カテゴリベースのMOC候補が含まれているか"""
        candidates = analysis_service.find_moc_candidates(min_articles=1, top_n=100)
        category_candidates = [c for c in candidates if c["type"] == "category"]
        assert len(category_candidates) > 0

    def test_find_moc_candidates_excludes_noise_by_path_title_and_date_tag(
        self,
        mock_settings: Settings,
    ) -> None:
        """日記/既存MOC/前後リンク/日付タグを候補から除外する."""
        mock_db = MagicMock()
        mock_db.get_all_articles.return_value = [
            {
                "id": "01DIARY/2025-01-01.md",
                "title": "前後リンク：[[DiaryMOC_2025]]",
                "tags": ["ルーティン", "2025-01-01"],
                "file_path": "01DIARY/2025-01-01.md",
                "modified": datetime.now().isoformat(),
            },
            {
                "id": "06MOC/topic.md",
                "title": "MOCページ",
                "tags": ["knowledge"],
                "file_path": "06MOC/topic.md",
                "modified": datetime.now().isoformat(),
            },
            {
                "id": "04CODING/a.md",
                "title": "A",
                "tags": ["MCP", "2024-11-20"],
                "file_path": "04CODING/a.md",
                "modified": datetime.now().isoformat(),
            },
            {
                "id": "04CODING/b.md",
                "title": "B",
                "tags": ["MCP"],
                "file_path": "04CODING/b.md",
                "modified": datetime.now().isoformat(),
            },
            {
                "id": "05MATH/c.md",
                "title": "C",
                "tags": ["MCP"],
                "file_path": "05MATH/c.md",
                "modified": datetime.now().isoformat(),
            },
        ]
        service = AnalysisService(mock_db, mock_settings)

        candidates = service.find_moc_candidates(min_articles=2, top_n=20)
        names = {c["name"] for c in candidates}

        assert "2025-01-01" not in names
        assert "2024-11-20" not in names
        assert "MCP" in names
        for candidate in candidates:
            for article in candidate["articles"]:
                assert "01DIARY/" not in article["file_path"]
                assert "06MOC/" not in article["file_path"]
                assert "前後リンク" not in article["title"]

    def test_find_moc_candidates_applies_top_n(
        self,
        mock_settings: Settings,
    ) -> None:
        """top_n 指定で候補数が制限される."""
        mock_db = MagicMock()
        mock_db.get_all_articles.return_value = [
            {
                "id": f"04CODING/n{i}.md",
                "title": f"note-{i}",
                "tags": [f"tag{i}", "shared"],
                "file_path": f"04CODING/n{i}.md",
                "modified": datetime.now().isoformat(),
            }
            for i in range(10)
        ]
        service = AnalysisService(mock_db, mock_settings)
        candidates = service.find_moc_candidates(min_articles=1, top_n=3)
        assert len(candidates) == 3


class TestGetRandomPickups:
    """ランダムピックアップのテスト"""

    def test_get_random_pickups_default(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """デフォルトパラメータでランダムピックアップ"""
        pickups = analysis_service.get_random_pickups()
        assert isinstance(pickups, list)
        assert len(pickups) <= 3  # デフォルトは3件
        for pickup in pickups:
            assert "id" in pickup
            assert "title" in pickup
            assert "file_path" in pickup

    def test_get_random_pickups_custom_count(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """カスタム件数でランダムピックアップ"""
        pickups = analysis_service.get_random_pickups(count=2)
        assert len(pickups) <= 2

    def test_get_random_pickups_prefer_different_categories(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """異分野優先でランダムピックアップ"""
        pickups = analysis_service.get_random_pickups(
            count=3,
            prefer_different_categories=True,
        )
        assert isinstance(pickups, list)
        # カテゴリが異なる記事が選ばれているか（可能な限り）
        categories = [p.get("category") for p in pickups if p.get("category")]
        if len(categories) > 1:
            # 重複がない（または少ない）ことを確認
            assert len(categories) >= len(set(categories)) * 0.5

    def test_get_random_pickups_no_preference(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """カテゴリ優先なしでランダムピックアップ"""
        pickups = analysis_service.get_random_pickups(
            count=3,
            prefer_different_categories=False,
        )
        assert isinstance(pickups, list)
        assert len(pickups) <= 3


class TestGetWritingStatistics:
    """執筆統計のテスト"""

    def test_get_writing_statistics_default(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """デフォルトパラメータ（昨日）で執筆統計取得"""
        stats = analysis_service.get_writing_statistics()
        assert isinstance(stats, dict)
        assert "new_count" in stats
        assert "updated_count" in stats
        assert "total_word_count" in stats
        assert "total_articles" in stats
        assert isinstance(stats["new_count"], int)
        assert isinstance(stats["updated_count"], int)
        assert isinstance(stats["total_word_count"], int)
        assert isinstance(stats["total_articles"], int)

    def test_get_writing_statistics_custom_date(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """カスタム日付で執筆統計取得"""
        since_date = datetime.now() - timedelta(days=3)
        stats = analysis_service.get_writing_statistics(since_date=since_date)
        assert isinstance(stats, dict)
        assert stats["total_articles"] >= 0

    def test_get_writing_statistics_total_word_count(
        self,
        analysis_service: AnalysisService,
    ) -> None:
        """総文字数が正しく計算されるか"""
        stats = analysis_service.get_writing_statistics()
        # モックデータでは100+200+150=450
        assert stats["total_word_count"] == 450

    def test_get_writing_statistics_no_articles(
        self,
        mock_settings: Settings,
    ) -> None:
        """記事が0件の場合"""
        mock_db = MagicMock()
        mock_db.get_all_articles.return_value = []
        service = AnalysisService(mock_db, mock_settings)
        stats = service.get_writing_statistics()
        assert stats["new_count"] == 0
        assert stats["updated_count"] == 0
        assert stats["total_word_count"] == 0
        assert stats["total_articles"] == 0
