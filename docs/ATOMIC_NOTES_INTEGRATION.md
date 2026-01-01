# アトミック・ノート統合設計書

## 概要

このドキュメントは、ObsidianConsciergeに**アトミック・ノート（Atomic Notes）**のワークフローを統合するための設計書です。

### アトミック・ノートとは

> 情報を原子レベル（アトミック）に分解し、1つのノートに1つのテーマのみを記述する手法。
> フォルダによる分類ではなく、リンクによる関連付けを重視する。

**メリット:**
- AIが情報を参照しやすい（フォルダ階層による混乱を防ぐ）
- ノートの再利用性が高い（レゴブロックのように組み合わせ可能）
- 分類の曖昧さを解消（「集客用のAI動画」はどこに入れる？問題の回避）
- グラフビューが整理される（関連性が可視化される）

---

## 4段階パイプライン

アトミック・ノートのワークフローは以下の4段階で構成されます：

### 1️⃣ 00_Raw（ぶち込み）
**目的:** 情報の高速投入
- 殴り書き、文字おこし、メモを分類せずに即座に保存
- 「どこに入れるか」を考える時間を削減

**既存機能との関連:**
- ✅ Git同期で自動的にインデックス化される
- ✅ セマンティック検索で即座に検索可能

### 2️⃣ 01_Summary（整形）
**目的:** AIによる要約・整形
- 生情報を人間が読みやすい形（議事録、サマリー）に変換
- タグ付け、要点抽出

**既存機能との関連:**
- ✅ `app/services/llm_service.py` でサマリー生成済み
- ✅ `app/core/analysis.py` でタグ自動生成可能

### 3️⃣ 02_Atomic（資産化）
**目的:** 1ファイル1テーマへの分解
- 長文ノートから重要な概念を短冊化
- 独立したテーマとして再利用可能にする

**🆕 必要な新機能:**
- **ノート分解機能**: 長文から複数のアトミック・ノートを自動抽出
- **アトミック性評価**: ノートが「1テーマ」になっているかチェック

### 4️⃣ 03_MOC（地図）
**目的:** ノート同士をリンクで繋ぐ
- フォルダ分類ではなく、関連性（リンク）でノートを整理
- Map of Contents（MOC）による知識マップ作成

**既存機能との関連:**
- ✅ `app/core/analysis.py` でMOC候補抽出済み
- ✅ `app/core/link_inserter.py` で類似リンク自動挿入済み
- 🆕 MOC自動生成機能の強化が必要

---

## 既存機能との整合性分析

### ✅ 活用できる既存機能

| 既存機能 | アトミック・ノートでの活用 | 該当ステージ |
|---------|--------------------------|-------------|
| セマンティック検索 | 00_Rawの投入直後から検索可能 | 1️⃣ |
| サマリー自動生成 | 01_Summaryの整形に活用 | 2️⃣ |
| タグ自動生成 | 01_Summaryでのタグ付けに活用 | 2️⃣ |
| 重複検知 | 02_Atomicでの分解前に重複をチェック | 3️⃣ |
| 類似リンク挿入 | 03_MOCでの関連付けに活用 | 4️⃣ |
| MOC候補抽出 | 03_MOCの自動生成に活用 | 4️⃣ |

### 🆕 新規開発が必要な機能

| 新機能 | 目的 | 優先度 | 該当ステージ |
|--------|------|--------|-------------|
| ノート分解機能 | 長文ノートを複数のアトミック・ノートに分解 | 🔴 P0 | 3️⃣ |
| アトミック性評価 | ノートが1テーマになっているかスコア化 | 🟡 P2 | 3️⃣ |
| パイプライン管理 | 4段階のステージを追跡・管理 | 🟠 P1 | 全体 |
| MOC自動生成強化 | 関連ノートを自動でMOCにまとめる | 🟠 P1 | 4️⃣ |
| グラフビュー最適化 | アトミック・ノート間の関係性可視化 | 🟡 P2 | 4️⃣ |

