# アーキテクチャドキュメント: ObsidianConscierge

## システム概要

ObsidianConsciergeは、Obsidian Vaultのコンテンツを自動的に分析・インデックス化し、セマンティック検索とインサイト生成を提供するシステムです。

### 技術スタックの特徴

- **LLM**: Ollama（ローカル実行、プライバシー保護）
- **Embedding**: sentence-transformers（distiluse-base-multilingual-cased-v2、既存実装を継続）
- **パッケージ管理**: uv（高速パッケージマネージャー）
- **Git同期**: TargetObsidianVaultディレクトリのローカル同期（GitPython使用）
- **既存実装の活用**: `sample_code/`の実証済みTF-IDF/ChromaDB実装を基盤として使用

## 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│          Obsidian Vault (GitHub Repository)                 │
│                  (Remote Source of Truth)                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Git pull/push (自動同期)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          TargetObsidianVault (Local Directory)              │
│                  (ローカルVaultコピー)                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ File System Access
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend Service (Python + uv)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Indexing    │  │   Analysis   │  │   Report     │    │
│  │   Service    │  │   Service    │  │   Service    │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            │                                │
│  ┌─────────────────────────▼──────────────────────────┐   │
│  │           Service Layer (Business Logic)            │   │
│  │  - Git Sync Service (GitPython)                     │   │
│  │  - LLM Service (Ollama - ローカル)                  │   │
│  │  - Vector DB Service (ChromaDB)                     │   │
│  │  - Content Parser (既存実装活用)                    │   │
│  │  - TF-IDF Analyzer (既存実装活用)                   │   │
│  └─────────────────────────┬──────────────────────────┘   │
└────────────────────────────┼────────────────────────────────┘
                             │
                             │ Read/Write
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    ChromaDB (Vector Store)                   │
│         - Article Embeddings (sentence-transformers)         │
│              - Metadata                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Query
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Web API (FastAPI)                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Search API  │  │  Report API  │  │  Map API     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            │                                │
│  ┌─────────────────────────▼──────────────────────────┐   │
│  │          Frontend (TypeScript + HTML/CSS)           │   │
│  │  - Search UI                                         │   │
│  │  - Daily Report View                                 │   │
│  │  - Knowledge Map (D3.js - Phase 3)                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             ▲
                             │
                             │ Local HTTP
                             │
┌─────────────────────────────────────────────────────────────┐
│                  Ollama (Local LLM Server)                   │
│              - llama3/mistral (Text Generation)              │
│          (Embeddingsはsentence-transformersを使用)           │
└─────────────────────────────────────────────────────────────┘
```

## コンポーネント詳細

### 1. Indexing Service

**責任範囲:**
- GitHubリポジトリからの変更検知
- マークダウンファイルの抽出とパース
- ベクトル化とDB格納

**主要クラス:**
```python
class IndexingService:
    def detect_changes(self) -> List[FileChange]
    def extract_content(self, file_path: str) -> ArticleContent
    def generate_embeddings(self, content: str) -> Embedding
    def store_to_db(self, article: Article) -> bool
```

**データフロー:**
1. GitHub APIから変更ファイルリストを取得
2. 各ファイルをパースしてコンテンツを抽出
3. LLM Serviceでサマリーとタグを生成
4. Embedding Serviceでベクトル化
5. Vector DB Serviceで格納

### 2. Analysis Service

**責任範囲:**
- 記事間の類似度計算
- クラスタリング
- ブリッジ記事の特定

**主要クラス:**
```python
class AnalysisService:
    def detect_duplicates(self, threshold: float) -> List[DuplicatePair]
    def cluster_articles(self, k: int) -> ClusterResult
    def identify_bridges(self, clusters: ClusterResult) -> List[BridgeArticle]
    def generate_knowledge_map(self) -> KnowledgeMapData
```

**アルゴリズム:**
- **重複検知**: コサイン類似度によるペアワイズ比較
- **クラスタリング**: K-means（scikit-learn）
- **次元削減**: UMAP（ナレッジマップ用）

### 3. Report Service

**責任範囲:**
- デイリーレポートの生成
- 統計情報の集計
- MOC候補の抽出

**主要クラス:**
```python
class ReportService:
    def generate_daily_report(self, date: datetime) -> DailyReport
    def calculate_statistics(self, date: datetime) -> Statistics
    def find_moc_candidates(self) -> List[MOCCandidate]
```

### 4. LLM Service

**責任範囲:**
- サマリー生成
- タグ自動生成
- 統合提案の生成

**主要クラス:**
```python
class LLMService:
    def generate_summary(self, content: str) -> str
    def generate_tags(self, content: str, existing_tags: List[str]) -> List[str]
    def propose_integration(self, articles: List[Article]) -> IntegrationProposal
```

**プロバイダー抽象化:**
```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str) -> str

class OllamaProvider(LLMProvider):
    """Ollamaローカルサーバーを使用（推奨）"""
    def generate(self, prompt: str, model: str = "llama3") -> str:
        # Ollama SDK使用
        pass

