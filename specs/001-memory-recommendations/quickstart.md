# Quickstart Guide: Memory-Based Additional Recipe Recommendations

**Feature**: 001-memory-recommendations
**Date**: 2026-02-16
**Audience**: Developers implementing this feature

## Overview

This guide provides a quick reference for implementing conversation memory to support the `more=true` parameter in recipe recommendations. Follow these steps to add session-based memory without breaking existing functionality.

---

## Implementation Checklist

### Phase 1: Core Memory Infrastructure

- [ ] 1. Create session memory data structure in `agent_server.py`
- [ ] 2. Implement session lifecycle management (create, retrieve, update, cleanup)
- [ ] 3. Add background cleanup task for expired sessions
- [ ] 4. Update `AgentRequestBody` to include optional `session_id` field

### Phase 2: Request Handling

- [ ] 5. Modify `/v1/request` endpoint in `api_server.py` to accept and forward `session_id`
- [ ] 6. Update `RequestBody` to include optional `session_id` field
- [ ] 7. Implement session ID generation logic (UUID4 fallback)
- [ ] 8. Update response to include `session_id`

### Phase 3: Agent Integration

- [ ] 9. Modify agent request handler to check for `more=true` parameter
- [ ] 10. Implement session context retrieval for `more=true` requests
- [ ] 11. Build dynamic prompt with original ingredients + exclusions + recipe exclusions
- [ ] 12. Update session memory with new recommended recipes after each response

### Phase 4: Testing

- [ ] 13. Add unit tests for session management (create, retrieve, expire)
- [ ] 14. Add integration tests for `more=true` flow
- [ ] 15. Test edge cases (no session, expired session, empty results)
- [ ] 16. Verify backward compatibility (existing clients without `session_id`)

---

## Key Implementation Points

### 1. Session Memory Structure

**Location**: `agent_server.py` (global scope)

```python
from collections import defaultdict
from typing import Dict, List
import asyncio
import time
import uuid

# Global session storage
session_memory: Dict[str, dict] = {}
session_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# Session structure
def create_session(session_id: str, ingredients: List[str], exclusions: List[str] = None) -> dict:
    return {
        "session_id": session_id,
        "original_ingredients": ingredients,
        "original_exclusions": exclusions or [],
        "recommended_recipes": [],
        "last_accessed": time.time(),
        "created_at": time.time()
    }
```

---

### 2. Background Cleanup Task

**Location**: `agent_server.py` startup event

```python
SESSION_TIMEOUT = 1800  # 30 minutes in seconds
CLEANUP_INTERVAL = 300  # 5 minutes in seconds

async def cleanup_expired_sessions():
    """Background task to remove expired sessions"""
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

@app.on_event("startup")
async def startup_event():
    """Server startup: initialize vector store, chain, and cleanup task"""
    initialize_vector_store()
    initialize_chain()
    asyncio.create_task(cleanup_expired_sessions())
```

---

### 3. Session Management Functions

**Location**: `agent_server.py` or new file `util/memory/session_manager.py`

```python
def get_or_create_session(session_id: str = None, ingredients: List[str] = None) -> tuple[str, dict]:
    """
    Retrieve existing session or create new one.

    Returns:
        (session_id, session_data)
    """
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Check if session exists
    if session_id in session_memory:
        session = session_memory[session_id]
        session["last_accessed"] = time.time()
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
    """
    async with session_locks[session_id]:
        if session_id in session_memory:
            session_memory[session_id]["recommended_recipes"].extend(new_recipes)
            session_memory[session_id]["last_accessed"] = time.time()
            print(f"📝 Updated session {session_id} with {len(new_recipes)} new recipes")
```

---

### 4. Modified Request Body Models

**Location**: `util/request/request_body.py` and `util/request/agent_request_body.py`

