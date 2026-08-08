"""Generate 3 visitor-style suggested questions from a site's H2 headings (spec 4.5 étape 6)."""
import re

from .config import settings
from .llm import client

_H2 = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
MAX_H2 = 20


def extract_h2s(markdowns: list[str], limit: int = MAX_H2) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for md in markdowns:
        for h in _H2.findall(md):
            h = h.strip()
            key = h.lower()
            if h and key not in seen:
                seen.add(key)
                out.append(h)
                if len(out) >= limit:
                    return out
    return out


async def generate(display_name: str, h2s: list[str]) -> list[str]:
    if not h2s:
        return []
    titles = "\n".join(f"- {h}" for h in h2s)
    prompt = (
        f"Voici des titres de sections du site {display_name} :\n{titles}\n\n"
        "Génère exactement 3 questions courtes (max 10 mots) qu'un visiteur "
        "poserait à l'assistant, basées sur ces titres. Une question par ligne, "
        "sans numérotation ni puce, sans aucun autre texte."
    )
    resp = await client().chat.completions.create(
        model=settings.chat_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=150,
    )
    lines = [ln.strip(" -•\t") for ln in (resp.choices[0].message.content or "").splitlines()]
    return [ln for ln in lines if ln][:3]


def _demo():
    md = "# Titre\n## Livraison et retours\ntexte\n## Livraison et retours\ndup\n### Paiement\nx\n## Garantie\ny"
    h2s = extract_h2s([md])
    assert h2s == ["Livraison et retours", "Garantie"], h2s  # H2 only, deduped, order kept
    print("ok:", h2s)


if __name__ == "__main__":
    _demo()
