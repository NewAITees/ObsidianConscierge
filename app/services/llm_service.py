"""LLM service using Ollama."""

import time
from typing import List

import ollama


class LLMService:
    """Ollamaを使用したLLMサービス"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        LLMServiceを初期化

        Args:
            base_url: OllamaサーバーのベースURL
            model: 使用するLLMモデル名
            max_retries: 最大リトライ回数
            retry_delay: リトライ間の待機時間（秒）
        """
        self.base_url = base_url
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def generate_summary(self, content: str, max_length: int = 200) -> str:
        """
        記事の内容からサマリーを生成する

        Args:
            content: 記事の本文
            max_length: サマリーの最大文字数

        Returns:
            str: 生成されたサマリー

        Raises:
            Exception: リトライ回数を超えても失敗した場合
        """
        prompt = (
            f"以下の記事を{max_length}字程度で要約してください。"
            "重要なキーワードや概念を含めてください。\n\n"
            f"{content}"
        )

        return self._generate_with_retry(prompt)

    def generate_tags(
        self,
        content: str,
        existing_tags: List[str] | None = None,
        min_tags: int = 3,
        max_tags: int = 7,
    ) -> List[str]:
        """
        記事の内容からタグを生成する

        Args:
            content: 記事の本文
            existing_tags: 既存のタグリスト
            min_tags: 最小タグ数
            max_tags: 最大タグ数

        Returns:
            List[str]: 生成されたタグリスト（既存タグと統合）
        """
        existing_tags_str = ", ".join(existing_tags) if existing_tags else "なし"

        prompt = (
            f"以下の記事の内容に基づいて、{min_tags}〜{max_tags}個の適切なタグを提案してください。"
            f"既存のタグは {existing_tags_str} です。"
            "過度に一般的なタグ（例：「メモ」「日記」）は避けてください。\n\n"
            f"{content}\n\n"
            "タグはカンマ区切りで返してください。"
        )

        response = self._generate_with_retry(prompt)

        # レスポンスからタグを抽出
        new_tags = [
            tag.strip() for tag in response.split(",") if tag.strip()
        ]

        # 既存タグと統合（重複を除去）
        all_tags = list(set(existing_tags or []) | set(new_tags))

        return all_tags[:max_tags]  # 最大タグ数に制限

    def _generate_with_retry(self, prompt: str) -> str:
        """
        リトライロジック付きでLLMを呼び出す

        Args:
            prompt: プロンプト

        Returns:
            str: LLMのレスポンス

        Raises:
            Exception: リトライ回数を超えても失敗した場合
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = ollama.generate(
                    model=self.model,
                    prompt=prompt,
                )
                return response["response"]
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # 指数バックオフ
                else:
                    raise last_error from None

        # ここには到達しないはずだが、型チェッカーのため
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected error in _generate_with_retry")

