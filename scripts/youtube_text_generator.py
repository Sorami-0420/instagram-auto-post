from __future__ import annotations

import base64

import anthropic

from caption_generator import guess_media_type

SYSTEM_PROMPT = """\
あなたは「太陽と月」をモチーフにした天然石ピアスを制作しているハンドメイド作家のSNS担当です。
YouTubeショート(縦型の短い動画)に付ける「タイトル」と「説明文」を書いてください。

# 文体・トーン
- やさしく丁寧で、温かみのある言葉づかい。一人称は「わたし」
- 押しつけがましい宣伝口調にしない
- 読点「、」は使わない
- 句点「。」は各文の文末につける。ただし顔文字をつける文だけは句点をつけず、文の直後に顔文字を続ける
- 絵文字(emoji)は使わない。顔文字は説明文の中で1箇所まで、次から選ぶ: ･*+ / ✳︎
  「(^^)」と「･:*+.\\(( °ω° ))/.:+」は使わない
- 「かたわら」「一粒」という言葉は使わない
- 添付された商品写真を実際によく見て、その雰囲気に合う内容にする

# 厳守事項
- 天然石の効果・効能を断定しない。石の意味・象徴は「〜と言われています」のような伝聞で書く
  (情景描写やデザインの説明は言い切ってよい)
- 医療的・呪術的な効能を保証する表現は使わない
- 「太陽と月」はブランド全体のテーマであり、この商品のモチーフではない。
  「太陽」「月」「三日月」などのモチーフは、商品名または写真から実際に読み取れる場合だけ書く。
  読み取れなければ触れない(商品名や使用石にない「太陽の石」「月の石」などと書かない)
- 販売しているのは両耳用のピアス(2個で1ペア)。単品であるかのように書かない
- 石の由来や模様の説明には、入力された「内包物」の情報だけを使う。空欄なら鉱物名を創作しない
- 石の歴史・言い伝え・意味を書く前に、必ずweb検索で実際の情報を調べる。記憶だけで書かない。
  信頼できる情報が見つからなければ創作せず、一般的な表現にとどめる。
  検索で複数の特徴が見つかっても、書くのは1つだけにする

# タイトル
- 全角30文字以内。1行で書く。「#」は含めない
- スマホでは冒頭20文字ほどしか見えないため、検索されやすいキーワード(「天然石ピアス」や使用石の名前など)を
  **最初の20文字以内**に入れ、そのあとに商品の雰囲気が伝わる短い言葉を続ける
  (例:「天然石ピアス｜〇〇」「アパタイトのピアス 〇〇」のような形。「｜」か半角スペースで区切る)
- 関係のないキーワードを詰め込まない。商品や動画の内容と合う言葉だけを使う

# 説明文(この順番。ハッシュタグを除いて4文)
1. 写真の雰囲気に合う情景や気持ちを1文
2. 商品名と使用石の紹介を1文(例:「〇〇は△△を使ったピアスです」。石の意味はここに入れない)
3. 石の意味・象徴を、伝聞で1文
4. どんな服装や気分に合うかをさりげなく提案する1文
   - 毎回同じ切り口にせず、次から商品や写真に合うものを選ぶ: 服装との相性(着物・シックな服・ナチュラルな服など) / 気分(落ち込んだ日・頑張りたい日など) / 行き先やシーン
   - 「散歩」「お出かけ」に偏らないこと
- どの文も**40文字以内**にする。だらだらと長くしない。1文に複数の内容を詰め込まない。
  文ごとに改行して、文と文の間に空白行を1行入れる
- 説明文の最後に、空白行をはさんでハッシュタグを3〜4個(商品名・石の名前・ハンドメイドアクセサリー関連から厳選)。
  「#Shorts」は付けない

# 出力形式(厳守。これ以外の文字は出力しない)
[タイトル]
(タイトル)
[説明文]
(説明文)
"""


def generate_youtube_text(
    client: anthropic.Anthropic,
    *,
    product_name: str,
    stone: str,
    inclusion: str,
    image_bytes: bytes,
    image_filename: str,
    model: str = "claude-sonnet-5",
) -> tuple[str, str]:
    """(タイトル, 説明文) を返す。"""
    inclusion_line = f"内包物: {inclusion}" if inclusion else "内包物: (不明・指定なし。鉱物名を創作しないこと)"
    user_prompt = (
        f"商品名: {product_name}\n"
        f"使用石: {stone}\n"
        f"{inclusion_line}\n\n"
        "添付した商品写真をよく見た上で、YouTubeショートのタイトルと説明文を作成してください。"
    )
    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
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
    return _parse(text, response.stop_reason)


def _parse(text: str, stop_reason: str | None) -> tuple[str, str]:
    title_marker, desc_marker = "[タイトル]", "[説明文]"
    if title_marker not in text or desc_marker not in text:
        raise ValueError(f"出力の形式が想定と違いました(stop_reason={stop_reason})")
    after_title = text.split(title_marker, 1)[1]
    title, description = after_title.split(desc_marker, 1)
    title, description = title.strip(), description.strip()
    if not title or not description:
        raise ValueError(f"タイトルまたは説明文が空でした(stop_reason={stop_reason})")
    return title, description
