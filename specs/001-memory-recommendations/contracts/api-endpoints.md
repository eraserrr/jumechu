# API Contracts: Memory-Based Additional Recipe Recommendations

**Feature**: 001-memory-recommendations
**Date**: 2026-02-16
**Status**: Complete

## Overview

This document defines the API contract changes required to support conversation memory and the `more=true` parameter. The contracts extend the existing `/v1/request` endpoint without breaking backward compatibility.

---

## Modified Endpoints

### POST /v1/request

**Description**: Request recipe recommendations based on available ingredients. Supports continuation via `more=true` to get additional recommendations using conversation memory.

**URL**: `/v1/request`

**Method**: `POST`

**Headers**:
```
Content-Type: application/json
X-Session-ID: <optional-session-id>  [NEW - Optional]
```

**Request Body**:

```json
{
    "ingredients": ["string"],
    "excludeIngredients": ["string"],  // Optional
    "more": boolean,                   // Optional, defaults to false
    "session_id": "string"             // [NEW] Optional
}
```

**Request Body Schema**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `ingredients` | array[string] | Yes (unless more=true) | - | List of available ingredients. Ignored when `more=true` (uses session memory) |
| `excludeIngredients` | array[string] | No | `[]` | Ingredients to exclude from recommendations |
| `more` | boolean | No | `false` | If true, retrieve additional recommendations using conversation memory |
| `session_id` | string | No | auto-generated | Session identifier for conversation continuity. If not provided, server generates one |

**Request Validation**:

- If `more=false` or absent:
  - `ingredients` MUST be non-empty array
  - `excludeIngredients` is optional
  - `session_id` is optional

- If `more=true`:
  - `ingredients` is ignored (session memory used instead)
  - `excludeIngredients` is optional (combines with original exclusions)
  - `session_id` is optional (if absent, creates new session and treats as regular request)

**Response Body** (Success):

```json
{
    "answer": [
        {
            "dishName": "string",
            "ingredients": ["string"],
            "recipe": "string",
            "recommendedIngredient": "string",
            "warning": "string"
        }
    ],
    "session_id": "string"  // [NEW] Always present
}
```

**Response Schema**:

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `answer` | array[RecipeRecommendation] | Yes | List of recommended recipes (may be empty) |
| `answer[].dishName` | string | Yes | Name of the dish |
| `answer[].ingredients` | array[string] | Yes | Ingredients required for this recipe |
| `answer[].recipe` | string | Yes | Cooking instructions |
| `answer[].recommendedIngredient` | string | Yes | Ingredients user needs to purchase, or "모든 재료가 있습니다" |
| `answer[].warning` | string | Yes | Health guidance from slow-aging perspective (저속노화 관점) |
| `session_id` | string | Yes | Session ID for use in subsequent requests (NEW) |

**Status Codes**:

| Code | Description | Response Body |
|------|-------------|---------------|
| 200 | Success | Recipe recommendations with session_id |
| 400 | Bad Request | `{"error": "Invalid request body"}` |
| 500 | Internal Server Error | `{"error": "Error message"}` |
| 503 | Service Unavailable | `{"error": "Recipe chain is not initialized"}` |

**Response Headers**:
```
Content-Type: application/json
X-Session-ID: <session-id>  [NEW - Optional mirror of session_id in body]
```

---

## Request/Response Examples

### Example 1: Initial Recipe Request (No Session)

**Request**:
```http
POST /v1/request HTTP/1.1
Content-Type: application/json

{
    "ingredients": ["양파", "소시지", "토마토"],
    "excludeIngredients": [],
    "more": false
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "answer": [
        {
            "dishName": "소시지 토마토 볶음",
            "ingredients": ["소시지", "토마토", "양파", "올리브유"],
            "recipe": "1. 양파를 슬라이스하고 토마토는 큐브로 자릅니다...",
            "recommendedIngredient": "올리브유",
            "warning": "소시지는 가공육이므로 과도한 섭취는 피하세요. 토마토의 리코펜 성분은 가열 시 흡수율이 높아집니다."
        },
        {
            "dishName": "토마토 소시지 스튜",
            "ingredients": ["소시지", "토마토", "양파", "마늘"],
            "recipe": "1. 소시지를 적당한 크기로 자릅니다...",
            "recommendedIngredient": "마늘",
            "warning": "저속노화를 위해 나트륨 함량이 낮은 소시지를 선택하세요."
        }
    ],
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

### Example 2: Request More Recommendations (With Session)

**Request**:
```http
POST /v1/request HTTP/1.1
Content-Type: application/json

