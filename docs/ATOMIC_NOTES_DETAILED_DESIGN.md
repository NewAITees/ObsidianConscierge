# Obsidian × AI「第2の脳みそ」詳細設計書

**作成日**: 2025-01-01
**対象**: ObsidianConscierge Phase 3 - アトミック・ノートワークフロー実装
**目的**: 運用時の判断に迷わず、エンジニアがすぐに実装開始できる完全な設計書

---

## 目次

### Part 1: 設計原則・概念
1. [設計原則](#1-設計原則)
2. [フォルダ構造](#2-フォルダ構造)
3. [00_Raw：入力フェーズ](#3-00_raw入力フェーズ)
4. [01_Summary：整形フェーズ](#4-01_summary整形フェーズ)
5. [02_Atomic：資産化フェーズ](#5-02_atomic資産化フェーズ)
6. [03_MOC：地図フェーズ](#6-03_moc地図フェーズ)
7. [リンク設計](#7-リンク設計)
8. [タグ設計](#8-タグ設計)

### Part 2: 技術実装仕様
9. [LLMプロンプト設計](#9-llmプロンプト設計)
10. [実装詳細](#10-実装詳細)
11. [API仕様](#11-api仕様)
12. [段階的移行プラン](#12-段階的移行プラン)
13. [テストケース](#13-テストケース)

### Part 3: 運用・保守
14. [運用ルール](#14-運用ルール)
15. [アンチパターン集](#15-アンチパターン集)
16. [判断フローチャート集](#16-判断フローチャート集)
17. [成功の指標](#17-成功の指標)

---

# Part 1: 設計原則・概念

## 1. 設計原則

### 1.1 基本思想

```
フォルダ分類 → 廃止
階層構造 → 廃止
意味単位分解 + リンク構造 → 採用
```

**理由：**
- AIは階層構造を理解しにくい
- 人間の記憶も階層的ではない
- 情報の複数分類問題（「AI動画のマーケティング活用」はどこに入れる？）を解決できない

### 1.2 4段階パイプラインの原則

```
00_Raw → 01_Summary → 02_Atomic → 03_MOC
```

各段階は**一方向にのみ流れる**。
逆流（AtomicからRawへ戻すなど）は原則禁止。

### 1.3 判断停止の原則

情報入力時に「どこに分類するか」を考えない。
**思考コストをゼロにし、入力速度を最大化する。**

---

## 2. フォルダ構造

```
TargetObsidianVault/
├── 00_Raw/          # 入力バッファ
├── 01_Summary/      # 整形済み中間ファイル
├── 02_Atomic/       # 最小意味単位ノート（資産）
├── 03_MOC/          # Map of Contents（地図）
└── (既存フォルダ)   # 後方互換性のため残す
```

**重要：これは処理段階の区別であり、分類ではない。**

---

## 3. 00_Raw：入力フェーズ

### 3.1 目的

情報を**即座に捕捉**し、消失を防ぐ。

### 3.2 入力ルール

#### 許可される行為
- 殴り書き
- コピペ
- 文字起こし
- スクリーンショット埋め込み
- 音声メモ添付
- 感情混じりの文章

#### 禁止される行為
- 整形
- 分類
- タイトル熟考（仮タイトルで即保存）
- リンク追加

### 3.3 ファイル命名規則

```
概要_YYYYMMDD.md
```

**例：**
```
VTuber配信メモ_20250115.md
AI動画アイデア_20250115.md
```

**タイトルを先頭にする理由：**
- ファイル検索時にタイトルがヒットしやすい
- アルファベット順でタイトル別に整理される
- 日付は一意性確保と時系列把握のために末尾に付与

### 3.4 処理タイミングと自動化

**自動生成方針（変更）：**
- 全てのRawファイルは**自動的にSummary化**する（判断不要）
- 条件判定（文字数、トピック数など）は廃止
- 作成後、自動パイプラインで即座に処理

**日記ファイル連携：**
- 作成したRawファイルは、その日の日記ファイル（`01DIARY/YYYY-MM-DD.md`）に自動リンク追加
- 日記ファイルに「## 今日作成したファイル」セクションを作成し、そこにリンクを追加

---

## 4. 01_Summary：整形フェーズ

### 4.1 目的

Rawを「人間が読める形」「AIが解釈しやすい形」に変換する。
**完成品ではなく、Atomic化のための中間表現である。**

### 4.2 Summary化の方針（自動化）

**変更：判断基準を廃止し、全自動化**

- 全てのRawファイルを自動的にSummary化
- 文字数やトピック数による条件判定は不要
- AI（LLM）がRaw内容を解析し、適切な形式でSummary生成

### 4.3 Summaryの必須構造

```markdown
---
title: "タイトル"
created: YYYY-MM-DD
tags: [タグ1, タグ2, タグ3]
pipeline_stage: "01_Summary"
source_file: "00_Raw/YYYYMMDD_HHMM_xxx.md"
---

# タイトル（明確な問い、または内容の要約）

## サマリー（1〜3行）
このメモの要点を3行以内でまとめる。

## 観点1
- 要点
- 要点

## 観点2
- 要点
- 要点

## 次のアクション（任意）
- [ ] Atomic化候補のリストアップ
- [ ] MOC作成の検討
```

### 4.4 「観点」の分け方

**観点とは、異なる切り口のこと。**

#### 観点分離のチェックリスト

以下の質問に「はい」と答えられる場合、別観点として分離する：

- [ ] 主語が変わるか？（誰の視点か）
- [ ] 目的が変わるか？（何のための情報か）
- [ ] 使う場面が異なるか？
- [ ] 論点が独立しているか？

---

## 5. 02_Atomic：資産化フェーズ

### 5.1 目的

情報を**再利用可能な最小単位**に分解する。
これが本設計の**最重要フェーズ**である。

### 5.2 Atomicノートの定義

**1ノート = 1意味単位 = 1再利用可能な知識**

以下の3条件をすべて満たすこと：

1. **単独で意味が通る**
   - 元ドキュメントを参照しなくても理解できる
   - 他の文脈に持ち出しても成立する

2. **1つの主張・概念のみを含む**
   - 主張が2つある場合は分割する
   - 「〇〇と△△」は2ファイルに分割

3. **再利用可能である**
   - ポスト・記事・台本などに転用可能
   - 他のノートと組み合わせ可能

### 5.3 Atomicノートの必須構造

```markdown
---
title: "タイトル"
created: YYYY-MM-DD
tags: [タグ1, タグ2, タグ3]
pipeline_stage: "02_Atomic"
source_file: "01_Summary/xxx.md"
atomic_concept: "1文での概念定義"
---

# タイトル（問い形式 or 定義文）

## 概念
[1文での概念定義]

## 詳細
[詳細説明、理由、背景を含める]
[文字数目安：200〜800字]

## 応用例（任意だが推奨）
- 具体的な使用場面1
- 具体的な使用場面2

## 関連リンク
- [[関連ノート1]]
- [[関連ノート2]]
```

### 5.4 タイトル設計ルール

以下のいずれかの形式を採用：

1. **問い形式**（推奨）
   - なぜ〇〇は△△なのか
   - どうすれば〇〇できるか
   - 〇〇と△△の違いは何か

2. **定義文**
   - 〇〇とは△△である
   - 〇〇の本質は△△

3. **手法・パターン名**
   - 〇〇による△△の実現方法
   - 〇〇パターンの適用条件

### 5.5 分割しすぎの防止

以下の場合は分割**しない**：

- [ ] 本文が200字未満になる
- [ ] タイトルが「〇〇の一例」「△△の補足」など補助的
- [ ] 単独では意味が通らない
- [ ] 他のノートへの依存が強い

---

## 6. 03_MOC：地図フェーズ

### 6.1 目的

**Atomicノートの「交差点」を作る。**

MOCはフォルダの代替ではなく、
**問いを軸にした関連ノート群の可視化**である。

### 6.2 MOCの定義

以下の条件をすべて満たすこと：

1. **問いを持つ**
   - タイトルは必ず問い形式
   - 答えが固定されていない（探索的）

2. **複数のAtomicノートを束ねる**
   - 最低3つ以上のAtomicノートをリンク
   - リンクには必ず文脈コメントを付ける

3. **動的である**
   - 新しいAtomicノートが追加されたら更新
   - 固定された「完成品」ではない

### 6.3 MOCの必須構造

```markdown
---
title: "MOC: テーマ名"
pipeline_stage: "03_MOC"
tags: [moc, テーマ名]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# 【問い】なぜ〇〇は△△なのか

## この問いの背景
（なぜこの問いが重要か、どういう文脈で生まれたかを説明）

## 関連するAtomicノート

### 仮説1：〇〇である
- [[Atomicノート1]]：なぜなら...
- [[Atomicノート2]]：これは...と関連

### 仮説2：△△である
- [[Atomicノート3]]：一方で...
- [[Atomicノート4]]：別の視点では...

### 反例・対立する視点
- [[Atomicノート5]]：しかし...

## 現時点での暫定的な答え
（現状の理解をまとめる。変更可能であることを前提とする）

## 未解決の疑問
- 疑問1
- 疑問2

## 関連MOC
- [[別のMOC1]]
- [[別のMOC2]]
```

---

## 7. リンク設計

### 7.1 リンクの種類と使い分け

#### 定義リンク
```markdown
AはBである。詳細は[[B]]を参照。
```

#### 因果リンク
```markdown
[[A]]だから[[B]]が起きる。
```

#### 応用リンク
```markdown
[[A]]は[[B]]に応用できる。
```

#### 対比リンク
```markdown
[[A]]と[[B]]は異なる。
```

### 7.2 リンク追加のルール

1. **リンクには必ず文脈コメントを付ける**

NG例：
```markdown
関連：[[ノート1]]、[[ノート2]]
```

OK例：
```markdown
この概念は[[ノート1]]の応用例である。
一方で[[ノート2]]とは対立する視点を持つ。
```

2. **リンクは3〜7個を目安とする**

- 0〜2個：孤立ノート（問題）
- 3〜7個：適切
- 8個以上：分割を検討、またはMOC化

### 7.3 リンク自動更新機能

**目的**: ファイル名変更時にVault内の全リンクを自動更新

**動作**:
1. ファイル名が変更されたことを検知
2. Vault内の全`.md`ファイルをスキャン
3. `[[旧ファイル名]]` を `[[新ファイル名]]` に一括置換
4. 変更されたファイルを保存

**実装**: `app/core/link_updater.py`

```python
def update_all_links(vault_path: Path, old_name: str, new_name: str):
    """Vault内の全ファイルでリンクを更新"""
    updated_count = 0

    for file in vault_path.rglob("*.md"):
        content = file.read_text(encoding="utf-8")
        old_link = f"[[{old_name}]]"
        new_link = f"[[{new_name}]]"

        if old_link in content:
            updated = content.replace(old_link, new_link)
            file.write_text(updated, encoding="utf-8")
            updated_count += 1
            logger.info(f"リンク更新: {file.name}")

    logger.info(f"リンク自動更新完了: {updated_count}ファイル")
```

**使用場面**:
- 02_Atomicファイルのタイトル変更時
- 03_MOCファイルの問い変更時
- ファイルのリネーム時

### 7.4 日記ファイル連携機能

**目的**: 作成したファイルをその日の日記ファイルに自動リンク

**動作**:
1. ファイル作成時に作成日を取得
2. その日の日記ファイル（`01DIARY/YYYY-MM-DD.md`）を探す
3. 日記ファイルがなければ自動作成
4. 「## 今日作成したファイル」セクションにリンクを追加

**実装**: `app/core/daily_note_linker.py`

```python
def add_to_daily_note(
    vault_path: Path,
    created_file: Path,
    created_date: str  # "YYYY-MM-DD"
):
    """その日の日記ファイルにリンクを追加"""
    diary_dir = vault_path / "01DIARY"
    diary_file = diary_dir / f"{created_date}.md"

    # 日記ファイルがなければ作成
    if not diary_file.exists():
        diary_file.parent.mkdir(parents=True, exist_ok=True)
        diary_file.write_text(
            f"# {created_date}\n\n## 今日作成したファイル\n\n",
            encoding="utf-8"
        )

    # リンクを追加
    link = f"- [[{created_file.stem}]]\n"
    content = diary_file.read_text(encoding="utf-8")

    # 「## 今日作成したファイル」セクションを探す
    if "## 今日作成したファイル" in content:
        # セクションの後に追加
        content = content.replace(
            "## 今日作成したファイル\n",
            f"## 今日作成したファイル\n{link}"
        )
    else:
        # セクションを新規作成
        content += f"\n## 今日作成したファイル\n{link}"

    diary_file.write_text(content, encoding="utf-8")
    logger.info(f"日記ファイルにリンク追加: {diary_file.name} ← {created_file.name}")
```

**適用対象**:
- 00_Raw ファイル作成時
- 01_Summary ファイル作成時
- 02_Atomic ファイル作成時

---

## 8. タグ設計

### 8.1 タグの役割

**タグは分類ではなく、横断的な検索軸である。**

### 8.2 タグの3軸

#### 分野タグ（何の領域か）
```
#AI #マーケティング #思考法 #演出 #VTuber #技術
```

#### 用途タグ（何に使うか）
```
#投稿ネタ #記事候補 #台本候補 #メモ
```

#### 状態タグ（処理状況）
```
#要処理 #要確認 #完了
```

### 8.3 タグ付与ルール

- **Rawファイル**: `#要処理`
- **Summaryファイル**: `#分野タグ #要処理 or #完了`
- **Atomicノート**: `#分野タグ1 #分野タグ2 #用途タグ`
- **MOC**: `#MOC #分野タグ`

---

# Part 2: 技術実装仕様

## 9. LLMプロンプト設計

### 9.1 要約プロンプト（00_Raw → 01_Summary）

**実装**: `app/core/summarizer.py` (新規作成)

```python
"""Summarizer - converts Raw notes to Summary format."""

import logging
from pathlib import Path
from datetime import datetime

from app.services.llm_service import LLMService
from app.core.config import Settings

logger = logging.getLogger(__name__)


class Summarizer:
    """00_Raw → 01_Summary 変換サービス"""

    def __init__(
        self,
        llm_service: LLMService,
        settings: Settings
    ) -> None:
        self.llm_service = llm_service
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

    def generate_summary_prompt(
        self,
        raw_content: str,
        file_path: str
    ) -> str:
        """00_Raw → 01_Summary 要約プロンプトを生成"""
        return f"""以下の殴り書きメモを整形し、構造化されたサマリーを作成してください。

【ルール】
1. タイトルを付ける（ファイル名: {file_path}）
2. サマリーセクション: 全体を3-5文で要約
3. 主要トピックを観点ごとにセクション分け
4. アクションアイテムを抽出（あれば）
5. Frontmatterメタデータを生成（YAML形式）
   - title: タイトル
   - created: 作成日（YYYY-MM-DD形式）
   - tags: 関連タグ（3-7個）
   - pipeline_stage: "01_Summary"
   - source_file: 元ファイルパス

【入力】
{raw_content}

【出力形式】
---
title: "タイトル"
created: YYYY-MM-DD
tags: [タグ1, タグ2, タグ3]
pipeline_stage: "01_Summary"
source_file: "00_Raw/xxx.md"
---

# タイトル

## サマリー
[3-5文の要約]

## 観点1
- 要点
- 要点

## 観点2
- 要点
- 要点

## 次のアクション
- [ ] アクションアイテム1
"""

    def summarize_raw_file(self, raw_file_path: Path) -> str:
        """Rawファイルを要約してSummary形式のMarkdownを生成"""
        try:
            # ファイルを読み込み
            with open(raw_file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            # プロンプトを生成
            prompt = self.generate_summary_prompt(
                raw_content,
                str(raw_file_path.relative_to(self.vault_path))
            )

            # LLMで要約
            summary_content = self.llm_service._generate_with_retry(prompt)

            logger.info(f"要約完了: {raw_file_path.name}")
            return summary_content

        except Exception as exc:
            logger.error(f"要約に失敗: {exc}")
            return ""

    def save_summary(self, summary_content: str, raw_file_path: Path) -> Path:
        """Summaryを保存"""
        summary_dir = self.vault_path / "01_Summary"
        summary_dir.mkdir(parents=True, exist_ok=True)

        # ファイル名を生成（日付_テーマ_Summary.md）
        date_str = datetime.now().strftime("%Y%m%d")
        theme = raw_file_path.stem.split("_", 2)[-1]  # YYYYMMDD_HHMM_テーマ から テーマ を抽出
        summary_file_path = summary_dir / f"{date_str}_{theme}_Summary.md"

        # ファイルを保存
        with open(summary_file_path, "w", encoding="utf-8") as f:
            f.write(summary_content)

        logger.info(f"Summary保存: {summary_file_path}")
        return summary_file_path
```

---

### 9.2 分解プロンプト（01_Summary → 02_Atomic）

**実装**: `app/core/atomic_splitter.py` (新規作成)

```python
"""Atomic note splitter - splits summarized notes into atomic concepts."""

import logging
import re
from pathlib import Path
from typing import Any
from datetime import datetime

from app.services.llm_service import LLMService
from app.core.config import Settings

logger = logging.getLogger(__name__)


class AtomicSplitter:
    """01_Summary から 02_Atomic への分解を行うサービス"""

    def __init__(
        self,
        llm_service: LLMService,
        settings: Settings
    ) -> None:
        self.llm_service = llm_service
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

    def generate_split_prompt(
        self,
        summary_content: str,
        file_path: str
    ) -> str:
        """01_Summary → 02_Atomic 分解プロンプトを生成"""
        return f"""以下の文章から、独立した概念（アトミック・ノート）を抽出してください。

【ルール】
1. **1つの概念 = 1つのノート**
2. 各ノートは「1ファイル1テーマ」
3. 他のノートと組み合わせて使える「レゴブロック」として設計
4. 各ノートは以下の形式で出力:

---ATOMIC_NOTE---
タイトル: [概念名（問い形式推奨）]
タグ: [関連タグをカンマ区切り]
概念: [1文での概念定義]
詳細:
[詳細説明（200〜800字）]

応用例:
- [具体的な使用場面1]
- [具体的な使用場面2]

関連リンク:
- [[元ファイル名]]
---END---

【抽出基準】
- 独立して理解できる概念
- 再利用可能な知識
- 他の文脈でも適用可能
- 過度に具体的すぎない（例: 「2025-01-01の会議」ではなく「AI動画集客戦略」）
- 本文が200字未満になる場合は分割しない

【入力文章】
元ファイル: {file_path}

{summary_content}

【出力例】
---ATOMIC_NOTE---
タイトル: なぜAI動画は集客に効果的なのか
タグ: マーケティング, AI動画, 集客
概念: AI動画を使ったYouTube shorts/TikTokでの集客施策
詳細:
AI動画は短尺フォーマットでの展開により、若年層へのリーチを拡大する。
プラットフォーム: YouTube shorts、TikTok
費用: 月50万円、ROI: 3ヶ月で回収見込み。
短尺動画は視聴完了率が高く、アルゴリズムに好まれるため、
オーガニックリーチが期待できる。

応用例:
- YouTube shortsでの商品PR
- TikTokでのブランド認知施策
- Instagram Reelsでのエンゲージメント向上

関連リンク:
- [[プロジェクトX進捗会議 2025-01-01]]
---END---
"""

    def split_into_atomic_notes(
        self,
        summary_file_path: Path
    ) -> list[dict[str, Any]]:
        """01_Summaryファイルを複数の02_Atomicノートに分解"""
        try:
            # ファイルを読み込み
            with open(summary_file_path, "r", encoding="utf-8") as f:
                summary_content = f.read()

            # 分解プロンプトを生成
            prompt = self.generate_split_prompt(
                summary_content,
                str(summary_file_path.relative_to(self.vault_path))
            )

            # LLMで分解
            response = self.llm_service._generate_with_retry(prompt)

            # レスポンスをパース
            atomic_notes = self._parse_atomic_notes(response, summary_file_path)

            logger.info(
                f"分解完了: {summary_file_path.name} → {len(atomic_notes)}個のアトミック・ノート"
            )
            return atomic_notes

        except Exception as exc:
            logger.error(f"アトミック・ノート分解に失敗: {exc}")
            return []

    def _parse_atomic_notes(
        self,
        response: str,
        source_file: Path
    ) -> list[dict[str, Any]]:
        """LLMレスポンスをパースしてアトミック・ノートのリストを生成"""
        notes: list[dict[str, Any]] = []

        # ---ATOMIC_NOTE--- ... ---END--- のパターンで分割
        pattern = r"---ATOMIC_NOTE---(.*?)---END---"
        matches = re.findall(pattern, response, re.DOTALL)

        for match in matches:
            try:
                # タイトル抽出
                title_match = re.search(r"タイトル:\s*(.+)", match)
                title = title_match.group(1).strip() if title_match else "Untitled"

                # タグ抽出
                tags_match = re.search(r"タグ:\s*(.+)", match)
                tags = []
                if tags_match:
                    tags = [
                        tag.strip()
                        for tag in tags_match.group(1).split(",")
                    ]

                # 概念抽出
                concept_match = re.search(r"概念:\s*(.+)", match)
                atomic_concept = (
                    concept_match.group(1).strip()
                    if concept_match
                    else title
                )

                # 詳細抽出
                details_match = re.search(
                    r"詳細:(.*?)(?:応用例:|関連リンク:|$)",
                    match,
                    re.DOTALL
                )
                details = (
                    details_match.group(1).strip()
                    if details_match
                    else ""
                )

                # 応用例抽出
                examples_match = re.search(
                    r"応用例:(.*?)(?:関連リンク:|$)",
                    match,
                    re.DOTALL
                )
                examples = (
                    examples_match.group(1).strip()
                    if examples_match
                    else ""
                )

                # Frontmatter付きMarkdownコンテンツを生成
                content = self._build_atomic_note_content(
                    title=title,
                    tags=tags,
                    atomic_concept=atomic_concept,
                    details=details,
                    examples=examples,
                    source_file=source_file
                )

                notes.append({
                    "title": title,
                    "content": content,
                    "tags": tags,
                    "atomic_concept": atomic_concept,
                })

            except Exception as exc:
                logger.warning(f"アトミック・ノートのパースに失敗: {exc}")
                continue

        return notes

    def _build_atomic_note_content(
        self,
        title: str,
        tags: list[str],
        atomic_concept: str,
        details: str,
        examples: str,
        source_file: Path
    ) -> str:
        """アトミック・ノートのMarkdownコンテンツを生成"""
        created_date = datetime.now().strftime("%Y-%m-%d")
        tags_str = "[" + ", ".join(tags) + "]" if tags else "[]"
        source_link = f"[[{source_file.stem}]]"

        content = f"""---
title: "{title}"
created: {created_date}
tags: {tags_str}
pipeline_stage: "02_Atomic"
source_file: "{source_file.relative_to(self.vault_path)}"
atomic_concept: "{atomic_concept}"
---

# {title}

## 概念
{atomic_concept}

## 詳細
{details}
"""

        if examples:
            content += f"""
## 応用例
{examples}
"""

        content += f"""
## 関連リンク
- {source_link}
"""

        return content

    def save_atomic_notes(
        self,
        atomic_notes: list[dict[str, Any]]
    ) -> list[Path]:
        """アトミック・ノートをファイルとして保存"""
        saved_files: list[Path] = []
        atomic_dir = self.vault_path / "02_Atomic"
        atomic_dir.mkdir(parents=True, exist_ok=True)

        for note in atomic_notes:
            try:
                title = note["title"]
                content = note["content"]

                # ファイル名を生成（タイトルそのまま、特殊文字を除去）
                safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
                file_path = atomic_dir / f"{safe_title}.md"

                # ファイルを保存
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                saved_files.append(file_path)
                logger.info(f"アトミック・ノート保存: {file_path.name}")

            except Exception as exc:
                logger.error(f"アトミック・ノート保存に失敗: {exc}")
                continue

        return saved_files
```

---

### 9.3 MOC生成プロンプト（02_Atomic → 03_MOC）

**実装**: `app/core/moc_generator.py` (新規作成)

```python
"""MOC (Map of Contents) generator - creates knowledge maps from atomic notes."""

import logging
import re
from pathlib import Path
from typing import Any
from datetime import datetime

from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.core.analysis import AnalysisService
from app.core.config import Settings

logger = logging.getLogger(__name__)


class MOCGenerator:
    """02_Atomic から 03_MOC への変換を行うサービス"""

    def __init__(
        self,
        llm_service: LLMService,
        vector_db_service: VectorDBService,
        analysis_service: AnalysisService,
        settings: Settings
    ) -> None:
        self.llm_service = llm_service
        self.vector_db_service = vector_db_service
        self.analysis_service = analysis_service
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

    def generate_moc_prompt(
        self,
        related_notes: list[dict[str, Any]],
        moc_theme: str
    ) -> str:
        """02_Atomic → 03_MOC MOC生成プロンプトを生成"""
        notes_list = "\n".join([
            f"- {note['title']} (タグ: {', '.join(note.get('tags', []))})"
            for note in related_notes
        ])

        return f"""以下の関連ノートから、MOC（Map of Contents）を作成してください。

【テーマ】
{moc_theme}

【関連ノート一覧】
{notes_list}

【ルール】
1. タイトルは必ず問い形式（「なぜ〇〇は△△なのか」など）
2. 問いの背景: なぜこの問いが重要かを2-3文で説明
3. 関連ノートを仮説ごとにグループ分けしてリスト化
4. 各リンクには必ず文脈コメントを付ける
5. 現時点での暫定的な答えをまとめる
6. 未解決の疑問をリストアップ
7. Frontmatterメタデータを生成
   - title: "MOC: [問い]"
   - pipeline_stage: "03_MOC"
   - tags: [moc, テーマ名]

【出力形式】
---
title: "MOC: なぜ{moc_theme}は〇〇なのか"
pipeline_stage: "03_MOC"
tags: [moc, {moc_theme}]
created: {datetime.now().strftime('%Y-%m-%d')}
updated: {datetime.now().strftime('%Y-%m-%d')}
---

# 【問い】なぜ{moc_theme}は〇〇なのか

## この問いの背景
[なぜこの問いが重要か、どういう文脈で生まれたかを説明]

## 関連するAtomicノート

### 仮説1：〇〇である
- [[Atomicノート1]]：なぜなら...という理由
- [[Atomicノート2]]：これは...と関連している

### 仮説2：△△である
- [[Atomicノート3]]：一方で...という視点もある
- [[Atomicノート4]]：別の角度では...

### 反例・対立する視点
- [[Atomicノート5]]：しかし...という反論もある

## 現時点での暫定的な答え
[現状の理解をまとめる。変更可能であることを前提とする]

## 未解決の疑問
- 疑問1
- 疑問2

## 関連MOC
- （あれば）
"""

    def generate_moc(
        self,
        theme: str,
        min_articles: int = 3
    ) -> dict[str, Any] | None:
        """指定されたテーマでMOCを生成"""
        try:
            # 既存のMOC候補抽出機能を活用
            moc_candidates = self.analysis_service.find_moc_candidates(
                min_articles=min_articles
            )

            # 指定されたテーマに一致する候補を検索
            matching_candidate = None
            for candidate in moc_candidates:
                if candidate["name"] == theme:
                    matching_candidate = candidate
                    break

            if not matching_candidate:
                logger.warning(f"MOC候補が見つかりません: {theme}")
                return None

            # 関連ノートを取得
            related_notes = matching_candidate["articles"]

            # MOC生成プロンプトを作成
            prompt = self.generate_moc_prompt(related_notes, theme)

            # LLMでMOCを生成
            moc_content = self.llm_service._generate_with_retry(prompt)

            # MOCファイルを保存
            moc_file_path = self._save_moc(theme, moc_content)

            logger.info(f"MOC生成完了: {theme} ({len(related_notes)}件の関連ノート)")
            return {
                "title": f"MOC: {theme}",
                "content": moc_content,
                "file_path": str(moc_file_path),
                "related_notes_count": len(related_notes),
            }

        except Exception as exc:
            logger.error(f"MOC生成に失敗: {exc}")
            return None

    def _save_moc(self, theme: str, content: str) -> Path:
        """MOCファイルを保存"""
        moc_dir = self.vault_path / "03_MOC"
        moc_dir.mkdir(parents=True, exist_ok=True)

        # ファイル名を生成（【MOC】タイトル.md）
        safe_theme = re.sub(r'[<>:"/\\|?*]', '', theme)

        # タイトル抽出（Frontmatterから）
        title_match = re.search(r'title:\s*"([^"]+)"', content)
        if title_match:
            title = title_match.group(1)
            safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
            file_path = moc_dir / f"【MOC】{safe_title}.md"
        else:
            file_path = moc_dir / f"【MOC】{safe_theme}.md"

        # ファイルを保存
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"MOC保存: {file_path}")
        return file_path
```

---

## 10. 実装詳細

### 10.1 pipeline_manager.py の設計

**役割**: パイプラインステージの遷移を管理

```python
"""Pipeline stage manager - manages transitions between stages."""

import logging
from pathlib import Path

from app.core.config import Settings

logger = logging.getLogger(__name__)


class PipelineManager:
    """パイプラインステージ管理サービス"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

        # パイプラインステージのフォルダパス
        self.stage_paths = {
            "00_Raw": self.vault_path / "00_Raw",
            "01_Summary": self.vault_path / "01_Summary",
            "02_Atomic": self.vault_path / "02_Atomic",
            "03_MOC": self.vault_path / "03_MOC",
        }

    def get_stage_from_file(self, file_path: Path) -> str | None:
        """ファイルパスからパイプラインステージを取得"""
        try:
            relative_path = file_path.relative_to(self.vault_path)
            for stage_name, stage_path in self.stage_paths.items():
                stage_relative = stage_path.relative_to(self.vault_path)
                if str(relative_path).startswith(str(stage_relative)):
                    return stage_name
            return None
        except ValueError:
            return None

    def get_next_stage(self, current_stage: str) -> str | None:
        """次のパイプラインステージを取得"""
        stages = ["00_Raw", "01_Summary", "02_Atomic", "03_MOC"]
        try:
            current_index = stages.index(current_stage)
            if current_index < len(stages) - 1:
                return stages[current_index + 1]
            return None
        except ValueError:
            return None

    def get_files_in_stage(self, stage: str) -> list[Path]:
        """指定されたステージの全ファイルを取得"""
        stage_path = self.stage_paths.get(stage)
        if not stage_path or not stage_path.exists():
            return []

        return list(stage_path.rglob("*.md"))

    def update_frontmatter_stage(
        self,
        file_path: Path,
        new_stage: str
    ) -> bool:
        """Frontmatterのpipeline_stageフィールドを更新"""
        try:
            import frontmatter

            # ファイルを読み込み
            with open(file_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            # pipeline_stageを更新
            post.metadata["pipeline_stage"] = new_stage

            # ファイルに書き戻し
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

            logger.info(f"Frontmatter更新: {file_path.name} → {new_stage}")
            return True

        except Exception as exc:
            logger.error(f"Frontmatter更新に失敗: {exc}")
            return False
```

---

### 10.2 atomic_scorer.py の設計

**役割**: Atomicノートのアトミック性を評価

```python
"""Atomic scorer - evaluates atomicity of notes."""

import logging
from pathlib import Path
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)


class AtomicScorer:
    """アトミック性評価サービス"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

    def score_atomicity(self, file_path: Path) -> dict[str, Any]:
        """ファイルのアトミック性スコアを計算"""
        try:
            # ファイルを読み込み
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 各基準でスコアリング
            single_concept_score = self._score_single_concept(content)
            reusability_score = self._score_reusability(content)
            independence_score = self._score_independence(content)
            length_score = self._score_length(content)

            # 総合スコア（平均）
            total_score = (
                single_concept_score + reusability_score +
                independence_score + length_score
            ) / 4.0

            # 改善提案
            suggestions = self._generate_suggestions(
                single_concept_score,
                reusability_score,
                independence_score,
                length_score
            )

            return {
                "file_path": str(file_path.relative_to(self.vault_path)),
                "atomicity_score": round(total_score, 2),
                "criteria": {
                    "single_concept": round(single_concept_score, 2),
                    "reusability": round(reusability_score, 2),
                    "independence": round(independence_score, 2),
                    "length_appropriateness": round(length_score, 2),
                },
                "suggestions": suggestions,
            }

        except Exception as exc:
            logger.error(f"アトミック性評価に失敗: {exc}")
            return {
                "file_path": str(file_path),
                "atomicity_score": 0.0,
                "error": str(exc),
            }

    def _score_single_concept(self, content: str) -> float:
        """1つの概念のみを含むかをスコアリング"""
        # 簡易実装：見出しの数で判定
        heading_count = content.count("\n## ")

        if heading_count <= 3:
            return 1.0  # 概念、詳細、応用例など
        elif heading_count <= 5:
            return 0.7
        else:
            return 0.4  # 多すぎる場合は分割を示唆

    def _score_reusability(self, content: str) -> float:
        """再利用可能性をスコアリング"""
        # 応用例セクションの有無
        has_examples = "## 応用例" in content or "## 適用例" in content

        # リンクの数（3-7個が理想）
        link_count = content.count("[[")

        score = 0.5  # ベーススコア
        if has_examples:
            score += 0.3

        if 3 <= link_count <= 7:
            score += 0.2
        elif link_count > 0:
            score += 0.1

        return min(score, 1.0)

    def _score_independence(self, content: str) -> float:
        """独立性をスコアリング"""
        # 「これ」「それ」などの代名詞の多用をチェック
        pronouns = ["これ", "それ", "あれ", "この", "その"]
        pronoun_count = sum(content.count(p) for p in pronouns)

        # 文字数に対する代名詞の割合
        char_count = len(content)
        pronoun_ratio = pronoun_count / max(char_count, 1) * 1000  # 1000字あたり

        if pronoun_ratio < 5:
            return 1.0
        elif pronoun_ratio < 10:
            return 0.7
        else:
            return 0.4

    def _score_length(self, content: str) -> float:
        """適切な長さかをスコアリング"""
        # 本文のみを抽出（Frontmatterと見出しを除く）
        body = content.split("---", 2)[-1] if "---" in content else content
        body_chars = len(body.strip())

        if 200 <= body_chars <= 800:
            return 1.0
        elif body_chars < 200:
            return 0.5  # 短すぎる
        elif 800 < body_chars <= 1200:
            return 0.7  # やや長い
        else:
            return 0.4  # 分割を検討

    def _generate_suggestions(
        self,
        single: float,
        reuse: float,
        indep: float,
        length: float
    ) -> list[str]:
        """改善提案を生成"""
        suggestions = []

        if single < 0.7:
            suggestions.append("複数の主張が混在している可能性があります。分割を検討してください。")
        else:
            suggestions.append("ノートは1つの概念に集中しています（良好）")

        if reuse < 0.7:
            suggestions.append("応用例を追加すると再利用性が向上します。")
        else:
            suggestions.append("他のノートと組み合わせて使いやすい構造です（良好）")

        if indep < 0.7:
            suggestions.append("代名詞が多いです。固有名詞を明記して文脈を省略しないようにしてください。")

        if length < 0.7:
            if length == 0.5:
                suggestions.append("本文が短すぎます（200字未満）。他のノートと統合を検討してください。")
            else:
                suggestions.append("本文が長すぎます（800字以上）。分割を検討してください。")

        return suggestions
```

---

### 10.3 link_updater.py の設計

**役割**: ファイル名変更時にVault内の全リンクを自動更新

**ファイルパス**: `app/core/link_updater.py`

```python
"""Link updater - automatically updates all links when file is renamed."""

import logging
from pathlib import Path

from app.core.config import Settings

logger = logging.getLogger(__name__)


class LinkUpdater:
    """リンク自動更新サービス"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)

    def update_all_links(
        self,
        old_name: str,
        new_name: str
    ) -> int:
        """
        Vault内の全ファイルでリンクを更新

        Args:
            old_name: 旧ファイル名（拡張子なし）
            new_name: 新ファイル名（拡張子なし）

        Returns:
            int: 更新されたファイル数
        """
        updated_count = 0

        try:
            for file in self.vault_path.rglob("*.md"):
                try:
                    content = file.read_text(encoding="utf-8")
                    old_link = f"[[{old_name}]]"
                    new_link = f"[[{new_name}]]"

                    if old_link in content:
                        updated = content.replace(old_link, new_link)
                        file.write_text(updated, encoding="utf-8")
                        updated_count += 1
                        logger.info(f"リンク更新: {file.name}")

                except Exception as exc:
                    logger.warning(f"リンク更新失敗: {file.name} - {exc}")
                    continue

            logger.info(f"リンク自動更新完了: {updated_count}ファイル")
            return updated_count

        except Exception as exc:
            logger.error(f"リンク自動更新に失敗: {exc}")
            return 0

    def rename_file_and_update_links(
        self,
        file_path: Path,
        new_name: str
    ) -> Path:
        """
        ファイルをリネームし、全リンクを更新

        Args:
            file_path: 対象ファイルのパス
            new_name: 新しいファイル名（拡張子なし）

        Returns:
            Path: リネーム後のファイルパス
        """
        old_name = file_path.stem
        new_file_path = file_path.parent / f"{new_name}.md"

        # ファイルをリネーム
        file_path.rename(new_file_path)
        logger.info(f"ファイルリネーム: {old_name} → {new_name}")

        # 全リンクを更新
        self.update_all_links(old_name, new_name)

        return new_file_path
```

---

### 10.4 daily_note_linker.py の設計

**役割**: 作成したファイルをその日の日記ファイルに自動リンク

**ファイルパス**: `app/core/daily_note_linker.py`

```python
"""Daily note linker - automatically links created files to daily note."""

import logging
from pathlib import Path
from datetime import datetime

from app.core.config import Settings

logger = logging.getLogger(__name__)


class DailyNoteLinker:
    """日記ファイル連携サービス"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.vault_path = Path(settings.obsidian_vault_path)
        self.diary_dir = self.vault_path / "01DIARY"

    def add_to_daily_note(
        self,
        created_file: Path,
        created_date: str | None = None
    ) -> bool:
        """
        その日の日記ファイルにリンクを追加

        Args:
            created_file: 作成されたファイルのパス
            created_date: 作成日（YYYY-MM-DD形式、Noneの場合は今日）

        Returns:
            bool: 成功/失敗
        """
        try:
            # 作成日を取得
            if created_date is None:
                created_date = datetime.now().strftime("%Y-%m-%d")

            # 日記ファイルパス
            diary_file = self.diary_dir / f"{created_date}.md"

            # 日記ファイルがなければ作成
            if not diary_file.exists():
                self._create_daily_note(created_date)

            # リンクを追加
            link = f"- [[{created_file.stem}]]\n"
            content = diary_file.read_text(encoding="utf-8")

            # 「## 今日作成したファイル」セクションを探す
            section_header = "## 今日作成したファイル"

            if section_header in content:
                # セクションの後に追加（重複チェック）
                if link.strip() not in content:
                    content = content.replace(
                        f"{section_header}\n",
                        f"{section_header}\n{link}"
                    )
                else:
                    logger.info(f"リンク既存: {created_file.name}")
                    return True
            else:
                # セクションを新規作成
                content += f"\n{section_header}\n{link}"

            # ファイルに書き戻し
            diary_file.write_text(content, encoding="utf-8")
            logger.info(f"日記ファイルにリンク追加: {diary_file.name} ← {created_file.name}")
            return True

        except Exception as exc:
            logger.error(f"日記ファイル連携に失敗: {exc}")
            return False

    def _create_daily_note(self, date: str):
        """日記ファイルを作成"""
        self.diary_dir.mkdir(parents=True, exist_ok=True)
        diary_file = self.diary_dir / f"{date}.md"

        template = f"""---
title: "{date}"
created: {date}
tags: [日記]
---

# {date}

## 今日作成したファイル

"""

        diary_file.write_text(template, encoding="utf-8")
        logger.info(f"日記ファイル作成: {diary_file.name}")
```

---

### 10.5 auto_pipeline.py の設計（自動化スクリプト）

**役割**: Raw → Summary → Atomic の全自動化

**ファイルパス**: `scripts/auto_pipeline.py`

```python
"""Automatic pipeline - Raw → Summary → Atomic full automation."""

import logging
from pathlib import Path
from datetime import datetime

from app.core.config import get_settings
from app.core.summarizer import Summarizer
from app.core.atomic_splitter import AtomicSplitter
from app.core.daily_note_linker import DailyNoteLinker
from app.services.llm_service import LLMService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_auto_pipeline():
    """Raw → Summary → Atomic の全自動パイプライン"""
    settings = get_settings()
    vault_path = Path(settings.obsidian_vault_path)

    # サービス初期化
    llm_service = LLMService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_llm_model
    )
    summarizer = Summarizer(llm_service, settings)
    splitter = AtomicSplitter(llm_service, settings)
    linker = DailyNoteLinker(settings)

    # 00_Rawの全ファイルを処理
    raw_dir = vault_path / "00_Raw"
    if not raw_dir.exists():
        logger.warning("00_Rawディレクトリが見つかりません")
        return

    raw_files = list(raw_dir.glob("*.md"))
    logger.info(f"処理対象: {len(raw_files)}件のRawファイル")

    for raw_file in raw_files:
        try:
            logger.info(f"処理開始: {raw_file.name}")
            created_date = datetime.now().strftime("%Y-%m-%d")

            # Step 1: Raw → Summary
            summary_content = summarizer.summarize_raw_file(raw_file)
            if not summary_content:
                logger.warning(f"Summary生成失敗: {raw_file.name}")
                continue

            summary_file = summarizer.save_summary(summary_content, raw_file)
            logger.info(f"Summary作成: {summary_file.name}")

            # Step 2: Summary → Atomic
            atomic_notes = splitter.split_into_atomic_notes(summary_file)
            if not atomic_notes:
                logger.warning(f"Atomic分解失敗: {summary_file.name}")
                continue

            saved_files = splitter.save_atomic_notes(atomic_notes)
            logger.info(f"Atomic作成: {len(saved_files)}件")

            # Step 3: 日記ファイル連携
            for file in [raw_file, summary_file] + saved_files:
                linker.add_to_daily_note(file, created_date)

            logger.info(f"処理完了: {raw_file.name}")

        except Exception as exc:
            logger.error(f"処理失敗: {raw_file.name} - {exc}")
            continue


if __name__ == "__main__":
    run_auto_pipeline()
```

**実行：**
```bash
# 手動実行
uv run python scripts/auto_pipeline.py

# cron設定（1時間ごとに実行）
0 * * * * cd /home/perso/analysis/ObsidianConscierge && /home/perso/.local/bin/uv run python scripts/auto_pipeline.py
```

---

## 11. API仕様

### 11.1 POST /api/v1/atomic/split

**説明**: `01_Summary` ファイルを複数の `02_Atomic` ノートに分解

**実装**: `app/api/atomic.py` (新規作成)

```python
"""API endpoints for atomic notes operations."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from pathlib import Path

from app.core.atomic_splitter import AtomicSplitter
from app.core.pipeline_manager import PipelineManager
from app.core.atomic_scorer import AtomicScorer
from app.services.llm_service import LLMService
from app.core.config import Settings, get_settings
from app.dependencies import get_llm_service

router = APIRouter(prefix="/api/v1/atomic", tags=["atomic"])


class SplitRequest(BaseModel):
    summary_file_path: str


class SplitResponse(BaseModel):
    success: bool
    atomic_notes_count: int
    atomic_notes: list[dict[str, str]]


@router.post("/split", response_model=SplitResponse)
async def split_summary_to_atomic(
    request: SplitRequest,
    llm_service: LLMService = Depends(get_llm_service),
    settings: Settings = Depends(get_settings),
):
    """Summary → Atomic 分解エンドポイント"""
    try:
        splitter = AtomicSplitter(llm_service, settings)
        vault_path = Path(settings.obsidian_vault_path)
        summary_file = vault_path / request.summary_file_path

        if not summary_file.exists():
            raise HTTPException(status_code=404, detail="Summary file not found")

        # 分解実行
        atomic_notes = splitter.split_into_atomic_notes(summary_file)

        # 保存
        saved_files = splitter.save_atomic_notes(atomic_notes)

        return SplitResponse(
            success=True,
            atomic_notes_count=len(atomic_notes),
            atomic_notes=[
                {
                    "title": note["title"],
                    "file_path": str(Path(saved_files[i]).relative_to(vault_path)),
                    "tags": ", ".join(note["tags"]),
                }
                for i, note in enumerate(atomic_notes)
            ]
        )

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/score")
async def score_atomic_note(
    file_path: str,
    settings: Settings = Depends(get_settings),
):
    """Atomicノートのアトミック性スコア評価"""
    try:
        scorer = AtomicScorer(settings)
        vault_path = Path(settings.obsidian_vault_path)
        atomic_file = vault_path / file_path

        if not atomic_file.exists():
            raise HTTPException(status_code=404, detail="Atomic note not found")

        score_result = scorer.score_atomicity(atomic_file)
        return score_result

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

---

### 11.2 POST /api/v1/moc/generate

**実装**: `app/api/moc.py` (新規作成)

```python
"""API endpoints for MOC operations."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.moc_generator import MOCGenerator
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.core.analysis import AnalysisService
from app.core.config import Settings, get_settings
from app.dependencies import get_llm_service, get_vector_db_service

router = APIRouter(prefix="/api/v1/moc", tags=["moc"])


class MOCGenerateRequest(BaseModel):
    theme: str
    min_articles: int = 3


class MOCGenerateResponse(BaseModel):
    success: bool
    moc: dict[str, str | int] | None = None


@router.post("/generate", response_model=MOCGenerateResponse)
async def generate_moc(
    request: MOCGenerateRequest,
    llm_service: LLMService = Depends(get_llm_service),
    vector_db_service: VectorDBService = Depends(get_vector_db_service),
    settings: Settings = Depends(get_settings),
):
    """MOC生成エンドポイント"""
    try:
        analysis_service = AnalysisService(vector_db_service, settings)
        moc_generator = MOCGenerator(
            llm_service,
            vector_db_service,
            analysis_service,
            settings
        )

        moc_result = moc_generator.generate_moc(
            theme=request.theme,
            min_articles=request.min_articles
        )

        if not moc_result:
            return MOCGenerateResponse(
                success=False,
                moc=None
            )

        return MOCGenerateResponse(
            success=True,
            moc={
                "title": moc_result["title"],
                "file_path": moc_result["file_path"],
                "related_notes_count": moc_result["related_notes_count"],
            }
        )

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

---

### 11.3 GET /api/v1/pipeline/status

**実装**: `app/api/pipeline.py` (新規作成)

```python
"""API endpoints for pipeline status."""

from fastapi import APIRouter, Depends

from app.core.pipeline_manager import PipelineManager
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


@router.get("/status")
async def get_pipeline_status(
    settings: Settings = Depends(get_settings),
):
    """パイプライン全体のステータスを取得"""
    try:
        manager = PipelineManager(settings)

        status = {}
        total_files = 0

        for stage in ["00_Raw", "01_Summary", "02_Atomic", "03_MOC"]:
            files = manager.get_files_in_stage(stage)
            file_count = len(files)
            total_files += file_count

            latest_file = None
            if files:
                # 最新ファイルを取得（更新日時順）
                latest_file = max(files, key=lambda f: f.stat().st_mtime).name

            status[stage] = {
                "file_count": file_count,
                "latest_file": latest_file,
            }

        return {
            "pipeline_stages": status,
            "total_files": total_files,
        }

    except Exception as exc:
        return {"error": str(exc)}
```

---

## 12. 段階的移行プラン

### 12.1 YellowMableの現在の構成

```
TargetObsidianVault/
├── 00CreatedFiles/  ← 実質的な00_Raw
├── 01DIARY/
├── 04CODING/
├── 06MOC/          ← 既存のMOC（手動作成）
└── ...
```

### 12.2 移行手順（4段階）

#### 段階0: 既存フォルダはそのまま（後方互換性）

- 既存のフォルダ構成は維持
- 新規に `00_Raw/`, `01_Summary/`, `02_Atomic/`, `03_MOC/` を作成
- 既存のファイルは移動しない

#### 段階1: 新規フォルダ作成

```bash
cd TargetObsidianVault
mkdir -p 00_Raw 01_Summary 02_Atomic 03_MOC
```

#### 段階2: `00CreatedFiles/` → `01_Summary/` 移行

**自動移行スクリプト** (`scripts/migrate_to_pipeline.py`):

```python
"""Migrate existing files to atomic notes pipeline."""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_files():
    """00CreatedFiles → 01_Summary 移行"""
    vault_path = Path("TargetObsidianVault")
    old_dir = vault_path / "00CreatedFiles"
    new_dir = vault_path / "01_Summary"

    if not old_dir.exists():
        logger.error(f"ソースディレクトリが見つかりません: {old_dir}")
        return

    new_dir.mkdir(parents=True, exist_ok=True)

    # .mdファイルを全てコピー
    for file in old_dir.glob("*.md"):
        new_file = new_dir / file.name

        # 既存ファイルはスキップ
        if new_file.exists():
            logger.info(f"スキップ（既存）: {file.name}")
            continue

        # コピー
        new_file.write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info(f"移行完了: {file.name}")


if __name__ == "__main__":
    migrate_files()
```

**実行：**
```bash
uv run python scripts/migrate_to_pipeline.py
```

#### 段階3: `01_Summary` → `02_Atomic` 分解開始

**API呼び出し：**
```bash
curl -X POST http://localhost:8000/api/v1/atomic/split \
  -H "Content-Type: application/json" \
  -d '{"summary_file_path": "01_Summary/2025-01-01_プロジェクトX進捗会議_Summary.md"}'
```

#### 段階4: `03_MOC` 自動生成有効化

**API呼び出し：**
```bash
curl -X POST http://localhost:8000/api/v1/moc/generate \
  -H "Content-Type: application/json" \
  -d '{"theme": "プロジェクトX", "min_articles": 3}'
```

### 12.3 除外フォルダ設定

`.env`:
```env
# アトミック・ノートパイプラインから除外するフォルダ
PIPELINE_FOLDERS=00_Raw,01_Summary,02_Atomic,03_MOC
EXCLUDED_FOLDERS=01DIARY,02TEMPLATES,06MOC,10KANBAN,11MEDIA,Excalidraw,Maybe,Omnivore
```

`app/core/config.py`:
```python
class Settings(BaseSettings):
    ...
    pipeline_folders: list[str] = Field(
        default=["00_Raw", "01_Summary", "02_Atomic", "03_MOC"]
    )
    excluded_folders: list[str] = Field(default_factory=list)
```

---

## 13. テストケース

### 13.1 単体テスト

**ファイル**: `tests/unit/test_atomic_splitter.py`

```python
"""Unit tests for AtomicSplitter."""

import pytest
from pathlib import Path
from app.core.atomic_splitter import AtomicSplitter


def test_parse_atomic_notes(mock_llm_service, settings, tmp_path):
    """LLMレスポンスを正しくパースできるか"""
    splitter = AtomicSplitter(mock_llm_service, settings)

    response = """
---ATOMIC_NOTE---
タイトル: AI動画集客戦略
タグ: マーケティング, AI動画
概念: AI動画を使った集客施策
詳細:
費用: 月50万円

応用例:
- YouTube shortsでの活用

関連リンク:
- [[test]]
---END---
"""

    notes = splitter._parse_atomic_notes(response, tmp_path / "test.md")

    assert len(notes) == 1
    assert notes[0]["title"] == "AI動画集客戦略"
    assert "マーケティング" in notes[0]["tags"]
    assert "AI動画" in notes[0]["tags"]
```

**ファイル**: `tests/unit/test_pipeline_manager.py`

```python
"""Unit tests for PipelineManager."""

import pytest
from pathlib import Path
from app.core.pipeline_manager import PipelineManager


def test_get_stage_from_file(settings, tmp_path):
    """ファイルパスから正しくステージを取得できるか"""
    manager = PipelineManager(settings)

    # テスト用ファイル作成
    raw_file = tmp_path / "00_Raw" / "test.md"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text("test", encoding="utf-8")

    stage = manager.get_stage_from_file(raw_file)
    assert stage == "00_Raw"


def test_get_next_stage(settings):
    """次のステージを正しく取得できるか"""
    manager = PipelineManager(settings)

    assert manager.get_next_stage("00_Raw") == "01_Summary"
    assert manager.get_next_stage("01_Summary") == "02_Atomic"
    assert manager.get_next_stage("02_Atomic") == "03_MOC"
    assert manager.get_next_stage("03_MOC") is None
```

### 13.2 統合テスト

**ファイル**: `tests/integration/test_pipeline_workflow.py`

```python
"""Integration tests for full pipeline workflow."""

import pytest
from pathlib import Path


def test_full_pipeline_workflow(
    atomic_splitter,
    pipeline_manager,
    moc_generator,
    tmp_vault_path
):
    """00_Raw → 01_Summary → 02_Atomic → 03_MOC の全フロー"""

    # 1. 01_Summaryファイルを作成
    summary_file = tmp_vault_path / "01_Summary" / "test_summary.md"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        """---
title: テスト
pipeline_stage: 01_Summary
---

# テスト

## サマリー
AI動画とレコメンデーションの提案

## 観点1: AI動画
YouTube shortsで集客

## 観点2: レコメンデーション
ベクトル検索で類似記事推薦
""",
        encoding="utf-8"
    )

    # 2. 02_Atomicに分解
    atomic_notes = atomic_splitter.split_into_atomic_notes(summary_file)
    assert len(atomic_notes) >= 1

    saved_files = atomic_splitter.save_atomic_notes(atomic_notes)
    assert len(saved_files) >= 1
    assert all(f.exists() for f in saved_files)

    # 3. ステージ確認
    for file in saved_files:
        stage = pipeline_manager.get_stage_from_file(file)
        assert stage == "02_Atomic"
```

### 13.3 E2Eテスト

**ファイル**: `tests/e2e/test_api_workflow.py`

```python
"""End-to-end tests for API workflow."""

import pytest
from fastapi.testclient import TestClient


def test_api_split_workflow(client: TestClient, tmp_vault_path):
    """POST /api/v1/atomic/split エンドポイントのテスト"""

    # 01_Summaryファイルを作成
    summary_file = tmp_vault_path / "01_Summary" / "test.md"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        """---
title: テスト
pipeline_stage: 01_Summary
---

# テスト

## 観点1: AI動画
YouTube shortsで集客提案
""",
        encoding="utf-8"
    )

    # APIリクエスト
    response = client.post(
        "/api/v1/atomic/split",
        json={"summary_file_path": "01_Summary/test.md"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["atomic_notes_count"] >= 1


def test_api_pipeline_status(client: TestClient):
    """GET /api/v1/pipeline/status エンドポイントのテスト"""
    response = client.get("/api/v1/pipeline/status")

    assert response.status_code == 200
    data = response.json()
    assert "pipeline_stages" in data
    assert "00_Raw" in data["pipeline_stages"]
    assert "total_files" in data
```

---

# Part 3: 運用・保守

## 14. 運用ルール

### 14.1 日次ルール

- [ ] Rawフォルダをチェック（48時間以上経過したファイルを処理）
- [ ] 新規Atomicノートにリンクを追加

### 14.2 週次ルール

- [ ] Summary化の遅延ファイルを確認
- [ ] 孤立Atomicノート（リンク0〜2個）を確認
- [ ] MOCの更新（新規Atomicノートの追加）

### 14.3 月次ルール

- [ ] タグの棚卸し
- [ ] MOCの見直し（統合・分割の検討）
- [ ] ベクトル検索の精度確認

---

## 15. アンチパターン集

### 15.1 やってはいけないこと

#### ❌ フォルダ分けで分類する
理由：情報の複数分類問題が発生する。

#### ❌ Rawで整形する
理由：Rawの目的は「捕捉」であり、整形は次フェーズの仕事。

#### ❌ Atomicを大きくしすぎる
理由：1ノート1意味単位の原則に反する。

#### ❌ MOCを単なるリストにする
理由：フォルダの代替にしかなっていない。

#### ❌ リンクに文脈を付けない
理由：なぜ関連しているのかが不明。

### 15.2 よくある失敗パターン

#### パターン1：分割しすぎて意味が通らない
**対処法**: 親ノートに統合するか、別のAtomicノートと結合する。

#### パターン2：Summaryがただのコピペ
**対処法**: AIに「観点ごとに見出しを分けて要約」を依頼する。

#### パターン3：MOCが乱立して管理不能
**対処法**: 類似MOCを統合し、「大きな問い」にまとめる。

#### パターン4：タグが無秩序に増える
**対処法**: 月次でタグを棚卸しし、統合・削除する。

---

## 16. 判断フローチャート集

### 16.1 「このメモはどこに入れる？」

```
START
  ↓
Q: まだ整形されていないか？
  YES → 00_Raw へ
  NO → 次へ
  ↓
Q: 複数トピックが混在しているか？
  YES → 01_Summary へ
  NO → 次へ
  ↓
Q: 単独で意味が通るか？
  YES → 02_Atomic へ
  NO → 01_Summary へ
  ↓
END
```

### 16.2 「このノートは分割すべきか？」

```
START: Summaryの各観点を見る
  ↓
Q: 複数の主張が含まれているか？
  YES → 分割する
  NO → 次へ
  ↓
Q: 別の文脈で使えるか？
  YES → Atomic化する
  NO → Summary内に留める
  ↓
Q: 文字数が800字を超えているか？
  YES → 分割を検討
  NO → 次へ
  ↓
Q: 「〇〇と△△」のように複数要素があるか？
  YES → 分割する
  NO → Atomic化完了
  ↓
END
```

### 16.3 「MOCを作るべきか？」

```
START: Atomicノート作成完了
  ↓
Q: 類似する既存Atomicが2つ以上あるか？
  YES → 次へ
  NO → MOC不要（終了）
  ↓
Q: それらを束ねる「問い」を立てられるか？
  YES → 次へ
  NO → MOC不要（終了）
  ↓
Q: その問いは既存MOCとかぶっていないか？
  YES → 既存MOCに追加（終了）
  NO → 新規MOC作成
  ↓
END
```

---

## 17. 成功の指標

### 17.1 定量指標

- [ ] Rawファイルの滞留時間：48時間以内
- [ ] Atomicノートの増加：月10個以上
- [ ] 孤立ノート（リンク0〜2個）の割合：10%以下
- [ ] MOCあたりのAtomicノート数：3〜15個

### 17.2 定性指標

- [ ] 「あのメモどこだっけ？」が減った
- [ ] 過去の知識を組み合わせて新しいアイデアが生まれる
- [ ] AIに文脈を説明する手間が減った
- [ ] コンテンツ生成（投稿・記事）の速度が上がった

---

## まとめ

本設計の核心は以下の3点：

1. **フォルダ分類を廃止し、意味単位で分解する**
2. **各フェーズの役割を明確にする（Raw / Summary / Atomic / MOC）**
3. **リンクとベクトル検索でAIと協働する**

この設計により、Obsidianは「保管庫」から「思考装置」に変わる。
情報は「分類される」のではなく、「接続される」。

運用の成否は「ルールを守る」ことではなく、
**「考え直せる状態を維持する」**ことにある。

完璧な整理は不要。
必要なのは、いつでも組み替えられる柔軟性である。

---

**次のステップ**:
1. `app/core/atomic_splitter.py` の実装から開始
2. API endpoints (`app/api/atomic.py`, `app/api/moc.py`, `app/api/pipeline.py`) の追加
3. テストケースの作成
4. 移行スクリプトの実行
