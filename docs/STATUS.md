# プロジェクト進捗と次のTODO

> **詳細なTODOリスト**: 実装タスクの詳細は [TODO.md](./TODO.md) を参照してください。

## 現状サマリ
- [x] コアの下回り（設定、抽出、埋め込み生成、LLMラッパー、Chromaラッパー、Git差分検知、CLI検索）が揃い、ユニットテストが存在する。
- [x] FastAPIアプリとインデックスパイプラインが実装済み ✅
- [x] フロントエンドUI（検索UI）が実装済み ✅
- [x] Git同期スクリプトとsystemd設定が実装済み ✅
- [x] デイリーレポート機能が実装済み（Phase 2.1完了） ✅
- [x] Vault指定の柔軟化が実装済み（Phase 2.2完了） ✅
- [x] ドキュメント整合性は整備済み ✅
- [ ] テストカバレッジ: 現在59%（目標80%）

## 完了済み（実装/テスト済み）

### Phase 1.1: FastAPIアプリ実装 ✅
- [x] FastAPIアプリケーション基盤: `app/main.py`、ライフサイクル管理、DI、ヘルスチェック、CORS
- [x] 検索API: `app/api/search.py` - `GET /api/v1/search` エンドポイント
- [x] 設定API: `app/api/config.py` - `GET /api/v1/config` エンドポイント
- [x] データモデル: `app/models/search.py` - 検索リクエスト/レスポンスモデル
- [x] フロントエンドUI: `app/static/` - 検索UI（HTML/CSS/JavaScript）、リアルタイム検索、ページネーション、Obsidian連携
- [x] 統合テスト: `tests/integration/test_main.py`, `test_api_search.py` - 全7テスト通過

### Phase 1.2: インデックスパイプライン ✅
- [x] インデックスサービス: `app/core/indexing.py` - 記事処理フロー、バッチ処理、前回コミット管理
- [x] 初期インデックス作成: `scripts/initial_index.py` - 全記事のインデックス化
- [x] Git同期スクリプト: `scripts/git_sync.py`, `scripts/git_sync.sh` - Git pull/push、変更検知、インデックス更新
- [x] systemd設定: `systemd/obsidian-conscierge-sync.service`, `.timer` - 30分ごとの自動同期
- [x] 統合テスト: `tests/integration/test_indexing.py` - 全3テスト通過

### Phase 1.3: ドキュメント更新 ✅
- [x] `.env.example` の作成 - 全設定項目を網羅、コメント付き
- [x] `README.md` の更新 - Poetry→uv、未実装機能の明記
- [x] `docs/SETUP_GUIDE.md` の更新 - Poetry→uv、Ollamaセットアップ手順
- [x] `docs/STATUS.md` の更新 - Phase 1完了を反映

### Phase 2.1: デイリーレポート機能 ✅
- [x] 分析サービス: `app/core/analysis.py` - 重複検知、MOC候補抽出、ランダムピックアップ、執筆統計
- [x] レポートAPI: `app/api/reports.py` - `GET /api/v1/reports/daily/{date}` エンドポイント
- [x] レポートモデル: `app/models/report.py` - DailyReportResponse、WritingStatistics等
- [x] デイリーレポートスクリプト: `scripts/daily_report.py` - Markdown/HTML形式でのレポート生成
- [x] CLIエントリ: `pyproject.toml` に `oc-report` を追加
- [x] 統合テスト: `tests/integration/test_api_reports.py` - 全7テスト通過
- [x] ユニットテスト: `tests/unit/test_analysis.py` - 全25テスト通過

### Phase 2.2: Vault指定の柔軟化 ✅
- [x] `app/core/config.py` の `resolve_github_repo_url()` メソッド実装
  - [x] `GITHUB_REPO_NAME`（owner/repo形式）のサポート
  - [x] `GITHUB_REPO_URL`（完全URL形式）のサポート
  - [x] 両形式の自動変換とバリデーション
- [x] `.env.example` に両形式の例を追加
- [x] `docs/SETUP_GUIDE.md` に設定方法を記載

### Phase 2.3: テスト拡充 ⏳
- [x] Git変更検知のエラーハンドリング改善
- [x] 統合テストの修正（実際のGitリポジトリを使用）
- [x] 全71テスト通過 ✅
- [ ] カバレッジ80%以上（現在59%）

