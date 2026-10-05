from __future__ import annotations

import base64
import re
import unicodedata

import anthropic

from caption_generator import ensure_sentence_periods, guess_media_type

SYSTEM_PROMPT = """\
あなたは天然石のハンドメイドピアスを制作している作家のSNS担当です。
X(旧Twitter)に、商品写真に添える短い投稿文を書いてください。

# 文体・トーン
- やさしく丁寧で、温かみのある言葉づかい。一人称が必要なら「わたし」
- 押しつけがましい宣伝口調にしない
- 読点「、」は使わない
- 句点「。」は各文の文末につける。ただし顔文字をつける文だけは句点をつけず、文の直後に顔文字を続ける
- 文末は「です」「ます」「ました」「そうです」などの、やさしい丁寧語で終える。
  体言止め(「〜を使用。」「〜な一片。」のような名詞や言い切りで終わる文)は使わない
- 絵文字(emoji)は使わない。顔文字は1箇所まで、次から選ぶ: ･*+ / ✳︎
  「(^^)」と「･:*+.\\(( °ω° ))/.:+」は使わない
- 「かたわら」「一粒」という言葉は使わない
- 添付された商品写真を実際によく見て、その雰囲気に合う内容にする
- 場所の種類(公園・海・川・山道・街・庭など)を断定して書かない。写真から確信できないからである。
  書いてよいのは、写真にはっきり写っているもの(木々・緑・落ち葉・光・石の台・水面など)の描写だけ

# アカウントのコンセプト
- このアカウントは「耳とピアス図鑑」。写真に写っている耳は「フォロワーさんの耳」を表している。
  初めて見る人にも、自分がつけている姿を想像してもらうことが狙い
- 本文の1文目に、必ず「フォロワーさんの耳」という言葉をそのまま入れる(下の「本文」の構成参照)
  (例:「フォロワーさんの耳でそっと揺れます」「フォロワーさんの耳に寄り添うピアスです」)
- 新しい文は足さない。今ある文の中に自然に溶かし込み、文の数と長さは今のままにする

# 厳守事項
- 石の効果・意味・言い伝えは書かない(断定する危険を避けるため、書かない)
- 販売しているのは両耳用のピアス(2個で1ペア)。単品であるかのように書かない
- 「太陽と月」はブランド全体のテーマであり、この商品のモチーフではない。
  「太陽」「月」「三日月」などのモチーフは、商品名または写真から実際に読み取れる場合だけ書く
- 石の名前や鉱物名は、**本文には書かず、ハッシュタグにだけ使う**。使うのは、入力された「使用石」「内包物」にあるものだけ。内包物が空欄なら鉱物名を創作しない
  (ただし**商品名は例外**。商品名に石の名前が入っていても、商品名は一字も変えず、省かずに、そのまま本文に入れる)

# 本文(合計で全角90文字以内。この順番で2〜3文)
1. 1文目は、「フォロワーさんの耳と〇〇へ行ってきました」という旅の記録の形にする
   (〇〇には「撮影場所」に書かれた言葉をそのまま入れる。書かれていない場所の名前は、足さない)
   - 〇〇のあとの助詞と動詞は、その言葉に合わせて自然な日本語にする。
     場所の名前(公園・川辺・城下町など)なら「へ」「で」「を」が使える。
     「秋を感じられる場所」のように場所の名前ではない説明的な言葉のときは、「〇〇でひと休みしてきました」
     「〇〇をお散歩してきました」のように、「〇〇へ」が不自然にならない形にする
   - 「撮影場所」が未指定のときは、場所の名前を書かない。写真にはっきり写っているものだけを使い、
     「フォロワーさんの耳と△△の中でひと休みしてきました」の形で書く(△△は写っているもの)
   - 毎回「行ってきました」で終えず、「お散歩してきました」「ひと休みしてきました」などの言い方を変える
   - 写真の雰囲気(光・緑・色)が伝わる言葉を、1文目の中に添えてよい
2. 商品名(**入力された商品名を、一字も変えず、省かずに、そのまま書く**。「このピアス」などに言い換えない)と、写真に写っているデザインやモチーフの紹介を1文(例:「〇〇は△△が揺れるピアスです」。△△は写真から読み取れる形や特徴。石の名前は書かない)
   - △△は、写真ではっきり見分けられる形・色・質感だけを書く。羽根・三日月・太陽・葉・しずくなどの具体的な形は、
     写真で確実に見分けられるときか、商品名に書かれているときだけ使う
   - 素材の名前(銀・金・真鍮・ステンレスなど)は書かない。見た目だけでは素材を判断できないからである。
     「ワイヤー」「金色の三日月」のように、形と色だけで書く
   - 写真にある小さな粒を、実・しずく・花びらなどに見立てて書かない。石の粒は「小さな石」のように書く
   - 石の色の名前(赤・オレンジ・青など)は書かない。1つの石に複数の色が混ざっていたり、光で色が違って見えたりして、
     色名を決めると事実と違うことがあるからである。色に触れたいときは、「あたたかな色合いの石」「深い色合いの石」
     「澄んだ色合いの石」のように、色名を使わない言い方にする
   - 形に自信がないときは、形を断定せず、「やさしい色合いが揺れるピアスです」「光を受けてきらめくピアスです」のように、
     色・光・揺れ方などの確実なことだけを書く
3. (入れる場合)どんな服装や気分に合うかを、さりげなく提案する1文
- どの行も28文字以内。文ごとに改行して、文と文の間に空白行を1行入れる
- URLは本文に含めない(あとから自動で付ける)

# ハッシュタグ
- 全体で最大3個。**石の名前を最優先**で、使用石のうち主なものを最大2個ハッシュタグにする(例: 使用石が「ガーネット」なら「#ガーネット」。石の名前に「ピアス」などは付け足さず、そのままの名前にする)
- 3個目は、余裕があるときだけ、「#ハンドメイドアクセサリー」などの汎用のタグか、商品名のタグにする
- 使用石に括弧書きがあるとき(例:「フローライト（蛍石）」)は、括弧の中を除いた名前にする。ハッシュタグには空白や記号を含めない
- 「#」を付けて、半角スペースで区切る

# 出力形式(厳守。これ以外の文字は出力しない)
[本文]
(本文)
[ハッシュタグ]
(ハッシュタグ)
"""