```python
# request_body.py (API server)
from pydantic import BaseModel
from typing import List, Optional

class RequestBody(BaseModel):
    ingredients: List[str]
    excludeIngredients: Optional[List[str]] = None
    more: Optional[bool] = False
    session_id: Optional[str] = None  # NEW

# agent_request_body.py (Agent server)
class AgentRequestBody(BaseModel):
    question: str
    more: Optional[bool] = False
    session_id: Optional[str] = None  # NEW
```

---

### 5. Request Handler Logic (API Server)

**Location**: `api_server.py` - modify `/v1/request` endpoint

```python
@app.post("/v1/request")
def request(request_body: RequestBody):
    # Extract or generate session ID
    session_id = request_body.session_id

    # Build question based on more parameter
    question = get_question(request_body)

    # Call agent server with session ID
    response_data = query(request_body, question)

    # Add session_id to response
    if isinstance(response_data, dict):
        response_data["session_id"] = session_id or "generated-by-agent"

    return response_data

def query(body_data, question):
    data = AgentRequestBody(
        question=str(question),
        more=body_data.more,
        session_id=body_data.session_id  # NEW: Forward session ID
    )

    response = requests.post(
        AGENT_SERVER_API_URL,
        headers={"Content-Type": "application/json"},
        json=data.model_dump(exclude_none=True),
    )
    return response.json()
```

---

### 6. Agent Request Handler (Agent Server)

**Location**: `agent_server.py` - modify `/v1/request` endpoint

```python
@app.post("/v1/request")
@traceable(name="chat_ai_endpoint", run_type="chain")
def chat_ai(request_body: AgentRequestBody):
    """Process recipe recommendation with optional session memory"""
    global recipe_chain

    if recipe_chain is None:
        return {"error": "Recipe chain is not initialized"}

    # Handle session
    session_id = request_body.session_id
    session_data = None

    if request_body.more:
        # Retrieve or create session
        session_id, session_data = get_or_create_session(session_id)

        if not session_data["original_ingredients"]:
            # No previous context, treat as new request
            print(f"⚠️ more=true but no session context, treating as new request")
            request_body.more = False
        else:
            # Build question with session context
            request_body.question = build_more_question(session_data, request_body.question)
    else:
        # New request: create session
        # Extract ingredients from question (or parse from request)
        session_id, session_data = get_or_create_session(session_id, ingredients=[])

    print(f"\n{'=' * 50}")
    print(f"💬 질문: {request_body.question}")
    print(f"🔑 Session ID: {session_id}")
    print(f"{'=' * 50}\n")

    try:
        result = recipe_chain(request_body.question)
        final_message = result["messages"][-1].content
        parsed_answer = parse_recipe_response(final_message)

        # Update session with new recipes
        if isinstance(parsed_answer, list):
            new_recipes = [recipe["dishName"] for recipe in parsed_answer if "dishName" in recipe]
            asyncio.create_task(update_session_recipes(session_id, new_recipes))

        response = {
            "answer": parsed_answer,
            "session_id": session_id  # NEW: Include session ID in response
        }

        return response

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "session_id": session_id}

def build_more_question(session_data: dict, exclude_ingredients_str: str) -> str:
    """Build question for more=true requests using session context"""
    original_ingredients = ", ".join(session_data["original_ingredients"])
    recommended_recipes = ", ".join(session_data["recommended_recipes"])

    # Parse exclude_ingredients from current request if provided
    # (this would come from request_body.question or separate field)

    question = f"""이전 질문의 조건들을 동일하게 적용해서 다른 요리 더 추천해줘.

원래 재료: {original_ingredients}

대신 아래 재료들은 빼줬으면 좋겠어:
{exclude_ingredients_str}

그리고 이미 추천한 요리는 제외해줘:
{recommended_recipes}"""

    return question
```

---

### 7. Testing Examples

**Unit Test**: Session expiration

