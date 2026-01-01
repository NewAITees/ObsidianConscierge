# 引き継ぎ作業依頼書：アトミック・ノート詳細設計

## 📋 作業概要

**目的:** アトミック・ノートワークフローの**具体的な実装設計**を作成する

**背景:**
- `docs/ATOMIC_NOTES_INTEGRATION.md`に抽象的な設計は完成
- **しかし、具体的な実装例がない**（これが問題）
- ユーザーから「どういう文章からどう中身を取り出して資産化するのか？」と指摘あり

---

## ✅ 完了済みの作業（このセッション）

### 1. バグ修正 ✅
- パス重複バグ修正（`scripts/git_sync.py` line 53）
- 日付型変換バグ修正（`app/core/indexing.py` line 269-273）

### 2. systemd自動化 ✅
- 全設定ファイルでユーザー名・パス自動置換
- ワンコマンドセットアップスクリプト作成（`scripts/setup_systemd.sh`）
- **現在動作中**: Git同期（30分ごと）、デイリーレポート（毎朝6時）、FastAPI（常駐）

### 3. ドキュメント作成 ✅
- `docs/ATOMIC_NOTES_INTEGRATION.md` - 抽象的な設計書（完成）
- `CLAUDE.md` - 144行追加（pre-commit、MCP、アトミック・ノート概念）

---

## 🎯 次に実施すべき作業（最優先）

### 作業: `docs/ATOMIC_NOTES_DETAILED_DESIGN.md` の作成

**ユーザーの要求:**
> 「具体的にどういう文章からどういう風に中身を取り出して、資産化に持って行くんですか？」

### 必須項目（これがないと実装できない）

#### 1. 具体例で示す（最重要）

**入力例（00_Raw）:**
```markdown
# 2025-01-01 会議メモ

今日はプロジェクトXの進捗会議。

## 議題1: AI動画の集客戦略
マーケティングチームから、AI動画を使った集客施策の提案があった。
YouTube shortsとTikTokでの展開を検討。
費用は月50万円、ROIは3ヶ月で回収見込み。

## 議題2: 新機能の開発
エンジニアチームから、レコメンデーション機能の実装提案。
ベクトル検索を使った類似記事推薦。
実装期間は2週間、リリースは来月中旬予定。

## 決定事項
- AI動画施策は承認、来週から開始
- レコメンデーション機能も承認、優先度高で実装

## 次回アクション
- マーケティング: 動画制作会社との契約
- エンジニア: 技術調査とスケジュール作成
```

**↓ 01_Summary（整形）:**
```markdown
---
title: "プロジェクトX進捗会議 2025-01-01"
created: 2025-01-01
tags: [会議, プロジェクトX, AI動画, レコメンデーション]
pipeline_stage: "01_Summary"
---

# プロジェクトX進捗会議 2025-01-01

## サマリー
AI動画集客施策とレコメンデーション機能の2つの提案を承認。
AI動画は月50万円でYouTube/TikTok展開、ROI 3ヶ月。
レコメンデーション機能は2週間で実装、来月リリース予定。

## 議題
1. AI動画の集客戦略（承認）
2. レコメンデーション機能開発（承認）

## アクション
- マーケティング: 動画制作会社との契約
- エンジニア: 技術調査とスケジュール
```

**↓ 02_Atomic（資産化）- 分解結果:**

**ファイル1: `02_Atomic/AI動画集客戦略.md`**
```markdown
---
title: "AI動画集客戦略"
created: 2025-01-01
tags: [マーケティング, AI動画, 集客]
pipeline_stage: "02_Atomic"
source: "プロジェクトX進捗会議 2025-01-01"
---

# AI動画集客戦略

## 概念
AI動画を使ったYouTube shorts/TikTokでの集客施策

## 詳細
- プラットフォーム: YouTube shorts、TikTok
- 費用: 月50万円
- ROI: 3ヶ月で回収見込み
- ステータス: 承認済み、来週開始

## 関連リンク
- [[プロジェクトX進捗会議 2025-01-01]]
```

**ファイル2: `02_Atomic/ベクトル検索レコメンデーション.md`**
```markdown
---
title: "ベクトル検索レコメンデーション"
created: 2025-01-01
tags: [技術, ベクトル検索, レコメンデーション]
pipeline_stage: "02_Atomic"
source: "プロジェクトX進捗会議 2025-01-01"
---

# ベクトル検索レコメンデーション

## 概念
ベクトル検索を使った類似記事推薦機能

## 詳細
- 技術: ベクトル検索
- 実装期間: 2週間
- リリース予定: 来月中旬
- ステータス: 承認済み、優先度高

## 関連リンク
- [[プロジェクトX進捗会議 2025-01-01]]
```

**↓ 03_MOC（地図）:**
```markdown
---
title: "MOC: プロジェクトX"
pipeline_stage: "03_MOC"
tags: [moc, プロジェクトX]
---

# MOC: プロジェクトX

## 関連ノート

### マーケティング
- [[AI動画集客戦略]]

### 技術
- [[ベクトル検索レコメンデーション]]

### 会議メモ
- [[プロジェクトX進捗会議 2025-01-01]]

## 概要
プロジェクトXに関連する全ノートのマップ。
マーケティング施策と技術実装を並行して進行中。
```

#### 2. LLMプロンプトの完全版