---

## 新機能の詳細設計

### 🆕 機能1: ノート分解機能

**概要:** 長文ノートから複数のアトミック・ノートを自動抽出

**アルゴリズム:**
1. 長文ノートをLLMに渡す
2. プロンプト: "この文章から独立したテーマ（概念）を抽出し、それぞれを1つのノートに分解してください。各ノートは以下の形式で出力してください: [タイトル] | [内容]"
3. 出力を解析し、個別のマークダウンファイルとして保存
4. 元ノートから新ノートへのリンクを自動挿入

**実装場所:** `app/core/atomic_splitter.py`

**API:** `POST /api/v1/atomic/split`
- Input: `{"file_path": "00_Raw/long_note.md"}`
- Output: `{"created_files": ["02_Atomic/concept1.md", "02_Atomic/concept2.md"]}`

**設定:**
- `ENABLE_ATOMIC_SPLIT`: ON/OFF（デフォルト: false）
- `MIN_CHARS_FOR_SPLIT`: 分解対象の最小文字数（デフォルト: 1000）
- `MAX_ATOMIC_NOTES`: 1つのノートから生成する最大分割数（デフォルト: 5）

---

### 🆕 機能2: アトミック性評価

**概要:** ノートが「1ファイル1テーマ」になっているかスコア化

**評価基準:**
1. **テーマの一貫性**: ノート内のトピックが1つに絞られているか（0-100点）
2. **長さの適切性**: 短すぎず長すぎないか（100-500文字が理想、0-100点）
3. **リンクの有無**: 関連ノートへのリンクがあるか（0-100点）

**スコア計算:**
```
アトミック性スコア = (テーマ一貫性 * 0.5) + (長さ適切性 * 0.3) + (リンク有無 * 0.2)
```

**実装場所:** `app/core/atomic_scorer.py`

**API:** `GET /api/v1/atomic/score?file_path=02_Atomic/concept.md`
- Output: `{"score": 85, "details": {"theme": 90, "length": 80, "links": 85}}`

---

### 🆕 機能3: パイプライン管理

**概要:** 4段階のステージを追跡・管理

**データ構造:**
各ノートのメタデータに以下を追加:
```yaml
---
title: "ノートタイトル"
pipeline_stage: "00_Raw"  # 00_Raw, 01_Summary, 02_Atomic, 03_MOC
pipeline_created_at: "2025-01-15T10:00:00"
pipeline_updated_at: "2025-01-15T11:00:00"
---
```

**ステージ遷移ルール:**
- 00_Raw → 01_Summary: サマリー生成完了時
- 01_Summary → 02_Atomic: ノート分解完了時
- 02_Atomic → 03_MOC: MOCに追加された時

**実装場所:** `app/core/pipeline_manager.py`

**API:**
- `GET /api/v1/pipeline/status`: 各ステージの記事数を取得
- `POST /api/v1/pipeline/move`: ノートを次のステージに移動

---

### 🆕 機能4: MOC自動生成強化

**概要:** 関連ノートを自動でMOCにまとめる

**アルゴリズム:**
1. 02_Atomicフォルダ内の全ノートを取得
2. セマンティック検索で類似度0.7以上のノート群を抽出
3. クラスタリング（既存の`app/core/analysis.py`を活用）
4. 各クラスタごとにMOCを自動生成

**MOCテンプレート:**
```markdown
---
title: "MOC: [クラスタテーマ]"
pipeline_stage: "03_MOC"
tags: [moc, auto-generated]
---

# MOC: [クラスタテーマ]

## 関連ノート

- [[ノート1]] - 説明
- [[ノート2]] - 説明
- [[ノート3]] - 説明

## 概要

このMOCは、以下のテーマに関連するノートをまとめています：
[AIが生成した概要文]
```

**実装場所:** `app/core/moc_generator.py`