```python
import pytest
import time
from agent_server import create_session, SESSION_TIMEOUT

def test_session_expiration():
    session = create_session("test-123", ["양파", "토마토"])

    # Simulate 31 minutes passing
    session["last_accessed"] = time.time() - (SESSION_TIMEOUT + 60)

    # Cleanup logic should detect this as expired
    current_time = time.time()
    is_expired = current_time - session["last_accessed"] > SESSION_TIMEOUT

    assert is_expired is True
```

**Integration Test**: more=true flow

```python
import pytest
from fastapi.testclient import TestClient
from api_server import app

client = TestClient(app)

def test_more_true_workflow():
    # Step 1: Initial request
    response1 = client.post("/v1/request", json={
        "ingredients": ["양파", "토마토"],
        "excludeIngredients": [],
        "more": False
    })

    assert response1.status_code == 200
    data1 = response1.json()
    assert "session_id" in data1
    session_id = data1["session_id"]

    # Step 2: Request more with session
    response2 = client.post("/v1/request", json={
        "ingredients": [],  # Ignored
        "excludeIngredients": ["양파"],
        "more": True,
        "session_id": session_id
    })

    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["session_id"] == session_id

    # Verify different recipes returned
    recipes1 = [r["dishName"] for r in data1["answer"]]
    recipes2 = [r["dishName"] for r in data2["answer"]]
    assert set(recipes1).isdisjoint(set(recipes2))  # No overlap
```

---

## Common Pitfalls

### 1. Race Conditions in Session Updates

**Problem**: Multiple concurrent requests updating the same session.

**Solution**: Use per-session locks with `asyncio.Lock`.

```python
async with session_locks[session_id]:
    session_memory[session_id]["recommended_recipes"].extend(new_recipes)
```

---

### 2. Memory Leaks from Abandoned Sessions

**Problem**: Sessions never accessed again but never cleaned up.

**Solution**: Background cleanup task runs every 5 minutes.

**Verify**: Add logging to cleanup task to monitor session count.

```python
print(f"🧹 Cleanup: {len(expired_sessions)} sessions removed, {len(session_memory)} active")
```

---

### 3. Session ID Collisions

**Problem**: Generated UUIDs or user IDs collide.

**Solution**: Use UUID4 (cryptographically random) for generated IDs. For user IDs, ensure uniqueness at user creation.

---

### 4. Backward Compatibility Breaking

**Problem**: Existing clients without `session_id` fail.

**Solution**: Make `session_id` optional in request, always generate if absent.

**Test**: Send request without `session_id` field, verify response still works.

---

## Deployment Notes

### Environment Variables

No new environment variables required. Existing `.env` configuration continues to work.

### Dependencies

No new dependencies beyond testing:

```txt
# Add to requirements.txt for testing
pytest==7.4.3
pytest-asyncio==0.21.1
freezegun==1.4.0  # For time-based tests
```

### Performance Monitoring

Add logging for session metrics:

```python
# Periodic stats logging
@app.on_event("startup")
async def log_session_stats():
    while True:
        await asyncio.sleep(600)  # Every 10 minutes
        print(f"📊 Active sessions: {len(session_memory)}")
```

---

## Quick Reference

**Session Creation**:
```python
session_id, session = get_or_create_session(session_id, ingredients)
```

**Session Retrieval**:
```python
if session_id in session_memory:
    session = session_memory[session_id]
```

**Session Update**:
```python
await update_session_recipes(session_id, new_recipe_names)
```

**Session Cleanup**:
```python
# Automatic via background task, or manual:
del session_memory[session_id]
```

---

## Next Steps

After implementing the core functionality:

1. Run integration tests to verify `more=true` flow
2. Test edge cases (expired sessions, no results, etc.)
3. Monitor session memory usage in development
4. Consider adding session management endpoints for debugging
5. Proceed to `/speckit.tasks` to generate detailed implementation tasks

---

## Support

**Documentation**:
- [Feature Spec](./spec.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/api-endpoints.md)
- [Research Findings](./research.md)

**Constitutional Compliance**: All principles verified in [Implementation Plan](./plan.md#constitution-check)
