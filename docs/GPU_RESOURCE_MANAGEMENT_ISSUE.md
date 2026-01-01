# GPU リソース管理問題の分析と設計改善案

**作成日**: 2026-01-01
**問題発生日**: 2025-12-31 23:56 ～ 2026-01-01 15:50 (約16時間ハング)

## 📋 概要

`scripts/git_sync.py` がGPUリソースを掴んだままハングアップし、16時間以上GPUを占有し続ける問題が発生。根本原因はリソース管理の設計不備にある。

---

## 🚨 発生した問題

### 症状
- **GPU使用率**: 97% (16時間継続)
- **GPUメモリ**: 21.9GB / 24.5GB 占有
- **プロセス状態**: デッドロック (git cat-file とのパイプ通信で詰まる)
- **データベース更新**: 15時間以上停止
- **CPU/IO**: 完全に停止 (voluntary_ctxt_switches: 275,711回)

### 直接原因
1. GitPython の `repo.iter_commits()` が `git cat-file --batch` を呼び出し
2. パイプ通信でデッドロック発生
3. Pythonプロセスがハング → GPUリソースを解放できない

---

## 🔍 根本原因：設計上の問題

### 問題1: GPUリソースのライフサイクル管理の欠如

#### 現在の実装 (`app/services/embedding_service.py`)

```python
class EmbeddingService:
    def __init__(self, model_name: str = "distiluse-base-multilingual-cased-v2"):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None  # ❌ 遅延初期化だが解放機構なし

    def _get_or_load_model(self) -> SentenceTransformer | None:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)  # ❌ GPUにロードされる
        return self._model  # ❌ 一度ロードしたら解放されない

    def embed(self, text: str) -> list[float]:
        model = self._get_or_load_model()  # ❌ GPUにモデルが常駐
        embedding = model.encode(text)
        return embedding.tolist()
        # ❌ モデルをGPUから解放しない
```

**問題点:**
- モデルは **一度ロードしたらプロセス終了まで解放されない**
- Pythonのガベージコレクションに依存 → ハング時はGCが動かない
- 明示的な `model.to('cpu')` や `del model` がない
- **デストラクタ (`__del__`) もない**

#### なぜGPUが解放されないのか

1. **sentence-transformers のデフォルト動作**
   ```python
   model = SentenceTransformer('model-name')
   # ↓ 内部で以下が実行される
   # if torch.cuda.is_available():
   #     self.model = self.model.to('cuda')  # GPUにロード
   ```

2. **Pythonプロセスがハングすると**
   - ガベージコレクタが動作しない
   - `__del__` も呼ばれない
   - GPUメモリがリークしたまま

3. **明示的な解放処理がない**
   ```python
   # ❌ こういうコードが存在しない
   def cleanup(self):
       if self._model:
           self._model.to('cpu')  # GPUから退避
           del self._model
           torch.cuda.empty_cache()  # GPUメモリ解放
   ```

---

### 問題2: タイムアウトとシグナルハンドリングの欠如

#### 現在の実装 (`scripts/git_sync.py`)

```python
def main(pull_only: bool, use_sh_script: bool) -> None:
    try:
        # ... 省略 ...

        # サービスを初期化
        embedding_service = EmbeddingService()  # ❌ GPUロード開始

        # 変更を処理 (ここでハング可能性あり)
        commits = self.repo.iter_commits(f"{since_commit}..HEAD")  # ❌ タイムアウトなし
        for commit in commits:
            diffs = commit.diff(parent)  # ❌ 重い処理、タイムアウトなし
            # ...

    except KeyboardInterrupt:
        logger.info("処理が中断されました")
        sys.exit(1)  # ❌ クリーンアップ処理なし
    except Exception as exc:
        logger.error(f"エラーが発生しました: {exc}")
        sys.exit(1)  # ❌ GPUリソース解放なし
```

**問題点:**
- **タイムアウトがない** → 無限に待ち続ける可能性
- **シグナルハンドラがない** → SIGTERM/SIGINT でもクリーンアップされない
- **finally ブロックがない** → 例外時にリソース解放されない
- **コンテキストマネージャーを使っていない** → with文で自動解放されない
- **ハング中は cleanup が実行されない** → finally/シグナルは「動ける時だけ」有効

---

### 問題3: リソース確保と解放のタイミング設計

#### 現在のアーキテクチャ

```
git_sync.py 起動
    ↓
EmbeddingService() 初期化 ← GPUメモリ確保 (21.9GB)
    ↓
git 操作開始
    ↓
デッドロック発生 ← ここで詰まる
    ↓
(16時間経過)
    ↓
GPUメモリ解放されない ← プロセスが終了しないため
```

**問題点:**
- **GPUリソース確保が早すぎる** (git操作前に確保)
- **使わない時間もGPUを占有** (git操作中は embedding 不要)
- **必要な時だけ確保する設計になっていない**

---

## ✅ あるべき設計パターン

### パターン1: コンテキストマネージャーによる自動解放

