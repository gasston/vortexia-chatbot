"""Extract clean markdown + title from raw HTML. Rejects thin pages (<200 chars)."""
import trafilatura
from lxml import html as lxml_html

MIN_CHARS = 200


def _title(html_text: str) -> str | None:
    try:
        t = lxml_html.fromstring(html_text).xpath("//title/text()")
        return t[0].strip() if t else None
    except Exception:
        return None


def extract(url: str, html_text: str) -> dict | None:
    md = trafilatura.extract(
        html_text,
        output_format="markdown",
        include_links=False,
        include_images=False,
        url=url,
    )
    if not md or len(md) < MIN_CHARS:
        return None
    return {"url": url, "title": _title(html_text), "markdown": md}
