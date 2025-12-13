# ObsidianConscierge - Project Information for Codex CLI

## プロジェクト構造

```
ObsidianConscierge/
├── app/                          # メインアプリケーション
│   ├── __init__.py
│   ├── main.py                   # FastAPIアプリケーション
│   ├── config.py                 # 設定管理（pydantic-settings）
│   ├── core/                     # コアビジネスロジック
│   │   ├── indexing.py           # インデックス作成ロジック
│   │   ├── search.py             # 検索ロジック
│   │   ├── analysis.py           # 分析ロジック
│   │   └── git_sync.py           # Git同期ロジック
│   ├── services/                 # 外部サービス連携
│   │   ├── ollama_service.py     # Ollama API連携
│   │   ├── vector_db_service.py  # ChromaDB操作
│   │   ├── content_parser.py     # マークダウンパーサー
│   │   └── tfidf_analyzer.py     # TF-IDF分析（既存実装活用）
│   ├── api/                      # FastAPI エンドポイント
│   │   ├── search.py             # 検索API
│   │   ├── reports.py            # レポートAPI
│   │   └── knowledge_map.py      # ナレッジマップAPI
│   ├── models/                   # Pydanticモデル
│   │   ├── article.py            # 記事モデル
│   │   ├── search.py             # 検索リクエスト/レスポンス
│   │   └── report.py             # レポートモデル
│   └── utils/                    # ユーティリティ
│       ├── logger.py             # ロギング設定
│       └── markdown.py           # マークダウン処理
├── scripts/                      # CLIスクリプト
│   ├── initial_index.py          # 初期インデックス作成
│   ├── search_cli.py             # CLI検索ツール
│   ├── git_sync.py               # Git同期スクリプト
│   └── daily_report.py           # デイリーレポート生成
├── tests/                        # テストコード
│   ├── test_core/
│   ├── test_services/
│   ├── test_api/
│   └── fixtures/
├── sample_code/                  # 既存実装（参照用）
│   ├── enhanced_tfidf_analyzer.py
│   ├── find_similar_documents.py
│   ├── ultra_smart_tag_inserter.py
│   └── ...
├── TargetObsidianVault/          # Obsidian Vaultのローカルコピー（.gitignore）
├── data/                         # データストレージ（.gitignore）
│   └── chroma_db/                # ChromaDBデータ
├── logs/                         # ログファイル（.gitignore）
├── reports/                      # 生成されたレポート（.gitignore）
│   └── daily/
├── docs/                         # ドキュメント
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   └── MIGRATION.md
├── .env                          # 環境変数（.gitignore）
├── .env.example                  # 環境変数テンプレート
├── pyproject.toml                # uv依存関係管理
├── README.md                     # プロジェクト概要
├── AGENTS.md                     # このファイル（Codex CLI用）
└── .gitignore
```

## 開発コマンド

### セットアップ

```bash
# Python環境のセットアップ（uv使用）
uv venv
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate  # Windows

# 依存関係のインストール
uv sync

# 開発用依存関係も含める
uv sync --extra dev

# Ollamaのセットアップ（テキスト生成用）
ollama serve  # 別ターミナルで実行
ollama pull llama3
# Note: Embeddingsはsentence-transformersを使用（nomic-embed-textは不要）
```

### テスト

```bash
# 全テストを実行
uv run pytest

# カバレッジ付きで実行
uv run pytest --cov=app --cov-report=html

# 特定のテストファイルのみ実行
uv run pytest tests/test_core/test_indexing.py

# マーカー付きテスト実行（例: @pytest.mark.slow）
uv run pytest -m "not slow"
```

### リント・フォーマット

```bash
# ruffでリント
uv run ruff check .

# ruffでフォーマット
uv run ruff format .

# 自動修正付きでリント
uv run ruff check --fix .
```

### 型チェック

```bash
# mypy で型チェック
uv run mypy app/
```

### アプリケーション実行

```bash
# FastAPIサーバーの起動（開発モード）
uv run uvicorn app.main:app --reload --port 8000

# 本番モード
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 初期インデックス作成
uv run python scripts/initial_index.py

# CLI検索
uv run python scripts/search_cli.py --query "検索クエリ"

# Git同期（手動実行）
uv run python scripts/git_sync.py

# デイリーレポート生成（手動実行）
uv run python scripts/daily_report.py
```

## コーディング規約

### Python

- **バージョン**: Python 3.11以上
- **スタイル**: ruff準拠（PEP 8ベース）
- **行の長さ**: 最大100文字
- **インデント**: スペース4つ
- **クォート**: ダブルクォート（"）を使用
- **型ヒント**: すべての関数に型ヒントを付与（mypy strict モード）
- **Docstring**: Google Styleを使用

#### 型ヒントの例

```python
from typing import List, Optional

def process_article(
    file_path: str,
    generate_summary: bool = True
) -> Optional[Article]:
    """記事ファイルを処理してArticleオブジェクトを返す。

    Args:
        file_path: 記事ファイルのパス
        generate_summary: サマリーを生成するかどうか

    Returns:
        処理された Article オブジェクト。処理に失敗した場合は None。

    Raises:
        FileNotFoundError: ファイルが存在しない場合
    """
    pass
```

