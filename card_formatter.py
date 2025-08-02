from html import escape
from schemas import Card

def render_html(c: Card) -> str:
    parts = [f"<b>🌿 {escape(c.title)}</b>", escape(c.summary)]

    for block in c.blocks:
        parts.append(f"• {escape(block)}")

    if c.tips:
        tips_html = "\n".join(f"◦ {escape(tip)}" for tip in c.tips)
        parts.append(f"<i>Советы:</i>\n{tips_html}")

    if c.sources:
        src_html = "\n".join(f'<a href="{escape(url)}">{escape(url)}</a>' for url in c.sources)
        parts.append(f"<i>Источники:</i>\n{src_html}")

    return "\n\n".join(parts)