# 将来的な拡張（現在は未使用）
class OpenAIProvider(LLMProvider): ...
class AnthropicProvider(LLMProvider): ...
```

**Embedding Service（独立）:**
```python
class EmbeddingService:
    """sentence-transformersを使用したEmbedding生成"""
    def __init__(self, model_name: str = "distiluse-base-multilingual-cased-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        # 既存実装（find_similar_documents.py）を活用
        return self.model.encode(text).tolist()
```

### 5. Vector DB Service

**責任範囲:**
- ベクトルの格納と検索
- メタデータの管理

**主要クラス:**
```python
class VectorDBService:
    def store(self, article: Article) -> bool
    def search(self, query: str, limit: int, filters: Dict) -> List[SearchResult]
    def delete(self, article_id: str) -> bool
    def update(self, article: Article) -> bool
```

## データフロー

### インデックス作成フロー

```
GitHub API
    │
    ├─> detect_changes()
    │       │
    │       └─> [FileChange, FileChange, ...]
    │
    ├─> extract_content(file_path)
    │       │
    │       └─> ArticleContent {title, body, metadata}
    │
    ├─> generate_summary(body)
    │       │
    │       └─> summary_text
    │
    ├─> generate_tags(body, existing_tags)
    │       │
    │       └─> [tag1, tag2, ...]
    │
    ├─> generate_embeddings(body, summary)
    │       │
    │       └─> Embedding {body_embedding, summary_embedding}
    │
    └─> store_to_db(article)
            │
            └─> ChromaDB
```

### 検索フロー

```
User Query
    │
    ├─> generate_embedding(query)
    │       │
    │       └─> query_embedding
    │
    ├─> vector_db.search(query_embedding, filters)
    │       │
    │       └─> [SearchResult, ...]
    │
    └─> format_results(results)
            │
            └─> JSON Response
```

## エラーハンドリング戦略

### リトライロジック

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def call_llm_api(prompt: str) -> str:
    # LLM API呼び出し
    pass
```

### エラー分類

1. **一時的エラー（Retryable）**
   - ネットワークエラー
   - APIレート制限
   - タイムアウト

2. **永続的エラー（Non-retryable）**
   - 認証エラー
   - 無効なリクエスト
   - ファイルパースエラー

### ログ戦略

- **DEBUG**: 詳細な処理フロー
- **INFO**: 重要な処理の開始・完了
- **WARNING**: リカバリー可能なエラー
- **ERROR**: 処理失敗

## パフォーマンス最適化

### 1. バッチ処理

- ベクトル生成: 複数記事をまとめて処理
- DB書き込み: 100件ずつバッチインサート

### 2. キャッシング

- サマリー生成結果をキャッシュ（同じコンテンツの場合）
- クラスタリング結果をキャッシュ（週次更新時のみ再計算）

### 3. 非同期処理

- FastAPIの非同期エンドポイントを活用
- 長時間処理（クラスタリングなど）はバックグラウンドタスクとして実行

## セキュリティ考慮事項

1. **APIキー管理**
   - `.env`ファイルで管理
   - Gitにコミットしない（`.gitignore`に追加）
   - 本番環境では環境変数またはシークレット管理サービスを使用

2. **データプライバシー**
   - ベクトルDBはローカルに保存
   - LLM APIへの送信データは最小限に

3. **入力検証**
   - すべてのAPI入力に対してPydanticでバリデーション
   - パストラバーサル攻撃を防ぐため、ファイルパスを検証

## テスト戦略

### 単体テスト

- 各サービスクラスのメソッドをテスト
- モックを使用して外部依存を排除

### 統合テスト

- GitHub APIとの連携テスト（モックAPI使用）
- ChromaDBとの統合テスト

### E2Eテスト

- インデックス作成から検索までのフローをテスト

## デプロイメント

### 開発環境

```bash
# uv環境のセットアップ
uv venv
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate  # Windows

# 依存関係のインストール
uv sync

# Ollamaの起動（別ターミナル）
ollama serve

# Ollamaモデルのダウンロード（テキスト生成用のみ）
ollama pull llama3
# Note: Embeddingsはsentence-transformersを使用するため、nomic-embed-textは不要

# FastAPIサーバーの起動
uv run uvicorn app.main:app --reload --port 8000
```

### 本番環境（将来対応）

- Gunicorn + Uvicorn workers
- systemdでサービス化（推奨）
- Dockerは Phase 2 以降で検討
- リバースプロキシ（Nginx）でHTTPS対応（将来）

### Git自動同期の設定

#### systemd（Linux - 推奨）

`/etc/systemd/system/obsidian-sync.service`:
```ini
[Unit]
Description=ObsidianConscierge Git Sync
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/ObsidianConscierge
ExecStart=/path/to/uv run python scripts/git_sync.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/obsidian-sync.timer`:
```ini
[Unit]
Description=ObsidianConscierge Git Sync Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min

[Install]
WantedBy=timers.target
```

#### cron（macOS/Linux）

```bash
# 30分ごとに同期
*/30 * * * * cd /path/to/ObsidianConscierge && /path/to/uv run python scripts/git_sync.py
```

