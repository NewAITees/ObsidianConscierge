"""Article data models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ArticleContent:
    """記事のコンテンツを表現するデータクラス"""

    title: str
    """記事のタイトル"""
    body: str
    """クリーニング済みの本文"""
    metadata: dict
    """YAML Frontmatterから抽出されたメタデータ（tags, created, modified等）"""
    file_path: str
    """ファイルの相対パス"""
    word_count: int = 0
    """文字数（単語数）"""


@dataclass
class Article:
    """ベクトルDBに格納する記事データ"""

    id: str
    """ファイルパス（相対パス）"""
    title: str
    """記事のタイトル"""
    body: str
    """本文"""
    summary: str
    """サマリーテキスト（200字程度）"""
    tags: list[str]
    """タグリスト"""
    created: datetime | None
    """作成日時"""
    modified: datetime | None
    """更新日時"""
    file_path: str
    """ファイルパス"""
    body_embedding: list[float]
    """本文ベクトル（768次元）"""
    summary_embedding: list[float]
    """サマリーベクトル（768次元）"""
    word_count: int = 0
    """文字数"""


@dataclass
class FileChange:
    """Git変更検知で検出されたファイル変更情報"""

    file_path: str
    """ファイルパス（相対パス）"""
    change_type: str
    """変更タイプ: 'added', 'modified', 'deleted'"""
    commit_id: str
    """コミットID"""




