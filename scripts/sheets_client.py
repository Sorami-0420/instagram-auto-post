from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass

import gspread
from google.oauth2.service_account import Credentials

import sheets_retry

sheets_retry.install()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# スプレッドシートの1行目(ヘッダー)に必要な列名
COL_SCHEDULED_AT = "投稿日時"  # 旧形式(互換用)。新形式は投稿日+投稿時刻
COL_SCHEDULED_DATE = "投稿日"
COL_SCHEDULED_TIME = "投稿時刻"
COL_IMAGE_FILENAME = "画像ファイル名"
COL_PRODUCT_NAME = "商品名"
COL_STONE = "使用石"
COL_INCLUSION = "内包物"
COL_BASE_URL = "BASE商品URL"
COL_PRODUCT_TAG_ID = "商品タグID"
COL_STATUS = "投稿済みフラグ"
COL_RESULT_AT = "投稿日時(実績)"
COL_NOTE = "結果メモ"

REQUIRED_COLUMNS = [
    COL_SCHEDULED_AT,
    COL_SCHEDULED_DATE,
    COL_SCHEDULED_TIME,
    COL_IMAGE_FILENAME,
    COL_PRODUCT_NAME,
    COL_STONE,
    COL_INCLUSION,
    COL_BASE_URL,
    COL_PRODUCT_TAG_ID,
    COL_STATUS,
    COL_RESULT_AT,
    COL_NOTE,
]


# X(旧Twitter)用の投稿文を入れる列。シートにあるときだけ機能する(なければ何もしない)
COL_X_TEXT = "X投稿文"

# 写真を撮った場所を書く列(任意)。AIが写真から場所を勝手に決めつけないために使う
COL_LOCATION = "撮影場所"

# X投稿文の欄がこの接頭辞で始まる行は、原因を直したあとで自動的に再生成される
RETRY_PREFIX = "[要確認]"


@dataclass
class ProductInfo:
    product_name: str
    stone: str
    inclusion: str
    image_filename: str
    location: str = ""


@dataclass
class XTextTask:
    row_number: int
    product_name: str
    stone: str
    inclusion: str
    image_filename: str
    base_url: str
    location: str = ""


@dataclass
class PostRow:
    row_number: int  # スプレッドシート上の行番号(ヘッダーを含む実際の行)
    scheduled_at: str
    image_filename: str
    product_name: str
    stone: str
    inclusion: str  # 内包物の鉱物名(わからない場合は空欄)
    base_url: str
    product_tag_id: str  # Facebookコマースマネージャーの商品ID(わからない場合は空欄でタグなし)
    status: str
    location: str = ""  # 撮影場所(空欄なら場所の名前は書かない)


