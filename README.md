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
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3  # or mistral

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
- Ollamaでベクトル化とサマリー生成
- ChromaDBへの格納

### ステップ 5: Web UIの起動

開発サーバーを起動：

```bash
uv run uvicorn app.main:app --reload --port 8000
```

ブラウザで `http://localhost:8000` にアクセスし、検索やデイリーレポートを確認できます。

### ステップ 6: 自動実行の設定

#### Linux/macOS (cron)

```bash
# 毎日午前6時にデイリーレポート生成
0 6 * * * cd /path/to/ObsidianConscierge && /path/to/uv run python scripts/daily_report.py

# 30分ごとにGit同期
*/30 * * * * cd /path/to/ObsidianConscierge && /path/to/uv run python scripts/git_sync.py
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

`/etc/systemd/system/obsidian-conscierge.service`を作成：

```ini
[Unit]
Description=ObsidianConscierge Daily Report
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/ObsidianConscierge
ExecStart=/path/to/uv run python scripts/daily_report.py
Environment="PATH=/home/your-username/.local/bin:/usr/local/bin:/usr/bin"

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/obsidian-conscierge.timer`を作成：

```ini
[Unit]
Description=ObsidianConscierge Daily Report Timer

[Timer]
OnCalendar=*-*-* 06:00:00

[Install]
WantedBy=timers.target
```

タイマーの有効化と開始：

```bash
sudo systemctl enable obsidian-conscierge.timer
sudo systemctl start obsidian-conscierge.timer
```

## 📖 主な機能

### セマンティック検索
自然な文章で記事を検索。例：「Pythonでデータ分析をする方法について書いた記事」

### デイリーレポート
毎朝自動生成されるレポートには以下が含まれます：
- 昨日の執筆統計（記事数、総文字数）
- 重複検知警告（類似度80%以上）
- ランダムピックアップ3記事（異分野優先）
- MOC候補リスト

### ナレッジマップ
記事間の関連性を可視化。クラスター分析により、知識の構造を一目で把握できます。

### ブリッジ記事の発見
異なるテーマ間をつなぐ「ブリッジ記事」を自動で特定。新しいアイデア創出を支援します。

詳細な機能仕様については、[要件定義ドキュメント](docs/PRD.md)を参照してください。

## 🛠️ 開発

### プロジェクト構造

```
ObsidianConscierge/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPIアプリケーション
│   ├── core/
│   │   ├── indexing.py      # インデックス作成ロジック
│   │   ├── search.py        # 検索ロジック
│   │   └── analysis.py      # 分析ロジック
│   ├── services/
│   │   ├── github.py        # GitHub API連携
│   │   ├── llm.py           # LLM API連携
│   │   └── vector_db.py     # ChromaDB操作
│   └── api/
│       ├── search.py        # 検索API
│       └── reports.py       # レポートAPI
├── scripts/
│   ├── initial_index.py     # 初期インデックス作成
│   └── daily_update.py      # 日次更新処理
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
poetry add package-name
```

### テストの実行

```bash
poetry run pytest
```

### 型チェック

```bash
poetry run mypy app/
```

### 未使用コードの検出

```bash
poetry run vulture app/
```

## 📝 ライセンス

[LICENSE](LICENSE)ファイルを参照してください。

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します。詳細は[CONTRIBUTING.md](CONTRIBUTING.md)（作成予定）を参照してください。

## 📚 参考資料

- [Obsidian公式ドキュメント](https://help.obsidian.md/)
- [ChromaDBドキュメント](https://docs.trychroma.com/)
- [FastAPIドキュメント](https://fastapi.tiangolo.com/)
