from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic
from dateutil import parser as dateparser

from caption_generator import generate_caption
from config import Config, ConfigError
from instagram_client import InstagramPostError, publish_feed_post, publish_story_video
from sheets_client import PostRow, SheetsClient
from story_sheets_client import StoryRow, StorySheetsClient

JST = ZoneInfo("Asia/Tokyo")
REPO_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = REPO_ROOT / "posts"
STORIES_DIR = REPO_ROOT / "stories"


def now_jst() -> datetime:
    return datetime.now(JST)


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = dateparser.parse(value)
    except (ValueError, OverflowError):
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JST)
    return parsed


def is_due(row: PostRow | StoryRow, now: datetime) -> bool:
    """投稿予定日時が現在時刻を過ぎているかどうか。日時が読めない行はスキップする。"""
    scheduled = parse_datetime(row.scheduled_at)
    return scheduled is not None and scheduled <= now


def run_feed(config: Config, claude: anthropic.Anthropic, now: datetime) -> tuple[int, list[str]]:
    """フィード投稿を処理する。戻り値は (終了コード, 処理した行の投稿日時の一覧)。"""
    sheets = SheetsClient(config.google_service_account_json, config.spreadsheet_id, config.sheet_name)
    processed_scheduled_at = sheets.list_all_scheduled_at()

    rows = sheets.load_pending_rows()
    due_rows = [row for row in rows if is_due(row, now)]

    print(f"[フィード] 未処理行: {len(rows)}件 / 投稿日時到達: {len(due_rows)}件 / TEST_MODE={config.test_mode}")

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

    return exit_code, processed_scheduled_at


def run_stories(config: Config, feed_scheduled_at: list[str], now: datetime) -> int:
    """ストーリー投稿を処理する。フィード投稿と同じ日に予定されている行はスキップする。"""
    stories = StorySheetsClient(
        config.google_service_account_json, config.spreadsheet_id, config.story_sheet_name
    )

    feed_dates = {
        parsed.date() for parsed in (parse_datetime(value) for value in feed_scheduled_at) if parsed
    }

    rows = stories.load_pending_rows()
    due_rows = [row for row in rows if is_due(row, now)]

    print(f"[ストーリー] 未処理行: {len(rows)}件 / 投稿日時到達: {len(due_rows)}件 / TEST_MODE={config.test_mode}")

    exit_code = 0
    for row in due_rows:
        checked_at = now_jst().strftime("%Y-%m-%d %H:%M:%S")
        scheduled = parse_datetime(row.scheduled_at)

        if scheduled and scheduled.date() in feed_dates:
            print(f"[ストーリー 行{row.row_number}] 同じ日にフィード投稿が予定されているためスキップ")
            stories.mark_skipped(row, "同じ日にフィード投稿が予定されているためスキップしました", checked_at)
            continue

        video_path = STORIES_DIR / row.video_filename
        if not video_path.exists():
            print(f"[ストーリー 行{row.row_number}] 動画ファイルが見つかりません: {row.video_filename}", file=sys.stderr)
            stories.mark_error(row, f"動画ファイルが見つかりません: {row.video_filename}", checked_at)
            exit_code = 1
            continue

        if config.test_mode:
            print(f"[ストーリー 行{row.row_number}] (テストモード) 動画: {row.video_filename}")
            stories.mark_test_preview(row, checked_at)
            continue

        video_url = f"{config.video_base_url}/{row.video_filename}"
        try:
            media_id = publish_story_video(
                ig_user_id=config.ig_user_id,
                access_token=config.ig_access_token,
                video_url=video_url,
            )
        except InstagramPostError as exc:
            print(f"[ストーリー 行{row.row_number}] Instagram投稿エラー: {exc}", file=sys.stderr)
            stories.mark_error(row, f"Instagram投稿エラー: {exc}", checked_at)
            exit_code = 1
            continue

        print(f"[ストーリー 行{row.row_number}] 投稿完了 media_id={media_id}")
        stories.mark_posted(row, checked_at)

    return exit_code


def run() -> int:
    config = Config.load()
    claude = anthropic.Anthropic(api_key=config.anthropic_api_key)
    now = now_jst()

    feed_exit_code, feed_scheduled_at = run_feed(config, claude, now)
    story_exit_code = run_stories(config, feed_scheduled_at, now)

    return feed_exit_code or story_exit_code


if __name__ == "__main__":
    try:
        sys.exit(run())
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        sys.exit(1)
