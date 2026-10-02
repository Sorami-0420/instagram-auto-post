from __future__ import annotations

import json
from dataclasses import dataclass

import gspread
from google.oauth2.service_account import Credentials

import sheets_retry

sheets_retry.install()

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

# YouTube用の文章生成に使う列。3つすべてがシートにあるときだけ機能する(なければ何もしない)
COL_PRODUCT_NAME = "商品名"
COL_YT_TITLE = "YouTubeタイトル"
COL_YT_DESCRIPTION = "YouTube説明文"
YOUTUBE_COLUMNS = [COL_PRODUCT_NAME, COL_YT_TITLE, COL_YT_DESCRIPTION]

# YouTubeタイトル欄がこの接頭辞で始まる行は、商品名を直したあとで自動的に再生成される
RETRY_PREFIX = "[要確認]"


@dataclass
class StoryRow:
    row_number: int
    scheduled_at: str
    video_filename: str
    status: str


@dataclass
class YoutubeTextTask:
    row_number: int
    product_name: str


class StorySheetsClient:
    def __init__(self, service_account_json: str, spreadsheet_id: str, sheet_name: str):
        info = json.loads(service_account_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        client = gspread.authorize(creds)
        self._worksheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        self._header = self._worksheet.row_values(1)
        self._col_index = self._build_column_index()
        self.has_youtube_columns = all(name in self._header for name in YOUTUBE_COLUMNS)
        if self.has_youtube_columns:
            self._col_index.update({name: self._header.index(name) + 1 for name in YOUTUBE_COLUMNS})

    def _build_column_index(self) -> dict[str, int]:
        missing = [name for name in REQUIRED_COLUMNS if name not in self._header]
        if missing:
            raise ValueError(
                "ストーリー用シートの1行目に必要な列が見つかりません: " + ", ".join(missing)
            )
        return {name: self._header.index(name) + 1 for name in REQUIRED_COLUMNS}

    def load_youtube_text_tasks(self, limit: int) -> list[YoutubeTextTask]:
        """商品名が入っていて、YouTubeタイトルが空欄(または[要確認])の行を最大limit件返す。"""
        if not self.has_youtube_columns:
            return []

        all_values = self._worksheet.get_all_values()
        tasks: list[YoutubeTextTask] = []

        for i, values in enumerate(all_values[1:], start=2):

            def get(col: str) -> str:
                idx = self._col_index[col] - 1
                return values[idx].strip() if idx < len(values) else ""

            product_name = get(COL_PRODUCT_NAME)
            title = get(COL_YT_TITLE)
            if product_name and (not title or title.startswith(RETRY_PREFIX)):
                tasks.append(YoutubeTextTask(row_number=i, product_name=product_name))
                if len(tasks) >= limit:
                    break
        return tasks

    def write_youtube_text(self, row_number: int, title: str, description: str) -> None:
        self._update(row_number, {COL_YT_TITLE: title, COL_YT_DESCRIPTION: description})

    def write_youtube_note(self, row_number: int, message: str) -> None:
        """生成できなかった理由をタイトル欄に残す(説明文欄は空にする)。"""
        self._update(row_number, {COL_YT_TITLE: message, COL_YT_DESCRIPTION: ""})

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
