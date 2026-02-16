# Tasks: Memory-Based Additional Recipe Recommendations

**Input**: Design documents from `/specs/001-memory-recommendations/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are NOT included in this task list as they were not explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This project uses a single-project structure at repository root:
- `/api_server.py` - API server (port 8000)
- `/agent_server.py` - Agent server (port 8080)
- `/util/` - Utility modules
- `/entity/` - Database entities
- `/database/` - Database session management

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies for memory management feature

- [X] T001 Add pytest, pytest-asyncio, and freezegun to requirements.txt for testing session management
- [X] T002 [P] Create util/memory/ directory for session management utilities
- [X] T003 [P] Create tests/unit/ and tests/integration/ directories for test organization

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core session memory infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] [US3] Add session_id field to RequestBody class in util/request/request_body.py
- [X] T005 [P] [US3] Add session_id field to AgentRequestBody class in util/request/agent_request_body.py
- [X] T006 [US3] Create session memory data structures in util/memory/session_store.py (session_memory dict, session_locks dict, SessionContext structure)
- [X] T007 [US3] Implement create_session function in util/memory/session_store.py
- [X] T008 [US3] Implement get_or_create_session function in util/memory/session_store.py
- [X] T009 [US3] Implement update_session_recipes async function in util/memory/session_store.py with per-session locking
- [X] T010 [US3] Implement cleanup_expired_sessions async function in util/memory/session_store.py (30-minute TTL, 5-minute interval)
- [X] T011 [US3] Add session memory imports to agent_server.py (import from util.memory.session_store)
- [X] T012 [US3] Add background cleanup task to agent_server.py startup event (asyncio.create_task for cleanup_expired_sessions)
- [X] T013 [US3] Add emoji-prefixed logging for session operations (✨ creation, 🧹 cleanup, 📝 updates) in util/memory/session_store.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Get Additional Recipe Recommendations with Memory Context (Priority: P1) 🎯 MVP

**Goal**: Users can request additional recipe recommendations using `more=true` parameter, with system remembering their original ingredient list and exclusions

**Independent Test**: Make an initial recipe request with specific ingredients, then make a follow-up request with `more=true` and verify different recipes are returned using the original ingredient context

**Acceptance Criteria**:
1. Initial request creates session and returns session_id
2. Subsequent `more=true` request with session_id returns different recipes using original ingredients
3. New exclusions are combined with original context
4. System treats `more=true` without session as new request

### Implementation for User Story 1

- [X] T014 [US1] Modify api_server.py /v1/request endpoint to accept optional session_id from request body
- [X] T015 [US1] Update get_question function in api_server.py to extract session_id from RequestBody
- [X] T016 [US1] Update query function in api_server.py to forward session_id to agent server in AgentRequestBody
- [X] T017 [US1] Modify agent_server.py /v1/request endpoint to handle session_id parameter
- [X] T018 [US1] Add session retrieval logic in agent_server.py: call get_or_create_session at start of request handling
- [X] T019 [US1] Implement session initialization for new requests (more=false): store ingredients from request in session
- [X] T020 [US1] Add logic to detect more=true without valid session: log warning and treat as new request
- [X] T021 [US1] Create build_more_question function in agent_server.py to format question using session context (original ingredients + exclusions + recommended recipes)
- [X] T022 [US1] Update request handler to use build_more_question when more=true and session exists
- [X] T023 [US1] Modify agent_server.py to extract dishName values from parsed_answer after agent response
- [X] T024 [US1] Add call to update_session_recipes after successful agent response with new dishNames
- [X] T025 [US1] Add session_id to response JSON in agent_server.py (always include in return dict)
- [X] T026 [US1] Update api_server.py query function to extract session_id from agent response and include in final response

**Checkpoint**: At this point, User Story 1 should be fully functional - users can make initial requests and get `more` recommendations

---

## Phase 4: User Story 2 - Exclude Previously Recommended Recipes (Priority: P2)

**Goal**: When users request more recommendations, previously suggested recipes are automatically excluded from new results

**Independent Test**: Make multiple sequential `more=true` requests and verify recipe names don't duplicate within the session

**Acceptance Criteria**:
1. Session tracks all recommended recipe names across multiple requests
2. build_more_question includes previously recommended recipes in exclusion list
3. Agent prompt instructs to exclude both ingredient and recipe exclusions
4. Multiple `more=true` requests return unique recipes

### Implementation for User Story 2

- [X] T027 [US2] Update build_more_question function in agent_server.py to include previously recommended recipes in prompt
- [X] T028 [US2] Format recipe exclusion list in prompt: "그리고 이미 추천한 요리는 제외해줘: [comma-separated recipe names]"
- [X] T029 [US2] Verify session.recommended_recipes list is properly retrieved and passed to build_more_question
- [X] T030 [US2] Add logging to show excluded recipes count: "🚫 Excluding {count} previously recommended recipes"

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - duplicate recipe prevention is active

---

## Phase 5: User Story 3 - Session Memory Maintenance (Priority: P1 - Infrastructure)

**Goal**: Automatic session cleanup ensures memory doesn't grow unbounded and sessions expire after 30 minutes of inactivity

**Independent Test**: Create session, wait for 30+ minutes of inactivity, verify session is cleaned up and subsequent `more=true` creates new session

**Acceptance Criteria**:
1. Background task runs every 5 minutes
2. Sessions inactive for >30 minutes are deleted
3. last_accessed timestamp updates on every request
4. Memory usage remains bounded

### Implementation for User Story 3 (Additional Polish)

- [X] T031 [US3] Verify cleanup_expired_sessions background task is started in agent_server.py startup event
- [X] T032 [US3] Add session statistics logging every 10 minutes: "📊 Active sessions: {count}"
- [X] T033 [US3] Test session expiration: create session, simulate 30-minute gap, verify cleanup
- [X] T034 [US3] Add last_accessed timestamp update in get_or_create_session function

**Checkpoint**: All user stories should now be independently functional with proper memory management

---

## Phase 6: Edge Case Handling & Polish

**Purpose**: Handle edge cases and improve robustness

- [X] T035 [P] Handle empty results case: when all recipes excluded, agent returns empty array
- [X] T036 [P] Add validation for session_id format in get_or_create_session (must be non-empty string if provided)
- [X] T037 [P] Update util/request/agent_request_additional_format.txt to document new prompt format with recipe exclusions
- [X] T038 [P] Add error handling for missing dishName in response: log warning if recipe doesn't have dishName field
- [X] T039 Update agent system prompt in agent_server.py to explicitly instruct excluding recommended recipes when provided
- [X] T040 [P] Add logging for session context retrieval: "🔑 Session {id}: {ingredient_count} ingredients, {recipe_count} exclusions"
- [X] T041 [P] Verify backward compatibility: test requests without session_id still work
- [X] T042 [P] Verify backward compatibility: test requests without more parameter still work
- [X] T043 Add comprehensive logging for debugging: log session state before and after each request

---

## Phase 7: Documentation & Final Validation

**Purpose**: Ensure feature is documented and validated

- [X] T044 [P] Add docstrings to all session management functions in util/memory/session_store.py
- [X] T045 [P] Add inline comments explaining session lifecycle in agent_server.py /v1/request handler
- [X] T046 [P] Update quickstart.md with actual implementation notes if any changes from design
- [X] T047 Run manual integration test: initial request → more request → verify different recipes
- [X] T048 Run manual edge case test: more=true without session → verify treated as new request
- [X] T049 Run manual expiration test: verify 30-minute cleanup works
- [X] T050 Code review: verify all emoji logging follows existing patterns (🔍, 📄, ✂️, 🔢, ✅, 💬, 🤖)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) - Core feature implementation
- **User Story 2 (Phase 4)**: Depends on User Story 1 - Extends exclusion logic
- **User Story 3 (Phase 5)**: Infrastructure tasks that run in parallel with US1/US2 implementation
- **Edge Cases (Phase 6)**: Depends on US1, US2, US3 completion
- **Documentation (Phase 7)**: Depends on all implementation phases

### User Story Dependencies

- **User Story 3 (Infrastructure)**: Must complete first (Phase 2) - provides session memory foundation
- **User Story 1 (Core)**: Can start after US3 - implements `more=true` functionality
- **User Story 2 (Enhancement)**: Can start after US1 - adds recipe exclusion to existing flow

**Key Insight**: US3 is actually foundational infrastructure, not a separate user journey. It enables US1 and US2.

### Within Each Phase

**Foundational (Phase 2 - US3)**:
- T004, T005 can run in parallel (different files)
- T006 must complete before T007, T008, T009 (dependencies)
- T007, T008, T009 can run in parallel after T006 (different functions)
- T010 can run in parallel with T007-T009
- T011, T012, T013 must run sequentially (depend on imports)

**User Story 1 (Phase 3)**:
- T014, T015, T016 are sequential (same file, dependent changes in api_server.py)
- T017, T018, T019, T020 are sequential (same file, dependent changes in agent_server.py)
- T021 can be parallel (new function)
- T022, T023, T024, T025 are sequential (same handler function)
- T026 is sequential with T014-T016 (api_server.py)

**User Story 2 (Phase 4)**:
- T027, T028, T029 are sequential (modifying build_more_question)
- T030 is parallel (just logging)

**User Story 3 (Phase 5)**:
- T031, T032, T033, T034 can mostly run in parallel (verification tasks)

**Edge Cases (Phase 6)**:
- T035-T043 can mostly run in parallel (different concerns, different locations)

**Documentation (Phase 7)**:
- T044, T045, T046 can run in parallel (different files)
- T047, T048, T049, T050 should run sequentially (manual testing)

### Parallel Opportunities

**Phase 2 (Foundational)**:
```bash
# Parallel group 1:
Task T004: Add session_id to RequestBody
Task T005: Add session_id to AgentRequestBody

