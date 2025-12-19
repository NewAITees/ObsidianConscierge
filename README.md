# ObsidianConscierge

**思考に集中するための、あなたのナレッジベースAIコンシェルジュ**

ObsidianConsciergeは、Obsidianでのノート管理と知識の再発見に特化した、自動化・AI駆動型のソリューションです。タグ付け、リンク付け、整理といった煩雑な作業からあなたを解放し、「書くこと」と「考えること」だけに集中できる環境を提供します。

## ✨ 3つの主要な価値

### 1. 意味による検索（Vector Indexing）
キーワードではなく、自然な文章で過去の記事を探し出せます。表記ゆれや曖昧な記憶に悩まされることはありません。

### 2. 自動での知識統合（Bridge Analysis）
記事の重複を検知し、異なるテーマ間の関連性（ブリッジ）を自動で発見。アイデア創出を加速します。

### 3. 日々の思考支援（Insight Report）
毎朝、あなたの行動に基づいたパーソナライズされたレポートを提供。次に書くべきこと、見直すべきことが一目で分かります。

## 🏗️ アーキテクチャ概要

ObsidianConsciergeは、ObsidianのVault外で動作する**独立したPython製バックエンド**と、結果を表示するためのシンプルな**カスタム検索UI/レポート画面**で構成されます。

```
┌─────────────────┐
│  Obsidian Vault │
│  (GitHub Repo)  │
└────────┬────────┘
         │
         │ Git API / Webhook
         ▼
┌─────────────────┐
│  Backend Service│
│  (Python)       │
│  - Indexing     │
│  - Analysis     │
│  - Report Gen   │
└────────┬────────┘
         │
         │ Vector DB
         ▼
┌─────────────────┐
│   ChromaDB      │
│  (Vector Store) │
└─────────────────┘
         │
         │ Query
         ▼
┌─────────────────┐
│  Web UI         │
│  (FastAPI)      │
│  - Search       │
│  - Reports      │
│  - Knowledge Map│
└─────────────────┘
```

## 🚀 クイックスタート

### 前提条件

- Python 3.11以上
- **uv**（高速パッケージマネージャー）
- **Ollama**（ローカルLLMサーバー）
- Obsidian Vault（GitHubリポジトリにプッシュ済み）
- Git（TargetObsidianVault同期用）

### 既存実装の活用

本プロジェクトは、`sample_code/`フォルダに存在する**実証済みの実装を基盤**として構築されています：

- TF-IDF分析システム（5,800+ファイルの自動タグ付け、45種類の例外パターン）
- ChromaDB統合（ベクトル検索）
- MOC（Map of Contents）生成
- デイリーノート自動生成
- 類似度分析・リンク挿入

### ステップ 1: リポジトリのクローンとセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/ObsidianConscierge.git
cd ObsidianConscierge

# uvのインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/macOS
# または
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Python環境のセットアップ
uv venv
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate  # Windows

# 依存関係のインストール
uv sync

# 開発用依存関係も含める
uv sync --extra dev
```

### ステップ 2: 環境変数の設定

`.env.example`を参考に、`.env`ファイルを作成します：

```bash
cp .env.example .env
```

`.env`ファイルに以下を設定：

```env
# GitHub設定（TargetObsidianVault同期用）
GITHUB_REPO_URL=https://github.com/yourusername/your-vault-repo.git
GITHUB_TOKEN=ghp_your_github_token_here

# Obsidian設定
OBSIDIAN_VAULT_NAME=your-vault-name
OBSIDIAN_VAULT_PATH=./TargetObsidianVault

# Ollama設定（ローカルLLMサーバー）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3  # or mistral
# Note: Embeddingsはsentence-transformersを使用（OLLAMA_EMBEDDING_MODELは不要）

# ベクトルDB設定
CHROMA_DB_PATH=./data/chroma_db

# Git同期設定
GIT_AUTO_SYNC_ENABLED=true
GIT_SYNC_INTERVAL_MINUTES=30

# その他
LOG_LEVEL=INFO
```

### ステップ 3: Ollamaのセットアップ

別ターミナルでOllamaを起動し、必要なモデルをダウンロードします：

```bash
# Ollamaのインストール（未インストールの場合）
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windowsの場合は https://ollama.com/download からダウンロード

# Ollamaサーバーの起動（別ターミナル）
ollama serve

# LLMモデルのダウンロード（テキスト生成用）
ollama pull llama3        # テキスト生成用（約4.7GB）

# オプション: 他のモデル
ollama pull mistral       # 代替LLMモデル

# Note: Embeddingsはsentence-transformersを使用（既存実装を継続）
```

### ステップ 4: 最初のインデックス作成

既存の全記事をベクトル化してDBに格納します：

```bash
# TargetObsidianVaultディレクトリにVaultをクローン
git clone https://github.com/yourusername/your-vault-repo.git TargetObsidianVault