### コア機能（既存）
- [x] 設定管理: `app/core/config.py` で`.env`を読むPydantic Settingsを用意。
- [x] コンテンツ抽出/クリーニング: `app/core/content_extractor.py` でFrontmatterパース、タイトル抽出、Markdownクリーニングを実装。
- [x] 埋め込み生成: `app/services/embedding_service.py` でsentence-transformers読み込みと決定論的フォールバック実装、バッチ対応。
- [x] LLMラッパー: `app/services/llm_service.py` でOllama呼び出し＋リトライ（サマリー/タグ生成）を実装。
- [x] ベクトルDB: `app/services/vector_db_service.py` でChromaへの保存/検索/削除/更新を実装。
- [x] Git差分検知: `app/core/git_sync.py` でGitPythonによる変更検出を実装。
- [x] セマンティック検索サービス: `app/core/search.py` ＋ `scripts/search_cli.py` によりCLI検索が動くパスを用意。
- [x] モデル: `app/models/article.py` に記事/変更検知用データクラスを定義。
- [x] テスト: `tests/unit/*` に埋め込み、LLM、Chroma、コンテンツ抽出、Git検知、CLI検索のユニットテストを配置。

## 未完了/TODO（優先順位別）

### 🔴 P0: 最優先（MVP実装に必須）
- [x] **FastAPIアプリ実装**: `app/main.py` とAPIルーターを追加し、ヘルスチェックと検索APIを提供。DI経路を整理（設定→サービス→エンドポイント）。✅
- [x] **インデックスパイプライン**: `app/core/indexing.py` と `scripts/initial_index.py` を作成し、Git差分→抽出→サマリー/タグ生成→埋め込み→Chroma登録のフローを構築。前回コミットの保存（例: `data/last_commit.txt`）も実装。✅
- [x] **ドキュメント更新**: READMEをuv前提に整理し、Poetry記述や未実装の機能説明を修正。`.env.example` と `Settings` の項目齟齬を解消。✅

### 🟠 P1: 高優先度（日常利用に必要）
- [x] **Git同期スクリプト**: `scripts/git_sync.py` と `scripts/git_sync.sh` を実装 ✅
- [x] **デイリーレポートスクリプト**: `scripts/daily_report.py` をPRD準拠で実装 ✅
- [x] **Vault指定の柔軟化**: GitHubリポジトリ名（owner/repo）またはURLを`.env`で設定し、`resolve_github_repo_url`の挙動を確認・ドキュメントに反映。 ✅
- [ ] **テスト拡充**: カバレッジを80%以上に引き上げる（現在59%、目標80%）

### 🟡 P2: 中優先度（運用改善）
- [x] **systemd雛形の仕上げ**: `systemd/obsidian-conscierge-sync.service`, `.timer` を作成、`docs/SYSTEMD_SETUP.md` に起動手順を追記 ✅
- [ ] **運用/品質**: ロギング設定の集中管理、共通リトライ/タイムアウトの導入、ChromaクライアントとEmbeddingモデルのライフサイクル管理（シングルトン化）、バッチ処理・パフォーマンス最適化をPRD要件に合わせて強化。

## 補足
- systemdテンプレート:
  - ✅ `systemd/obsidian-conscierge-sync.service` と `.timer`（Git同期用、30分ごと）- 実装済み
  - `systemd/obsidian-conscierge-api.service`（API用）- 未使用（uvicornで直接起動）
  - `systemd/obsidian-conscierge-daily.service` と `.timer`（デイリーレポート用）- Phase 2で実装予定
- すべてのsystemdファイルで`YOUR_USER`とパスを環境に合わせて書き換えて使用する必要があります。

## ブロッカー/注意点
- モデルダウンロード（sentence-transformers, Ollamaモデル）が重いため、CIやテストではモック利用を前提にする。
- `pyproject.toml` に定義されたCLIエントリ（`oc-index`, `oc-sync`, `oc-search`, `oc-report`）は実装済み ✅

## 関連ドキュメント
- [TODO.md](./TODO.md) - 詳細な実装タスクリスト（優先順位、依存関係、推定工数を含む）
- [PRD.md](./PRD.md) - プロダクト要件定義書
- [ARCHITECTURE.md](./ARCHITECTURE.md) - アーキテクチャドキュメント