# Parallel group 2 (after T006):
Task T007: create_session function
Task T008: get_or_create_session function
Task T009: update_session_recipes function
Task T010: cleanup_expired_sessions function
```

**Phase 3 (User Story 1)**:
Limited parallelization due to sequential changes in same files.

**Phase 6 (Edge Cases)**:
```bash
# Most edge case tasks can run in parallel:
Task T035: Handle empty results
Task T036: Validate session_id format
Task T037: Update template docs
Task T038: Error handling for missing dishName
Task T040: Session retrieval logging
Task T041: Backward compat test (no session_id)
Task T042: Backward compat test (no more param)
```

---

## Parallel Example: Foundational Phase (US3)

```bash
# Step 1: Launch model updates together
Task T004: "Add session_id field to RequestBody in util/request/request_body.py"
Task T005: "Add session_id field to AgentRequestBody in util/request/agent_request_body.py"

# Step 2: After T006 completes, launch session management functions
Task T007: "Implement create_session in util/memory/session_store.py"
Task T008: "Implement get_or_create_session in util/memory/session_store.py"
Task T009: "Implement update_session_recipes in util/memory/session_store.py"
Task T010: "Implement cleanup_expired_sessions in util/memory/session_store.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 3)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational / US3 (T004-T013) - CRITICAL session infrastructure
3. Complete Phase 3: User Story 1 (T014-T026) - Core `more=true` functionality
4. **STOP and VALIDATE**:
   - Test initial request returns session_id
   - Test `more=true` request returns different recipes
   - Test `more=true` without session treats as new request
