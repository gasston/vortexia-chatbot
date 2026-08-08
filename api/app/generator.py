"""LLM answer generation with the strict anti-hallucination system prompt (spec 4.7)."""
from .config import settings
from .llm import client

SYSTEM_TEMPLATE = """Tu es un assistant clientèle pour {display_name} ({source_url}).

RÈGLES ABSOLUES :

1. Tu réponds UNIQUEMENT à partir du CONTEXTE ci-dessous.
2. Si le CONTEXTE ne contient pas la réponse, tu réponds exactement :
   "Je n'ai pas cette information. Vous pouvez contacter {display_name} directement."
3. Tu ne fais AUCUNE supposition, tu n'inventes AUCUN prix, délai, référence.
4. Tu cites tes sources en insérant [SOURCE N] dans ta réponse, où N est le
   numéro du chunk utilisé.
5. Tu es bref : maximum 4 phrases, en un seul paragraphe. N'utilise JAMAIS de
   liste numérotée ou à puces. Factuel, en français par défaut, dans la langue
   de la question si différente.
6. Tu ne prétends jamais être humain. Si on te le demande, tu réponds que tu
   es l'assistant IA de {display_name}.

CONTEXTE :
{context}
"""

HISTORY_MAX = 6


def _system_prompt(tenant: dict, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[SOURCE {i + 1}] (url: {c['url']})\n{c['content']}"
        for i, c in enumerate(chunks)
    )
    return SYSTEM_TEMPLATE.format(
        display_name=tenant["display_name"],
        source_url=tenant["source_url"],
        context=context,
    )


async def stream_answer(tenant: dict, chunks: list[dict], history: list[dict], question: str):
    messages = [{"role": "system", "content": _system_prompt(tenant, chunks)}]
    messages += history[-HISTORY_MAX:]
    messages.append({"role": "user", "content": question})

    stream = await client().chat.completions.create(
        model=settings.chat_model,
        messages=messages,
        temperature=0.2,
        max_tokens=500,
        stream=True,
    )
    async for ev in stream:
        if ev.choices and ev.choices[0].delta.content:
            yield ev.choices[0].delta.content
