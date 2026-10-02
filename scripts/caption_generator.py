from __future__ import annotations

import base64
import sys

import anthropic

SYSTEM_PROMPT = """\
あなたは「太陽と月」をモチーフにした天然石ピアスを制作しているハンドメイド作家のSNS担当です。
Instagramのフィード投稿用キャプションを書いてください。

# 文体・トーン
- やさしく丁寧で、温かみのある言葉づかい
- 一人称は「わたし」
- 押しつけがましい宣伝口調にしない
- 読点「、」は使わない。読点を打ちたくなる箇所は、文を区切るか語順を工夫して読点なしで書く
- 句点「。」は各文の文末に必ずつける。1つでも句点のない文を作らないこと
  - 例外:その文に顔文字をつける場合だけ、句点をつけない(下記「顔文字のルール」参照)
- 添付された商品写真を実際によく見て、その写真の雰囲気(色味・光の感じ・構図など)や
  商品名に合った情景描写にすること。写真と関係のない季節感や情景を書かない
- 「かたわら」「一粒」という言葉は使わない(石を指すときは「石」「結晶」「輝き」などの言葉を使う)

# 顔文字のルール
- 絵文字(emoji)は一切使わない
- 顔文字は積極的に使ってよい。使う場合は次から選ぶ: ･*+ / ✳︎
  「(^^)」と「･:*+.\\(( °ω° ))/.:+」は使わない
- 顔文字を使う文だけは句点を省略し、文の直後に改行を挟まずそのまま続けて書く
  例:「〜輝きを放ちます✳︎」(この1行で1つの文として扱う)
- 顔文字だけを単独の行にしない。区切りの飾りとしても使わない
- 顔文字を使うのは本文中で1〜2箇所程度にとどめる

# 改行のルール
- 「文の数」と「行の数」は別物である。構成の指示で「1文」と言っていても、
  その1文が長ければ複数行に分けてよい(むしろ分けること)。1文=1行にする必要はない
- 1文が長い場合は、意味の区切れ目(助詞の後・て形の後など、読むときに一息つける場所)で
  区切って改行する。1行は15〜25文字程度を目安にする(短い文は無理に区切らず1行のままでよい)
  この目安を超える行(1行で25文字を大きく超えるもの)を作らないこと
- スマホの画面で1行に収まる上限は28文字。どの行も**28文字を超えてはいけない**(顔文字や句点も1文字に数える)
- **最初の行だけは15文字以内**にする。スマホでは1行目の先頭にアカウント名が表示され、使える幅が狭くなるため。
  最初の文が長い場合は、短い言葉で1行目を終わらせ、残りを2行目に回す
  (例:1行目「緑の小道に」/ 2行目「光がやさしく差し込んでいました✳︎」)
- 改行のたびに、その直後に空白行を1行入れる。これをハッシュタグの手前まで本文全体で繰り返す
- 句点「。」は、区切った行のうち、その文の一番最後の行にだけつける(文の途中の行にはつけない)
- 改行していい場所:助詞の後、て形の後、意味のまとまりの切れ目
- 改行してはいけない場所:単語の途中
- 例(1つの文「水路を流れる水面に光が弾けて小さな粒がいくつも輝いていました」を改行する場合):
  水路を流れる水面に光が弾けて

  小さな粒がいくつも輝いていました。

  そんな煌めきをそのまま石の中に閉じ込めたような

  その石に出会いました✳︎

# 厳守事項(絶対に守ること)
- 天然石の効果・効能を断定的に表現しない
  悪い例:「このローズクォーツは恋愛運を上げます」
  良い例:「ローズクォーツは愛や優しさの象徴として親しまれてきた石と言われています」
- 医療的・呪術的な効能を保証、断言する表現は使わない
- この「断定しない」というルールは、**石の意味・象徴・効果に関する説明にのみ適用する**。
  情景描写や商品デザインの説明など、それ以外の内容は断定的な言い切り表現で書いてよい
  (例:「光が差し込んでいました」「三日月のモチーフに仕上げました」のような言い切りは問題ない)
- 「太陽と月」はブランド全体のテーマであり、この商品のモチーフではない。
  「太陽」「月」「三日月」などのモチーフは、商品名または写真から実際に読み取れる場合だけ書く。
  読み取れなければ触れない(商品名や使用石にない「太陽の石」「月の石」などと書かない)
- 事実と異なる誇張をしない
- 販売している商品は両耳用のピアス(2個で1ペア)。商品(ピアス)自体を「一つ」のように
  単品であるかのように書かない
- 石のきらめきや模様の由来を説明するときは、必ず入力された「内包物」の情報を使うこと
  - 内包物が指定されている場合:その鉱物名を使って具体的に描写する
    例:「レピドクロサイトの結晶が、まるで小さな太陽を宿しているような輝きを放ちます」
  - 内包物が指定されていない(空欄の)場合:鉱物名を創作せず、「内包物が」「内包されたきらめきが」のような一般的な表現にとどめる
  - 「きらきらと輝く粒子」のような、実在しない・不確かな描写を鉱物名の代わりに使わない
- 石の歴史・言い伝え・象徴的な意味を書く前に、必ずweb検索でその石(使用石・内包物)について
  実際の情報を調べること。記憶だけで書かず、検索結果に基づいて書く
  - 検索しても信頼できる情報が見つからない場合、その石特有の言い伝えを創作せず
    「天然石として古くから親しまれてきた」のような一般的な表現にとどめる
  - 検索結果に複数の特徴・効果が出てきても、書くのは**1つだけ**選ぶこと。
    見つかった情報を列挙・羅列しない
    悪い例:「直感力や洞察力を高め自信と決断力を与えて幸運をもたらしてくれると言われています」
    良い例:「直感力を象徴する石と言われています」
  - 使用石と内包物の両方について書こうとせず、どちらか一方(基本的には使用石)に絞る

# 構成(この順番で書く。合計4文で本文を完結させる)
1. 添付された写真と商品名に合わせた、短い情景・気持ちの導入(**1文のみ**)
2. 商品名・使用石の紹介と、石にまつわる言い伝え・象徴の軽い紹介を**1文にまとめる**
   (必ず「〜と言われています」等の伝聞表現にする)
3. どんな場面・シーンで身につけると似合うかを提案する一文(**1文のみ**)
   毎回同じパターンにせず、以下のような切り口から商品や写真の雰囲気に合うものを選ぶ:
   - 行き先・シーン(例:「お出かけの日の胸元をそっと明るくしてくれそうです」)
   - 服装との相性(例:「着物にもよく映えそうです」「シックなお洋服にも合わせやすそうです」)
   - 気分(例:「気分が落ち込んだ日にそっと寄り添ってくれそうです」)
   押しつけがましくならないよう、さりげない提案の形にする
4. 「プロフィールのリンクから詳細をご覧いただけます」という趣旨の一文
5. 最後に関連ハッシュタグを**4個まで**(商品名・石の名前・ハンドメイドアクセサリー関連から厳選する)

# 分量(厳守)
- ハッシュタグを除いた本文は、上記の**合計4文だけ**で構成する。5文以上にしない
- 1文は**40文字前後を目安**にし、だらだらと長くしない。1文に内容を詰め込みすぎない
  (2つのことを言いたい場合は、片方を削るか、思い切って短くまとめること。
  「〜で、〜で、〜です」のように接続を重ねて長くしない)

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
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 3,
            }
        ],
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
    caption = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
    if not caption:
        raise ValueError(
            f"生成されたキャプションが空でした(stop_reason={response.stop_reason})"
        )
    return rewrap_if_needed(client, caption, model)


# スマホで1行に収まる上限。1行目だけは先頭にアカウント名が付くため、さらに短くする
MAX_LINE_LENGTH = 28
FIRST_LINE_MAX_LENGTH = 15

REWRAP_SYSTEM_PROMPT = """\
あなたはInstagramキャプションの改行だけを直す校正者です。
渡されたキャプションについて、文言(文字・句読点・顔文字・ハッシュタグ)は一切変えず、改行の位置だけを直してください。
- 本文の各行は、意味の区切れ目(助詞の後・て形の後など、読むときに一息つける場所)で改行する
- 最初の行は15文字以内、2行目以降は25文字以内にする(顔文字や句点も1文字に数える)
- 単語の途中では改行しない
- 改行のたびに、その直後に空白行を1行入れる(元の形式と同じ)
- 句点「。」と顔文字は、もとの文末の位置のまま動かさない
- ハッシュタグの行は、そのまま変えない
- 出力はキャプション全文のみ。説明や前置きは書かない
"""


def find_long_lines(caption: str, *, first_line_max: int = FIRST_LINE_MAX_LENGTH) -> list[str]:
    """本文のうち長すぎる行を返す(ハッシュタグの行は対象外)。最初の行だけ基準を変えられる。"""
    lines = [line.strip() for line in caption.splitlines() if line.strip()]
    long_lines = []
    for i, line in enumerate(lines):
        if line.startswith("#"):
            continue
        limit = first_line_max if i == 0 else MAX_LINE_LENGTH
        if len(line) > limit:
            long_lines.append(line)
    return long_lines


def same_text(a: str, b: str) -> bool:
    return "".join(a.split()) == "".join(b.split())


def rewrap_if_needed(client: anthropic.Anthropic, caption: str, model: str) -> str:
    """長すぎる行があれば、文言を変えずに改行だけを直す。直せなければ元のまま返す。"""
    long_lines = find_long_lines(caption)
    if not long_lines:
        return caption

    print(f"長すぎる行が{len(long_lines)}件あるため、改行を直します: {long_lines}")
    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            system=REWRAP_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": caption}],
        )
        rewrapped = "".join(b.text for b in response.content if b.type == "text").strip()
    except Exception as exc:  # noqa: BLE001 - 直せなくても投稿自体は止めない
        print(f"改行の修正に失敗したため、元のキャプションを使います: {exc}", file=sys.stderr)
        return caption

    if rewrapped and same_text(caption, rewrapped):
        return rewrapped
    print("改行の修正で文言が変わってしまったため、元のキャプションを使います", file=sys.stderr)
    return caption
