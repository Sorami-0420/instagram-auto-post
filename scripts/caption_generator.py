from __future__ import annotations

import anthropic

SYSTEM_PROMPT = """\
あなたは「太陽と月」をモチーフにした天然石ピアスを制作しているハンドメイド作家のSNS担当です。
Instagramのフィード投稿用キャプションを書いてください。

# 文体・トーン
- やさしく、丁寧で、温かみのある言葉づかい
- 一人称は「わたし」
- 押しつけがましい宣伝口調にしない
- 絵文字は控えめに(0〜3個程度)。太陽・月・星・きらきら系を中心に使う

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
1. 作品や石にまつわる短い情景・気持ちの導入(1〜3文)
2. 商品名と使用石の紹介
3. 石にまつわる言い伝え・象徴の軽い紹介(必ず「〜と言われています」等の伝聞表現にする)
4. 「プロフィールのリンクから詳細をご覧いただけます」という趣旨の一文
5. 最後に関連ハッシュタグを**4個まで**(商品名・石の名前・ハンドメイドアクセサリー関連から厳選する)

出力はキャプション本文のみとし、説明や前置き、Markdown記法は書かないでください。
"""


def generate_caption(
    client: anthropic.Anthropic,
    *,
    product_name: str,
    stone: str,
    inclusion: str = "",
    base_url: str,
    model: str = "claude-sonnet-5",
) -> str:
    inclusion_line = f"内包物: {inclusion}" if inclusion else "内包物: (不明・指定なし。鉱物名を創作しないこと)"
    user_prompt = (
        f"商品名: {product_name}\n"
        f"使用石: {stone}\n"
        f"{inclusion_line}\n"
        f"商品ページ(本文には貼らない・参考情報): {base_url}\n\n"
        "上記の商品についてのInstagramフィード投稿キャプションを作成してください。"
    )
    response = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
