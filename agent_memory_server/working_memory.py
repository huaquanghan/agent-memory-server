"""Working memory management for sessions."""

import json
import logging
import time
from datetime import UTC, datetime

from redis.asyncio import Redis

from agent_memory_server.models import (
    MemoryMessage,
    MemoryRecord,
    MemoryStrategyConfig,
    WorkingMemory,
)
from agent_memory_server.utils.keys import Keys
from agent_memory_server.utils.redis import get_redis_conn


logger = logging.getLogger(__name__)


def json_datetime_handler(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def list_sessions(
    redis,
    limit: int = 10,
    offset: int = 0,
    namespace: str | None = None,
    user_id: str | None = None,
) -> tuple[int, list[str]]:
    """
    List sessions

    Args:
        redis: Redis client
        limit: Maximum number of sessions to return
        offset: Offset for pagination
        namespace: Optional namespace filter
        user_id: Optional user ID filter (not yet implemented - sessions are stored in sorted sets)

    Returns:
        Tuple of (total_count, session_ids)

    Note:
        The user_id parameter is accepted for API compatibility but filtering by user_id
        is not yet implemented. This would require changing how sessions are stored to
        enable efficient user_id-based filtering.
    """
    # Calculate start and end indices (0-indexed start, inclusive end)
    start = offset
    end = offset + limit - 1

    # TODO: This should take a user_id
    sessions_key = Keys.sessions_key(namespace=namespace)

    async with redis.pipeline() as pipe:
        pipe.zcard(sessions_key)
        pipe.zrange(sessions_key, start, end)
        total, session_ids = await pipe.execute()

    return total, [
        s.decode("utf-8") if isinstance(s, bytes) else s for s in session_ids
    ]


async def get_working_memory(
    session_id: str,
    user_id: str | None = None,
    namespace: str | None = None,
    redis_client: Redis | None = None,
    recent_messages_limit: int | None = None,
) -> WorkingMemory | None:
    """
    Get working memory for a session.

    If no working memory exists but index_all_messages_in_long_term_memory is enabled,
    attempts to reconstruct working memory from messages stored in long-term memory.

    Args:
        session_id: The session ID
        namespace: Optional namespace for the session
        redis_client: Optional Redis client
        recent_messages_limit: Optional limit on number of recent messages to return

    Returns:
        WorkingMemory object or None if not found
    """
    from agent_memory_server.config import settings

    if not redis_client:
        redis_client = await get_redis_conn()

    key = Keys.working_memory_key(
        session_id=session_id,
        user_id=user_id,
        namespace=namespace,
    )

    try:
        data = await redis_client.get(key)
        if not data:
            logger.debug(
                f"No working memory found for parameters: {session_id}, {user_id}, {namespace}"
            )

            # Try to reconstruct from long-term memory if enabled
            if settings.index_all_messages_in_long_term_memory:
                reconstructed = await _reconstruct_working_memory_from_long_term(
                    session_id=session_id,
                    user_id=user_id,
                    namespace=namespace,
                    recent_messages_limit=recent_messages_limit,
                )
                if reconstructed:
                    logger.info(
                        f"Reconstructed working memory for session {session_id} from long-term storage"
                    )
                    return reconstructed

            return None

        # Parse the JSON data
        working_memory_data = json.loads(data)

        # Convert memory records back to MemoryRecord objects
        memories = []
        for memory_data in working_memory_data.get("memories", []):
            memory = MemoryRecord(**memory_data)
            memories.append(memory)

        # Convert messages back to MemoryMessage objects
        messages = []
        for message_data in working_memory_data.get("messages", []):
            message = MemoryMessage(**message_data)
            messages.append(message)

        # Apply recent messages limit if specified (in-memory slice)
        if recent_messages_limit is not None and recent_messages_limit > 0:
            # Sort messages by created_at timestamp to ensure proper chronological order
            messages.sort(key=lambda m: m.created_at)
            # Get the most recent N messages
            messages = messages[-recent_messages_limit:]

        # Handle memory strategy configuration
        strategy_data = working_memory_data.get("long_term_memory_strategy")
        if strategy_data:
            long_term_memory_strategy = MemoryStrategyConfig(**strategy_data)
        else:
            long_term_memory_strategy = (
                MemoryStrategyConfig()
            )  # Default to discrete strategy

        return WorkingMemory(
            messages=messages,
            memories=memories,
            context=working_memory_data.get("context"),
            user_id=working_memory_data.get("user_id"),
            tokens=working_memory_data.get("tokens", 0),
            session_id=session_id,
            namespace=namespace,
            ttl_seconds=working_memory_data.get("ttl_seconds", None),
            data=working_memory_data.get("data") or {},
            long_term_memory_strategy=long_term_memory_strategy,
            last_accessed=datetime.fromtimestamp(
                working_memory_data.get("last_accessed", int(time.time())), UTC
            ),
            created_at=datetime.fromtimestamp(
                working_memory_data.get("created_at", int(time.time())), UTC
            ),
            updated_at=datetime.fromtimestamp(
                working_memory_data.get("updated_at", int(time.time())), UTC
            ),
        )

    except Exception as e:
        logger.error(f"Error getting working memory for session {session_id}: {e}")
        return None


async def set_working_memory(
    working_memory: WorkingMemory,
    redis_client: Redis | None = None,
) -> None:
    """
    Set working memory for a session with TTL.

    Args:
        working_memory: WorkingMemory object to store
        redis_client: Optional Redis client
    """
    if not redis_client:
        redis_client = await get_redis_conn()

    # Validate that all memories have id (Stage 3 requirement)
    for memory in working_memory.memories:
        if not memory.id:
            raise ValueError("All memory records in working memory must have an ID")

    key = Keys.working_memory_key(
        session_id=working_memory.session_id,
        user_id=working_memory.user_id,
        namespace=working_memory.namespace,
    )

    # Update the updated_at timestamp
    working_memory.updated_at = datetime.now(UTC)

    # Convert to JSON-serializable format with timestamp conversion
    data = {
        "messages": [
            message.model_dump(mode="json") for message in working_memory.messages
        ],
        "memories": [
            memory.model_dump(mode="json") for memory in working_memory.memories
        ],
        "context": working_memory.context,
        "user_id": working_memory.user_id,
        "tokens": working_memory.tokens,
        "session_id": working_memory.session_id,
        "namespace": working_memory.namespace,
        "ttl_seconds": working_memory.ttl_seconds,
        "data": working_memory.data or {},
        "long_term_memory_strategy": working_memory.long_term_memory_strategy.model_dump(),
        "last_accessed": int(working_memory.last_accessed.timestamp()),
        "created_at": int(working_memory.created_at.timestamp()),
        "updated_at": int(working_memory.updated_at.timestamp()),
    }

    try:
        if working_memory.ttl_seconds is not None:
            # Store with TTL
            await redis_client.setex(
                key,
                working_memory.ttl_seconds,
                json.dumps(data, default=json_datetime_handler),
            )
            logger.info(
                f"Set working memory for session {working_memory.session_id} with TTL {working_memory.ttl_seconds}s"
            )
        else:
            await redis_client.set(
                key,
                json.dumps(data, default=json_datetime_handler),
            )
            logger.info(
                f"Set working memory for session {working_memory.session_id} with no TTL"
            )
    except Exception as e:
        logger.error(
            f"Error setting working memory for session {working_memory.session_id}: {e}"
        )
        raise


async def delete_working_memory(
    session_id: str,
    user_id: str | None = None,
    namespace: str | None = None,
    redis_client: Redis | None = None,
) -> None:
    """
    Delete working memory for a session.

    Args:
        session_id: The session ID
        user_id: Optional user ID for the session
        namespace: Optional namespace for the session
        redis_client: Optional Redis client
    """
    if not redis_client:
        redis_client = await get_redis_conn()

    key = Keys.working_memory_key(
        session_id=session_id, user_id=user_id, namespace=namespace
    )

    try:
        await redis_client.delete(key)
        logger.info(f"Deleted working memory for session {session_id}")

    except Exception as e:
        logger.error(f"Error deleting working memory for session {session_id}: {e}")
        raise


async def _reconstruct_working_memory_from_long_term(
    session_id: str,
    user_id: str | None = None,
    namespace: str | None = None,
    recent_messages_limit: int | None = None,
) -> WorkingMemory | None:
    """
    Reconstruct working memory from messages stored in long-term memory.

    This function searches for messages in long-term memory that belong to the
    specified session and reconstructs a WorkingMemory object from them.

    Args:
        session_id: The session ID to reconstruct
        user_id: Optional user ID filter
        namespace: Optional namespace filter
        recent_messages_limit: Optional limit on number of recent messages to return

    Returns:
        Reconstructed WorkingMemory object or None if no messages found
    """
    from agent_memory_server.filters import MemoryType, Namespace, SessionId, UserId
    from agent_memory_server.long_term_memory import search_long_term_memories

    try:
        # Search for message-type memories for this session
        session_filter = SessionId(eq=session_id)
        user_filter = UserId(eq=user_id) if user_id else None
        namespace_filter = Namespace(eq=namespace) if namespace else None
        memory_type_filter = MemoryType(eq="message")

        # Search for messages with appropriate limit
        # We use empty text since we're filtering by session_id and memory_type
        search_limit = recent_messages_limit if recent_messages_limit else 1000
        results = await search_long_term_memories(
            text="",  # Empty query since we're filtering by metadata
            session_id=session_filter,
            user_id=user_filter,
            namespace=namespace_filter,
            memory_type=memory_type_filter,
            limit=search_limit,
            offset=0,
        )

        if not results.memories:
            logger.debug(
                f"No message memories found for session {session_id} in long-term storage"
            )
            return None

        # Convert memory records back to messages
        messages = []
        for memory in results.memories:
            # Parse the message text which should be in format "role: content"
            text = memory.text
            if ": " in text:
                role, content = text.split(": ", 1)
                message = MemoryMessage(
                    id=memory.id,
                    role=role.lower(),
                    content=content,
                    created_at=memory.created_at,  # Use the original creation time
                    persisted_at=memory.persisted_at,  # Mark as already persisted
                )
                messages.append(message)
            else:
                logger.warning(
                    f"Skipping malformed message memory: {memory.id} - {text}"
                )

        if not messages:
            logger.debug(f"No valid messages found for session {session_id}")
            return None

        # Sort messages by creation time to maintain conversation order (most recent first for API response)
        messages.sort(key=lambda m: m.created_at, reverse=True)

        # If we have a limit, take only the most recent N messages
        if recent_messages_limit and len(messages) > recent_messages_limit:
            messages = messages[:recent_messages_limit]

        # Reverse back to chronological order for working memory (oldest first)
        messages.reverse()

        # Create reconstructed working memory
        now = datetime.now(UTC)
        reconstructed = WorkingMemory(
            session_id=session_id,
            namespace=namespace,
            user_id=user_id,
            messages=messages,
            memories=[],  # No structured memories in reconstruction
            context="",  # No context in reconstruction
            data={},  # No session data in reconstruction
            created_at=messages[0].persisted_at or now if messages else now,
            updated_at=now,
            last_accessed=now,
        )

        logger.info(
            f"Reconstructed working memory for session {session_id} with {len(messages)} messages"
        )
        return reconstructed

    except Exception as e:
        logger.error(
            f"Error reconstructing working memory for session {session_id}: {e}"
        )
        return None
