#!/bin/bash
# ObsidianConscierge systemdセットアップスクリプト
# 使い方: sudo bash scripts/setup_systemd.sh

set -e  # エラー時に終了

# 色付きログ出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# rootチェック
if [ "$EUID" -ne 0 ]; then
    log_error "このスクリプトはsudo権限で実行してください"
    echo "使い方: sudo bash scripts/setup_systemd.sh"
    exit 1
fi

# プロジェクトディレクトリ
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log_info "プロジェクトディレクトリ: $PROJECT_DIR"

# systemd設定ファイルをコピー
log_info "systemd設定ファイルをコピー中..."

cp "$PROJECT_DIR/systemd/obsidian-conscierge-sync.service" /etc/systemd/system/
cp "$PROJECT_DIR/systemd/obsidian-conscierge-sync.timer" /etc/systemd/system/
cp "$PROJECT_DIR/systemd/obsidian-conscierge-daily.service" /etc/systemd/system/
cp "$PROJECT_DIR/systemd/obsidian-conscierge-daily.timer" /etc/systemd/system/
cp "$PROJECT_DIR/systemd/obsidian-conscierge-api.service" /etc/systemd/system/

log_info "✅ systemd設定ファイルのコピー完了"

# systemd設定の再読み込み
log_info "systemd設定を再読み込み中..."
systemctl daemon-reload
log_info "✅ systemd設定の再読み込み完了"

# Git同期サービスを有効化
log_info "Git同期サービスを有効化中..."
systemctl enable obsidian-conscierge-sync.timer
systemctl start obsidian-conscierge-sync.timer
log_info "✅ Git同期サービスの有効化完了（30分ごとに実行）"

# デイリーレポートサービスを有効化（オプション）
read -p "デイリーレポートサービスを有効化しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "デイリーレポートサービスを有効化中..."
    systemctl enable obsidian-conscierge-daily.timer
    systemctl start obsidian-conscierge-daily.timer
    log_info "✅ デイリーレポートサービスの有効化完了（毎朝6時に実行）"
fi

# FastAPIサービスを有効化（オプション）
read -p "FastAPIサービスを有効化しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "FastAPIサービスを有効化中..."
    systemctl enable obsidian-conscierge-api.service
    systemctl start obsidian-conscierge-api.service
    log_info "✅ FastAPIサービスの有効化完了（ポート8000で起動）"
fi

# ステータス確認
echo ""
log_info "=========================================="
log_info "サービスステータス"
log_info "=========================================="

echo ""
log_info "📅 Git同期タイマー:"
systemctl status obsidian-conscierge-sync.timer --no-pager | head -10

if systemctl is-enabled obsidian-conscierge-daily.timer &>/dev/null; then
    echo ""
    log_info "📊 デイリーレポートタイマー:"
    systemctl status obsidian-conscierge-daily.timer --no-pager | head -10
fi

if systemctl is-active obsidian-conscierge-api.service &>/dev/null; then
    echo ""
    log_info "🌐 FastAPI サービス:"
    systemctl status obsidian-conscierge-api.service --no-pager | head -10
fi

echo ""
log_info "=========================================="
log_info "セットアップ完了！"
log_info "=========================================="
echo ""
log_info "便利なコマンド:"
echo "  サービス状態確認: sudo systemctl status obsidian-conscierge-sync.timer"
echo "  ログ確認: sudo journalctl -u obsidian-conscierge-sync.service -f"
echo "  サービス停止: sudo systemctl stop obsidian-conscierge-sync.timer"
echo "  サービス再起動: sudo systemctl restart obsidian-conscierge-sync.timer"
echo ""
