"""
Session memory management for conversation context.

This module provides in-memory session storage for recipe recommendation
conversation history, enabling the `more=true` parameter functionality.
"""

import asyncio
import time
import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# Global session storage
session_memory: Dict[str, dict] = {}
session_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# Configuration constants
SESSION_TIMEOUT = 1800  # 30 minutes in seconds
CLEANUP_INTERVAL = 300  # 5 minutes in seconds


def create_session(session_id: str, ingredients: List[str], exclusions: List[str] = None) -> dict:
    """
    Create a new session context.

    Args:
        session_id: Unique session identifier (UUID or user_id)
        ingredients: List of ingredients from initial request
        exclusions: List of ingredients to exclude (optional)

    Returns:
        Session dictionary with structure defined in data-model.md
    """
    current_time = time.time()
    return {
        "session_id": session_id,
        "original_ingredients": ingredients,
        "original_exclusions": exclusions or [],
        "recommended_recipes": [],
        "last_accessed": current_time,
        "created_at": current_time
    }


def get_or_create_session(session_id: Optional[str] = None, ingredients: List[str] = None) -> Tuple[str, dict]:
    """
    Retrieve existing session or create new one.

    Args:
        session_id: Optional session ID to retrieve
        ingredients: Ingredients for new session if creating

    Returns:
        Tuple of (session_id, session_data)
    """
    # Validate session_id if provided
    if session_id and (not session_id.strip()):
        print(f"⚠️ Invalid session_id (empty string), generating new one")
        session_id = None

    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
        print(f"✨ Generating new session ID: {session_id}")

    # Check if session exists
    if session_id in session_memory:
        session = session_memory[session_id]
        session["last_accessed"] = time.time()
        print(f"🔑 Retrieved existing session: {session_id}")
        return session_id, session

    # Create new session
    session = create_session(session_id, ingredients or [])
    session_memory[session_id] = session
    print(f"✨ New session created: {session_id}")
    return session_id, session


async def update_session_recipes(session_id: str, new_recipes: List[str]):
    """
    Add newly recommended recipes to session memory.
    Thread-safe with per-session locking.

    Args:
        session_id: Session identifier
        new_recipes: List of dishName values to add
    """
    async with session_locks[session_id]:
        if session_id in session_memory:
            session_memory[session_id]["recommended_recipes"].extend(new_recipes)
            session_memory[session_id]["last_accessed"] = time.time()
            print(f"📝 Updated session {session_id} with {len(new_recipes)} new recipes")


async def cleanup_expired_sessions():
    """
    Background task to remove sessions inactive for >30 minutes.
    Runs every 5 minutes.
    """
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        current_time = time.time()
        expired_sessions = [
            sid for sid, session in session_memory.items()
            if current_time - session["last_accessed"] > SESSION_TIMEOUT
        ]
        for sid in expired_sessions:
            del session_memory[sid]
            print(f"🧹 Session {sid} expired and cleaned up")

        if expired_sessions:
            print(f"🧹 Cleanup: {len(expired_sessions)} sessions removed, {len(session_memory)} active")
