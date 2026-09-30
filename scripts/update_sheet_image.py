from __future__ import annotations

import os
import sys
from pathlib import Path

from sheets_client import SheetsClient


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
    if len(sys.argv) != 3:
        print("使い方: update_sheet_image.py <商品名> <画像ファイル名>", file=sys.stderr)
        return 2

    product_name, filename = sys.argv[1], sys.argv[2]

    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")

    service_account_path = repo_root / "service-account.json"
    if not service_account_path.exists():
        print(f"認証情報ファイルが見つかりません: {service_account_path}", file=sys.stderr)
        return 1
    service_account_json = service_account_path.read_text(encoding="utf-8")

    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sheet_name = os.environ.get("SHEET_NAME", "投稿管理")
    if not spreadsheet_id:
        print("SPREADSHEET_ID が設定されていません(.env を確認してください)", file=sys.stderr)
        return 1

    sheets = SheetsClient(service_account_json, spreadsheet_id, sheet_name)
    result = sheets.fill_image_filename(product_name, filename)

    if result == "filled":
        print(f"スプレッドシートに反映しました: 商品名「{product_name}」→ 画像ファイル名「{filename}」")
        return 0
    if result == "not_found":
        print(f"商品名「{product_name}」に一致する未入力の行が見つかりませんでした。手動で入力してください。")
        return 0
    if result == "ambiguous":
        print(f"商品名「{product_name}」に一致する行が複数あり、自動入力できませんでした。手動で入力してください。")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
