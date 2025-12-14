# セットアップガイド: ObsidianConscierge

このガイドでは、ObsidianConsciergeを初めてセットアップする手順を詳しく説明します。

## 前提条件

### 必須

- **Python 3.11以上**: `python --version`で確認
- **uv**: 高速パッケージマネージャー（[インストール方法](https://github.com/astral-sh/uv#installation)）
- **Ollama**: ローカルLLMサーバー（[インストール方法](https://ollama.com/download)）
- **Git**: バージョン管理
- **Obsidian Vault**: GitHubリポジトリにプッシュ済み

### 推奨

- **pyenv**: Pythonバージョン管理（オプション）
- **Obsidianアプリ**: ローカルで記事を開くため

## ステップ1: リポジトリのクローン

```bash
git clone https://github.com/yourusername/ObsidianConscierge.git
cd ObsidianConscierge
```

## ステップ2: Python環境のセットアップ

### pyenvを使用する場合（推奨）

```bash
# pyenvのインストール（未インストールの場合）
curl https://pyenv.run | bash

# Python 3.11.0のインストール
pyenv install 3.11.0

# プロジェクトディレクトリでPythonバージョンを設定
pyenv local 3.11.0

# 確認
python --version  # Python 3.11.0 と表示されるはず
```

### pyenvを使用しない場合

システムのPython 3.11以上を使用します。

```bash
python3 --version  # 3.11以上であることを確認
```

## ステップ3: uvのインストール

```bash
# uvのインストール（未インストールの場合）
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# PATHに追加（必要に応じて）
export PATH="$HOME/.local/bin:$PATH"

# 確認
uv --version
```

## ステップ4: 依存関係のインストール

```bash
# Python環境のセットアップ
uv venv

# 仮想環境をアクティベート
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate  # Windows

# 依存関係のインストール
uv sync

# 開発用依存関係も含める
uv sync --extra dev
```

## ステップ5: 環境変数の設定

### `.env.example`の確認

プロジェクトルートに`.env.example`ファイルがあることを確認します。

### `.env`ファイルの作成

```bash
cp .env.example .env
```

### `.env`ファイルの編集

エディタで`.env`ファイルを開き、以下の値を設定します：

```env
# GitHub設定（TargetObsidianVault同期用）
# GitHubリポジトリ名（owner/repo形式、推奨）
GITHUB_REPO_NAME=username/my-vault
# またはGitHubリポジトリURL
GITHUB_REPO_URL=https://github.com/username/my-vault.git
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Obsidian設定
OBSIDIAN_VAULT_NAME=MyVault
OBSIDIAN_VAULT_PATH=./TargetObsidianVault

# Ollama設定（ローカルLLMサーバー）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3  # or mistral
# 注意: Embeddingsはsentence-transformersを使用（OLLAMA_EMBEDDING_MODELは不要）

# ベクトルDB設定
CHROMA_DB_PATH=./data/chroma_db

# 分析設定
DUPLICATE_THRESHOLD=0.8
CLUSTER_COUNT=auto
ENABLE_AUTO_TAGGING=true

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=./logs/obsidian_conscierge.log

# Web UI設定
WEB_HOST=0.0.0.0
WEB_PORT=8000

# Git同期設定
GIT_AUTO_SYNC_ENABLED=true
GIT_SYNC_INTERVAL_MINUTES=30
```

### GitHubトークンの取得

1. GitHubにログイン
2. Settings → Developer settings → Personal access tokens → Tokens (classic)
3. "Generate new token (classic)"をクリック
4. スコープで`repo`（リポジトリへの読み取りアクセス）を選択
5. トークンを生成し、`.env`ファイルにコピー

### Ollamaのセットアップ

1. Ollamaをインストール（未インストールの場合）
   - Linux/macOS: `curl -fsSL https://ollama.com/install.sh | sh`
   - Windows: https://ollama.com/download からダウンロード

2. Ollamaサーバーを起動（別ターミナル）
   ```bash
   ollama serve
   ```

3. LLMモデルをダウンロード（テキスト生成用）
   ```bash
   ollama pull llama3  # 約4.7GB
   # または
   ollama pull mistral  # 代替モデル
   ```

**注意**: Embeddingはsentence-transformersを使用するため、Ollamaのembeddingモデルは不要です。

## ステップ6: ディレクトリ構造の作成

```bash
# 必要なディレクトリを作成
mkdir -p data/chroma_db
mkdir -p logs
mkdir -p reports/daily
```

## ステップ7: 初期インデックスの作成

既存の全記事をベクトル化してDBに格納します：

```bash
# TargetObsidianVaultディレクトリにVaultをクローン（まだの場合）
git clone https://github.com/yourusername/your-vault-repo.git TargetObsidianVault

# 初期インデックス作成
uv run python scripts/initial_index.py
# または
uv run oc-index
```

このスクリプトは以下を実行します：
1. TargetObsidianVaultから全`.md`ファイルを取得
2. 各ファイルの内容を抽出・クリーニング
3. Ollamaでサマリーとタグを生成（LLM）
4. sentence-transformersでベクトル化（埋め込み生成）
5. ChromaDBに格納

**注意**: 初回実行時は、記事数が多い場合、LLMの呼び出しに時間がかかります（100記事あたり約5-10分）。

## ステップ8: Web UIの起動

開発サーバーを起動：

```bash
uv run uvicorn app.main:app --reload --port 8000
```

ブラウザで `http://localhost:8000` にアクセスします。

### 動作確認

1. 検索UIで記事を検索してみる
   - 自然な文章で検索（例: "Pythonでデータ分析をする方法"）
   - タグフィルタやページネーションを試す
   - 検索結果から「Obsidianで開く」ボタンをクリック

**注意**: デイリーレポートとナレッジマップ機能は現在未実装です（Phase 2/3で実装予定）。

## ステップ9: 自動実行の設定

### Linux/macOS (cron)

```bash
# crontabを編集
crontab -e

# 30分ごとにGit同期
*/30 * * * * cd /path/to/ObsidianConscierge && /path/to/uv run python scripts/git_sync.py >> /path/to/logs/cron.log 2>&1
```

**注意**: `uv`のパスを絶対パスで指定する必要があります。`which uv`で確認できます。

**注意**: デイリーレポート機能は未実装（Phase 2で実装予定）

### systemd (Linux - 推奨)

詳細な設定手順は [docs/SYSTEMD_SETUP.md](SYSTEMD_SETUP.md) を参照してください。

#### Git同期サービスの設定

```bash
# 設定ファイルをコピー
sudo cp systemd/obsidian-conscierge-sync.service /etc/systemd/system/
sudo cp systemd/obsidian-conscierge-sync.timer /etc/systemd/system/

# ファイルを編集（YOUR_USERとパスを変更）
sudo nano /etc/systemd/system/obsidian-conscierge-sync.service

# 有効化と開始
sudo systemctl daemon-reload
sudo systemctl enable obsidian-conscierge-sync.timer
sudo systemctl start obsidian-conscierge-sync.timer

# ステータス確認
sudo systemctl status obsidian-conscierge-sync.timer
```

**注意**: デイリーレポート機能は未実装（Phase 2で実装予定）

### Windows (Task Scheduler)

1. タスクスケジューラを開く（`taskschd.msc`）
2. "基本タスクの作成"を選択
3. 名前: "ObsidianConscierge Git Sync"
4. トリガー: "繰り返し" → 間隔: 30分
5. 操作: "プログラムの起動"
   - プログラム/スクリプト: `C:\Users\YourUsername\.local\bin\uv.exe`
   - 引数の追加: `run python C:\path\to\ObsidianConscierge\scripts\git_sync.py`
   - 開始場所: `C:\path\to\ObsidianConscierge`

**注意**: デイリーレポート機能は未実装（Phase 2で実装予定）

## トラブルシューティング

### uvが見つからない

```bash
# PATHに追加
export PATH="$HOME/.local/bin:$PATH"

# または、シェル設定ファイル（.bashrc, .zshrc）に追加
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 確認
uv --version
```

### Pythonバージョンが正しくない

```bash
# pyenvを使用している場合
pyenv local 3.11.0

# 仮想環境を再作成
rm -rf .venv
uv venv
uv sync
```

### APIキーエラー

- `.env`ファイルのAPIキーが正しく設定されているか確認
- APIキーに余分なスペースや改行が含まれていないか確認
- APIキーの有効期限を確認

### ChromaDBのエラー

```bash
# データベースをリセット（注意: すべてのデータが削除されます）
rm -rf data/chroma_db/*
uv run python scripts/initial_index.py
```

### ポートが既に使用されている

```bash
# 別のポートを指定
uv run uvicorn app.main:app --reload --port 8001
```

### Ollama接続エラー

```bash
# Ollamaが起動しているか確認
curl http://localhost:11434/api/version

# Ollamaを再起動
ollama serve
```

## 次のステップ

セットアップが完了したら、以下を確認してください：

1. [README.md](../README.md) - 機能の詳細
2. [PRD.md](./PRD.md) - 要件定義
3. [ARCHITECTURE.md](./ARCHITECTURE.md) - アーキテクチャの詳細

