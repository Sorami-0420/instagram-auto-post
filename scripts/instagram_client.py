from __future__ import annotations

import time

import requests

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class InstagramPostError(RuntimeError):
    """Instagram Graph APIへの投稿に失敗したときのエラー。"""


def publish_feed_post(*, ig_user_id: str, access_token: str, image_url: str, caption: str) -> str:
    """画像URLとキャプションからフィード投稿を作成し、公開する。戻り値は投稿(media)のID。"""
    creation_id = _create_media_container(ig_user_id, access_token, image_url, caption)
    _wait_until_ready(creation_id, access_token)
    return _publish_container(ig_user_id, access_token, creation_id)


def _create_media_container(ig_user_id: str, access_token: str, image_url: str, caption: str) -> str:
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": access_token},
        timeout=30,
    )
    data = _parse_response(resp)
    return data["id"]


def _wait_until_ready(creation_id: str, access_token: str, timeout_seconds: int = 60) -> None:
    """画像URLの取得・エンコードが完了するまで待つ(Instagram側の非同期処理)。"""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        resp = requests.get(
            f"{GRAPH_API_BASE}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        data = _parse_response(resp)
        status = data.get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise InstagramPostError(f"メディアの準備に失敗しました: {data}")
        time.sleep(3)
    raise InstagramPostError("メディアの準備がタイムアウトしました。")


def _publish_container(ig_user_id: str, access_token: str, creation_id: str) -> str:
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=30,
    )
    data = _parse_response(resp)
    return data["id"]


def _parse_response(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except ValueError as exc:
        raise InstagramPostError(f"Instagram APIの応答を解析できません: {resp.text}") from exc
    if resp.status_code >= 400 or "error" in data:
        raise InstagramPostError(f"Instagram APIエラー: {data.get('error', data)}")
    return data
