from __future__ import annotations

import json
from dataclasses import dataclass

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# スプレッドシートの1行目(ヘッダー)に必要な列名
COL_SCHEDULED_AT = "投稿日時"
COL_IMAGE_FILENAME = "画像ファイル名"
COL_PRODUCT_NAME = "商品名"
COL_STONE = "使用石"
COL_INCLUSION = "内包物"
COL_BASE_URL = "BASE商品URL"
COL_STATUS = "投稿済みフラグ"
COL_RESULT_AT = "投稿日時(実績)"
COL_NOTE = "結果メモ"

REQUIRED_COLUMNS = [
    COL_SCHEDULED_AT,
    COL_IMAGE_FILENAME,
    COL_PRODUCT_NAME,
    COL_STONE,
    COL_INCLUSION,
    COL_BASE_URL,
    COL_STATUS,
    COL_RESULT_AT,
    COL_NOTE,
]


@dataclass
class PostRow:
    row_number: int  # スプレッドシート上の行番号(ヘッダーを含む実際の行)
    scheduled_at: str
    image_filename: str
    product_name: str
    stone: str
    inclusion: str  # 内包物の鉱物名(わからない場合は空欄)
    base_url: str
    status: str


class SheetsClient:
    def __init__(self, service_account_json: str, spreadsheet_id: str, sheet_name: str):
        info = json.loads(service_account_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        client = gspread.authorize(creds)
        self._worksheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        self._header = self._worksheet.row_values(1)
        self._col_index = self._build_column_index()

    def _build_column_index(self) -> dict[str, int]:
        missing = [name for name in REQUIRED_COLUMNS if name not in self._header]
        if missing:
            raise ValueError(
                "スプレッドシートの1行目に必要な列が見つかりません: " + ", ".join(missing)
            )
        return {name: self._header.index(name) + 1 for name in REQUIRED_COLUMNS}

    def load_pending_rows(self) -> list[PostRow]:
        """投稿済みフラグが空欄の行だけを未処理として取得する。"""
        all_values = self._worksheet.get_all_values()
        rows: list[PostRow] = []

        for i, values in enumerate(all_values[1:], start=2):  # 1行目はヘッダー

            def get(col: str) -> str:
                idx = self._col_index[col] - 1
                return values[idx].strip() if idx < len(values) else ""

            status = get(COL_STATUS)
            if status:
                continue  # 投稿済み/エラー済みはスキップ
            image_filename = get(COL_IMAGE_FILENAME)
            if not image_filename:
                continue  # 空行はスキップ

            rows.append(
                PostRow(
                    row_number=i,
                    scheduled_at=get(COL_SCHEDULED_AT),
                    image_filename=image_filename,
                    product_name=get(COL_PRODUCT_NAME),
                    stone=get(COL_STONE),
                    inclusion=get(COL_INCLUSION),
                    base_url=get(COL_BASE_URL),
                    status=status,
                )
            )
        return rows

    def mark_posted(self, row: PostRow, posted_at: str) -> None:
        self._update(
            row.row_number,
            {COL_STATUS: "投稿済み", COL_RESULT_AT: posted_at, COL_NOTE: ""},
        )

    def mark_error(self, row: PostRow, error_message: str, checked_at: str) -> None:
        self._update(
            row.row_number,
            {COL_STATUS: "エラー", COL_RESULT_AT: checked_at, COL_NOTE: error_message},
        )

    def mark_test_preview(self, row: PostRow, caption: str, checked_at: str) -> None:
        """テストモード:フラグは変更せず、生成キャプションだけメモ欄に残す。"""
        self._update(
            row.row_number,
            {COL_RESULT_AT: checked_at, COL_NOTE: f"[テストモード確認] {caption}"},
        )

    def _update(self, row_number: int, values: dict[str, str]) -> None:
        updates = [
            {"range": self._cell(row_number, col), "values": [[val]]}
            for col, val in values.items()
        ]
        if updates:
            self._worksheet.batch_update(updates)

    def _cell(self, row_number: int, col_name: str) -> str:
        col_letter = gspread.utils.rowcol_to_a1(1, self._col_index[col_name]).rstrip("0123456789")
        return f"{col_letter}{row_number}"