**API:** `POST /api/v1/moc/generate`
- Input: `{"min_similarity": 0.7, "min_cluster_size": 3}`
- Output: `{"created_mocs": ["03_MOC/ai_video.md", "03_MOC/marketing.md"]}`

---

## フォルダ構成の変更

### 現状の問題点
現在のObsidianConsciergeは、ユーザーのVault構成に依存しており、フォルダ分けを前提としていません。

### 推奨フォルダ構成（アトミック・ノート対応）

```
TargetObsidianVault/
├── 00_Raw/              # 生情報（分類前）
├── 01_Summary/          # AI整形済み
├── 02_Atomic/           # アトミック・ノート（1ファイル1テーマ）
├── 03_MOC/              # Map of Contents（関連付け）
└── [その他のフォルダ]   # 従来の分類フォルダ（互換性維持）
```

**重要:** 既存のフォルダ構成との互換性を維持します。`00_Raw`〜`03_MOC`はオプションです。

### 設定ファイル（`.env`）への追加

```env
# アトミック・ノート設定
ENABLE_ATOMIC_WORKFLOW=false  # アトミック・ノートワークフローのON/OFF
PIPELINE_FOLDERS=00_Raw,01_Summary,02_Atomic,03_MOC  # パイプラインフォルダ

# ノート分解設定
ENABLE_ATOMIC_SPLIT=false
MIN_CHARS_FOR_SPLIT=1000
MAX_ATOMIC_NOTES=5

# MOC自動生成設定
ENABLE_AUTO_MOC_GENERATION=false
MIN_SIMILARITY_FOR_MOC=0.7
MIN_CLUSTER_SIZE_FOR_MOC=3
```

---

## 実装ロードマップ

### Phase 3.1: パイプライン管理基盤 (🔴 P0)
- [ ] `app/core/pipeline_manager.py` の実装
- [ ] メタデータへの`pipeline_stage`追加
- [ ] ステージ遷移API（`/api/v1/pipeline/*`）
- [ ] テスト: `tests/unit/test_pipeline_manager.py`

### Phase 3.2: ノート分解機能 (🔴 P0)
- [ ] `app/core/atomic_splitter.py` の実装
- [ ] LLMプロンプトの最適化
- [ ] 分解API（`/api/v1/atomic/split`）
- [ ] テスト: `tests/unit/test_atomic_splitter.py`

### Phase 3.3: MOC自動生成強化 (🟠 P1)
- [ ] `app/core/moc_generator.py` の実装
- [ ] クラスタリング統合（`app/core/analysis.py`を活用）
- [ ] MOC生成API（`/api/v1/moc/generate`）
- [ ] テスト: `tests/unit/test_moc_generator.py`

### Phase 3.4: アトミック性評価 (🟡 P2)
- [ ] `app/core/atomic_scorer.py` の実装
- [ ] スコアリングアルゴリズムの最適化
- [ ] スコア取得API（`/api/v1/atomic/score`）
- [ ] テスト: `tests/unit/test_atomic_scorer.py`

### Phase 3.5: グラフビュー最適化 (🟡 P2)
- [ ] アトミック・ノート間の関係性を可視化するAPI
- [ ] グラフデータのエクスポート機能
- [ ] Obsidianグラフビューとの連携

---

## ユーザーストーリー

### ストーリー1: 生情報の投入
**As a user,** 情報を分類せずに即座に保存したい
**So that** 思考の流れを中断せずにメモできる

**実装:**
1. Obsidianで`00_Raw/memo.md`を作成
2. Git同期でObsidianConsciergeに自動インデックス
3. セマンティック検索で即座に検索可能

---

### ストーリー2: AIによる整形
**As a user,** 生情報をAIで整形して読みやすくしたい
**So that** 後で見返しやすくなる