5. Deploy/demo MVP

### Incremental Delivery

1. **MVP**: Setup + Foundational + US1 → Basic `more=true` works
2. **Enhancement**: Add US2 (T027-T030) → No duplicate recipes
3. **Robustness**: Add Edge Cases (T035-T043) → Handle all scenarios
4. **Polish**: Add Documentation (T044-T050) → Production ready

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With 2 developers:

1. **Together**: Complete Setup (Phase 1) + Foundational (Phase 2)
2. **Split work**:
   - Developer A: User Story 1 core implementation (T014-T026)
   - Developer B: User Story 3 polish (T031-T034) + prepare US2 (T027 prep)
3. **Sequence**: US2 (T027-T030) → Edge Cases (T035-T043) → Documentation (T044-T050)

---

## Task Summary

**Total Tasks**: 50

**Tasks per User Story**:
- Setup (Phase 1): 3 tasks
- US3 - Foundational Infrastructure (Phase 2): 10 tasks
- US1 - Core Feature (Phase 3): 13 tasks
- US2 - Recipe Exclusion Enhancement (Phase 4): 4 tasks
- US3 - Memory Maintenance Polish (Phase 5): 4 tasks
- Edge Cases & Polish (Phase 6): 9 tasks
- Documentation (Phase 7): 7 tasks

**Parallel Opportunities**:
- Phase 1: 2 parallel tasks (T002, T003)
- Phase 2: 6 parallel tasks in 2 groups
- Phase 6: 8 parallel tasks
- Phase 7: 3 parallel tasks (documentation)

**Critical Path**:
1. Setup (3 tasks)
2. Foundational infrastructure (10 tasks)
3. US1 core implementation (13 tasks)
4. US2 enhancement (4 tasks)
5. Edge cases (9 tasks)
6. Documentation (7 tasks)

**MVP Scope** (Phase 1-3):
- 26 tasks total
- Delivers core `more=true` functionality
- Includes session memory and automatic cleanup
- Ready for user testing and feedback

**Success Metrics**:
- All FR requirements from spec.md implemented
- All acceptance scenarios testable
- 30-minute session expiration working
- Response time <3 seconds for `more=true` requests
- Backward compatibility maintained (existing clients work)

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- US3 is infrastructure, not a user-facing story - enables US1 and US2
- Each user story should be independently testable
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- All file paths are absolute from repository root
- Follow existing emoji logging patterns in codebase
- No tests included (not requested in spec)
- Session management uses asyncio for concurrency
- Memory cleanup runs automatically via background task
