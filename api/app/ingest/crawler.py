"""Crawl a public site: sitemap.xml first, else BFS from the root URL.

Returns a dict {url: html}. Respects robots.txt, same-domain only, excludes
cart/admin paths. ponytail: naive BFS + in-memory sets, fine for < 200 pages.
"""
import asyncio
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import httpx
from lxml import html as lxml_html

USER_AGENT = "VortexiaBot/0.1 (+https://vortexia.agency/bot)"
EXCLUDE = ("/wp-admin", "/cart", "/checkout", "/account", "?add-to-cart=")
MAX_PAGES = 200
MAX_DEPTH = 3
CONCURRENCY = 5
TIMEOUT = 10.0


def _same_domain(root: str, url: str) -> bool:
    return urlparse(url).netloc == urlparse(root).netloc


def _excluded(url: str) -> bool:
    return any(p in url for p in EXCLUDE)


def _allowed(rp, url: str) -> bool:
    return rp is None or rp.can_fetch(USER_AGENT, url)


async def _get(client: httpx.AsyncClient, url: str):
    """Return (text, content_type) for a 200 response, else (None, "")."""
    try:
        r = await client.get(url, timeout=TIMEOUT, follow_redirects=True)
        if r.status_code == 200:
            return r.text, r.headers.get("content-type", "")
    except httpx.HTTPError:
        pass
    return None, ""


async def _get_html(client: httpx.AsyncClient, url: str):
    text, ct = await _get(client, url)
    return text if text and "text/html" in ct else None


def _links(root: str, base: str, html_text: str):
    try:
        doc = lxml_html.fromstring(html_text)
    except Exception:
        return []
    out = []
    for href in doc.xpath("//a/@href"):
        u = urljoin(base, href.split("#")[0])
        if u.startswith("http"):
            out.append(u)
    return out


def _parse_locs(xml_text: str):
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []
    return [e.text.strip() for e in root.iter()
            if e.text and (e.tag.endswith("}loc") or e.tag == "loc")]


async def _load_robots(client: httpx.AsyncClient, root: str):
    base = f"{urlparse(root).scheme}://{urlparse(root).netloc}"
    txt, _ = await _get(client, urljoin(base, "/robots.txt"))
    if not txt:
        return None
    rp = RobotFileParser()
    rp.parse(txt.splitlines())
    return rp


async def _sitemap_urls(client: httpx.AsyncClient, root: str):
    base = f"{urlparse(root).scheme}://{urlparse(root).netloc}"
    txt, _ = await _get(client, urljoin(base, "/sitemap.xml"))
    if not txt:
        return []
    locs = _parse_locs(txt)
    subs = [l for l in locs if l.endswith(".xml")]
    if not subs:
        return locs
    pages = []
    for s in subs[:50]:  # one level of sitemap-index nesting
        t, _ = await _get(client, s)
        if t:
            pages.extend(x for x in _parse_locs(t) if not x.endswith(".xml"))
    return pages


async def _fetch_all(client, urls):
    sem = asyncio.Semaphore(CONCURRENCY)
    out: dict[str, str] = {}

    async def one(u):
        async with sem:
            h = await _get_html(client, u)
        if h:
            out[u] = h

    await asyncio.gather(*(one(u) for u in urls))
    return out


async def _bfs(client, root, rp):
    seen = {root}
    out: dict[str, str] = {}
    frontier = [(root, 0)]
    while frontier and len(out) < MAX_PAGES:
        level, frontier = frontier, []
        sem = asyncio.Semaphore(CONCURRENCY)

        async def one(u, depth):
            async with sem:
                h = await _get_html(client, u)
            if not h or len(out) >= MAX_PAGES:
                return
            out[u] = h
            if depth < MAX_DEPTH:
                for link in _links(root, u, h):
                    if (link not in seen and _same_domain(root, link)
                            and not _excluded(link) and _allowed(rp, link)):
                        seen.add(link)
                        frontier.append((link, depth + 1))

        await asyncio.gather(*(one(u, d) for u, d in level))
    return dict(list(out.items())[:MAX_PAGES])


async def crawl(root: str) -> dict[str, str]:
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        rp = await _load_robots(client, root)
        sm = await _sitemap_urls(client, root)
        targets = [u for u in sm if _same_domain(root, u)
                   and not _excluded(u) and _allowed(rp, u)][:MAX_PAGES]
        if targets:
            return await _fetch_all(client, targets)
        return await _bfs(client, root, rp)