```python
from contextlib import contextmanager
import torch

class EmbeddingService:
    def __init__(self, model_name: str = "distiluse-base-multilingual-cased-v2"):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @contextmanager
    def get_model(self):
        """コンテキストマネージャーでモデルを取得・自動解放"""
        try:
            if self._model is None:
                self._model = SentenceTransformer(self.model_name)
            yield self._model
        finally:
            # 使用後は必ずGPUから解放
            if self._model is not None:
                self._model.to('cpu')
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

    def embed(self, text: str) -> list[float]:
        """使う時だけGPUにロード、終わったら解放"""
        with self.get_model() as model:
            embedding = model.encode(text)
            return embedding.tolist()
        # ← ここでGPU解放される
```

**メリット:**
- `with` 文を抜けると **必ず** GPU解放される
- 例外が発生しても `finally` で確実にクリーンアップ
- プロセスがハングしても影響範囲が限定的

---

### パターン2: タイムアウト付きリソース管理

```python
import signal
from contextlib import contextmanager

class TimeoutError(Exception):
    pass

@contextmanager
def timeout(seconds: int):
    """タイムアウト付きコンテキストマネージャー"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # タイムアウト設定
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)  # タイムアウト解除
        signal.signal(signal.SIGALRM, old_handler)

# 使用例
def process_git_changes():
    embedding_service = EmbeddingService()

    try:
        with timeout(300):  # 5分でタイムアウト
            commits = repo.iter_commits(f"{since_commit}..HEAD")
            for commit in commits:
                # ...
    except TimeoutError:
        logger.error("Git処理がタイムアウトしました")
        raise
    finally:
        # 必ずGPUリソースを解放
        embedding_service.cleanup()
```

**注意点:**
- `signal.alarm` はUnixのメインスレッド限定で、Windowsでは動作しない
- C拡張内のブロッキングやデッドロックには効かない可能性がある

---

### パターン3: Lazy Loading + Eager Cleanup

```python
class EmbeddingService:
    def __init__(self, model_name: str = "distiluse-base-multilingual-cased-v2"):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self._gpu_loaded = False

    def _load_to_gpu(self):
        """必要な時だけGPUにロード"""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        if not self._gpu_loaded and torch.cuda.is_available():
            self._model = self._model.to('cuda')
            self._gpu_loaded = True

    def _unload_from_gpu(self):
        """即座にGPUから解放"""
        if self._model is not None and self._gpu_loaded:
            self._model = self._model.to('cpu')
            self._gpu_loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """バッチ処理 - 使用前にロード、使用後に即解放"""
        try:
            self._load_to_gpu()  # GPUロード
            embeddings = self._model.encode(texts)
            return [e.tolist() for e in embeddings]
        finally:
            self._unload_from_gpu()  # 即座に解放

    def __del__(self):
        """デストラクタでも念のため解放"""
        self._unload_from_gpu()
```

**メリット:**
- バッチ処理単位でGPU確保・解放
- 処理が終わったら **即座に** GPU解放
- デストラクタでも保険的にクリーンアップ

---

### パターン4: シグナルハンドラによるクリーンアップ

```python
import signal
import sys

class GracefulKiller:
    """SIGTERM/SIGINTを捕捉してクリーンアップするクラス"""
    def __init__(self):
        self.kill_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        logger.info(f"Signal {signum} received, cleaning up...")
        self.kill_now = True

def main():
    killer = GracefulKiller()
    embedding_service = EmbeddingService()

    try:
        for commit in commits:
            if killer.kill_now:
                logger.info("Interrupted, cleaning up...")
                break
            # 処理...
    finally:
        # 必ずクリーンアップ
        embedding_service.cleanup()
        logger.info("Cleanup completed")
```

---

**注意点:**
- シグナルハンドラは「処理が動いている場合のみ」有効で、デッドロック中は動かない

---

### パターン5: 別プロセス化 + 監視 (推奨)

**狙い:** ハング時でも GPU を解放できるように、GPU処理を**別プロセス**に隔離し、親プロセスが監視して強制終了できる構造にする。

```
Parent Process (git_sync.py)
    ↓
Spawn Embedding Worker Process
    ↓
Worker loads model to GPU and processes batches
    ↓
Parent enforces timeout / heartbeat
    ↓
If hang -> kill worker -> GPU memory released by OS
```

**設計ポイント:**
- **GPUはワーカープロセスが独占**し、親はGPUを持たない
- **タイムアウトは親で管理** (subprocess/multiprocessing + kill)
- **ハング時に確実にGPU解放** (プロセス終了が唯一の保証)

**擬似コード例:**

```python
# parent process
proc = subprocess.Popen(["python", "scripts/embedding_worker.py", "..."])
try:
    proc.wait(timeout=1800)  # 30分
except TimeoutExpired:
    proc.kill()
```

## 🛠️ 推奨実装案

### ステップ1: EmbeddingService の改修

