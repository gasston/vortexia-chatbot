"""Chunk markdown into 500-800 token pieces (tiktoken cl100k_base).

Strategy (spec 4.5 étape 4):
- split on H2/H3 headings
- merge sections < 200 tokens forward
- split sections > 800 tokens with a sliding token window (100 overlap)
"""
import re

import tiktoken

ENC = tiktoken.get_encoding("cl100k_base")
MIN_TOKENS = 200
MAX_TOKENS = 800
OVERLAP = 100


def count_tokens(text: str) -> int:
    return len(ENC.encode(text))


def _split_sections(md: str) -> list[str]:
    parts = re.split(r"(?m)^(?=#{2,3}\s)", md)
    return [p.strip() for p in parts if p.strip()]


def _split_large(text: str) -> list[str]:
    toks = ENC.encode(text)
    step = MAX_TOKENS - OVERLAP
    out = []
    for i in range(0, len(toks), step):
        out.append(ENC.decode(toks[i:i + MAX_TOKENS]))
        if i + MAX_TOKENS >= len(toks):
            break
    return out


def chunk(markdown: str) -> list[str]:
    merged: list[str] = []
    buf = ""
    for section in _split_sections(markdown):
        buf = f"{buf}\n\n{section}".strip() if buf else section
        if count_tokens(buf) >= MIN_TOKENS:
            merged.append(buf)
            buf = ""
    if buf:  # trailing small remainder → glue to last, or keep if it's the only one
        if merged:
            merged[-1] = f"{merged[-1]}\n\n{buf}"
        else:
            merged.append(buf)

    chunks: list[str] = []
    for m in merged:
        chunks.extend([m] if count_tokens(m) <= MAX_TOKENS else _split_large(m))
    return chunks


def _demo():
    small = "## A\nshort\n\n## B\nalso short"
    assert len(chunk(small)) == 1, "tiny sections should merge into one chunk"

    big = "## Big\n" + " ".join(["mot"] * 4000)
    out = chunk(big)
    assert len(out) > 1, "oversized section must split"
    assert all(count_tokens(c) <= MAX_TOKENS for c in out), "no chunk over MAX_TOKENS"
    print(f"ok: small={len(chunk(small))} chunk, big={len(out)} chunks")


if __name__ == "__main__":
    _demo()
