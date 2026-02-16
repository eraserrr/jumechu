# Data Model: Memory-Based Additional Recipe Recommendations

**Feature**: 001-memory-recommendations
**Date**: 2026-02-16
**Status**: Complete

## Overview

This document defines the data structures and entities required to implement conversation memory for the recipe recommendation system. These models extend the existing system to support session-based memory without modifying the core database schema.

---

## Entities

### 1. Session Context (In-Memory)

**Purpose**: Stores conversation state for a user's recipe exploration session to enable `more=true` functionality.

**Storage**: In-memory dictionary on agent server (not persisted to database)

**Lifecycle**: Created on first request, expires after 30 minutes of inactivity

**Structure**:

```python
SessionContext = {
    "session_id": str,              # UUID or user_id
    "original_ingredients": List[str],  # Ingredients from first request
    "original_exclusions": List[str],   # Exclusions from first request
    "recommended_recipes": List[str],   # dishName values from all responses
    "last_accessed": float,         # Unix timestamp of last request
    "created_at": float             # Unix timestamp of session creation
}
```

**Fields**:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `session_id` | string | Unique session identifier (UUID4 or user_id) | Required, non-empty |
| `original_ingredients` | array[string] | List of ingredients from the initial request that started this session | Required (can be empty array) |
| `original_exclusions` | array[string] | List of ingredients to exclude from the initial request | Optional (defaults to empty array) |
| `recommended_recipes` | array[string] | Cumulative list of recipe names (`dishName`) recommended in this session | Starts as empty array, appended after each response |
| `last_accessed` | float | Unix timestamp (seconds since epoch) of the most recent request using this session | Updated on every access |
| `created_at` | float | Unix timestamp of session creation | Set once on creation, immutable |

**Relationships**:
- One session per user/session_id (1:1 mapping)
- Session references recipes by name (not stored in session, just names for exclusion)
- No database relationships (in-memory only)

**State Transitions**:

```
[New Request]
    → Check if session exists
        → Yes: Load session, update last_accessed
        → No: Create new session

[Request with more=true]
    → Retrieve original_ingredients and recommended_recipes
    → Combine with new exclusions
    → Send to agent
    → Update recommended_recipes with new results
    → Update last_accessed

[Background Cleanup Task (every 5 min)]
    → For each session:
        → If (current_time - last_accessed > 1800):
            → Delete session
```

---

### 2. Extended Request Body (Modified)

**Purpose**: Extends existing `RequestBody` and `AgentRequestBody` to support session identification.

**Storage**: Request payload (transient)

**Changes to Existing Schema**:

**RequestBody** (api_server.py):
```python
class RequestBody(BaseModel):
    ingredients: List[str]
    excludeIngredients: Optional[List[str]] = None
    more: Optional[bool] = False
    # NEW FIELD:
    session_id: Optional[str] = None  # Client-provided session ID
```

**AgentRequestBody** (agent_server.py):
```python
class AgentRequestBody(BaseModel):
    question: str
    more: Optional[bool] = False
    # NEW FIELD:
    session_id: Optional[str] = None  # Passed from API server
```

**Fields (New)**:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `session_id` | string (optional) | Session identifier for conversation continuity | Optional; if not provided, derived from user_id or generated |

**Backward Compatibility**:
- All new fields are optional with defaults
- Existing requests without `session_id` will work (system generates one)
- `more=false` or absent `more` field continues to work as before

---

### 3. Extended Recipe Response (Modified)

**Purpose**: Return session information to client for subsequent requests.

**Storage**: Response payload (transient)

**Changes to Existing Schema**:

**Current Response** (from agent_server.py):
```python
{
    "answer": [
        {
            "dishName": str,
            "ingredients": List[str],
            "recipe": str,
            "recommendedIngredient": str,
            "warning": str
        }
    ]
}
```

**Extended Response**:
```python
{
    "answer": [...],  # Existing recipe array
    # NEW FIELD:
    "session_id": str  # Session ID for client to use in subsequent more=true requests
}
```

**Fields (New)**:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `session_id` | string | The session ID associated with this response | Always present in response |

**Usage**:
- Client receives `session_id` in first response
- Client includes `session_id` in subsequent `more=true` requests
- If client doesn't provide `session_id`, server generates new one

---

## Data Validation Rules

### Session Context

1. **Session ID Format**:
   - If user_id available: use user_id string
   - If no user_id: UUID4 format (8-4-4-4-12 hexadecimal)
   - Must be unique across active sessions

2. **Ingredient Lists**:
   - Each ingredient must be non-empty string
   - Duplicates allowed (will be de-duplicated during processing)
   - No minimum/maximum list length enforced

3. **Timestamps**:
   - Must be valid Unix timestamps (positive float)
   - `last_accessed` >= `created_at` (always true by design)

4. **Recipe Names**:
   - Must match `dishName` from response exactly
   - Case-sensitive
   - No validation that recipe exists (just stored for exclusion)

### Request Validation

1. **session_id** (optional):
   - If provided: must be non-empty string
   - If not provided: derived/generated automatically

