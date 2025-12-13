# セットアップガイド: ObsidianConscierge

このガイドでは、ObsidianConsciergeを初めてセットアップする手順を詳しく説明します。

## 前提条件

### 必須

- **Python 3.11以上**: `python --version`で確認
- **Poetry**: 依存関係管理ツール
- **Git**: バージョン管理
- **Obsidian Vault**: GitHubリポジトリにプッシュ済み

### 推奨

- **pyenv**: Pythonバージョン管理
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

## ステップ3: Poetryのインストール

```bash
# Poetryのインストール（未インストールの場合）
curl -sSL https://install.python-poetry.org | python3 -

# PATHに追加（必要に応じて）
export PATH="$HOME/.local/bin:$PATH"

# 確認
poetry --version
```

## ステップ4: 依存関係のインストール

```bash
# 仮想環境を作成し、依存関係をインストール
poetry install

# 仮想環境をアクティベート
poetry shell
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
# GitHub設定
GITHUB_REPO_URL=https://github.com/yourusername/your-vault-repo.git
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Obsidian設定
OBSIDIAN_VAULT_NAME=MyVault
OBSIDIAN_VAULT_PATH=/home/user/Documents/ObsidianVault

# LLM設定（OpenAIを使用する場合）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o

# LLM設定（Anthropicを使用する場合）
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# LLM_PROVIDER=anthropic
# LLM_MODEL=claude-3-5-sonnet-20241022

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
```

### GitHubトークンの取得

1. GitHubにログイン
2. Settings → Developer settings → Personal access tokens → Tokens (classic)
3. "Generate new token (classic)"をクリック
4. スコープで`repo`（リポジトリへの読み取りアクセス）を選択
5. トークンを生成し、`.env`ファイルにコピー

### APIキーの取得

#### OpenAI APIキー

1. https://platform.openai.com/ にアクセス
2. API Keysセクションで新しいキーを作成
3. `.env`ファイルに設定

#### Anthropic APIキー

1. https://console.anthropic.com/ にアクセス
2. API Keysセクションで新しいキーを作成
3. `.env`ファイルに設定

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
poetry run python scripts/initial_index.py
```

このスクリプトは以下を実行します：
1. GitHubリポジトリから全`.md`ファイルを取得
2. 各ファイルの内容を抽出・クリーニング
3. サマリーとタグを生成（LLM APIを使用）
4. ベクトル化
5. ChromaDBに格納

**注意**: 初回実行時は、記事数が多い場合、LLM APIの呼び出しに時間がかかります（100記事あたり約5-10分）。

## ステップ8: Web UIの起動

開発サーバーを起動：

```bash
poetry run uvicorn app.main:app --reload --port 8000
```

ブラウザで `http://localhost:8000` にアクセスします。

### 動作確認

1. 検索UIで記事を検索してみる
2. デイリーレポートを確認（`/api/reports/daily/{今日の日付}`）
3. ナレッジマップを確認（`/knowledge-map`）

## ステップ9: 自動実行の設定

### Linux/macOS (cron)

```bash
# crontabを編集
crontab -e

# 以下を追加（毎日午前6時に実行）
0 6 * * * cd /path/to/ObsidianConscierge && /path/to/poetry run python scripts/daily_update.py >> /path/to/logs/cron.log 2>&1
```

**注意**: `poetry`のパスを絶対パスで指定する必要があります。`which poetry`で確認できます。

### systemd (Linux)

#### サービスファイルの作成

`/etc/systemd/system/obsidian-conscierge.service`を作成：

```ini
[Unit]
Description=ObsidianConscierge Daily Update
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/home/your-username/ObsidianConscierge
Environment="PATH=/home/your-username/.local/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/your-username/.local/bin/poetry run python scripts/daily_update.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### タイマーファイルの作成

`/etc/systemd/system/obsidian-conscierge.timer`を作成：

```ini
[Unit]
Description=Run ObsidianConscierge Daily Update
Requires=obsidian-conscierge.service

[Timer]
OnCalendar=daily
OnCalendar=06:00
Persistent=true

[Install]
WantedBy=timers.target
```

#### タイマーの有効化

```bash
sudo systemctl daemon-reload
sudo systemctl enable obsidian-conscierge.timer
sudo systemctl start obsidian-conscierge.timer

# ステータス確認
sudo systemctl status obsidian-conscierge.timer
```

### Windows (Task Scheduler)

1. タスクスケジューラを開く（`taskschd.msc`）
2. "基本タスクの作成"を選択
3. 名前: "ObsidianConscierge Daily Update"
4. トリガー: "毎日" → 時刻: 6:00
5. 操作: "プログラムの起動"
   - プログラム/スクリプト: `C:\Users\YourUsername\AppData\Local\Programs\Python\Python311\python.exe`
   - 引数の追加: `-m poetry run python scripts/daily_update.py`
   - 開始場所: `C:\path\to\ObsidianConscierge`

## トラブルシューティング

### Poetryが見つからない

```bash
# PATHに追加
export PATH="$HOME/.local/bin:$PATH"

# または、シェル設定ファイル（.bashrc, .zshrc）に追加
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Pythonバージョンが正しくない

```bash
# pyenvを使用している場合
pyenv local 3.11.0

# 仮想環境を再作成
poetry env remove python
poetry install
```

### APIキーエラー

- `.env`ファイルのAPIキーが正しく設定されているか確認
- APIキーに余分なスペースや改行が含まれていないか確認
- APIキーの有効期限を確認

### ChromaDBのエラー

```bash
# データベースをリセット（注意: すべてのデータが削除されます）
rm -rf data/chroma_db/*
poetry run python scripts/initial_index.py
```

### ポートが既に使用されている

```bash
# 別のポートを指定
poetry run uvicorn app.main:app --reload --port 8001
```

## 次のステップ

セットアップが完了したら、以下を確認してください：

1. [README.md](../README.md) - 機能の詳細
2. [PRD.md](./PRD.md) - 要件定義
3. [ARCHITECTURE.md](./ARCHITECTURE.md) - アーキテクチャの詳細

