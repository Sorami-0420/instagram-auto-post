from __future__ import annotations

import os
import sys
from pathlib import Path

from story_sheets_client import StorySheetsClient


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    if len(sys.argv) != 2:
        print("使い方: update_story_sheet.py <動画ファイル名>", file=sys.stderr)
        return 2

    filename = sys.argv[1]

    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")

    service_account_path = repo_root / "service-account.json"
    if not service_account_path.exists():
        print(f"認証情報ファイルが見つかりません: {service_account_path}", file=sys.stderr)
        return 1
    service_account_json = service_account_path.read_text(encoding="utf-8")

    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sheet_name = os.environ.get("STORY_SHEET_NAME", "ストーリー管理")
    if not spreadsheet_id:
        print("SPREADSHEET_ID が設定されていません(.env を確認してください)", file=sys.stderr)
        return 1

    stories = StorySheetsClient(service_account_json, spreadsheet_id, sheet_name)
    result = stories.fill_video_filename(filename)

    if result == "filled":
        print(f"スプレッドシートに反映しました: 動画ファイル名「{filename}」")
        return 0
    print("投稿日時のみ入力済みで動画ファイル名が空欄の行が見つかりませんでした。手動で入力してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