**分解プロンプト（02_Atomic生成用）:**
```
以下の文章から、独立した概念（アトミック・ノート）を抽出してください。

【ルール】
1. 1つの概念 = 1つのノート
2. 各ノートは「1ファイル1テーマ」
3. 他のノートと組み合わせて使える「レゴブロック」として設計
4. 各ノートは以下の形式で出力:

---ATOMIC_NOTE---
タイトル: [概念名]
タグ: [関連タグ]
内容:
[詳細説明]
---END---

【入力文章】
{01_Summaryの内容}

【出力例】
---ATOMIC_NOTE---
タイトル: AI動画集客戦略
タグ: マーケティング, AI動画, 集客
内容:
AI動画を使ったYouTube shorts/TikTokでの集客施策。
費用: 月50万円、ROI: 3ヶ月で回収見込み。
---END---
```

#### 3. 既存実装との統合

**活用すべき既存コード:**
- `sample_code/find_similar_documents.py` - 類似度計算（MOC生成に使用）
- `app/services/llm_service.py` - LLM呼び出し（分解プロンプトに使用）
- `app/core/analysis.py` - クラスタリング（MOC候補抽出に使用）

**統合方針:**
```python
# 新規作成するモジュール
app/core/atomic_splitter.py  # 長文 → アトミック・ノート分解
app/core/atomic_scorer.py    # アトミック性評価
app/core/pipeline_manager.py # パイプラインステージ管理
app/core/moc_generator.py    # MOC自動生成（既存のanalysis.pyを活用）
```

#### 4. 段階的移行プラン

**YellowMableの現在の構成:**
```
TargetObsidianVault/
├── 00CreatedFiles/  ← ここが実質的な00_Raw
├── 01DIARY/
├── 04CODING/
├── 06MOC/          ← 既存のMOC（手動作成）
└── ...
```

**移行手順:**
1. **段階0**: 既存フォルダはそのまま（後方互換性）
2. **段階1**: 新規に`00_Raw/`, `01_Summary/`, `02_Atomic/`, `03_MOC/`を作成
3. **段階2**: `00CreatedFiles/`のファイルを`01_Summary/`に移行（手動または自動）
4. **段階3**: 01_Summaryから02_Atomicへの分解を開始
5. **段階4**: 03_MOCの自動生成を有効化

---

## 📝 作成すべきドキュメント構成

### `docs/ATOMIC_NOTES_DETAILED_DESIGN.md`

```markdown
# アトミック・ノート詳細設計書

## 1. 実装例（具体的なサンプル付き）
- 1.1 入力例（00_Raw）
- 1.2 整形後（01_Summary）
- 1.3 分解後（02_Atomic）- 複数ファイル
- 1.4 MOC生成（03_MOC）

## 2. LLMプロンプト設計
- 2.1 要約プロンプト（00_Raw → 01_Summary）
- 2.2 分解プロンプト（01_Summary → 02_Atomic）
- 2.3 MOC生成プロンプト（02_Atomic → 03_MOC）

## 3. 実装詳細
- 3.1 atomic_splitter.py の設計
  - split_into_atomic_notes() メソッド
  - LLM呼び出し処理
  - マークダウンファイル生成
- 3.2 pipeline_manager.py の設計
  - ステージ遷移管理
  - メタデータ更新
- 3.3 moc_generator.py の設計
  - 既存のanalysis.pyとの統合
  - クラスタリング活用

## 4. API仕様
- POST /api/v1/atomic/split
- GET /api/v1/atomic/score
- POST /api/v1/moc/generate
- GET /api/v1/pipeline/status

## 5. 段階的移行プラン
- 既存フォルダとの共存
- YellowMableの現構成からの移行手順

## 6. テストケース
- 単体テスト
- 統合テスト
- E2Eテスト
```

---

## 🔑 重要な制約・要件

### ユーザーの意図
- **フォルダ分けは禁止**（AIが混乱する）
- **1ファイル1テーマ**（レゴブロック化）
- **リンクで関連付け**（フォルダではなく）
- **4段階パイプライン**を厳守（00_Raw → 01_Summary → 02_Atomic → 03_MOC）

### 既存システムとの整合性
- YellowMableの既存構成を壊さない
- 既存の`sample_code/`実装を最大限活用
- ChromaDB、Ollama、sentence-transformersとの連携

---

## 📂 参考ファイル

- `docs/ATOMIC_NOTES_INTEGRATION.md` - 抽象的な設計（既存）
- `app/services/llm_service.py` - LLM呼び出し実装
- `app/core/analysis.py` - クラスタリング実装
- `sample_code/find_similar_documents.py` - 類似度計算

---

## 💡 次のClaude Codeインスタンスへ

**最初にすべきこと:**
1. このファイルを読む
2. `docs/ATOMIC_NOTES_INTEGRATION.md`を読む
3. ユーザーに「上記の理解で合っているか」確認
4. `docs/ATOMIC_NOTES_DETAILED_DESIGN.md`を作成開始

**作成時の注意:**
- 抽象論ではなく**具体例を豊富に**
- LLMプロンプトは**実際に動くレベル**で
- Pythonコードサンプルを含める
- 既存実装との統合方法を明確に

**成功の基準:**
このドキュメントを読めば、エンジニアがすぐに実装を開始できるレベル。

---

## 📊 現在の環境状態

- systemd: 全サービス稼働中（Git同期30分ごと、デイリーレポート毎朝6時、FastAPI常駐）
- ChromaDB: 5,437件のドキュメント格納済み
- バグ: 修正完了（パス重複、日付型変換）
- ユーザー: perso
- プロジェクトパス: `/home/perso/analysis/ObsidianConscierge`
- Vault: `/home/perso/analysis/ObsidianConscierge/TargetObsidianVault` (YellowMable)

---

作成日時: 2025-12-31 23:46
作成者: Claude Sonnet 4.5
