from __future__ import annotations

import time

from gspread import http_client
from gspread.exceptions import APIError

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
BASE_DELAY_SECONDS = 5


def install() -> None:
    """Googleスプレッドシートが一時的に使えないとき(503など)は、待ってからやり直す。

    gspreadの通信処理を1か所で包むので、読み取りも書き込みも(どちらも同じ値を何度書いても結果が変わらない)
    すべて対象になる。gspread側に想定の仕組みがなければ何もしない。
    """
    original = getattr(http_client.HTTPClient, "request", None)
    if original is None or getattr(original, "_with_retry", False):
        return

    def request_with_retry(self, *args, **kwargs):
        for attempt in range(MAX_ATTEMPTS):
            try:
                return original(self, *args, **kwargs)
            except APIError as exc:
                status = getattr(exc.response, "status_code", None)
                if status not in RETRYABLE_STATUS or attempt == MAX_ATTEMPTS - 1:
                    raise
                delay = BASE_DELAY_SECONDS * 2**attempt
                print(f"スプレッドシートの通信に失敗しました(status={status})。{delay}秒後にやり直します")
                time.sleep(delay)

    request_with_retry._with_retry = True
    http_client.HTTPClient.request = request_with_retry
