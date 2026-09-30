from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic
from dateutil import parser as dateparser

from caption_generator import generate_caption
from config import Config, ConfigError
from instagram_client import InstagramPostError, publish_feed_post
from sheets_client import PostRow, SheetsClient

JST = ZoneInfo("Asia/Tokyo")
POSTS_DIR = Path(__file__).resolve().parent.parent / "posts"


def now_jst() -> datetime:
    return datetime.now(JST)


def is_due(row: PostRow, now: datetime) -> bool:
    """投稿予定日時が現在時刻を過ぎているかどうか。日時が読めない行はスキップする。"""
    if not row.scheduled_at:
        return False
    try:
        scheduled = dateparser.parse(row.scheduled_at)
    except (ValueError, OverflowError):
        return False
    if scheduled is None:
        return False
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=JST)
    return scheduled <= now


def run() -> int:
    config = Config.load()
    sheets = SheetsClient(config.google_service_account_json, config.spreadsheet_id, config.sheet_name)
    claude = anthropic.Anthropic(api_key=config.anthropic_api_key)

    now = now_jst()
    rows = sheets.load_pending_rows()
    due_rows = [row for row in rows if is_due(row, now)]

    print(f"未処理行: {len(rows)}件 / 投稿日時到達: {len(due_rows)}件 / TEST_MODE={config.test_mode}")

    exit_code = 0
    for row in due_rows:
        checked_at = now_jst().strftime("%Y-%m-%d %H:%M:%S")

        image_path = POSTS_DIR / row.image_filename
        try:
            image_bytes = image_path.read_bytes()
        except OSError as exc:
            print(f"[行{row.row_number}] 画像読み込みエラー: {exc}", file=sys.stderr)
            sheets.mark_error(row, f"画像読み込みエラー: {exc}", checked_at)
            exit_code = 1
            continue

        try:
            caption = generate_caption(
                claude,
                product_name=row.product_name,
                stone=row.stone,
                inclusion=row.inclusion,
                base_url=row.base_url,
                image_bytes=image_bytes,
                image_filename=row.image_filename,
            )
        except Exception as exc:  # noqa: BLE001 - どんな失敗でも行にエラーを記録して継続する
            print(f"[行{row.row_number}] キャプション生成エラー: {exc}", file=sys.stderr)
            sheets.mark_error(row, f"キャプション生成エラー: {exc}", checked_at)
            exit_code = 1
            continue

        if config.test_mode:
            tag_note = f" / 商品タグ付き(ID: {row.product_tag_id})" if row.product_tag_id else ""
            print(f"[行{row.row_number}] (テストモード){tag_note} 生成キャプション:\n{caption}\n")
            sheets.mark_test_preview(row, caption, checked_at)
            continue

        image_url = f"{config.image_base_url}/{row.image_filename}"
        try:
            media_id = publish_feed_post(
                ig_user_id=config.ig_user_id,
                access_token=config.ig_access_token,
                image_url=image_url,
                caption=caption,
                product_tag_id=row.product_tag_id,
            )
        except InstagramPostError as exc:
            print(f"[行{row.row_number}] Instagram投稿エラー: {exc}", file=sys.stderr)
            sheets.mark_error(row, f"Instagram投稿エラー: {exc}", checked_at)
            exit_code = 1
            continue

        print(f"[行{row.row_number}] 投稿完了 media_id={media_id}")
        sheets.mark_posted(row, checked_at)

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(run())
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        sys.exit(1)