# 初期インデックス作成
uv run python scripts/initial_index.py
```

このスクリプトは以下を実行します：
- TargetObsidianVaultから全`.md`ファイルを取得
- 各ファイルの内容を抽出・クリーニング（既存実装を活用）
- Ollamaでサマリー生成（テキスト生成用）
- sentence-transformersでベクトル化（埋め込み生成）
- ChromaDBへの格納

### ステップ 5: Web UIの起動

開発サーバーを起動：

```bash
uv run uvicorn app.main:app --reload --port 8000
```

ブラウザで `http://localhost:8000` にアクセスし、セマンティック検索UIを利用できます。

**注意**: デイリーレポート機能は現在未実装です（Phase 2で実装予定）。

### ステップ 6: 自動実行の設定

#### Linux/macOS (cron)

```bash
# 30分ごとにGit同期
*/30 * * * * cd /path/to/ObsidianConscierge && /path/to/uv run python scripts/git_sync.py

# 注意: デイリーレポート機能は未実装（Phase 2で実装予定）
```

#### Windows (Task Scheduler)

1. タスクスケジューラを開く
2. 基本タスクを作成
3. トリガーを「毎日 6:00」に設定
4. 操作で以下を実行：
   ```powershell
   cd C:\path\to\ObsidianConscierge
   C:\path\to\uv.exe run python scripts/daily_report.py
   ```

#### systemd (Linux - 推奨)

詳細な設定手順は [docs/SYSTEMD_SETUP.md](docs/SYSTEMD_SETUP.md) を参照してください。

**Git同期サービス**（30分ごと）:
```bash
sudo cp systemd/obsidian-conscierge-sync.service /etc/systemd/system/
sudo cp systemd/obsidian-conscierge-sync.timer /etc/systemd/system/
# ファイルを編集（YOUR_USERとパスを変更）
sudo systemctl daemon-reload
sudo systemctl enable obsidian-conscierge-sync.timer
sudo systemctl start obsidian-conscierge-sync.timer
```

**注意**: デイリーレポート機能は未実装（Phase 2で実装予定）

## 📖 主な機能

### 検索機能（実装済み ✅）

ObsidianConsciergeでは、以下の7種類の検索方法を提供しています：

#### 1. セマンティック検索
自然な文章で記事を検索。リアルタイム検索、タグフィルタ、ページネーションに対応。

**Web UI**: `http://localhost:8000` で利用可能

**CLI使用例:**
```bash
# セマンティック検索（既存）
uv run python scripts/search_cli.py semantic -q "Python"

# タグ検索
uv run python scripts/search_cli.py tags -t python -t fastapi

# キーワード検索
uv run python scripts/search_cli.py keyword -k "ObsidianConscierge"

# 日付範囲検索
uv run python scripts/search_cli.py date --from 2024-01-01 --to 2024-12-31

# 文字数範囲検索
uv run python scripts/search_cli.py wordcount --min 100 --max 1000

# ハイブリッド検索
uv run python scripts/search_cli.py hybrid -q "Python" -t coding --min-words 500

# 類似ドキュメント検索
uv run python scripts/search_cli.py similar --doc-id "path/to/article.md"
```

詳細は [docs/SEARCH_METHODS.md](docs/SEARCH_METHODS.md) を参照してください。

### デイリーレポート（未実装 ⏳）
毎朝自動生成されるレポートには以下が含まれる予定：
- 昨日の執筆統計（記事数、総文字数）
- 重複検知警告（類似度80%以上）
- ランダムピックアップ3記事（異分野優先）
- MOC候補リスト

**実装予定**: Phase 2

### ナレッジマップ（未実装 ⏳）
記事間の関連性を可視化。クラスター分析により、知識の構造を一目で把握できます。

**実装予定**: Phase 3

### ブリッジ記事の発見（未実装 ⏳）
異なるテーマ間をつなぐ「ブリッジ記事」を自動で特定。新しいアイデア創出を支援します。

**実装予定**: Phase 3

詳細な機能仕様については、[要件定義ドキュメント](docs/PRD.md)を参照してください。

## 🛠️ 開発

### プロジェクト構造

