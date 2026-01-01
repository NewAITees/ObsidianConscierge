#!/usr/bin/env python3
"""
GPU処理専用ワーカープロセス

このスクリプトは別プロセスとして起動され、GPUリソースを使用してembedding処理を実行します。
親プロセスはこのワーカーをタイムアウト監視し、ハング時には強制終了できます。

使用例:
    # 標準入力からJSONを受信し、標準出力にJSONを返す
    echo '{"texts": ["text1", "text2"]}' | python embedding_worker.py

終了コード:
    0: 正常終了
    1: エラー発生
"""

import json
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.embedding_service import EmbeddingService

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # エラー出力はstderr
)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    メイン処理

    標準入力からJSONを読み取り、embedding処理を実行し、
    標準出力にJSONで結果を返す。
    """
    embedding_service = None

    try:
        # 標準入力からデータを読み込む
        logger.info("Reading input from stdin...")
        input_data = sys.stdin.read()

        if not input_data.strip():
            raise ValueError("No input data received")

        # JSONをパース
        data = json.loads(input_data)
        texts = data.get("texts", [])

        if not texts:
            raise ValueError("No texts provided in input data")

        logger.info(f"Processing {len(texts)} texts")

        # EmbeddingServiceを初期化
        embedding_service = EmbeddingService()

        # バッチ処理（GPU使用はコンテキストマネージャーで自動管理）
        embeddings = embedding_service.embed_batch(texts)

        logger.info(f"Successfully generated {len(embeddings)} embeddings")

        # 結果を標準出力にJSON形式で出力
        result = {
            "status": "success",
            "embeddings": embeddings,
            "count": len(embeddings),
        }
        print(json.dumps(result), flush=True)

    except KeyboardInterrupt:
        logger.info("Process interrupted")
        sys.exit(1)

    except Exception as exc:
        logger.error(f"Error occurred: {exc}", exc_info=True)

        # エラー情報を標準出力にJSON形式で出力
        error_result = {
            "status": "error",
            "error": str(exc),
            "type": type(exc).__name__,
        }
        print(json.dumps(error_result), flush=True)
        sys.exit(1)

    finally:
        # 必ずGPUリソースを解放
        if embedding_service is not None:
            logger.info("Cleaning up GPU resources...")
            embedding_service.cleanup()
            logger.info("Cleanup completed")


if __name__ == "__main__":
    main()
