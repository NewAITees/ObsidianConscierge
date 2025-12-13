# プロジェクト進捗と次のTODO

## 現状サマリ
- [x] コアの下回り（設定、抽出、埋め込み生成、LLMラッパー、Chromaラッパー、Git差分検知、CLI検索）が揃い、ユニットテストが存在する。
- [ ] FastAPIアプリやインデックス/同期/レポートの実行フロー、ドキュメント整合性は未実装・未整備。

## 完了済み（実装/テスト済み）
- [x] 設定管理: `app/core/config.py` で`.env`を読むPydantic Settingsを用意。
- [x] コンテンツ抽出/クリーニング: `app/core/content_extractor.py` でFrontmatterパース、タイトル抽出、Markdownクリーニングを実装。
- [x] 埋め込み生成: `app/services/embedding_service.py` でsentence-transformers読み込みと決定論的フォールバック実装、バッチ対応。
- [x] LLMラッパー: `app/services/llm_service.py` でOllama呼び出し＋リトライ（サマリー/タグ生成）を実装。
- [x] ベクトルDB: `app/services/vector_db_service.py` でChromaへの保存/検索/削除/更新を実装。
- [x] Git差分検知: `app/core/git_sync.py` でGitPythonによる変更検出を実装。
- [x] セマンティック検索サービス: `app/core/search.py` ＋ `scripts/search_cli.py` によりCLI検索が動くパスを用意。
- [x] モデル: `app/models/article.py` に記事/変更検知用データクラスを定義。
- [x] テスト: `tests/unit/*` に埋め込み、LLM、Chroma、コンテンツ抽出、Git検知、CLI検索のユニットテストを配置（未実行）。

## 未完了/TODO（優先順でチェック可能）
- [ ] Vault指定の柔軟化を実地確認: GitHubリポジトリ名（owner/repo）またはURLを`.env`で設定し、`resolve_github_repo_url`の挙動を確認・ドキュメントに反映。
- [ ] systemd雛形の仕上げ: `systemd/`のサービス/タイマーファイルに環境固有のUser/パスを適用し、起動手順をドキュメントに追記。
- [ ] FastAPIアプリ実装: `app/main.py` とAPIルーターを追加し、ヘルスチェックと検索APIを提供。DI経路を整理（設定→サービス→エンドポイント）。
- [ ] インデックスパイプライン: `app/core/indexing.py` と `scripts/initial_index.py` を作成し、Git差分→抽出→サマリー/タグ生成→埋め込み→Chroma登録のフローを構築。前回コミットの保存（例: `data/last_commit.txt`）も実装。
- [ ] 定期ジョブスクリプト: `scripts/git_sync.py` と `scripts/daily_report.py` をPRD準拠で実装し、`pyproject.toml` のエントリポイントと整合させる。
- [ ] ドキュメント更新: READMEをuv前提に整理し、Poetry記述や未実装の機能説明を修正。`.env.example` と `Settings` の項目齟齬を解消。
- [ ] テスト拡充: FastAPIエンドポイントの統合テスト、インデックスパイプラインのフロー試験、Chroma/Ollamaをモックしたケースを追加し、カバレッジを80%以上に引き上げる。
- [ ] 運用/品質: ロギング設定の集中管理、共通リトライ/タイムアウトの導入、ChromaクライアントとEmbeddingモデルのライフサイクル管理（シングルトン化）、バッチ処理・パフォーマンス最適化をPRD要件に合わせて強化。

## 補足
- systemdテンプレート: `systemd/obsidian-conscierge-api.service`（API用）、`systemd/obsidian-conscierge-daily.service` と `systemd/obsidian-conscierge-daily.timer`（デイリーレポート用）の雛形を配置。`YOUR_USER` とパスを環境に合わせて書き換えて使用する。

## ブロッカー/注意点
- モデルダウンロード（sentence-transformers, Ollamaモデル）が重いため、CIやテストではモック利用を前提にする。
- `pyproject.toml` に定義されたCLIエントリ（`scripts.initial_index` など）が未実装のままなので、実行時エラーに注意。
