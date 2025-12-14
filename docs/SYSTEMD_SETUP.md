# systemd設定ガイド: ObsidianConscierge

このドキュメントでは、ObsidianConsciergeをsystemdで自動実行する設定方法を説明します。

## 前提条件

- Linuxシステム（systemdが利用可能）
- ObsidianConsciergeがインストール済み
- `.env`ファイルが設定済み

## 設定ファイルの配置

### 1. Git同期サービス（30分ごと）

#### サービスファイル: `obsidian-conscierge-sync.service`

```bash
sudo cp systemd/obsidian-conscierge-sync.service /etc/systemd/system/
```

ファイルを編集して、環境に合わせて以下を変更：

```ini
[Service]
User=your-username          # 実際のユーザー名に変更
Group=your-username         # 実際のグループ名に変更
WorkingDirectory=/path/to/ObsidianConscierge  # 実際のパスに変更
EnvironmentFile=/path/to/ObsidianConscierge/.env  # 実際のパスに変更
```

#### タイマーファイル: `obsidian-conscierge-sync.timer`

```bash
sudo cp systemd/obsidian-conscierge-sync.timer /etc/systemd/system/
```

### 2. デイリーレポートサービス（毎日6:00）

#### サービスファイル: `obsidian-conscierge-daily.service`

```bash
sudo cp systemd/obsidian-conscierge-daily.service /etc/systemd/system/
```

ファイルを編集して、環境に合わせて以下を変更：

```ini
[Service]
User=your-username          # 実際のユーザー名に変更
Group=your-username         # 実際のグループ名に変更
WorkingDirectory=/path/to/ObsidianConscierge  # 実際のパスに変更
EnvironmentFile=/path/to/ObsidianConscierge/.env  # 実際のパスに変更
ExecStart=/path/to/uv run python /path/to/ObsidianConscierge/scripts/daily_report.py
```

#### タイマーファイル: `obsidian-conscierge-daily.timer`

```bash
sudo cp systemd/obsidian-conscierge-daily.timer /etc/systemd/system/
```

## 有効化と開始

### Git同期サービスの有効化

```bash
# systemdの設定を再読み込み
sudo systemctl daemon-reload

# タイマーを有効化
sudo systemctl enable obsidian-conscierge-sync.timer

# タイマーを開始
sudo systemctl start obsidian-conscierge-sync.timer

# ステータス確認
sudo systemctl status obsidian-conscierge-sync.timer
```

### デイリーレポートサービスの有効化

```bash
# タイマーを有効化
sudo systemctl enable obsidian-conscierge-daily.timer

# タイマーを開始
sudo systemctl start obsidian-conscierge-daily.timer

# ステータス確認
sudo systemctl status obsidian-conscierge-daily.timer
```

## 実行スケジュール

### Git同期サービス

- **初回実行**: システム起動後5分
- **定期実行**: 前回実行から30分後
- **実行内容**: 
  1. `scripts/git_sync.sh` を実行（Git pull）
  2. 変更を検知
  3. インデックスを更新

### デイリーレポートサービス

- **実行時刻**: 毎日6:00
- **実行内容**: デイリーレポートを生成

## ログの確認

### Git同期サービスのログ

```bash
# 最新のログを確認
sudo journalctl -u obsidian-conscierge-sync.service -n 50

# リアルタイムでログを確認
sudo journalctl -u obsidian-conscierge-sync.service -f
```

### デイリーレポートサービスのログ

```bash
# 最新のログを確認
sudo journalctl -u obsidian-conscierge-daily.service -n 50
```

## トラブルシューティング

### サービスが起動しない

1. パスを確認:
   ```bash
   which uv
   ls -la /path/to/ObsidianConscierge/.env
   ```

2. 権限を確認:
   ```bash
   ls -la /path/to/ObsidianConscierge/scripts/git_sync.sh
   chmod +x /path/to/ObsidianConscierge/scripts/git_sync.sh
   ```

3. 手動実行でテスト:
   ```bash
   cd /path/to/ObsidianConscierge
   bash scripts/git_sync.sh
   ```

### Git操作が失敗する

1. Git認証情報を確認:
   ```bash
   cd /path/to/TargetObsidianVault
   git config --list
   ```

2. SSH鍵またはトークンの設定を確認

3. `.env`ファイルの`GITHUB_TOKEN`を確認

## 無効化と停止

### サービスを停止

```bash
# タイマーを停止
sudo systemctl stop obsidian-conscierge-sync.timer
sudo systemctl stop obsidian-conscierge-daily.timer

# タイマーを無効化
sudo systemctl disable obsidian-conscierge-sync.timer
sudo systemctl disable obsidian-conscierge-daily.timer
```

## 参考

- [systemd公式ドキュメント](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [systemd timer公式ドキュメント](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)