MAX_ATTEMPTS = 3
URL_WEIGHT = 23
MAX_WEIGHT = 280
_NARROW_RANGES = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
_URL_PATTERN = re.compile(r"https?://\S+")


def weighted_length(text: str) -> int:
    """Xの文字数の数え方: URLは一律23、半角の英数字などは1、日本語など全角は2として数える。"""
    total = 0
    cursor = 0
    for match in _URL_PATTERN.finditer(text):
        total += _plain_weight(text[cursor : match.start()]) + URL_WEIGHT
        cursor = match.end()
    return total + _plain_weight(text[cursor:])


def _plain_weight(text: str) -> int:
    return sum(
        1 if any(low <= ord(ch) <= high for low, high in _NARROW_RANGES) else 2 for ch in text
    )


def generate_x_text(
    client: anthropic.Anthropic,
    *,
    product_name: str,
    stone: str,
    inclusion: str,
    location: str = "",
    base_url: str,
    image_bytes: bytes,
    image_filename: str,
    model: str = "claude-sonnet-5",
) -> str:
    """Xに投稿する文章全体(本文 + URL + ハッシュタグ)を返す。"""
    inclusion_line = f"内包物: {inclusion}" if inclusion else "内包物: (不明・指定なし。鉱物名を創作しないこと)"
    location_line = (
        f"撮影場所: {location}"
        if location
        else "撮影場所: (未指定。場所の名前は書かず、写真に写っているものの描写だけにすること)"
    )
    user_prompt = (
        f"商品名: {product_name}\n"
        f"使用石: {stone}\n"
        f"{inclusion_line}\n"
        f"{location_line}\n\n"
        "添付した商品写真をよく見た上で、Xの投稿文を作成してください。"
    )
    name = unicodedata.normalize("NFC", product_name)
    for attempt in range(MAX_ATTEMPTS):
        response = client.messages.create(
            model=model,
            max_tokens=8000,
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
                                "data": base64.standard_b64encode(image_bytes).decode("utf-8"),
                            },
                        },
                        {"type": "text", "text": user_prompt},
                    ],
                }
            ],
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        body, hashtags = _parse(text, response.stop_reason)
        # 商品名が本文に入っていることを機械的に確認する(AIが言い換えて省くことがあるため)
        if name in unicodedata.normalize("NFC", body):
            return assemble(ensure_sentence_periods(body), base_url, hashtags)
        print(f"商品名が本文に入っていないため、作り直します(試行{attempt + 1}/{MAX_ATTEMPTS})")
    raise ValueError(f"商品名「{product_name}」が本文に入りませんでした")


def _parse(text: str, stop_reason: str | None) -> tuple[str, str]:
    body_marker, tag_marker = "[本文]", "[ハッシュタグ]"
    if body_marker not in text or tag_marker not in text:
        raise ValueError(f"出力の形式が想定と違いました(stop_reason={stop_reason})")
    body, hashtags = text.split(body_marker, 1)[1].split(tag_marker, 1)
    body, hashtags = body.strip(), hashtags.strip()
    if not body:
        raise ValueError(f"本文が空でした(stop_reason={stop_reason})")
    return body, hashtags


def assemble(body: str, url: str, hashtags: str) -> str:
    """本文・URL・ハッシュタグを、空白行をはさんで並べ、Xの上限(280)を超えていないか確認する。"""
    parts = [body]
    if url:
        parts.append(url)
    if hashtags:
        parts.append(hashtags)
    text = "\n\n".join(parts)
    weight = weighted_length(text)
    if weight > MAX_WEIGHT:
        raise ValueError(f"Xの文字数の上限を超えました({weight}/{MAX_WEIGHT})")
    return text
