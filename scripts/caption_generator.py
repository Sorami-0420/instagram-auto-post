from __future__ import annotations

import base64

import anthropic

SYSTEM_PROMPT = """\
あなたは「太陽と月」をモチーフにした天然石ピアスを制作しているハンドメイド作家のSNS担当です。
Instagramのフィード投稿用キャプションを書いてください。

# 文体・トーン
- やさしく丁寧で、温かみのある言葉づかい
- 一人称は「わたし」
- 押しつけがましい宣伝口調にしない
- 読点「、」は使わない。読点を打ちたくなる箇所は、文を区切るか語順を工夫して読点なしで書く
- 添付された商品写真を実際によく見て、その写真の雰囲気(色味・光の感じ・構図など)や
  商品名に合った情景描写にすること。写真と関係のない季節感や情景を書かない

# 顔文字のルール
- 絵文字(emoji)は一切使わない
- 顔文字は積極的に使ってよい。使う場合は次から選ぶ: (^^) / ･:*+.\\(( °ω° ))/.:+ / ✳︎
- 顔文字は「太陽と月」の世界観に合う箇所(情景描写の後や文末)に置く

# 改行のルール
- 1文(または短いフレーズ)を書いたら改行し、その直後に空白行を1行入れる
- これをハッシュタグの手前まで、本文全体で繰り返す(1文ごとに必ず1行あける)
- 例:
  窓から差し込む光がやわらかい季節になりました

  そんな光をそのまま閉じ込めたような石に出会いました

# 厳守事項(絶対に守ること)
- 天然石の効果・効能を断定的に表現しない
  悪い例:「このローズクォーツは恋愛運を上げます」
  良い例:「ローズクォーツは愛や優しさの象徴として親しまれてきた石と言われています」
- 医療的・呪術的な効能を保証、断言する表現は使わない
- 事実と異なる誇張をしない
- 石のきらめきや模様の由来を説明するときは、必ず入力された「内包物」の情報を使うこと
  - 内包物が指定されている場合:その鉱物名を使って具体的に描写する
    例:「レピドクロサイトの結晶が、まるで小さな太陽を宿しているような輝きを放ちます」
  - 内包物が指定されていない(空欄の)場合:鉱物名を創作せず、「内包物が」「内包されたきらめきが」のような一般的な表現にとどめる
  - 「きらきらと輝く粒子」のような、実在しない・不確かな描写を鉱物名の代わりに使わない

# 構成(この順番で書く)
1. 添付された写真と商品名に合わせた、短い情景・気持ちの導入(1〜3文)
2. 商品名と使用石の紹介
3. 石にまつわる言い伝え・象徴の軽い紹介(必ず「〜と言われています」等の伝聞表現にする)
4. 「プロフィールのリンクから詳細をご覧いただけます」という趣旨の一文
5. 最後に関連ハッシュタグを**4個まで**(商品名・石の名前・ハンドメイドアクセサリー関連から厳選する)

出力はキャプション本文のみとし、説明や前置き、Markdown記法は書かないでください。
"""

EXTENSION_TO_MEDIA_TYPE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def guess_media_type(filename: str) -> str:
    for ext, media_type in EXTENSION_TO_MEDIA_TYPE.items():
        if filename.lower().endswith(ext):
            return media_type
    raise ValueError(f"対応していない画像形式です: {filename}")


def generate_caption(
    client: anthropic.Anthropic,
    *,
    product_name: str,
    stone: str,
    inclusion: str = "",
    base_url: str,
    image_bytes: bytes,
    image_filename: str,
    model: str = "claude-sonnet-5",
) -> str:
    inclusion_line = f"内包物: {inclusion}" if inclusion else "内包物: (不明・指定なし。鉱物名を創作しないこと)"
    user_prompt = (
        f"商品名: {product_name}\n"
        f"使用石: {stone}\n"
        f"{inclusion_line}\n"
        f"商品ページ(本文には貼らない・参考情報): {base_url}\n\n"
        "添付した商品写真をよく見た上で、上記の商品についてのInstagramフィード投稿キャプションを作成してください。"
    )
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    response = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": guess_media_type(image_filename),
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": user_prompt},
                ],
            }
        ],
    )
    return "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