{
    "ingredients": [],
    "excludeIngredients": ["소시지"],
    "more": true,
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Internal Processing**:
- System retrieves session: `original_ingredients = ["양파", "소시지", "토마토"]`
- System retrieves session: `recommended_recipes = ["소시지 토마토 볶음", "토마토 소시지 스튜"]`
- Combines exclusions: `["소시지"]` (from request) + `[]` (from original) = `["소시지"]`
- Excludes recipes: `["소시지 토마토 볶음", "토마토 소시지 스튜"]`
- Agent query: "Use ingredients 양파, 소시지, 토마토 but exclude 소시지 and don't recommend these recipes: 소시지 토마토 볶음, 토마토 소시지 스튜"

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "answer": [
        {
            "dishName": "토마토 양파 샐러드",
            "ingredients": ["토마토", "양파", "발사믹 식초", "올리브유"],
            "recipe": "1. 토마토와 양파를 얇게 슬라이스합니다...",
            "recommendedIngredient": "발사믹 식초, 올리브유",
            "warning": "신선한 채소는 비타민C와 항산화 성분이 풍부하여 저속노화에 도움이 됩니다."
        }
    ],
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

### Example 3: more=true Without Session (Edge Case)

**Request**:
```http
POST /v1/request HTTP/1.1
Content-Type: application/json

{
    "ingredients": ["당근", "감자"],
    "excludeIngredients": [],
    "more": true,
    "session_id": "expired-or-invalid-session"
}
```

**Internal Processing**:
- Session not found (expired or invalid)
- System treats as new request (ignores `more=true`)
- Uses provided `ingredients` from request body
- Creates new session with `session_id = generated UUID`

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "answer": [
        {
            "dishName": "당근 감자 조림",
            "ingredients": ["당근", "감자", "간장", "설탕"],
            "recipe": "1. 당근과 감자를 적당한 크기로 자릅니다...",
            "recommendedIngredient": "간장, 설탕",
            "warning": "감자는 혈당 지수가 높으므로 적당량 섭취를 권장합니다."
        }
    ],
    "session_id": "f9e8d7c6-b5a4-3210-9876-543210fedcba"
}
```

---

### Example 4: No Results Available (All Recipes Excluded)

**Request**:
```http
POST /v1/request HTTP/1.1
Content-Type: application/json

{
    "ingredients": [],
    "excludeIngredients": [],
    "more": true,
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Scenario**: User has already received all available recipes matching their ingredients.

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "answer": [],
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Note**: Client should detect empty `answer` array and inform user that no more recipes are available.

---

## Backward Compatibility

### Existing Clients (No Changes Required)

**Scenario**: Client sends request without `session_id` or `more` fields.

**Request**:
```json
{
    "ingredients": ["양파", "소시지"],
    "excludeIngredients": []
}
```

**Behavior**:
- System generates `session_id` automatically
- Response includes `session_id` (client can ignore if not needed)
- Functionally identical to pre-feature behavior

**Response**:
```json
{
    "answer": [...],
    "session_id": "auto-generated-uuid"
}
```

**Impact**: None - existing clients continue to work without modification.

---

## Internal API: API Server → Agent Server

**Endpoint**: POST http://localhost:8080/v1/request

**Request Body** (Extended):

```json
{
    "question": "string or dict",
    "more": boolean,           // Optional
    "session_id": "string"     // [NEW] Optional
}
```

**Changes**:
- API server now forwards `session_id` to agent server
- Agent server uses `session_id` to retrieve/update session memory
- `question` field for `more=true` requests is formatted using session context

**Example** (more=true):
```json
{
    "question": "이전 질문의 조건들을 동일하게 적용해서 다른 요리 더 추천해줘.\n\n원래 재료: 양파, 소시지, 토마토\n\n대신 아래 재료들은 빼줬으면 좋겠어:\n소시지\n\n그리고 이미 추천한 요리는 제외해줘:\n소시지 토마토 볶음, 토마토 소시지 스튜",
    "more": true,
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## Session Management Endpoints (Optional Future Enhancement)

**Not implemented in this feature**, but reserved for future extension:

### GET /v1/sessions/{session_id}

Retrieve current session state (debugging/admin use).

### DELETE /v1/sessions/{session_id}

Explicitly clear a session (user-initiated "start fresh").

---

## Contract Summary

**Modified**:
- POST /v1/request (added `session_id` field to request and response)

**New Fields**:
- Request: `session_id` (optional string)
- Response: `session_id` (always present string)

**Backward Compatible**: Yes
- Existing clients without `session_id` continue to work
- New `session_id` response field can be ignored by legacy clients

**Breaking Changes**: None

**API Version**: No version increment required (backward compatible extension)
