#!/bin/bash
# Git同期スクリプト（push/pull）
# ObsidianConscierge用のGit操作を実行

set -e  # エラー時に終了

# 設定を読み込む（.envファイルから）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

# .envファイルが存在する場合は読み込む
if [ -f "$ENV_FILE" ]; then
    # シンプルな.env読み込み（コメントと空行をスキップ）
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # コメントと空行をスキップ
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        
        # 値からクォートを削除
        value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
        
        # 環境変数として設定
        export "$key=$value"
    done < "$ENV_FILE"
fi

# 設定値の取得（デフォルト値付き）
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-$PROJECT_DIR/TargetObsidianVault}"
GITHUB_REPO_URL="${GITHUB_REPO_URL:-}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# ログ出力関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# エラー出力関数
error() {
    echo "[ERROR] $*" >&2
}

# Vaultパスの確認
if [ ! -d "$VAULT_PATH" ]; then
    error "Vaultパスが存在しません: $VAULT_PATH"
    exit 1
fi

log "Vaultパス: $VAULT_PATH"

# Gitリポジトリの確認
if [ ! -d "$VAULT_PATH/.git" ]; then
    error "Gitリポジトリが見つかりません: $VAULT_PATH"
    exit 1
fi

# Git pull（リモートから最新を取得）
log "Git pullを実行中..."
cd "$VAULT_PATH"
if ! git pull origin main 2>&1; then
    # mainブランチがない場合はmasterを試す
    if ! git pull origin master 2>&1; then
        error "Git pullに失敗しました"
        exit 1
    fi
fi
log "Git pull完了"

# 変更がある場合はpush（オプション）
# 注意: 自動pushは危険な場合があるため、デフォルトでは無効
# AUTO_PUSH="${GIT_AUTO_PUSH:-false}"
# if [ "$AUTO_PUSH" = "true" ]; then
#     if [ -n "$(git status --porcelain)" ]; then
#         log "変更を検出しました。Git pushを実行中..."
#         git add .
#         git commit -m "Auto-sync: $(date '+%Y-%m-%d %H:%M:%S')" || true
#         git push origin main || git push origin master || true
#         log "Git push完了"
#     fi
# fi

log "Git同期が完了しました"

