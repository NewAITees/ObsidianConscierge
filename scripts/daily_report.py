"""Daily report generation script for ObsidianConscierge."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import click

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.analysis import AnalysisService
from app.core.config import get_settings
from app.services.vector_db_service import VectorDBService


def format_markdown_report(
    date: datetime,
    stats: dict,
    duplicates: list,
    pickups: list,
    moc_candidates: list,
) -> str:
    """
    Markdown形式のレポートを生成する

    Args:
        date: レポート日付
        stats: 執筆統計
        duplicates: 重複ペアのリスト
        pickups: ランダムピックアップ記事のリスト
        moc_candidates: MOC候補のリスト

    Returns:
        str: Markdown形式のレポート
    """
    lines: list[str] = []

    # ヘッダー
    lines.append(f"# デイリーレポート - {date.strftime('%Y年%m月%d日')}")
    lines.append("")
    lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 執筆統計
    lines.append("## 📊 執筆統計")
    lines.append("")
    lines.append(f"- **新規記事数**: {stats['new_count']}件")
    lines.append(f"- **更新記事数**: {stats['updated_count']}件")
    lines.append(f"- **総文字数**: {stats['total_word_count']:,}文字")
    lines.append(f"- **総記事数**: {stats['total_articles']}件")
    lines.append("")

    # 重複検知警告
    lines.append("## ⚠️ 重複検知警告")
    lines.append("")
    if duplicates:
        lines.append(f"類似度80%以上の記事ペアが **{len(duplicates)}組** 見つかりました:")
        lines.append("")
        for i, dup in enumerate(duplicates[:10], 1):  # 最大10組まで表示
            article1 = dup["article1"]
            article2 = dup["article2"]
            similarity = dup["similarity"]
            lines.append(f"### {i}. 類似度: {similarity:.1%}")
            lines.append(f"- **{article1['title']}** (`{article1['file_path']}`)")
            lines.append(f"- **{article2['title']}** (`{article2['file_path']}`)")
            lines.append("")
        if len(duplicates) > 10:
            lines.append(f"*他 {len(duplicates) - 10}組の重複ペアがあります*")
            lines.append("")
    else:
        lines.append("重複記事は見つかりませんでした。✅")
        lines.append("")

    # ランダムピックアップ
    lines.append("## 🎲 ランダムピックアップ")
    lines.append("")
    if pickups:
        for i, pickup in enumerate(pickups, 1):
            lines.append(f"### {i}. {pickup['title']}")
            lines.append(f"**ファイル**: `{pickup['file_path']}`")
            if pickup.get("category"):
                lines.append(f"**カテゴリ**: {pickup['category']}")
            if pickup.get("summary"):
                lines.append(f"**サマリー**: {pickup['summary']}")
            if pickup.get("tags"):
                tags_str = ", ".join([f"`{tag}`" for tag in pickup["tags"]])
                lines.append(f"**タグ**: {tags_str}")
            lines.append("")
    else:
        lines.append("ピックアップ記事がありません。")
        lines.append("")

    # MOC候補
    lines.append("## 📚 MOC候補")
    lines.append("")
    if moc_candidates:
        lines.append(f"**{len(moc_candidates)}件** のMOC候補が見つかりました:")
        lines.append("")
        for i, candidate in enumerate(moc_candidates[:10], 1):  # 最大10件まで表示
            candidate_type = candidate["type"]
            candidate_name = candidate["name"]
            article_count = candidate["count"]
            lines.append(f"### {i}. {candidate_name} ({candidate_type})")
            lines.append(f"**記事数**: {article_count}件")
            lines.append("")
            lines.append("**記事一覧**:")
            for article in candidate["articles"][:5]:  # 最大5件まで表示
                lines.append(f"- [{article['title']}]({article['file_path']})")
            if len(candidate["articles"]) > 5:
                lines.append(f"*他 {len(candidate['articles']) - 5}件の記事があります*")
            lines.append("")
        if len(moc_candidates) > 10:
            lines.append(f"*他 {len(moc_candidates) - 10}件のMOC候補があります*")
            lines.append("")
    else:
        lines.append("MOC候補は見つかりませんでした。")
        lines.append("")

    # フッター
    lines.append("---")
    lines.append("")
    lines.append("*このレポートは ObsidianConscierge によって自動生成されました。*")

    return "\n".join(lines)


def format_html_report(
    date: datetime,
    stats: dict,
    duplicates: list,
    pickups: list,
    moc_candidates: list,
) -> str:
    """
    HTML形式のレポートを生成する

    Args:
        date: レポート日付
        stats: 執筆統計
        duplicates: 重複ペアのリスト
        pickups: ランダムピックアップ記事のリスト
        moc_candidates: MOC候補のリスト

    Returns:
        str: HTML形式のレポート
    """
    html_lines: list[str] = []

    html_lines.append("<!DOCTYPE html>")
    html_lines.append("<html lang='ja'>")
    html_lines.append("<head>")
    html_lines.append("    <meta charset='UTF-8'>")
    html_lines.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html_lines.append(f"    <title>デイリーレポート - {date.strftime('%Y年%m月%d日')}</title>")
    html_lines.append("    <style>")
    html_lines.append("        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }")
    html_lines.append("        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }")
    html_lines.append("        h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }")
    html_lines.append("        h3 { color: #555; }")
    html_lines.append("        ul { line-height: 1.8; }")
    html_lines.append("        code { background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; }")
    html_lines.append("        .stats { background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }")
    html_lines.append("        .warning { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107; }")
    html_lines.append("        .pickup { background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 15px 0; }")
    html_lines.append("        .moc { background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0; }")
    html_lines.append("    </style>")
    html_lines.append("</head>")
    html_lines.append("<body>")

    # ヘッダー
    html_lines.append(f"    <h1>デイリーレポート - {date.strftime('%Y年%m月%d日')}</h1>")
    html_lines.append(f"    <p>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")

    # 執筆統計
    html_lines.append("    <h2>📊 執筆統計</h2>")
    html_lines.append("    <div class='stats'>")
    html_lines.append("        <ul>")
    html_lines.append(f"            <li><strong>新規記事数</strong>: {stats['new_count']}件</li>")
    html_lines.append(f"            <li><strong>更新記事数</strong>: {stats['updated_count']}件</li>")
    html_lines.append(f"            <li><strong>総文字数</strong>: {stats['total_word_count']:,}文字</li>")
    html_lines.append(f"            <li><strong>総記事数</strong>: {stats['total_articles']}件</li>")
    html_lines.append("        </ul>")
    html_lines.append("    </div>")

    # 重複検知警告
    html_lines.append("    <h2>⚠️ 重複検知警告</h2>")
    if duplicates:
        html_lines.append("    <div class='warning'>")
        html_lines.append(f"        <p>類似度80%以上の記事ペアが <strong>{len(duplicates)}組</strong> 見つかりました:</p>")
        for i, dup in enumerate(duplicates[:10], 1):
            article1 = dup["article1"]
            article2 = dup["article2"]
            similarity = dup["similarity"]
            html_lines.append(f"        <h3>{i}. 類似度: {similarity:.1%}</h3>")
            html_lines.append("        <ul>")
            html_lines.append(f"            <li><strong>{article1['title']}</strong> (<code>{article1['file_path']}</code>)</li>")
            html_lines.append(f"            <li><strong>{article2['title']}</strong> (<code>{article2['file_path']}</code>)</li>")
            html_lines.append("        </ul>")
        if len(duplicates) > 10:
            html_lines.append(f"        <p><em>他 {len(duplicates) - 10}組の重複ペアがあります</em></p>")
        html_lines.append("    </div>")
    else:
        html_lines.append("    <p>重複記事は見つかりませんでした。✅</p>")

    # ランダムピックアップ
    html_lines.append("    <h2>🎲 ランダムピックアップ</h2>")
    if pickups:
        for i, pickup in enumerate(pickups, 1):
            html_lines.append("    <div class='pickup'>")
            html_lines.append(f"        <h3>{i}. {pickup['title']}</h3>")
            html_lines.append(f"        <p><strong>ファイル</strong>: <code>{pickup['file_path']}</code></p>")
            if pickup.get("category"):
                html_lines.append(f"        <p><strong>カテゴリ</strong>: {pickup['category']}</p>")
            if pickup.get("summary"):
                html_lines.append(f"        <p><strong>サマリー</strong>: {pickup['summary']}</p>")
            if pickup.get("tags"):
                tags_str = ", ".join([f"<code>{tag}</code>" for tag in pickup["tags"]])
                html_lines.append(f"        <p><strong>タグ</strong>: {tags_str}</p>")
            html_lines.append("    </div>")
    else:
        html_lines.append("    <p>ピックアップ記事がありません。</p>")

    # MOC候補
    html_lines.append("    <h2>📚 MOC候補</h2>")
    if moc_candidates:
        html_lines.append(f"    <p><strong>{len(moc_candidates)}件</strong> のMOC候補が見つかりました:</p>")
        for i, candidate in enumerate(moc_candidates[:10], 1):
            candidate_type = candidate["type"]
            candidate_name = candidate["name"]
            article_count = candidate["count"]
            html_lines.append("    <div class='moc'>")
            html_lines.append(f"        <h3>{i}. {candidate_name} ({candidate_type})</h3>")
            html_lines.append(f"        <p><strong>記事数</strong>: {article_count}件</p>")
            html_lines.append("        <p><strong>記事一覧</strong>:</p>")
            html_lines.append("        <ul>")
            for article in candidate["articles"][:5]:
                html_lines.append(f"            <li><a href='{article['file_path']}'>{article['title']}</a></li>")
            html_lines.append("        </ul>")
            if len(candidate["articles"]) > 5:
                html_lines.append(f"        <p><em>他 {len(candidate['articles']) - 5}件の記事があります</em></p>")
            html_lines.append("    </div>")
        if len(moc_candidates) > 10:
            html_lines.append(f"    <p><em>他 {len(moc_candidates) - 10}件のMOC候補があります</em></p>")
    else:
        html_lines.append("    <p>MOC候補は見つかりませんでした。</p>")

    # フッター
    html_lines.append("    <hr>")
    html_lines.append("    <p><em>このレポートは ObsidianConscierge によって自動生成されました。</em></p>")
    html_lines.append("</body>")
    html_lines.append("</html>")

    return "\n".join(html_lines)


@click.command()
@click.option(
    "--date",
    "-d",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="レポート対象日（YYYY-MM-DD形式、デフォルト: 昨日）",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=Path("reports/daily"),
    help="出力ディレクトリ（デフォルト: reports/daily）",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "html", "both"], case_sensitive=False),
    default="markdown",
    help="出力形式（markdown, html, both）",
)
@click.option(
    "--duplicate-threshold",
    type=float,
    default=None,
    help="重複検知の閾値（0.0-1.0、デフォルト: 設定値を使用）",
)
def main(
    date: datetime | None,
    output_dir: Path,
    format: str,
    duplicate_threshold: float | None,
) -> None:
    """
    ObsidianConscierge デイリーレポート生成ツール

    例:
        python scripts/daily_report.py
        python scripts/daily_report.py -d 2024-01-15 -f both
        python scripts/daily_report.py -o ./custom_reports -f html
    """
    # 設定を読み込む
    settings = get_settings()

    # レポート対象日を決定（デフォルトは昨日）
    if date is None:
        date = datetime.now() - timedelta(days=1)
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)

    # サービスを初期化
    vector_db_service = VectorDBService(db_path=settings.get_chroma_db_path())
    analysis_service = AnalysisService(
        vector_db_service=vector_db_service,
        settings=settings,
    )

    click.echo(f"📊 デイリーレポートを生成中... (対象日: {date.strftime('%Y-%m-%d')})")

    # 執筆統計を取得
    click.echo("  - 執筆統計を取得中...")
    stats = analysis_service.get_writing_statistics(since_date=date)

    # 重複検知
    click.echo("  - 重複記事を検知中...")
    duplicates = analysis_service.detect_duplicates(threshold=duplicate_threshold)

    # ランダムピックアップ
    click.echo("  - ランダムピックアップを取得中...")
    pickups = analysis_service.get_random_pickups(count=3, prefer_different_categories=True)

    # MOC候補
    click.echo("  - MOC候補を抽出中...")
    moc_candidates = analysis_service.find_moc_candidates(min_articles=3)

    # 出力ディレクトリを作成
    output_dir.mkdir(parents=True, exist_ok=True)

    # ファイル名を生成
    date_str = date.strftime("%Y-%m-%d")

    # Markdown形式で出力
    if format.lower() in ("markdown", "both"):
        markdown_content = format_markdown_report(
            date=date,
            stats=stats,
            duplicates=duplicates,
            pickups=pickups,
            moc_candidates=moc_candidates,
        )
        markdown_path = output_dir / f"{date_str}.md"
        markdown_path.write_text(markdown_content, encoding="utf-8")
        click.echo(f"✅ Markdownレポートを保存しました: {markdown_path}")

    # HTML形式で出力
    if format.lower() in ("html", "both"):
        html_content = format_html_report(
            date=date,
            stats=stats,
            duplicates=duplicates,
            pickups=pickups,
            moc_candidates=moc_candidates,
        )
        html_path = output_dir / f"{date_str}.html"
        html_path.write_text(html_content, encoding="utf-8")
        click.echo(f"✅ HTMLレポートを保存しました: {html_path}")

    click.echo("\n🎉 デイリーレポートの生成が完了しました！")


if __name__ == "__main__":
    main()
