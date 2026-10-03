from __future__ import annotations

import base64
import sys

import anthropic

from caption_generator import MAX_LINE_LENGTH, find_long_lines, guess_media_type, same_text

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
- 場所の種類(公園・海・川・山道・街・庭など)を断定して書かない。写真から確信できないからである。
  書いてよいのは、写真にはっきり写っているもの(木々・緑・落ち葉・光・石の台・水面など)の描写だけ

# アカウントのコンセプト
- このアカウントは「耳とピアス図鑑」。写真に写っている耳は「フォロワーさんの耳」を表している。
  初めて見る人にも、自分がつけている姿を想像してもらうことが狙い
- 説明文の1文目に、必ず「フォロワーさんの耳」という言葉をそのまま入れる(下の「説明文」の構成参照)
  (例:「フォロワーさんの耳でそっと揺れます」「フォロワーさんの耳に寄り添うピアスです」)
- 新しい文は足さない。今ある文の中に自然に溶かし込み、文の数と長さは今のままにする

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
1. 1文目は、「フォロワーさんの耳と〇〇へ行ってきました」という旅の記録の形にする
   (〇〇には「撮影場所」に書かれた言葉をそのまま入れる。書かれていない場所の名前は、足さない)
   - 「撮影場所」が未指定のときは、場所の名前を書かない。写真にはっきり写っているものだけを使い、
     「フォロワーさんの耳と△△の中でひと休みしてきました」の形で書く(△△は写っているもの)
   - 毎回「行ってきました」で終えず、「お散歩してきました」「ひと休みしてきました」などの言い方を変える
   - 写真の雰囲気(光・緑・色)が伝わる言葉を、1文目の中に添えてよい
2. 商品名と使用石の紹介を1文(例:「〇〇は△△を使ったピアスです」。石の意味はここに入れない)
3. 石の意味・象徴を、伝聞で1文。意味は**1つだけ**選び、「〜を象徴する石と言われています」のように短く書く
   悪い例:「アパタイトの石言葉『調和』は感情と理性のバランスを整え人との関係をスムーズに保つためのサポートをしてくれると言われています」
   良い例:「アパタイトは調和を象徴する石と言われています」
4. どんな服装や気分に合うかをさりげなく提案する1文
   - 毎回同じ切り口にせず、次から商品や写真に合うものを選ぶ: 服装との相性(着物・シックな服・ナチュラルな服など) / 気分(落ち込んだ日・頑張りたい日など) / 行き先やシーン
   - 「散歩」「お出かけ」に偏らないこと
- どの文も短くし、だらだらと長くしない。1文に複数の内容を詰め込まない
- スマホの画面で1行に収まる上限は28文字。**どの行も28文字を超えてはいけない**(顔文字や句点も1文字に数える)。
  1文が28文字を超えるときは、意味の区切れ目(助詞の後・て形の後など)で改行して分ける(単語の途中では切らない。
  句点「。」は文の最後の行にだけつける)
- 文と文の間には空白行を1行入れる。同じ文を分けた行どうしの間には空白行を入れない
- 説明文の最後に、空白行をはさんでハッシュタグを3〜4個(商品名・石の名前・ハンドメイドアクセサリー関連から厳選)。
  「#Shorts」は付けない

# 出力前の確認
- 説明文の各行の文字数を数え、28文字を超える行があれば、意味の区切れ目で改行し直してから出力する

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
    location: str = "",
    image_bytes: bytes,
    image_filename: str,
    model: str = "claude-sonnet-5",
) -> tuple[str, str]:
    """(タイトル, 説明文) を返す。"""
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
    title, description = _parse(text, response.stop_reason)
    return title, rewrap_if_needed(client, description, model)


REWRAP_SYSTEM_PROMPT = """\
あなたはYouTube説明文の改行だけを直す校正者です。
渡された説明文について、文言(文字・句読点・顔文字・ハッシュタグ)は一切変えず、改行の位置だけを直してください。
- どの行も25文字以内にする(顔文字や句点も1文字に数える)。長い文は、意味の区切れ目(助詞の後・て形の後など)で改行して分ける
- 同じ文を分けた行どうしの間には空白行を入れない。文と文の間の空白行は、もとのまま残す
- 単語の途中では改行しない
- ハッシュタグの行は、そのまま変えない
- 出力は説明文の全文のみ。説明や前置きは書かない
"""


def rewrap_if_needed(client: anthropic.Anthropic, description: str, model: str) -> str:
    """28文字を超える行があれば、文言を変えずに改行だけを直す。直せなければ元のまま返す。"""
    long_lines = find_long_lines(description, first_line_max=MAX_LINE_LENGTH)
    if not long_lines:
        return description

    print(f"説明文に長すぎる行が{len(long_lines)}件あるため、改行を直します: {long_lines}")
    try:
        response = client.messages.create(
            model=model,
            max_tokens=8000,
            system=REWRAP_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": description}],
        )
        rewrapped = "".join(b.text for b in response.content if b.type == "text").strip()
    except Exception as exc:  # noqa: BLE001 - 直せなくても文章づくり自体は止めない
        print(f"改行の修正に失敗したため、元の説明文を使います: {exc}", file=sys.stderr)
        return description

    if rewrapped and same_text(description, rewrapped):
        return rewrapped
    print("改行の修正で文言が変わってしまったため、元の説明文を使います", file=sys.stderr)
    return description


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
