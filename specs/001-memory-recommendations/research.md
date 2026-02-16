# Research: Memory-Based Additional Recipe Recommendations

**Feature**: 001-memory-recommendations
**Date**: 2026-02-16
**Status**: Complete

## Overview

This document captures research findings for implementing conversation memory to support the `more=true` parameter in recipe recommendation requests. The research focuses on session management, memory storage patterns, and LangGraph agent memory integration.

## Research Areas

### 1. Session Management for Conversation Memory

**Decision**: Use in-memory dictionary with session IDs as keys, implementing time-based expiration using a background cleanup task.

**Rationale**:
- FastAPI supports background tasks for periodic cleanup
- Dictionary provides O(1) lookup for session context retrieval
- No external dependencies required for MVP (Redis, Memcached not needed initially)
- Session timeout can be tracked using timestamp comparison
- Scales adequately for moderate concurrent users without distributed caching

**Alternatives Considered**:

1. **Redis/External Cache**:
   - **Rejected because**: Adds infrastructure complexity and external dependency for MVP
   - May be reconsidered for production scale if session volume grows beyond single-server capacity

2. **LangGraph Built-in Memory (Checkpointer)**:
   - **Rejected because**: LangGraph checkpointers are designed for agent state persistence across invocations, not session-based request context
   - Checkpointers require explicit save/load which doesn't match our request/response pattern
   - We need request-level metadata (ingredients, exclusions) rather than agent conversation state

3. **Database-Backed Sessions**:
   - **Rejected because**: Unnecessary I/O overhead for transient conversation data
   - 30-minute TTL doesn't justify persistence
   - Session data is reconstructible from user preferences if lost

**Implementation Approach**:
```python
# Pseudocode structure
session_memory = {
    "session_id": {
        "original_ingredients": [...],
        "original_exclusions": [...],
        "recommended_recipes": [...],
        "last_accessed": timestamp,
        "created_at": timestamp
    }
}
```

---

### 2. Session Identification Strategy

**Decision**: Use a combination of user_id (if available) and request-level session token, falling back to connection-based session tracking for stateless clients.

**Rationale**:
- API server already handles user identification through endpoints like `/v1/{user_id}/ingredients`
- Session can be scoped per user to maintain context across their recipe exploration
- For anonymous users, use client-provided session ID or generate UUID on first request
- Allows flexibility for both authenticated and anonymous usage patterns

**Alternatives Considered**:

1. **Cookie-Based Sessions**:
   - **Rejected because**: API is designed for programmatic access, not browser-based
   - CORS is wide-open for development, cookies add unnecessary complexity
   - Mobile/app clients may not handle cookies well

2. **JWT Tokens**:
   - **Rejected because**: Overkill for session tracking
   - No authentication requirement specified
   - JWTs are immutable, can't update session state easily

3. **Connection-Based (IP + User-Agent)**:
   - **Rejected because**: Unreliable for mobile clients, NAT environments
   - Multiple users behind same IP would collide

**Implementation Approach**:
- Extract `user_id` from request path if available (`/v1/{user_id}/request`)
- Use `user_id` as session key
- If no `user_id`, accept optional `X-Session-ID` header from client
- Generate UUID session ID if neither provided (return in response header for client to reuse)

---

### 3. Memory Cleanup and TTL Management

**Decision**: Implement periodic background task (every 5 minutes) that removes sessions inactive for >30 minutes, plus eager cleanup on each request.

**Rationale**:
- Balances memory usage with cleanup overhead
- Background task prevents unbounded memory growth
- Eager cleanup (check on access) ensures immediate removal of expired sessions
- 5-minute interval is frequent enough to prevent memory bloat while not causing CPU overhead

**Alternatives Considered**:

1. **LRU Cache with Max Size**:
   - **Rejected because**: Doesn't guarantee 30-minute timeout compliance
   - Size limit doesn't map to time-based requirements
   - Could evict active sessions prematurely under load

2. **Cleanup on Every Request**:
   - **Rejected because**: O(n) scan on every request adds latency
   - Better to batch cleanup in background

3. **Python `cachetools` with TTL**:
   - **Considered but unnecessary**: Adds dependency for simple TTL logic
   - Built-in background task is simpler and sufficient

**Implementation Approach**:
```python
# Pseudocode
@app.on_event("startup")
async def start_cleanup_task():
    asyncio.create_task(cleanup_expired_sessions())

async def cleanup_expired_sessions():
    while True:
        await asyncio.sleep(300)  # 5 minutes
        current_time = time.time()
        expired = [sid for sid, data in session_memory.items()
                   if current_time - data["last_accessed"] > 1800]  # 30 min
        for sid in expired:
            del session_memory[sid]
```

---

### 4. Tracking Previously Recommended Recipes

**Decision**: Store recipe names (dishName field) in a list within session memory, append on each response, and use for exclusion in subsequent queries.

**Rationale**:
- Recipe names are unique identifiers from the response schema
- Simple list structure, easy to serialize and query
- Agent can be instructed to exclude specific recipe names in the prompt
- Minimal memory footprint (just recipe name strings)

**Alternatives Considered**:

1. **Store Full Recipe Objects**:
   - **Rejected because**: Wastes memory, only need names for exclusion
   - Recipe details are in vector store, no need to duplicate

