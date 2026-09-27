from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """設定(環境変数)が不足している/不正なときのエラー。"""


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"環境変数 {name} が設定されていません。")
    return value


@dataclass(frozen=True)
class Config:
    google_service_account_json: str
    spreadsheet_id: str
    sheet_name: str
    anthropic_api_key: str
    ig_user_id: str
    ig_access_token: str
    image_base_url: str
    test_mode: bool

    @classmethod
    def load(cls) -> "Config":
        test_mode_raw = os.environ.get("TEST_MODE", "true").strip().lower()
        test_mode = test_mode_raw not in ("false", "0", "no")

        image_base_url = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
        if not image_base_url:
            repo = os.environ.get("GITHUB_REPOSITORY")
            branch = os.environ.get("IMAGE_BRANCH", "main")
            if repo:
                image_base_url = f"https://raw.githubusercontent.com/{repo}/{branch}/posts"

        if not image_base_url:
            raise ConfigError(
                "画像の公開URLを決定できません。IMAGE_BASE_URL を設定するか、"
                "GitHub Actions上で実行してください。"
            )

        # テストモードではInstagramに投稿しないため、IG関連の認証情報は必須にしない
        ig_user_id = os.environ.get("IG_USER_ID", "")
        ig_access_token = os.environ.get("IG_ACCESS_TOKEN", "")
        if not test_mode:
            ig_user_id = _require("IG_USER_ID")
            ig_access_token = _require("IG_ACCESS_TOKEN")

        return cls(
            google_service_account_json=_require("GOOGLE_SERVICE_ACCOUNT_JSON"),
            spreadsheet_id=_require("SPREADSHEET_ID"),
            sheet_name=os.environ.get("SHEET_NAME", "投稿管理"),
            anthropic_api_key=_require("ANTHROPIC_API_KEY"),
            ig_user_id=ig_user_id,
            ig_access_token=ig_access_token,
            image_base_url=image_base_url,
            test_mode=test_mode,
        )
