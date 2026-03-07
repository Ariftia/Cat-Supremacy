"""OpenAI embedding generation for the vector memory pipeline."""

from __future__ import annotations

from typing import Optional

import config


async def generate_embedding(text: str) -> Optional[list[float]]:
    """Generate an embedding vector for *text* using the OpenAI API.

    Returns a list of floats on success, or ``None`` if the API key is
    missing or the call fails.
    """
    if not config.OPENAI_API_KEY:
        print("[EMBED] Skipped — no OpenAI API key configured")
        return None

    text = text[:2000].strip()
    if not text:
        print("[EMBED] Skipped — empty text after trimming")
        return None

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    try:
        response = await client.embeddings.create(
            model=config.EMBEDDING_MODEL,
            input=text,
            dimensions=config.EMBEDDING_DIMENSIONS,
        )
        embedding = response.data[0].embedding
        usage = response.usage
        print(
            f"[EMBED] Generated embedding ({len(embedding)} dims) | "
            f"tokens: {usage.total_tokens}"
        )
        return embedding
    except Exception as e:
        print(f"[EMBED] Failed to generate embedding: {e}")
        return None


async def generate_embeddings_batch(
    texts: list[str],
) -> list[Optional[list[float]]]:
    """Generate embeddings for multiple texts in a single API call.

    Returns a list of embedding vectors (or ``None`` for any that fail).
    """
    if not config.OPENAI_API_KEY:
        print("[EMBED] Batch skipped — no OpenAI API key configured")
        return [None] * len(texts)

    cleaned = [t[:2000].strip() for t in texts]
    if not any(cleaned):
        return [None] * len(texts)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    try:
        response = await client.embeddings.create(
            model=config.EMBEDDING_MODEL,
            input=cleaned,
            dimensions=config.EMBEDDING_DIMENSIONS,
        )
        results: list[Optional[list[float]]] = [None] * len(texts)
        for item in response.data:
            results[item.index] = item.embedding
        usage = response.usage
        print(
            f"[EMBED] Batch generated {len(response.data)} embeddings | "
            f"tokens: {usage.total_tokens}"
        )
        return results
    except Exception as e:
        print(f"[EMBED] Batch embedding failed: {e}")
        return [None] * len(texts)
