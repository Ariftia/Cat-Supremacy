"""ChromaDB CRUD operations for per-user vector memories.

All heavy ChromaDB calls are wrapped in ``asyncio.to_thread()`` to keep
the Discord event loop responsive.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Optional

import chromadb

import config
from memory.models import Memory
from services.embedding import generate_embedding


# ── ChromaDB client (initialised lazily) ─────────────────

_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None


def _get_collection() -> chromadb.Collection:
    """Return (and lazily create) the ChromaDB collection."""
    global _client, _collection
    if _collection is not None:
        return _collection

    print(f"[VECMEM] Initializing ChromaDB at {config.CHROMA_PERSIST_DIR}")
    _client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
    _collection = _client.get_or_create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    count = _collection.count()
    print(f"[VECMEM] Collection '{config.CHROMA_COLLECTION_NAME}' ready — {count} memories total")
    return _collection


# ── Public API ───────────────────────────────────────────

async def store_memory(
    user_id: int,
    memory_text: str,
    category: str = "general",
    embedding: Optional[list[float]] = None,
) -> bool:
    """Store a new memory for a user in the vector database."""
    if not memory_text or not memory_text.strip():
        return False

    if embedding is None:
        embedding = await generate_embedding(memory_text)
    if embedding is None:
        print("[VECMEM] Skipping store — embedding generation failed")
        return False

    memory_id = str(uuid.uuid4())
    timestamp = time.time()
    user_id_str = str(user_id)

    metadata = {
        "user_id": user_id_str,
        "timestamp": timestamp,
        "category": category,
    }

    try:
        collection = _get_collection()
        await asyncio.to_thread(
            collection.add,
            ids=[memory_id],
            embeddings=[embedding],
            documents=[memory_text],
            metadatas=[metadata],
        )
        print(
            f"[VECMEM] Stored memory {memory_id[:8]}… for user {user_id_str} | "
            f"category={category} | text='{memory_text[:60]}'"
        )
        asyncio.get_event_loop().create_task(_auto_prune(user_id))
        return True
    except Exception as e:
        print(f"[VECMEM] Failed to store memory: {e}")
        return False


async def search_memories(
    user_id: int,
    query_text: str,
    top_k: int | None = None,
) -> list[Memory]:
    """Search for the most relevant memories for a user."""
    if top_k is None:
        top_k = config.MEMORY_TOP_K

    query_embedding = await generate_embedding(query_text)
    if query_embedding is None:
        print("[VECMEM] Search skipped — could not embed query")
        return []

    user_id_str = str(user_id)

    try:
        collection = _get_collection()
        results = await asyncio.to_thread(
            collection.query,
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": user_id_str},
            include=["documents", "metadatas", "distances"],
        )

        memories: list[Memory] = []
        if results and results["ids"] and results["ids"][0]:
            for i, mid in enumerate(results["ids"][0]):
                memories.append(Memory(
                    memory_id=mid,
                    user_id=user_id_str,
                    memory_text=results["documents"][0][i],
                    timestamp=results["metadatas"][0][i].get("timestamp", 0.0),
                    category=results["metadatas"][0][i].get("category", "general"),
                    distance=results["distances"][0][i] if results["distances"] else 0.0,
                ))
        print(
            f"[VECMEM] Search for user {user_id_str} returned {len(memories)} memories "
            f"(query='{query_text[:50]}')"
        )
        return memories
    except Exception as e:
        print(f"[VECMEM] Search failed: {e}")
        return []


async def get_memory_count(user_id: int) -> int:
    """Return the total number of stored memories for a user."""
    user_id_str = str(user_id)
    try:
        collection = _get_collection()
        result = await asyncio.to_thread(
            collection.get,
            where={"user_id": user_id_str},
            include=[],
        )
        return len(result["ids"]) if result and result["ids"] else 0
    except Exception as e:
        print(f"[VECMEM] Failed to count memories for user {user_id_str}: {e}")
        return 0


async def get_all_memories(user_id: int) -> list[Memory]:
    """Retrieve all stored memories for a user (for export / display)."""
    user_id_str = str(user_id)
    try:
        collection = _get_collection()
        result = await asyncio.to_thread(
            collection.get,
            where={"user_id": user_id_str},
            include=["documents", "metadatas"],
        )
        memories: list[Memory] = []
        if result and result["ids"]:
            for i, mid in enumerate(result["ids"]):
                memories.append(Memory(
                    memory_id=mid,
                    user_id=user_id_str,
                    memory_text=result["documents"][i],
                    timestamp=result["metadatas"][i].get("timestamp", 0.0),
                    category=result["metadatas"][i].get("category", "general"),
                ))
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        return memories
    except Exception as e:
        print(f"[VECMEM] Failed to retrieve all memories for user {user_id_str}: {e}")
        return []


async def delete_user_memories(user_id: int) -> int:
    """Delete ALL memories for a user.  Returns the number deleted."""
    user_id_str = str(user_id)
    try:
        collection = _get_collection()
        result = await asyncio.to_thread(
            collection.get,
            where={"user_id": user_id_str},
            include=[],
        )
        ids = result["ids"] if result and result["ids"] else []
        if ids:
            await asyncio.to_thread(collection.delete, ids=ids)
        print(f"[VECMEM] Deleted {len(ids)} memories for user {user_id_str}")
        return len(ids)
    except Exception as e:
        print(f"[VECMEM] Failed to delete memories for user {user_id_str}: {e}")
        return 0


async def prune_memories(
    user_id: int,
    max_count: int | None = None,
) -> int:
    """Remove the oldest memories for a user if they exceed *max_count*."""
    if max_count is None:
        max_count = config.MAX_MEMORIES_PER_USER

    user_id_str = str(user_id)

    try:
        collection = _get_collection()
        result = await asyncio.to_thread(
            collection.get,
            where={"user_id": user_id_str},
            include=["metadatas"],
        )
        ids = result["ids"] if result and result["ids"] else []
        if len(ids) <= max_count:
            return 0

        id_ts_pairs = [
            (ids[i], result["metadatas"][i].get("timestamp", 0.0))
            for i in range(len(ids))
        ]
        id_ts_pairs.sort(key=lambda x: x[1])

        excess = len(ids) - max_count
        to_delete = [pair[0] for pair in id_ts_pairs[:excess]]
        await asyncio.to_thread(collection.delete, ids=to_delete)
        print(
            f"[VECMEM] Pruned {excess} oldest memories for user {user_id_str} "
            f"(was {len(ids)}, now {max_count})"
        )
        return excess
    except Exception as e:
        print(f"[VECMEM] Prune failed for user {user_id_str}: {e}")
        return 0


async def _auto_prune(user_id: int) -> None:
    """Internal helper — prune if over limit (called after every store)."""
    try:
        await prune_memories(user_id)
    except Exception as e:
        print(f"[VECMEM] Auto-prune error: {e}")


# ── Export / Import helpers ──────────────────────────────

async def export_user_memories_json(user_id: int) -> Optional[str]:
    """Export all memories for a user as a JSON string."""
    memories = await get_all_memories(user_id)
    if not memories:
        return None

    data = [
        {
            "memory_id": m.memory_id,
            "memory_text": m.memory_text,
            "timestamp": m.timestamp,
            "category": m.category,
        }
        for m in memories
    ]
    return json.dumps(data, ensure_ascii=False, indent=2)


async def import_user_memories_json(user_id: int, raw_json: str) -> tuple[int, str]:
    """Import memories for a user from a JSON string.

    Returns ``(count_imported, error_or_empty)``.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return 0, f"Invalid JSON: {e}"

    if not isinstance(data, list):
        return 0, "Expected a JSON array of memory objects."

    imported = 0
    for item in data:
        text = item.get("memory_text", "").strip()
        category = item.get("category", "general")
        if text:
            ok = await store_memory(user_id, text, category=category)
            if ok:
                imported += 1

    print(f"[VECMEM] Imported {imported} memories for user {user_id}")
    return imported, ""