2. **more** (optional):
   - Boolean or absent (defaults to false)
   - If true but no session exists: treated as new request (logged warning)

---

## Memory Management Rules

### Session Creation

```
IF request.session_id is provided AND exists in memory:
    session = load existing session
    session.last_accessed = current_time
ELSE IF request.user_id is available:
    session_id = user_id
    IF session exists for user_id:
        session = load existing session
        session.last_accessed = current_time
    ELSE:
        session = create new session with session_id = user_id
ELSE:
    session_id = generate UUID4()
    session = create new session with session_id
```

### Session Update

```
AFTER agent returns recommendations:
    new_recipe_names = extract dishNames from response
    session.recommended_recipes.extend(new_recipe_names)
    session.last_accessed = current_time
    save session to memory
```

### Session Cleanup

```
EVERY 5 minutes (background task):
    current_time = now()
    FOR EACH session IN memory:
        IF current_time - session.last_accessed > 1800:  # 30 minutes
            DELETE session
```

---

## Indexing Strategy

**In-Memory Dictionary**:
- Primary key: `session_id` (string)
- Lookup: O(1) by session_id
- No secondary indexes needed (single-key access pattern)

**Concurrency Control**:
- Read operations: No locking (dict reads are atomic in Python)
- Write operations: Per-session lock using `asyncio.Lock`
```python
session_locks = defaultdict(asyncio.Lock)

async with session_locks[session_id]:
    # Update session.recommended_recipes
    # Update session.last_accessed
```

---

## Example Data Flow

### Scenario: User requests recipes, then asks for more

**Request 1: Initial request**
```json
POST /v1/request
{
    "ingredients": ["양파", "소시지", "토마토"],
    "excludeIngredients": [],
    "more": false
}
```

**Session Created**:
```python
{
    "session_id": "user-123",  # Or generated UUID
    "original_ingredients": ["양파", "소시지", "토마토"],
    "original_exclusions": [],
    "recommended_recipes": [],  # Empty initially
    "last_accessed": 1708012345.67,
    "created_at": 1708012345.67
}
```

**Response 1**:
```json
{
    "answer": [
        {
            "dishName": "소시지 토마토 볶음",
            "ingredients": ["소시지", "토마토", "양파"],
            "recipe": "...",
            "recommendedIngredient": "모든 재료가 있습니다",
            "warning": "소시지는 가공육이므로 과도한 섭취는 피하세요"
        }
    ],
    "session_id": "user-123"
}
```

**Session Updated**:
```python
{
    "session_id": "user-123",
    "original_ingredients": ["양파", "소시지", "토마토"],
    "original_exclusions": [],
    "recommended_recipes": ["소시지 토마토 볶음"],  # Added
    "last_accessed": 1708012345.67,
    "created_at": 1708012345.67
}
```

---

**Request 2: More recommendations**
```json
POST /v1/request
{
    "ingredients": [],  # Ignored because more=true
    "excludeIngredients": ["소시지"],  # New exclusion
    "more": true,
    "session_id": "user-123"
}
```

**Session Retrieved**:
```python
{
    "session_id": "user-123",
    "original_ingredients": ["양파", "소시지", "토마토"],  # Retrieved
    "original_exclusions": [],
    "recommended_recipes": ["소시지 토마토 볶음"],  # Retrieved
    "last_accessed": 1708012345.67,
    "created_at": 1708012345.67
}
```

**Agent Query Built**:
```text
이전 질문의 조건들을 동일하게 적용해서 다른 요리 더 추천해줘.

원래 재료: 양파, 소시지, 토마토

대신 아래 재료들은 빼줬으면 좋겠어:
소시지

그리고 이미 추천한 요리는 제외해줘:
소시지 토마토 볶음
```

**Response 2**:
```json
{
    "answer": [
        {
            "dishName": "토마토 양파 샐러드",
            "ingredients": ["토마토", "양파"],
            "recipe": "...",
            "recommendedIngredient": "모든 재료가 있습니다",
            "warning": "신선한 채소로 건강한 식사입니다"
        }
    ],
    "session_id": "user-123"
}
```

**Session Updated**:
```python
{
    "session_id": "user-123",
    "original_ingredients": ["양파", "소시지", "토마토"],
    "original_exclusions": [],
    "recommended_recipes": [
        "소시지 토마토 볶음",
        "토마토 양파 샐러드"  # Added
    ],
    "last_accessed": 1708013245.89,  # Updated
    "created_at": 1708012345.67
}
```

---

## Summary

**New Entities**:
1. SessionContext (in-memory only)

**Modified Entities**:
1. RequestBody (added optional `session_id` field)
2. AgentRequestBody (added optional `session_id` field)
3. Recipe Response (added `session_id` field)

**Storage Requirements**:
- In-memory: ~1-2 KB per session
- No database changes required

**Validation**:
- Session ID format (UUID4 or user_id)
- Timestamp consistency
- Recipe name matching

**Indexes**:
- Single dictionary lookup by session_id (O(1))

All data structures are designed to integrate seamlessly with the existing API without breaking changes.
