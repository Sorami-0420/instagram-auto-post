from __future__ import annotations

import json
from dataclasses import dataclass

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

COL_SCHEDULED_AT = "投稿日時"  # 旧形式(互換用)。新形式は投稿日+投稿時刻
COL_SCHEDULED_DATE = "投稿日"
COL_SCHEDULED_TIME = "投稿時刻"
COL_VIDEO_FILENAME = "動画ファイル名"
COL_STATUS = "投稿済みフラグ"
COL_RESULT_AT = "投稿日時(実績)"
COL_NOTE = "結果メモ"

REQUIRED_COLUMNS = [
    COL_SCHEDULED_AT,
    COL_SCHEDULED_DATE,
    COL_SCHEDULED_TIME,
    COL_VIDEO_FILENAME,
    COL_STATUS,
    COL_RESULT_AT,
    COL_NOTE,
]


@dataclass
class StoryRow:
    row_number: int
    scheduled_at: str
    video_filename: str
    status: str


class StorySheetsClient:
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
                "ストーリー用シートの1行目に必要な列が見つかりません: " + ", ".join(missing)
            )
        return {name: self._header.index(name) + 1 for name in REQUIRED_COLUMNS}

    @staticmethod
    def _combine_scheduled_at(get) -> str:
        """投稿日+投稿時刻(新形式)があればそちらを優先し、なければ投稿日時(旧形式)を使う。"""
        date_val = get(COL_SCHEDULED_DATE)
        if date_val:
            return f"{date_val} {get(COL_SCHEDULED_TIME)}".strip()
        return get(COL_SCHEDULED_AT)

    def load_pending_rows(self) -> list[StoryRow]:
        """投稿済みフラグが空欄の行だけを未処理として取得する。"""
        all_values = self._worksheet.get_all_values()
        rows: list[StoryRow] = []

        for i, values in enumerate(all_values[1:], start=2):

            def get(col: str) -> str:
                idx = self._col_index[col] - 1
                return values[idx].strip() if idx < len(values) else ""

            status = get(COL_STATUS)
            if status:
                continue
            video_filename = get(COL_VIDEO_FILENAME)
            if not video_filename:
                continue

            rows.append(
                StoryRow(
                    row_number=i,
                    scheduled_at=self._combine_scheduled_at(get),
                    video_filename=video_filename,
                    status=status,
                )
            )
        return rows

    def fill_video_filename(self, filename: str) -> str:
        """投稿予定日時が入っていて動画ファイル名が空欄の、一番上の行に書き込む。

        戻り値: "filled"(書き込んだ) / "not_found"(該当行なし)
        """
        all_values = self._worksheet.get_all_values()

        for i, values in enumerate(all_values[1:], start=2):

            def get(col: str) -> str:
                idx = self._col_index[col] - 1
                return values[idx].strip() if idx < len(values) else ""

            if self._combine_scheduled_at(get) and not get(COL_VIDEO_FILENAME):
                self._update(i, {COL_VIDEO_FILENAME: filename})
                return "filled"

        return "not_found"

    def mark_posted(self, row: StoryRow, posted_at: str) -> None:
        self._update(
            row.row_number,
            {COL_STATUS: "投稿済み", COL_RESULT_AT: posted_at, COL_NOTE: ""},
        )

    def mark_error(self, row: StoryRow, error_message: str, checked_at: str) -> None:
        self._update(
            row.row_number,
            {COL_STATUS: "エラー", COL_RESULT_AT: checked_at, COL_NOTE: error_message},
        )

    def mark_skipped(self, row: StoryRow, note: str, checked_at: str) -> None:
        self._update(
            row.row_number,
            {COL_STATUS: "スキップ", COL_RESULT_AT: checked_at, COL_NOTE: note},
        )

    def mark_test_preview(self, row: StoryRow, checked_at: str) -> None:
        self._update(
            row.row_number,
            {
                COL_RESULT_AT: checked_at,
                COL_NOTE: "[テストモード確認] 実際には投稿していません",
            },
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