class SheetsClient:
    def __init__(self, service_account_json: str, spreadsheet_id: str, sheet_name: str):
        info = json.loads(service_account_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        client = gspread.authorize(creds)
        self._worksheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        self._header = self._worksheet.row_values(1)
        self._col_index = self._build_column_index()
        self.has_x_column = COL_X_TEXT in self._header
        for optional in (COL_X_TEXT, COL_LOCATION):
            if optional in self._header:
                self._col_index[optional] = self._header.index(optional) + 1

    def _build_column_index(self) -> dict[str, int]:
        missing = [name for name in REQUIRED_COLUMNS if name not in self._header]
        if missing:
            raise ValueError(
                "スプレッドシートの1行目に必要な列が見つかりません: " + ", ".join(missing)
            )
        return {name: self._header.index(name) + 1 for name in REQUIRED_COLUMNS}

    def load_x_text_tasks(self, limit: int) -> list[XTextTask]:
        """まだInstagramに投稿していない行のうち、X投稿文が空欄(または[要確認])の行を最大limit件返す。"""
        if not self.has_x_column:
            return []

        tasks: list[XTextTask] = []
        for i, values in enumerate(self._worksheet.get_all_values()[1:], start=2):

            def get(col: str) -> str:
                idx = self._col_index[col] - 1
                return values[idx].strip() if idx < len(values) else ""

            x_text = get(COL_X_TEXT)
            if get(COL_STATUS) or (x_text and not x_text.startswith(RETRY_PREFIX)):
                continue
            if not get(COL_PRODUCT_NAME) or not get(COL_IMAGE_FILENAME):
                continue
            tasks.append(
                XTextTask(
                    row_number=i,
                    product_name=get(COL_PRODUCT_NAME),
                    stone=get(COL_STONE),
                    inclusion=get(COL_INCLUSION),
                    image_filename=get(COL_IMAGE_FILENAME),
                    base_url=get(COL_BASE_URL),
                    location=get(COL_LOCATION) if COL_LOCATION in self._col_index else "",
                )
            )
            if len(tasks) >= limit:
                break
        return tasks

    def write_x_text(self, row_number: int, text: str) -> None:
        self._update(row_number, {COL_X_TEXT: text})

    @staticmethod
    def _combine_scheduled_at(get) -> str:
        """投稿日+投稿時刻(新形式)があればそちらを優先し、なければ投稿日時(旧形式)を使う。"""
        date_val = get(COL_SCHEDULED_DATE)
        if date_val:
            return f"{date_val} {get(COL_SCHEDULED_TIME)}".strip()
        return get(COL_SCHEDULED_AT)

    def list_all_scheduled_at(self) -> list[str]:
        """ストーリー投稿との同日判定に使う、全行(投稿済み・エラー含む)の投稿日時の一覧。"""
        all_values = self._worksheet.get_all_values()
        result: list[str] = []
        for values in all_values[1:]:

            def get(col: str) -> str:
                idx = self._col_index[col] - 1
                return values[idx].strip() if idx < len(values) else ""

            scheduled_at = self._combine_scheduled_at(get)
            if scheduled_at:
                result.append(scheduled_at)
        return result

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
                    scheduled_at=self._combine_scheduled_at(get),
                    image_filename=image_filename,
                    product_name=get(COL_PRODUCT_NAME),
                    stone=get(COL_STONE),
                    inclusion=get(COL_INCLUSION),
                    base_url=get(COL_BASE_URL),
                    product_tag_id=get(COL_PRODUCT_TAG_ID),
                    status=status,
                    location=get(COL_LOCATION) if COL_LOCATION in self._col_index else "",
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

    def find_product_info(self, product_name: str) -> ProductInfo | None:
        """商品名(NFC正規化して比較)が一致する行の商品情報を返す。画像ファイル名がある行を優先する。"""
        target = unicodedata.normalize("NFC", product_name.strip())
        matches: list[ProductInfo] = []

        for values in self._worksheet.get_all_values()[1:]:

            def get(col: str) -> str:
                idx = self._col_index[col] - 1
                return values[idx].strip() if idx < len(values) else ""

            if unicodedata.normalize("NFC", get(COL_PRODUCT_NAME)) != target:
                continue
            matches.append(
                ProductInfo(
                    product_name=get(COL_PRODUCT_NAME),
                    stone=get(COL_STONE),
                    inclusion=get(COL_INCLUSION),
                    image_filename=get(COL_IMAGE_FILENAME),
                    location=get(COL_LOCATION) if COL_LOCATION in self._col_index else "",
                )
            )

        if not matches:
            return None
        return next((m for m in matches if m.image_filename), matches[0])

    def fill_image_filename(self, product_name: str, filename: str) -> str:
        """商品名が完全一致し、画像ファイル名が空欄の行に書き込む。

        戻り値: "filled"(書き込んだ) / "not_found"(該当行なし) / "ambiguous"(複数該当)
        """
        all_values = self._worksheet.get_all_values()
        matches: list[int] = []
        target = unicodedata.normalize("NFC", product_name)

        for i, values in enumerate(all_values[1:], start=2):

            def get(col: str) -> str:
                idx = self._col_index[col] - 1
                return values[idx].strip() if idx < len(values) else ""

            sheet_name = unicodedata.normalize("NFC", get(COL_PRODUCT_NAME))
            if sheet_name == target and not get(COL_IMAGE_FILENAME):
                matches.append(i)

        if not matches:
            return "not_found"
        if len(matches) > 1:
            return "ambiguous"

        self._update(matches[0], {COL_IMAGE_FILENAME: filename})
        return "filled"

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
