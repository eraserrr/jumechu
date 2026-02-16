# Feature Specification: Memory-Based Additional Recipe Recommendations

**Feature Branch**: `001-memory-recommendations`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: "요청에 more이 true인 경우 메모리를 이용해서 추가적으로 추천해주는 기능"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get Additional Recipe Recommendations with Memory Context (Priority: P1)

Users want to receive additional recipe recommendations that remember their previous request context, including the ingredients they had and any exclusions they specified, without having to re-specify those details.

**Why this priority**: This is the core functionality that provides continuity in the conversation flow and improves user experience by maintaining context across multiple recommendation requests. It eliminates the need for users to repeatedly specify their available ingredients.

**Independent Test**: Can be fully tested by making an initial recipe request with specific ingredients, then making a follow-up request with `more=true`, and verifying that the system returns different recipes while respecting the original ingredient context and any newly specified exclusions.

**Acceptance Scenarios**:

1. **Given** a user has made an initial recipe recommendation request with their available ingredients, **When** they make a subsequent request with `more=true` and specify ingredients to exclude, **Then** the system returns different recipe recommendations that still match their original ingredient list but exclude the specified ingredients.

2. **Given** a user receives recipe recommendations, **When** they request more recommendations (`more=true`) without specifying additional exclusions, **Then** the system provides additional recipe recommendations based on the same original ingredient context.

3. **Given** a user has not made any previous recipe requests, **When** they send a request with `more=true`, **Then** the system treats it as a regular new request and ignores the `more` flag, processing it based on the current ingredient list provided.

---

### User Story 2 - Exclude Previously Recommended Recipes (Priority: P2)

Users want to ensure that when requesting additional recommendations, they don't receive recipes that were already suggested to them in previous responses.

**Why this priority**: Prevents user frustration from seeing duplicate recommendations and makes better use of the recipe database by exploring more options.

**Independent Test**: Can be tested by making multiple sequential requests with `more=true` and verifying that recipe names in subsequent responses don't duplicate those from earlier responses within the same session.

**Acceptance Scenarios**:

1. **Given** a user has received a set of recipe recommendations, **When** they request more recommendations (`more=true`), **Then** the system excludes the previously recommended recipe names from the new results.

2. **Given** a user has made multiple `more=true` requests in sequence, **When** they request additional recommendations, **Then** the system excludes all recipes recommended in the current conversation session.

---

### User Story 3 - Maintain Conversation Context Across Requests (Priority: P1)

The system must maintain conversation memory so that follow-up requests with `more=true` can access the original request parameters without requiring the user to resend them.

**Why this priority**: This is fundamental infrastructure that enables the feature to work. Without conversation memory, the `more=true` parameter has no context to operate on.

**Independent Test**: Can be tested by verifying that the agent server maintains message history and can retrieve previous request context when processing a `more=true` request.

**Acceptance Scenarios**:

1. **Given** a user makes an initial recipe request, **When** the agent server processes the request, **Then** it stores the request context (ingredients, exclusions) in conversation memory.

2. **Given** a user makes a follow-up request with `more=true`, **When** the agent server retrieves the conversation history, **Then** it successfully accesses the original ingredient list and request parameters.

3. **Given** conversation memory contains previous requests, **When** the user specifies new exclusions with `more=true`, **Then** the system combines the original context with new exclusions for the query.

---

### Edge Cases

- What happens when `more=true` is sent but there is no previous conversation context in memory? (System treats it as a regular request)
- What happens when the user has already seen all available recipes matching their ingredients and requests more?
- How does the system handle memory cleanup after extended periods of inactivity or when memory limits are reached? (Memory automatically expires after 30 minutes of inactivity)
- What happens if the user's original ingredient list has changed in the database but they request `more=true` based on old context?
- How does the system behave when `excludeIngredients` in a `more=true` request eliminates all possible recipe matches?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect when a request includes `more=true` parameter in the request body.
- **FR-002**: System MUST maintain conversation memory that stores the context of previous recipe recommendation requests, including the original ingredient list and any exclusions.
- **FR-003**: System MUST retrieve the previous request context from memory when processing a `more=true` request.
- **FR-004**: System MUST combine the original ingredient context with any newly specified `excludeIngredients` when processing `more=true` requests.
- **FR-005**: System MUST track previously recommended recipe names within a conversation session to avoid duplicate recommendations.
- **FR-006**: System MUST exclude previously recommended recipes when generating results for `more=true` requests.
- **FR-007**: System MUST format the question/query for the AI agent to include the instruction to provide different recommendations while maintaining the original ingredient constraints.
- **FR-008**: System MUST treat requests with `more=true` as regular new requests when no previous conversation context exists, ignoring the `more` flag and processing based on the current request's ingredient list.
- **FR-009**: System MUST apply the same recipe validation rules (database-only recipes, no synthetic combinations) to `more=true` requests as regular requests.
- **FR-010**: System MUST continue to use the `compare_ingredients` tool to identify missing ingredients for each recommended recipe in `more=true` responses.

### Key Entities

- **Conversation Memory**: Stores the history of user requests and system responses for a session, including original ingredients, exclusions, and previously recommended recipe names. The memory persists across multiple requests within the same user session.

- **Recipe Recommendation Request**: Extended to include a `more` boolean flag and updated to reference conversation memory when `more=true`. Contains user ingredients (from memory or current request), exclusions (combined from memory and current request), and session identifier.

- **Exclusion List**: Dynamically built list that combines user-specified ingredient exclusions with the names of previously recommended recipes to ensure variety in recommendations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can request additional recipe recommendations by setting `more=true` without re-specifying their original ingredient list, receiving different recipes in under 3 seconds.

- **SC-002**: When users specify ingredients to exclude in a `more=true` request, the system returns recommendations that exclude both those ingredients and previously suggested recipes from the current session.

- **SC-003**: The system successfully maintains conversation context for 30 minutes of inactivity per session, automatically clearing memory after this timeout period.

- **SC-004**: 95% of `more=true` requests return at least one new recipe recommendation that was not previously suggested in the session, when sufficient recipes exist in the database.

- **SC-005**: Users requesting additional recommendations receive responses that maintain the same quality standards (health warnings, accurate ingredient matching) as initial recommendations.

## Assumptions

- **A-001**: The current API server and agent server architecture will be maintained, with the API server forwarding `more=true` requests to the agent server.

- **A-002**: Conversation memory will be stored in-memory on the agent server with a 30-minute inactivity timeout. Memory is automatically cleared after 30 minutes of no requests from a session. No persistent storage across server restarts is required.

- **A-003**: Each user session is identified implicitly through the HTTP request flow, and the system will track conversation history per-session basis.

- **A-004**: The existing `agent_request_additional_format.txt` file provides the base template for formatting `more=true` requests to the AI agent.

- **A-005**: Memory management and cleanup will be handled through standard practices (e.g., session expiration, LRU cache) and does not require sophisticated distributed memory systems initially.

- **A-006**: Recipe database has sufficient variety to support multiple rounds of recommendations for common ingredient combinations.