**実装:**
1. `00_Raw/memo.md`に対してサマリー生成
2. タグ自動生成
3. `01_Summary/memo_summary.md`に保存
4. メタデータで`pipeline_stage: "01_Summary"`を記録

---

### ストーリー3: アトミック・ノートへの分解
**As a user,** 長文ノートを複数の独立したテーマに分解したい
**So that** 再利用しやすいレゴブロックとして活用できる

**実装:**
1. `01_Summary/long_article.md`を選択
2. API: `POST /api/v1/atomic/split`を呼び出し
3. `02_Atomic/concept1.md`, `02_Atomic/concept2.md`が自動生成
4. 元ノートに新ノートへのリンクが追加される

---

### ストーリー4: MOCの自動生成
**As a user,** 関連するノートを自動でMOCにまとめたい
**So that** フォルダ分けせずに関連性で整理できる

**実装:**
1. `02_Atomic/`内の全ノートを分析
2. 類似度0.7以上のノート群をクラスタリング
3. 各クラスタごとに`03_MOC/[テーマ].md`を自動生成
4. MOC内に関連ノートへのリンクを自動挿入

---

## 既存機能への影響

### 影響なし（後方互換性維持）
- セマンティック検索
- タグ検索
- デイリーレポート
- Git同期

### 変更が必要
- **フォルダ除外設定**: `EXCLUDED_FOLDERS`に`00_Raw,01_Summary,02_Atomic,03_MOC`を追加
- **MOC候補抽出**: パイプラインフォルダを除外する必要がある（`app/core/analysis.py`の`_get_category_from_path`を活用）

---

## テスト戦略

### ユニットテスト
- `tests/unit/test_pipeline_manager.py`
- `tests/unit/test_atomic_splitter.py`
- `tests/unit/test_moc_generator.py`
- `tests/unit/test_atomic_scorer.py`

### 統合テスト
- `tests/integration/test_atomic_workflow.py`: 00_Raw → 03_MOCまでの全フロー

### 目標カバレッジ
- Phase 3完了時: 70%以上（現在59%）

---

## 関連ドキュメント

- [PRD.md](./PRD.md): プロダクト要件定義書
- [STATUS.md](./STATUS.md): 実装状況
- [TODO.md](./TODO.md): 詳細タスクリスト
- [ARCHITECTURE.md](./ARCHITECTURE.md): アーキテクチャドキュメント

---

## 補足: アトミック・ノートのベストプラクティス

### ✅ 良い例
```markdown
---
title: "コサイン類似度とは"
pipeline_stage: "02_Atomic"
tags: [機械学習, ベクトル]
---

# コサイン類似度とは

コサイン類似度は、2つのベクトル間の類似性を測る指標です。
ベクトルの角度に基づいて計算され、0〜1の値を取ります。

## 計算式

similarity = (A · B) / (||A|| * ||B||)

## 用途

- テキストの類似度判定
- レコメンデーションシステム

## 関連ノート

- [[ベクトル空間モデル]]
- [[セマンティック検索]]
```

### ❌ 悪い例（アトミックでない）
```markdown
---
title: "機械学習メモ"
---

# 機械学習メモ

## コサイン類似度
[説明]

## TF-IDF
[説明]

## クラスタリング
[説明]

## 深層学習
[説明]
```

**問題点:** 複数のテーマが1つのノートに混在している

---

## まとめ

アトミック・ノートのワークフローをObsidianConsciergeに統合することで、以下のメリットが得られます：

1. **AI視点での最適化**: フォルダ分類の曖昧さを解消
2. **再利用性の向上**: レゴブロックのように情報を組み合わせ可能
3. **関連性の可視化**: グラフビューで知識のつながりが明確に
4. **効率的な情報管理**: 分類を考える時間を削減

既存機能（セマンティック検索、MOC候補抽出、類似リンク挿入）を最大限活用しつつ、新機能（ノート分解、パイプライン管理、MOC自動生成）を追加することで、シームレスな統合が可能です。