2. **Use Vector Embeddings for Similarity Exclusion**:
   - **Rejected because**: Over-engineered for simple "not these exact recipes" requirement
   - Vector similarity would be fuzzy, we want exact exclusion

3. **Set Data Structure**:
   - **Considered**: Would provide O(1) membership check
   - **Using list instead**: Small expected size (10-20 recipes per session), list is simpler and sufficient

**Implementation Approach**:
- After agent returns recommendations, parse JSON response
- Extract `dishName` from each recipe in the array
- Append to `session_memory[session_id]["recommended_recipes"]`
- On `more=true` request, pass this list to agent prompt as "do not recommend these: [list]"

---

### 5. Integration with Existing Agent Prompt System

**Decision**: Extend the system prompt to accept a dynamic exclusion list and modify the `agent_request_additional_format.txt` usage to include previously recommended recipes.

**Rationale**:
- Existing system already uses `agent_request_additional_format.txt` for `more=true` requests
- Template currently only handles ingredient exclusions (`excludeIngredients`)
- Can extend to include recipe name exclusions naturally
- Agent prompt already instructs to use tools and follow constraints, adding exclusion list is straightforward

**Alternatives Considered**:

1. **Create Separate Agent/Chain for more=true**:
   - **Rejected because**: Code duplication, maintenance burden
   - Same underlying logic, just different exclusions

2. **Implement as Tool Rather Than Prompt**:
   - **Rejected because**: Tools are for computation, not filtering logic
   - Prompt-based exclusion is simpler and more transparent

**Implementation Approach**:
```python
# Pseudocode
if request_body.more:
    session = get_or_create_session(user_id)
    excluded_recipes = session.get("recommended_recipes", [])
    excluded_ingredients = request_body.excludeIngredients or []

    prompt = f"""이전 질문의 조건들을 동일하게 적용해서 다른 요리 더 추천해줘.

대신 아래 재료들은 빼줬으면 좋겠어:
{', '.join(excluded_ingredients)}

그리고 이미 추천한 요리는 제외해줘:
{', '.join(excluded_recipes)}"""
```

---

### 6. Handling Edge Cases

**Research Question**: How to handle various edge cases identified in spec?

**Findings**:

1. **No previous context when more=true**:
   - **Decision**: Treat as regular request (per spec Q1 answer)
   - Check if session exists, if not, create new session and process normally
   - Ignore `more` flag silently, log warning for debugging

2. **All recipes exhausted**:
   - **Decision**: Let agent return empty array or best-effort partial results
   - Agent prompt already handles "if no recipes found, return []"
   - User experience: client receives fewer results, can decide whether to clear exclusions

3. **Memory cleared but more=true received**:
   - **Decision**: Same as case 1 - treat as new request
   - This happens naturally if 30-minute timeout expires

4. **Ingredient list changed in DB during session**:
   - **Decision**: Use ingredients from original session for consistency
   - Rationale: User's exploration context should remain stable within a conversation
   - If user wants new ingredients, they should start a new session (don't send `more=true`)

5. **Exclusions eliminate all matches**:
   - **Decision**: Agent returns empty array, documented in response
   - Client can detect empty response and inform user

---

## Technology Stack Additions

**No new dependencies required**:
- Built-in Python `asyncio` for background tasks
- Built-in `time` module for timestamp tracking
- Built-in `uuid` for session ID generation
- Existing FastAPI background task support

**Testing Additions**:
- Add `pytest` to requirements.txt (not currently present)
- Add `pytest-asyncio` for async test support
- Add `freezegun` for time-based test mocking (session expiration tests)

---

## Performance Considerations

**Memory Usage**:
- Estimated per-session memory: ~1-2 KB (ingredients list + recipe names + metadata)
- Assumption: Max 1000 concurrent active sessions = ~2 MB memory
- Negligible impact on server with typical 4-8 GB RAM

**Response Time**:
- Session lookup: O(1) dictionary access, <1ms
- Memory cleanup overhead: 5-minute background task, negligible CPU impact
- No impact on <3 second response time goal

**Concurrency**:
- Python dictionary with asyncio is safe for concurrent reads
- Use `asyncio.Lock` per session for write operations (updating recommended_recipes)
- Minimal contention expected since sessions are user-scoped

---

## Security Considerations

**Session Hijacking**:
- Risk: If session IDs are predictable, users could access others' sessions
- Mitigation: Use UUID4 for session ID generation (cryptographically random)
- Low risk for recipe recommendations (no PII or sensitive data)

**Memory Exhaustion Attack**:
- Risk: Malicious client creates infinite sessions
- Mitigation: 30-minute TTL + periodic cleanup limits growth
- Consider rate limiting at API gateway level if needed (out of scope for this feature)

**Data Leakage**:
- Risk: Session data visible across users
- Mitigation: Session scoped by user_id, no cross-user access possible
- Memory is server-side, not exposed to clients

---

## Summary

All technical unknowns have been resolved:

1. **Session management**: In-memory dictionary with background cleanup
2. **Session identification**: User ID-based with UUID fallback
3. **TTL implementation**: 30-minute timeout with 5-minute cleanup task
4. **Recipe tracking**: List of dishNames in session memory
5. **Agent integration**: Extend existing prompt templates
6. **Edge cases**: Documented handling strategies for all scenarios

No new dependencies required beyond testing libraries. Implementation is straightforward with minimal architectural changes.

**Ready to proceed to Phase 1: Design & Contracts**
