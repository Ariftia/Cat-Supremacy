"""Memory subsystem — vector store, conversation history, prompt assembly.

Public API re-exported for convenience::

    from memory import (
        # Conversation history
        get_user_memory, load_all, save_all, prune_old_conversations,
        export_user_conversation, export_all_conversations,
        import_user_conversation, import_all_conversations,
        migrate_legacy_notes_to_vector_store,
        extract_and_update_memories,
        # Vector store
        search_memories, store_memory, get_memory_count,
        get_all_memories, delete_user_memories,
        export_user_memories_json, import_user_memories_json,
        # Prompt building
        format_memories_block,
    )
"""

# ── Conversation history ─────────────────────────────────
from memory.conversation import (          # noqa: F401
    get_user_memory,
    load_all,
    save_all,
    prune_old_conversations,
    export_user_conversation,
    export_all_conversations,
    import_user_conversation,
    import_all_conversations,
    migrate_legacy_notes_to_vector_store,
    extract_and_update_memories,
)

# ── Vector store ─────────────────────────────────────────
from memory.vector_store import (          # noqa: F401
    search_memories,
    store_memory,
    get_memory_count,
    get_all_memories,
    delete_user_memories,
    export_user_memories_json,
    import_user_memories_json,
)

# ── Prompt building ──────────────────────────────────────
from memory.prompt_builder import (        # noqa: F401
    format_memories_block,
)
