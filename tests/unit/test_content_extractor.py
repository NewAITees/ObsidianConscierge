"""Tests for content extraction functionality."""

import tempfile
from pathlib import Path

import pytest

from app.core.content_extractor import ContentExtractor
from app.models.article import ArticleContent


class TestContentExtractor:
    """コンテンツ抽出機能のテストクラス"""

    def test_extract_content_with_frontmatter(self) -> None:
        """YAML Frontmatterを含むMarkdownファイルの抽出テスト"""
        # Arrange: テスト用のMarkdownファイルを作成
        content = """---
title: テスト記事
tags:
  - python
  - testing
created: 2024-01-01T00:00:00Z
modified: 2024-01-02T00:00:00Z
---

# テスト記事

これはテスト用の記事です。

## セクション1

コンテンツがここにあります。
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            extractor = ContentExtractor()
            # Act: コンテンツを抽出
            result = extractor.extract_content(temp_path)

            # Assert: 抽出結果を検証
            assert isinstance(result, ArticleContent)
            assert result.title == "テスト記事"
            assert "テスト用の記事" in result.body
            assert "python" in result.metadata.get("tags", [])
            assert "testing" in result.metadata.get("tags", [])
            assert result.file_path == str(temp_path)
        finally:
            temp_path.unlink()

    def test_extract_content_without_frontmatter(self) -> None:
        """YAML FrontmatterがないMarkdownファイルの抽出テスト"""
        # Arrange: FrontmatterなしのMarkdownファイル
        content = """# タイトルなしの記事

これはFrontmatterがない記事です。

## セクション

コンテンツです。
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            extractor = ContentExtractor()
            # Act: コンテンツを抽出
            result = extractor.extract_content(temp_path)

            # Assert: 見出しからタイトルを抽出
            assert isinstance(result, ArticleContent)
            assert result.title == "タイトルなしの記事"
            assert "Frontmatterがない記事" in result.body
            assert result.metadata == {}
        finally:
            temp_path.unlink()

    def test_extract_content_cleans_markdown(self) -> None:
        """Markdownのクリーニングが正しく動作するかテスト"""
        # Arrange: 複雑なMarkdownコンテンツ
        content = """---
title: クリーニングテスト
---

# タイトル

これは**太字**と*斜体*のテキストです。

```python
def hello():
    print("Hello")
```

[リンク](https://example.com)

![画像](image.png)

[[内部リンク]]

#タグ

> 引用
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            extractor = ContentExtractor()
            # Act: コンテンツを抽出
            result = extractor.extract_content(temp_path)

            # Assert: クリーニングが正しく行われているか確認
            assert isinstance(result, ArticleContent)
            # コードブロックが削除されている
            assert "def hello()" not in result.body
            # リンクが削除されている
            assert "https://example.com" not in result.body
            # 画像リンクが削除されている
            assert "image.png" not in result.body
            # 内部リンクが削除されている
            assert "[[" not in result.body
            # タグが削除されている
            assert "#タグ" not in result.body
        finally:
            temp_path.unlink()

    def test_extract_content_calculates_word_count(self) -> None:
        """文字数の計算が正しく動作するかテスト"""
        # Arrange: 既知の文字数のコンテンツ
        content = """---
title: 文字数テスト
---

これは10文字のテキストです。これは20文字のテキストです。
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            extractor = ContentExtractor()
            # Act: コンテンツを抽出
            result = extractor.extract_content(temp_path)

            # Assert: 文字数が計算されている
            assert isinstance(result, ArticleContent)
            assert result.word_count > 0
        finally:
            temp_path.unlink()

    def test_extract_content_handles_empty_file(self) -> None:
        """空ファイルの処理テスト"""
        # Arrange: 空のファイル
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            temp_path = Path(f.name)

        try:
            extractor = ContentExtractor()
            # Act & Assert: 空ファイルの場合は例外が発生するか、空のコンテンツが返される
            result = extractor.extract_content(temp_path)
            assert isinstance(result, ArticleContent)
            assert result.title == ""
            assert result.body == ""
        finally:
            temp_path.unlink()

    def test_extract_content_handles_nonexistent_file(self) -> None:
        """存在しないファイルの処理テスト"""
        # Arrange: 存在しないファイルパス
        nonexistent_path = Path("/nonexistent/path/file.md")
        extractor = ContentExtractor()

        # Act & Assert: FileNotFoundErrorが発生する
        with pytest.raises(FileNotFoundError):
            extractor.extract_content(nonexistent_path)




