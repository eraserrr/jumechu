# Implementation Plan: Memory-Based Additional Recipe Recommendations

**Branch**: `001-memory-recommendations` | **Date**: 2026-02-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-memory-recommendations/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement conversation memory for the recipe recommendation system to enable users to request additional recipe recommendations using the `more=true` parameter. When `more=true` is set, the system will retrieve the original ingredient list and exclusions from memory, combine them with any newly specified exclusions, and return different recipes while excluding previously recommended ones. Memory will persist for 30 minutes of inactivity per session.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: FastAPI 0.115, LangChain 0.3, LangGraph 0.2, LangSmith 0.2, SQLAlchemy 2.0
**Storage**: In-memory session storage for conversation context (30-minute TTL); MySQL with asyncmy driver for user ingredient data
**Testing**: pytest (to be added for memory management and session handling)
**Target Platform**: Linux/macOS server
**Project Type**: API server (dual-server architecture: api_server.py + agent_server.py)
**Performance Goals**: <3 seconds response time for `more=true` requests; handle concurrent sessions efficiently
**Constraints**: 30-minute memory timeout; in-memory only (no persistent conversation storage)
**Scale/Scope**: Support multiple concurrent user sessions with independent conversation contexts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. API-First Architecture ✅

**Compliance**: PASS

- API server (port 8000) will continue to receive client requests and forward to agent server (port 8080)
- No changes to server separation architecture
- `more` parameter will flow through existing request pipeline

**Justification**: N/A - fully compliant

---

### II. Data-Driven Recipe Recommendations ✅

**Compliance**: PASS

- All recommendations (including `more=true` requests) will use vector similarity search on document/ recipes
- No synthetic recipe generation
- Memory system only tracks context and exclusions, not recipe generation

**Justification**: N/A - fully compliant

---

### III. Database Persistence ✅

**Compliance**: PASS

- User ingredient data remains in MySQL with SQLAlchemy async operations
- Conversation memory is separate concern (in-memory only)
- No changes to database transaction boundaries

**Justification**: N/A - fully compliant

---

### IV. Observability and Tracing ✅

**Compliance**: PASS

- LangSmith tracing will cover `more=true` requests
- Console logging will include memory-related operations (session creation, context retrieval, cleanup)
- Follow existing emoji-prefixed logging patterns

**Justification**: N/A - fully compliant

---

### V. Ingredient Matching Intelligence ✅

**Compliance**: PASS

- `compare_ingredients` tool will continue to work for all recommendations
- Memory system doesn't affect ingredient normalization logic

**Justification**: N/A - fully compliant

---

### VI. Health-Focused Guidance ✅

**Compliance**: PASS

- All recommendations (including from `more=true`) will include "warning" field with slow-aging guidance
- No changes to recommendation quality standards

**Justification**: N/A - fully compliant

---

**GATE STATUS**: ✅ PASSED - All constitutional principles respected, proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-memory-recommendations/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
/
├── api_server.py         # API server (port 8000) - handles /v1/request endpoint
├── agent_server.py       # AI agent server (port 8080) - processes recipe recommendations
├── database/
│   └── session.py        # Database session management
├── entity/
│   ├── ingredient.py     # Ingredient entity
│   └── user.py           # User entity
├── util/
│   ├── request/
│   │   ├── agent_request_body.py
│   │   ├── request_body.py
│   │   ├── agent_request_format.json
│   │   └── agent_request_additional_format.txt
│   ├── api_uri.py
│   └── base_ingredients.py
├── document/             # Recipe text files for vector store
└── tests/               # Test suite (to be expanded)
    ├── unit/            # Unit tests for memory management
    └── integration/     # End-to-end tests for more=true flow
```

**Structure Decision**: This is a single-project API server implementation with a dual-server architecture (API server + Agent server). The structure aligns with the existing codebase layout. Memory management will be added to `agent_server.py` with supporting utilities in a new `util/memory/` directory.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitutional violations. All principles are fully respected by this feature implementation.