```
ObsidianConscierge/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPIアプリケーション ✅
│   ├── core/
│   │   ├── indexing.py      # インデックス作成ロジック ✅
│   │   ├── search.py        # 検索ロジック ✅
│   │   └── analysis.py      # 分析ロジック（未実装）
│   ├── services/
│   │   ├── embedding_service.py  # Embedding生成 ✅
│   │   ├── llm_service.py        # LLM API連携 ✅
│   │   └── vector_db_service.py  # ChromaDB操作 ✅
│   ├── api/
│   │   ├── search.py        # 検索API ✅
│   │   ├── config.py        # 設定API ✅
│   │   └── reports.py       # レポートAPI（未実装）
│   ├── models/
│   │   ├── article.py       # 記事モデル ✅
│   │   └── search.py       # 検索モデル ✅
│   └── static/              # フロントエンドUI ✅
│       ├── index.html
│       ├── css/
│       └── js/
├── scripts/
│   ├── initial_index.py     # 初期インデックス作成 ✅
│   ├── git_sync.py          # Git同期スクリプト ✅
│   ├── git_sync.sh          # Git同期スクリプト（Bash）✅
│   ├── search_cli.py        # CLI検索ツール ✅
│   └── daily_report.py      # デイリーレポート生成（未実装）
├── tests/
│   └── ...
├── docs/
│   └── PRD.md               # 要件定義ドキュメント
├── data/
│   └── chroma_db/           # ChromaDBデータ
├── .env.example
├── pyproject.toml
└── README.md
```

### 依存関係の追加

```bash
uv add package-name
```

### テストの実行

```bash
uv run pytest
```

### 型チェック

```bash
uv run mypy app/
```

### 未使用コードの検出

```bash
uv run vulture app/
```

## 📝 ライセンス

[LICENSE](LICENSE)ファイルを参照してください。

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します。詳細は[CONTRIBUTING.md](CONTRIBUTING.md)（作成予定）を参照してください。

## ⚠️ 重要: AI自動ファイル編集について

**【絶対遵守】ObsidianファイルへのAI編集ルール**

ObsidianConsciergeは、類似リンク挿入・タグ自動挿入などの機能で、Vaultのマークダウンファイルを自動編集します。
**安全性を最優先**するため、以下のルールが厳格に適用されます。

### AI自動生成セクション

各ファイルには、以下のマーカーで明確に区切られた「AI自動生成セクション」が追加される場合があります：

```markdown
========== AI AUTO-GENERATED SECTION START ==========
## 🤖 AI自動生成セクション

### 🔗 類似ドキュメント
- 🔗 [[関連ドキュメント1]] (類似度: 0.850)
- 📎 [[関連ドキュメント2]] (類似度: 0.720)

### 🏷️ 自動タグ
#python #ai #machine-learning

最終更新: 2025-01-15 10:30:00
========== AI AUTO-GENERATED SECTION END ==========
```

### 🚫 編集の絶対ルール

1. **AI自動生成セクション以外は絶対に変更しません**
   - 既存の本文、見出し、リンク、手動タグ、フロントマターは一切保護されます
   - セクション外のコンテンツは読み取り専用として扱われます

2. **セクションが存在しない場合**
   - ファイル末尾に新規追加のみ行います
   - 既存コンテンツには一切影響しません

3. **除外フォルダの設定**
   - `.env`の`EXCLUDED_FOLDERS`で指定したフォルダ内のファイルは編集対象外
   - ルートディレクトリのファイルも自動的に除外
   - デフォルト: `01DIARY,02TEMPLATES,06MOC,10KANBAN,11MEDIA,Excalidraw,Maybe,Omnivore,model_cache,PythonScripts,github,.chroma_db,.claude,.devcontainer,.smtcmp_json_db,.smtcmp_vector_db`

### 設定方法

`.env`ファイルで編集動作を制御できます：

```env
# 類似リンク自動挿入のON/OFF
ENABLE_AUTO_LINK_INSERT=true

# タグ自動挿入のON/OFF
ENABLE_AUTO_TAG_INSERT=true

# リンク挿入の最小類似度（0.0-1.0）
MIN_SIMILARITY_FOR_LINK=0.5

# 挿入する類似リンクの最大数（1-10）
MAX_SIMILAR_LINKS=3

# 編集対象外のフォルダ（カンマ区切り）
EXCLUDED_FOLDERS=01DIARY,02TEMPLATES,06MOC,10KANBAN,11MEDIA,Excalidraw,Maybe,Omnivore,model_cache,PythonScripts,github,.chroma_db,.claude,.devcontainer,.smtcmp_json_db,.smtcmp_vector_db

# ルートディレクトリのファイルを編集対象外にする
EXCLUDE_ROOT_FILES=true
```

### 安全性の保証

- 専用モジュール `app/core/document_updater.py` がファイル編集を集中管理
- 厳密なセクション検出により、偶然の誤編集を防止
- 除外フォルダ機能で重要ファイルを保護

詳細は [docs/TODO.md](docs/TODO.md) の「AI自動ファイル編集ルール」セクションを参照してください。

## 📚 参考資料

- [Obsidian公式ドキュメント](https://help.obsidian.md/)
- [ChromaDBドキュメント](https://docs.trychroma.com/)
- [FastAPIドキュメント](https://fastapi.tiangolo.com/)