```python
# app/services/embedding_service.py
from contextlib import contextmanager
import torch
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "distiluse-base-multilingual-cased-v2"):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    def _ensure_model_loaded(self):
        """モデルをCPUにロード（GPU転送は別途管理）"""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
            # デフォルトはCPUに配置
            if torch.cuda.is_available():
                self._model = self._model.to('cpu')

    @contextmanager
    def use_gpu(self):
        """GPU使用のコンテキストマネージャー"""
        self._ensure_model_loaded()
        try:
            if torch.cuda.is_available():
                self._model = self._model.to('cuda')
            yield self._model
        finally:
            if torch.cuda.is_available() and self._model is not None:
                self._model = self._model.to('cpu')
                torch.cuda.empty_cache()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """バッチ処理 - GPU使用後は即解放"""
        with self.use_gpu() as model:
            embeddings = model.encode(texts, show_progress_bar=False)
            return [e.tolist() for e in embeddings]

    def cleanup(self):
        """明示的なクリーンアップ"""
        if self._model is not None:
            if torch.cuda.is_available():
                self._model = self._model.to('cpu')
                torch.cuda.empty_cache()
            del self._model
            self._model = None

    def __del__(self):
        """デストラクタ（補助的な保険）"""
        self.cleanup()
```

### ステップ2: git_sync.py の改修

```python
# scripts/git_sync.py
import signal
import sys
from contextlib import contextmanager

class TimeoutError(Exception):
    pass

@contextmanager
def timeout(seconds: int):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Timeout after {seconds}s")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def main(pull_only: bool, use_sh_script: bool) -> None:
    embedding_service = None

    try:
        # Git操作（タイムアウト付き）
        with timeout(300):  # 5分
            detector = GitChangeDetector(vault_path)
            changes = detector.detect_changes(since_commit=last_commit)

        if not changes or pull_only:
            return

        # サービス初期化（GPUはまだ使わない）
        embedding_service = EmbeddingService()
        llm_service = LLMService(...)
        vector_db_service = VectorDBService(...)

        # インデックス処理（タイムアウト付き）
        with timeout(1800):  # 30分
            indexing_service = IndexingService(
                vector_db_service=vector_db_service,
                embedding_service=embedding_service,
                llm_service=llm_service,
            )

            # バッチ処理（GPU使用は内部で自動管理）
            articles = indexing_service.process_batch(all_files)
            indexing_service.index_articles(articles)

    except TimeoutError as e:
        logger.error(f"処理がタイムアウトしました: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("処理が中断されました")
        sys.exit(1)
    except Exception as exc:
        logger.error(f"エラーが発生しました: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        # 必ずクリーンアップ
        if embedding_service is not None:
            embedding_service.cleanup()
        logger.info("Cleanup completed")
```

### ステップ3: GPU処理の別プロセス化 (推奨)

```python
# scripts/git_sync.py (親プロセス側)
proc = subprocess.Popen(["python", "scripts/embedding_worker.py", "--batch", "..."])
try:
    proc.wait(timeout=1800)
except TimeoutExpired:
    logger.error("Embedding worker timed out, killing process")
    proc.kill()
```

```python
# scripts/embedding_worker.py (子プロセス側)
embedding_service = EmbeddingService()
try:
    # GPU処理のみ実行
    embedding_service.embed_batch(texts)
finally:
    embedding_service.cleanup()
```

---

## 📊 改善効果の比較

| 項目 | 改修前 | 改修後 |
|------|--------|--------|
| GPU占有時間 | プロセス起動～終了 (16時間+) | バッチ処理時のみ (数秒～数分) |
| ハング時のGPU解放 | されない | ワーカープロセス kill で強制解放 |
| タイムアウト | なし | Git: 5分、Index: 30分 |
| シグナルハンドリング | なし | SIGTERM/SIGINT で cleanup |
| リソースリーク | 発生する | 発生しない |

---

## 🎯 実装優先度

### 優先度 HIGH（即時対応）
1. ✅ **EmbeddingService のコンテキストマネージャー化**
   - GPU使用時間を最小化
   - 自動解放機構の実装

2. ✅ **タイムアウトの追加**
   - Git操作: 5分
   - インデックス処理: 30分

3. ✅ **finally ブロックでのクリーンアップ**
   - 例外時も必ず GPU解放

4. ✅ **GPU処理の別プロセス化 + 監視**
   - ハング時は親が kill
   - OSレベルでGPUを確実に解放

### 優先度 MEDIUM（次回対応）
5. ⏳ **シグナルハンドラの実装**
   - SIGTERM/SIGINT での graceful shutdown

6. ⏳ **デストラクタの実装**
   - 念のための保険的クリーンアップ

### 優先度 LOW（将来的に検討）
7. 📋 **監視・自動復旧機構**
   - プロセス監視デーモン
   - 自動kill & 再起動

---

## 📝 まとめ

### 問題の本質
> **「止まったままにならない設計」ではなく、「止まっても被害を最小化する設計」が必要**

### 設計原則
1. **リソースは必要最小限の時間だけ確保する**
2. **自動解放機構を必ず実装する** (context manager, finally, destructor)
3. **タイムアウトを設定する** (無限待ちを避ける)
4. **シグナルハンドリングでクリーンアップする**
5. **ハング時でも回収できるように別プロセス化する**
6. **例外時も必ずリソース解放する**

### 次のアクション
- [ ] EmbeddingService の改修実装
- [ ] git_sync.py のタイムアウト実装
- [ ] 統合テストの実施
- [ ] 本番環境での動作検証