### FastAPI

- **エンドポイント**: `/api/v1/` プレフィックスを使用
- **Pydanticモデル**: すべてのリクエスト/レスポンスに使用
- **エラーハンドリング**: HTTPExceptionで適切なステータスコードを返す
- **非同期処理**: I/O操作は `async/await` を使用

### Git コミットメッセージ

**フォーマット**: `<type>: <subject>`

**type 一覧**:
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント更新
- `style`: コードスタイル変更（動作に影響なし）
- `refactor`: リファクタリング
- `perf`: パフォーマンス改善
- `test`: テスト追加・修正
- `chore`: ビルド・補助ツール変更

**例**:
```
feat: add Ollama embedding support for vector generation
fix: correct duplicate detection threshold calculation
docs: update README with uv installation instructions
```

## ブランチ戦略

- `main`: 安定版・デプロイ可能なコード
- `develop`: 開発統合ブランチ
- `feature/*`: 機能開発
- `fix/*`: バグ修正
- `docs/*`: ドキュメント更新

## 主要な技術スタック

- **Python**: 3.11
- **パッケージ管理**: uv
- **Webフレームワーク**: FastAPI
- **LLM**: Ollama（llama3/mistral）
- **Embedding**: sentence-transformers（distiluse-base-multilingual-cased-v2、既存実装を継続）
- **ベクトルDB**: ChromaDB
- **TF-IDF分析**: scikit-learn + janome
- **Git操作**: GitPython
- **テスト**: pytest + pytest-cov
- **Linter/Formatter**: ruff
- **型チェック**: mypy

## 重要な実装ガイドライン

### 1. 既存実装の活用

`sample_code/`フォルダには実証済みの実装があります。以下を参照・活用してください：

- **TF-IDF分析**: `enhanced_tfidf_analyzer.py`
- **タグ挿入**: `ultra_smart_tag_inserter.py`（45種類の例外パターン）
- **ChromaDB統合**: `find_similar_documents.py`
- **MOC生成**: `generate_moc_from_analysis.py`
- **デイリーノート**: `daily_note_generator.py`

### 2. Ollama統合

Ollamaは`http://localhost:11434`で動作するローカルLLMサーバーです。

```python
import ollama
from sentence_transformers import SentenceTransformer

# Embedding生成（sentence-transformers使用、既存実装を継続）
embedding_model = SentenceTransformer("distiluse-base-multilingual-cased-v2")
embedding = embedding_model.encode("テキスト").tolist()

# テキスト生成（Ollama使用）
response = ollama.generate(
    model="llama3",
    prompt="以下の記事を200字で要約してください:\n\n{content}"
)
summary = response["response"]
```

### 3. エラーハンドリング

- すべての外部API呼び出しにリトライロジックを実装（最大3回）
- タイムアウト設定（Ollama: 60秒、Git操作: 30秒）
- 適切なロギング（DEBUG/INFO/WARNING/ERROR）

### 4. テストカバレッジ

- 目標: 80%以上
- 単体テスト: 各サービスクラスのメソッド
- 統合テスト: FastAPI エンドポイント
- モック使用: 外部依存（Ollama、ChromaDB）はモックを使用

### 5. パフォーマンス最適化

- ベクトル生成: バッチ処理（100件ずつ）
- DB書き込み: バッチインサート
- 非同期処理: FastAPIの非同期エンドポイントを活用

## 環境変数

主要な環境変数は`.env.example`を参照してください。

```bash
# 必須
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3  # テキスト生成用
OBSIDIAN_VAULT_PATH=./TargetObsidianVault
GITHUB_REPO_URL=https://github.com/user/vault.git

# オプション
DEBUG=false
LOG_LEVEL=INFO

# Note: Embeddingsはsentence-transformersを使用（OLLAMA_EMBEDDING_MODELは不要）
```

## トラブルシューティング

### Ollama接続エラー

```bash
# Ollamaが起動しているか確認
curl http://localhost:11434/api/version

# Ollamaを再起動
ollama serve
```

### ChromaDB初期化エラー

```bash
# ChromaDBディレクトリを削除して再作成
rm -rf ./data/chroma_db
uv run python scripts/initial_index.py
```

### Gitトークンエラー

- `.env`ファイルで`GITHUB_TOKEN`が正しく設定されているか確認
- トークンの権限（read/write）を確認

## 参考資料

- [FastAPI公式ドキュメント](https://fastapi.tiangolo.com/)
- [Ollama公式ドキュメント](https://github.com/ollama/ollama)
- [ChromaDB公式ドキュメント](https://docs.trychroma.com/)
- [uv公式ドキュメント](https://github.com/astral-sh/uv)
- [既存実装ワークフロー](sample_code/MASTER_WORKFLOW.md)
- [TF-IDFシステム設計](sample_code/TFIDF_TAGGING_SYSTEM_DESIGN.md)
