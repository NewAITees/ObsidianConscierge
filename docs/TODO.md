# TODO ドキュメント: ObsidianConscierge

このドキュメントは、プロジェクトの実装タスクを優先順位と依存関係に基づいて整理したものです。

## 📋 目次

1. [現状サマリ](#現状サマリ)
2. [優先度別TODO](#優先度別todo)
3. [実装フェーズ別TODO](#実装フェーズ別todo)
4. [詳細タスク一覧](#詳細タスク一覧)
5. [ブロッカー・注意点](#ブロッカー注意点)

---

## 現状サマリ

### ✅ 完了済み（実装/テスト済み）

- [x] **設定管理**: `app/core/config.py` で`.env`を読むPydantic Settingsを用意
- [x] **コンテンツ抽出/クリーニング**: `app/core/content_extractor.py` でFrontmatterパース、タイトル抽出、Markdownクリーニングを実装
- [x] **埋め込み生成**: `app/services/embedding_service.py` でsentence-transformers読み込みと決定論的フォールバック実装、バッチ対応
- [x] **LLMラッパー**: `app/services/llm_service.py` でOllama呼び出し＋リトライ（サマリー/タグ生成）を実装
- [x] **ベクトルDB**: `app/services/vector_db_service.py` でChromaへの保存/検索/削除/更新を実装
- [x] **Git差分検知**: `app/core/git_sync.py` でGitPythonによる変更検出を実装
- [x] **セマンティック検索サービス**: `app/core/search.py` ＋ `scripts/search_cli.py` によりCLI検索が動くパスを用意
- [x] **モデル**: `app/models/article.py` に記事/変更検知用データクラスを定義
- [x] **テスト**: `tests/unit/*` に埋め込み、LLM、Chroma、コンテンツ抽出、Git検知、CLI検索のユニットテストを配置（未実行）

### ❌ 未完了

- [ ] FastAPIアプリやインデックス/同期/レポートの実行フロー、ドキュメント整合性は未実装・未整備

---

## 優先度別TODO

### 🔴 P0: 最優先（MVP実装に必須）

1. **FastAPIアプリ実装** - 検索UIとAPI基盤
2. **インデックスパイプライン** - 初期インデックス作成と更新フロー
3. **ドキュメント更新** - READMEと`.env.example`の整合性確保

### 🟠 P1: 高優先度（日常利用に必要）

4. **定期ジョブスクリプト** - Git同期とデイリーレポート生成
5. **Vault指定の柔軟化** - GitHubリポジトリ設定の実地確認
6. **テスト拡充** - 統合テストとカバレッジ向上

### 🟡 P2: 中優先度（運用改善）

7. **systemd雛形の仕上げ** - 本番環境での自動実行設定
8. **運用/品質改善** - ロギング、リトライ、パフォーマンス最適化

---

## 実装フェーズ別TODO

### Phase 1: Core Service（MVP） - 🔴 P0

#### 1.1 FastAPIアプリ実装

**目標**: Web UIとAPI基盤を構築し、セマンティック検索を提供

**タスク**:
- [ ] `app/main.py` の実装
  - [ ] FastAPIアプリケーションの初期化
  - [ ] 設定（Settings）のDI（依存性注入）
  - [ ] サービス層の初期化（EmbeddingService, LLMService, VectorDBService）
  - [ ] ヘルスチェックエンドポイント (`GET /health`)
  - [ ] CORS設定（必要に応じて）
- [ ] `app/api/search.py` の実装
  - [ ] `GET /api/v1/search` エンドポイント
  - [ ] クエリパラメータ: `q` (必須), `tags` (オプション), `limit` (デフォルト20), `offset` (デフォルト0)
  - [ ] レスポンスモデル: `SearchResponse` (Pydantic)
  - [ ] エラーハンドリング（HTTPException）
- [ ] `app/api/__init__.py` でルーターを登録
- [ ] フロントエンド（HTML/JavaScript）の実装（オプション、Phase 1.5）
  - [ ] 検索UI（シンプルなHTML + Vanilla JS）
  - [ ] リアルタイム検索（デバウンス300ms）
  - [ ] 検索結果表示（タイトル、サマリー、類似度、Obsidianで開くボタン）

**依存関係**: 
- `app/core/search.py` (既存)
- `app/services/vector_db_service.py` (既存)
- `app/services/embedding_service.py` (既存)

**参考**: PRD.md B-1, ARCHITECTURE.md

**推定工数**: 2-3日

---

#### 1.2 インデックスパイプライン

**目標**: Git変更検知からChromaDB格納までの完全なフローを構築

**タスク**:
- [ ] `app/core/indexing.py` の実装
  - [ ] `IndexingService` クラスの作成
  - [ ] `detect_changes()` メソッド: Git差分検知（`app/core/git_sync.py`を活用）
  - [ ] `process_article()` メソッド: 単一記事の処理フロー
    - [ ] コンテンツ抽出（`app/core/content_extractor.py`）
    - [ ] サマリー生成（`app/services/llm_service.py`）
    - [ ] タグ生成（オプション、`app/services/llm_service.py`）
    - [ ] 埋め込み生成（`app/services/embedding_service.py`）
    - [ ] ChromaDB格納（`app/services/vector_db_service.py`）
  - [ ] `process_batch()` メソッド: バッチ処理（100件ずつ）
  - [ ] 前回コミットの保存/読み込み（`data/last_commit.txt`）
- [ ] `scripts/initial_index.py` の実装
  - [ ] コマンドライン引数パース（`click`使用）
  - [ ] 全記事の初期インデックス作成
  - [ ] 進捗表示（`tqdm`使用）
  - [ ] エラーハンドリングとログ出力
  - [ ] `pyproject.toml` の `[project.scripts]` と整合（`oc-index`）
- [ ] `scripts/git_sync.py` の実装（定期実行用）
  - [ ] Git pull実行（`app/core/git_sync.py`を活用）
  - [ ] 変更検知とインデックス更新
  - [ ] ログ出力
  - [ ] `pyproject.toml` の `[project.scripts]` と整合（`oc-sync`）

**依存関係**:
- `app/core/git_sync.py` (既存)
- `app/core/content_extractor.py` (既存)
- `app/services/llm_service.py` (既存)
- `app/services/embedding_service.py` (既存)
- `app/services/vector_db_service.py` (既存)

**参考**: PRD.md A-1, A-2, A-3, A-4, A-6, ARCHITECTURE.md

**推定工数**: 3-4日

---

#### 1.3 ドキュメント更新

**目標**: README、`.env.example`、その他ドキュメントをuv前提に整理

**タスク**:
- [ ] `README.md` の更新
  - [ ] Poetry記述をuvに置き換え
  - [ ] 未実装機能の説明を削除または「未実装」と明記
  - [ ] クイックスタート手順の確認と修正
  - [ ] コマンド例を `uv run` に統一
- [ ] `.env.example` の作成/更新
  - [ ] 必須項目の確認（`app/core/config.py` の `Settings` と整合）
  - [ ] オプション項目の追加
  - [ ] コメントで説明を追加
  - [ ] Ollama設定の明確化（Embeddingはsentence-transformers使用のため `OLLAMA_EMBEDDING_MODEL` は不要）
- [ ] `docs/SETUP_GUIDE.md` の更新
  - [ ] Poetry記述をuvに置き換え
  - [ ] Ollamaセットアップ手順の明確化
- [ ] `docs/STATUS.md` の更新（このドキュメント作成後）

**依存関係**: なし（独立タスク）

**参考**: PRD.md G, README.md

**推定工数**: 1日

---

### Phase 2: Daily Service - 🟠 P1

#### 2.1 定期ジョブスクリプト

**目標**: Git同期とデイリーレポート生成を定期実行可能にする

**タスク**:
- [ ] `scripts/daily_report.py` の実装
  - [ ] デイリーレポート生成ロジック
    - [ ] 昨日の執筆統計（新規記事数、更新記事数、総文字数）
    - [ ] 重複検知警告（類似度80%以上、`app/core/analysis.py` を活用）
    - [ ] ランダムピックアップ3記事（異分野優先）
    - [ ] MOC候補リスト（`app/core/analysis.py` を活用）
  - [ ] Markdown形式での出力（`reports/daily/{YYYY-MM-DD}.md`）
  - [ ] HTML形式での出力（オプション）
  - [ ] コマンドライン引数パース
  - [ ] `pyproject.toml` の `[project.scripts]` と整合（`oc-report`）
- [ ] `app/core/analysis.py` の実装（分析ロジック）
  - [ ] `detect_duplicates()` メソッド: 重複検知（コサイン類似度計算）
  - [ ] `find_moc_candidates()` メソッド: MOC候補抽出
  - [ ] `get_random_pickups()` メソッド: ランダムピックアップ（異分野優先）
- [ ] `app/api/reports.py` の実装（オプション、Web UI用）
  - [ ] `GET /api/v1/reports/daily/{date}` エンドポイント
  - [ ] レスポンスモデル: `DailyReportResponse` (Pydantic)

**依存関係**:
- `app/core/indexing.py` (Phase 1.2)
- `app/services/vector_db_service.py` (既存)
- `app/services/embedding_service.py` (既存)

**参考**: PRD.md B-2, B-3, C-1

**推定工数**: 3-4日

---

#### 2.2 Vault指定の柔軟化

**目標**: GitHubリポジトリ設定を柔軟に（URLまたはowner/repo形式）

**タスク**:
- [ ] `app/core/config.py` の `Settings` クラスを確認
  - [ ] `GITHUB_REPO_URL` の検証ロジックを確認
  - [ ] `resolve_github_repo_url()` 関数の実装/確認
    - [ ] URL形式（`https://github.com/owner/repo.git`）の処理
    - [ ] 短縮形式（`owner/repo`）の処理
    - [ ] エラーハンドリング（無効な形式の場合）
- [ ] `.env.example` に両方の形式の例を追加
- [ ] 実地確認とテスト
- [ ] ドキュメントに反映（README.md または SETUP_GUIDE.md）

**依存関係**: なし（独立タスク）

**参考**: PRD.md A-1

**推定工数**: 0.5日

---

#### 2.3 テスト拡充

**目標**: カバレッジ80%以上を達成

**タスク**:
- [ ] FastAPIエンドポイントの統合テスト
  - [ ] `tests/integration/test_api_search.py` の作成
    - [ ] 検索APIのテスト（モックChromaDB使用）
    - [ ] エラーハンドリングのテスト
  - [ ] `tests/integration/test_api_reports.py` の作成（オプション）
- [ ] インデックスパイプラインのフロー試験
  - [ ] `tests/integration/test_indexing.py` の作成
    - [ ] エンドツーエンドのフロー（Git差分→抽出→埋め込み→格納）
    - [ ] モックLLM/Ollama使用
- [ ] モックの整備
  - [ ] ChromaDBモック（`tests/fixtures/mock_chromadb.py`）
  - [ ] Ollamaモック（`tests/fixtures/mock_ollama.py`）
  - [ ] Embedding Serviceモック（`tests/fixtures/mock_embedding.py`）
- [ ] カバレッジレポートの確認
  - [ ] `uv run pytest --cov=app --cov-report=html` で確認
  - [ ] 80%未満の場合は追加テストを作成

**依存関係**:
- Phase 1.1 (FastAPIアプリ)
- Phase 1.2 (インデックスパイプライン)

**参考**: ARCHITECTURE.md (テスト戦略)

**推定工数**: 2-3日

---

### Phase 3: 運用改善 - 🟡 P2

#### 3.1 systemd雛形の仕上げ

**目標**: 本番環境での自動実行設定を完成させる

**タスク**:
- [ ] `systemd/obsidian-conscierge-api.service` の確認・更新
  - [ ] 環境固有のUser/パスを適用
  - [ ] `uv` コマンドのパスを確認
  - [ ] 環境変数の読み込み（`.env`ファイルまたは`EnvironmentFile`）
- [ ] `systemd/obsidian-conscierge-daily.service` の確認・更新
  - [ ] 環境固有のUser/パスを適用
  - [ ] `uv run python scripts/daily_report.py` のパスを確認
- [ ] `systemd/obsidian-conscierge-daily.timer` の確認・更新
  - [ ] 実行スケジュールの確認（毎日6:00）
- [ ] ドキュメントに起動手順を追記
  - [ ] `docs/SETUP_GUIDE.md` または `README.md` に追加
  - [ ] systemdの有効化・開始コマンドを記載
  - [ ] トラブルシューティング情報を追加

**依存関係**: Phase 2.1 (定期ジョブスクリプト)

**参考**: ARCHITECTURE.md (デプロイメント), SETUP_GUIDE.md

**推定工数**: 0.5日

---

#### 3.2 運用/品質改善

**目標**: ロギング、リトライ、パフォーマンス最適化を強化

**タスク**:
- [ ] ロギング設定の集中管理
  - [ ] `app/utils/logger.py` の実装/確認
    - [ ] ログフォーマットの統一
    - [ ] ログレベルの設定（`.env`から読み込み）
    - [ ] ファイル出力とコンソール出力の両対応
  - [ ] 各モジュールでのロギング使用を確認
- [ ] 共通リトライ/タイムアウトの導入
  - [ ] `app/utils/retry.py` の実装（`tenacity` ライブラリ使用、または自前実装）
    - [ ] 指数バックオフ付きリトライ
    - [ ] タイムアウト設定（Ollama: 60秒、Git操作: 30秒）
  - [ ] LLM Service、Git Sync Serviceでの使用
- [ ] ChromaクライアントとEmbeddingモデルのライフサイクル管理
  - [ ] シングルトンパターンの実装（またはFastAPIの依存性注入で管理）
  - [ ] Embeddingモデルの遅延読み込み
  - [ ] クリーンアップ処理（アプリ終了時）
- [ ] バッチ処理・パフォーマンス最適化
  - [ ] ベクトル生成のバッチ処理（100件ずつ）の確認
  - [ ] ChromaDB書き込みのバッチインサート確認
  - [ ] 非同期処理の活用（FastAPIの非同期エンドポイント）

**依存関係**: Phase 1.1, Phase 1.2

**参考**: PRD.md E-1 (パフォーマンス), ARCHITECTURE.md (パフォーマンス最適化)

**推定工数**: 2-3日

---

## 詳細タスク一覧

### 実装タスク（チェックリスト形式）

#### Phase 1: Core Service（MVP）

- [ ] **1.1 FastAPIアプリ実装**
  - [ ] `app/main.py` の実装
  - [ ] `app/api/search.py` の実装
  - [ ] `app/api/__init__.py` でルーター登録
  - [ ] フロントエンド（オプション）

- [ ] **1.2 インデックスパイプライン**
  - [ ] `app/core/indexing.py` の実装
  - [ ] `scripts/initial_index.py` の実装
  - [ ] `scripts/git_sync.py` の実装

- [ ] **1.3 ドキュメント更新**
  - [ ] `README.md` の更新（uv前提に）
  - [ ] `.env.example` の作成/更新
  - [ ] `docs/SETUP_GUIDE.md` の更新

#### Phase 2: Daily Service

- [ ] **2.1 定期ジョブスクリプト**
  - [ ] `scripts/daily_report.py` の実装
  - [ ] `app/core/analysis.py` の実装
  - [ ] `app/api/reports.py` の実装（オプション）

- [ ] **2.2 Vault指定の柔軟化**
  - [ ] `app/core/config.py` の確認・更新
  - [ ] 実地確認とテスト
  - [ ] ドキュメント更新

- [ ] **2.3 テスト拡充**
  - [ ] FastAPIエンドポイントの統合テスト
  - [ ] インデックスパイプラインのフロー試験
  - [ ] モックの整備
  - [ ] カバレッジ80%以上を達成

#### Phase 3: 運用改善

- [ ] **3.1 systemd雛形の仕上げ**
  - [ ] systemdファイルの確認・更新
  - [ ] ドキュメントに起動手順を追記

- [ ] **3.2 運用/品質改善**
  - [ ] ロギング設定の集中管理
  - [ ] 共通リトライ/タイムアウトの導入
  - [ ] ライフサイクル管理（シングルトン化）
  - [ ] バッチ処理・パフォーマンス最適化

---

## ブロッカー・注意点

### 技術的ブロッカー

1. **モデルダウンロードの重さ**
   - sentence-transformersモデル（distiluse-base-multilingual-cased-v2）の初回ダウンロード
   - Ollamaモデル（llama3）のダウンロード（約4.7GB）
   - **対策**: CIやテストではモック利用を前提にする

2. **`pyproject.toml` のCLIエントリ未実装**
   - `[project.scripts]` に定義された `oc-index`, `oc-search`, `oc-sync`, `oc-report` が未実装
   - **対策**: 実装完了まで実行時エラーに注意

### 実装上の注意点

1. **既存実装の活用**
   - `sample_code/` フォルダの実証済み実装を参照
   - TF-IDF分析、ChromaDB統合、MOC生成などは既存実装を基盤として使用

2. **uv前提の開発**
   - Poetry記述をすべてuvに置き換える
   - `poetry run` → `uv run`
   - `poetry add` → `uv add`

3. **Ollamaとsentence-transformersの使い分け**
   - **Ollama**: テキスト生成（サマリー、タグ生成）のみ
   - **sentence-transformers**: Embedding生成（既存実装を継続使用）
   - `.env` に `OLLAMA_EMBEDDING_MODEL` は不要

4. **Git同期の実装**
   - `TargetObsidianVault` ディレクトリへのローカル同期
   - GitHub APIではなく、GitPythonでローカルリポジトリを操作

### ドキュメント整合性

1. **README.md**
   - Poetry記述が残っている（uvに置き換え必要）
   - 未実装機能の説明を修正

2. **SETUP_GUIDE.md**
   - Poetry前提の記述が残っている（uvに置き換え必要）

3. **`.env.example`**
   - `app/core/config.py` の `Settings` クラスと項目が一致しているか確認

---

## 次のアクション

1. **Phase 1.1 (FastAPIアプリ実装)** から開始
2. 各タスク完了後、`docs/STATUS.md` を更新
3. ブロッカーが発生した場合は、このドキュメントに追記

---

## 参考資料

- [PRD.md](./PRD.md) - プロダクト要件定義書
- [ARCHITECTURE.md](./ARCHITECTURE.md) - アーキテクチャドキュメント
- [STATUS.md](./STATUS.md) - プロジェクト進捗状況
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - セットアップガイド
- [QUESTIONS.md](./QUESTIONS.md) - 確認事項と追加情報

---

**最終更新**: 2025-01-XX
**次回レビュー**: Phase 1完了時

