"""Content extraction from Markdown files."""

import re
from pathlib import Path

import frontmatter
from markdown import Markdown

from app.models.article import ArticleContent


class ContentExtractor:
    """Markdownファイルからコンテンツを抽出するクラス"""

    def __init__(self) -> None:
        """ContentExtractorを初期化"""
        self._markdown_parser = Markdown()

    def extract_content(self, file_path: Path) -> ArticleContent:
        """
        Markdownファイルからコンテンツを抽出する

        Args:
            file_path: 抽出対象のMarkdownファイルのパス

        Returns:
            ArticleContent: 抽出されたコンテンツ

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # ファイルを読み込む
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Frontmatterをパース
        post = frontmatter.loads(content)
        metadata: dict = dict(post.metadata) if post.metadata else {}

        # タイトルを取得（Frontmatterのtitle、なければ見出しから抽出）
        title = metadata.get("title", "")
        if not title:
            title = self._extract_title_from_content(post.content)

        # 本文をクリーニング
        cleaned_body = self._clean_markdown(post.content)

        # 文字数を計算
        word_count = len(cleaned_body)

        return ArticleContent(
            title=title,
            body=cleaned_body,
            metadata=metadata,
            file_path=str(file_path),
            word_count=word_count,
        )

    def _extract_title_from_content(self, content: str) -> str:
        """
        コンテンツから最初の見出しをタイトルとして抽出する

        Args:
            content: Markdownコンテンツ

        Returns:
            str: 抽出されたタイトル（見つからない場合は空文字列）
        """
        # 最初の見出し（# で始まる行）を探す
        lines = content.split("\n")
        for line in lines:
            # # で始まる行を探す
            match = re.match(r"^#+\s+(.+)$", line.strip())
            if match:
                return match.group(1).strip()
        return ""

    def _clean_markdown(self, text: str) -> str:
        """
        Markdownコンテンツをクリーニングする

        Args:
            text: クリーニング対象のMarkdownテキスト

        Returns:
            str: クリーニング済みテキスト
        """
        # 画像リンクを削除
        text = re.sub(r"!?\[[^\]]*\]\([^\)]*\)", " ", text)
        # コードブロックを削除
        text = re.sub(r"```[\s\S]*?```", " ", text)
        # インラインコードを削除
        text = re.sub(r"`[^`]*`", " ", text)
        # 見出し記号を削除
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        # YAML Frontmatterの区切り線を削除
        text = re.sub(r"^\s*---\s*$", "", text, flags=re.MULTILINE)
        # リスト記号を削除
        text = re.sub(r"^\s*[\*\-\+]\s+", " ", text, flags=re.MULTILINE)
        # 強調記号を削除
        text = re.sub(r"[\*_]{1,2}", " ", text)
        # URLを削除
        text = re.sub(r"https?://\S+", " ", text)
        # Obsidian内部リンクを削除
        text = re.sub(r"\[\[[^\]]*\]\]", " ", text)
        # Obsidian埋め込みを削除
        text = re.sub(r"\{\{[^\}]*\}\}", " ", text)
        # ブロック参照を削除
        text = re.sub(r"\^\w+", " ", text)
        # タグを削除
        text = re.sub(r"#\w+", " ", text)
        # 特殊文字を削除
        text = re.sub(r'[(){}\[\]"<>|]', " ", text)
        # 連続する空白を1つに
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()
