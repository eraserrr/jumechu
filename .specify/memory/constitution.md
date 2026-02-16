<!--
Sync Impact Report:
- Version change: Initial → 1.0.0
- Initial constitution ratification
- Principles established: 6 core principles
- Templates requiring updates:
  ✅ plan-template.md (verified - Constitution Check section present)
  ✅ spec-template.md (verified - aligned with user story requirements)
  ✅ tasks-template.md (verified - aligned with testing and implementation principles)
- No deferred placeholders
- No follow-up TODOs required
-->

# Jumechu API Constitution

## Core Principles

### I. API-First Architecture

The Jumechu API MUST maintain clear separation between the API server (api_server.py) and the AI agent server (agent_server.py). All client-facing endpoints MUST be exposed through the API server at port 8000, which communicates with the agent server at port 8080 for AI-powered recipe recommendations.

**Rationale**: This separation ensures scalability, allows independent scaling of the AI processing layer, and maintains clear boundaries between business logic and AI operations.

### II. Data-Driven Recipe Recommendations

All recipe recommendations MUST be based on documents stored in the `document/` directory. The system MUST NOT generate synthetic recipes or combine recipes from different sources. Vector similarity search MUST be used to find relevant recipes from the knowledge base.

**Rationale**: Ensures accuracy and reliability of recommendations by grounding all suggestions in verified recipe data, preventing hallucinations and maintaining nutritional integrity critical for the slow-aging health focus.

### III. Database Persistence

User ingredient data MUST be persisted in a relational database using SQLAlchemy with async support. All database operations MUST use async session management. Ingredient updates MUST be atomic - clearing existing ingredients and adding new ones within transactional boundaries.

**Rationale**: Guarantees data consistency and prevents race conditions when users update their refrigerator contents, ensuring accurate recipe matching.

### IV. Observability and Tracing

All AI agent interactions MUST be traced using LangSmith. Trace configuration MUST be loaded from environment variables. Console logging MUST provide clear visual indicators (emoji-prefixed messages) for key operations: document loading, vector store initialization, chain setup, and request processing.

**Rationale**: Enables debugging of complex AI workflows, performance monitoring, and troubleshooting of recommendation quality issues.

### V. Ingredient Matching Intelligence

The system MUST use intelligent ingredient normalization that removes quantities, units, and special characters when comparing user ingredients against recipe requirements. The `compare_ingredients` tool MUST be used to identify missing ingredients by normalizing both user and recipe ingredient lists.

**Rationale**: Provides flexible matching that accommodates variations in how users describe ingredients while maintaining accurate detection of what additional items they need to purchase.

### VI. Health-Focused Guidance (NON-NEGOTIABLE)

Every recipe recommendation MUST include a "warning" field that provides slow-aging health perspective guidance (저속노화 관점). Recommendations MUST consider the health implications of ingredients and preparation methods.

**Rationale**: Aligns with the core mission of promoting slow-aging through healthy dinner recommendations, ensuring every interaction provides educational value beyond just recipe matching.

## API Design Standards

### Request/Response Format

- All endpoints MUST accept and return JSON
- Agent requests MUST use structured request bodies (RequestBody, AgentRequestBody)
- Recipe responses MUST follow the standardized schema: dishName, ingredients (array), recipe (string), recommendedIngredient (string), warning (string)
- Parsing failures MUST return a `raw_answer` field rather than failing silently

### CORS Configuration

- API server MUST enable CORS for all origins during development
- Credentials, methods, and headers MUST be unrestricted for development flexibility
- Production deployment MUST restrict origins to specific allowed domains

### Error Handling

- Exceptions MUST be caught and logged with full stack traces
- Error responses MUST include descriptive error messages
- Chain initialization failures MUST return structured error responses

## Development Workflow

### Environment Configuration

- Sensitive configuration (API keys, database URLs) MUST be stored in `.env` files
- LangSmith configuration MUST be validated and logged at startup
- Database connection strings MUST use async-compatible drivers (asyncmy for MySQL)

### Testing Approach

- Recipe recommendations MUST be testable by comparing actual database content against results
- Ingredient matching MUST be unit-testable with known input/output pairs
- Integration tests SHOULD verify end-to-end flows from API request through agent processing to database updates

### Dependency Management

- Dependencies MUST be tracked in `requirements.txt`
- Core frameworks: FastAPI, LangChain, LangGraph, SQLAlchemy
- Version pinning MUST be used for production stability

## Governance

This constitution supersedes all other development practices. Changes to core principles require:

1. Documentation of the proposed change and rationale
2. Assessment of impact on existing architecture
3. Migration plan for affected components
4. Update of this constitution with incremented version number

All code reviews MUST verify compliance with these principles. Deviations MUST be justified in the Complexity Tracking section of the implementation plan.

The constitution guides project-wide decisions. For feature-specific guidance during active development, refer to the implementation plan for the feature being developed.

**Version**: 1.0.0 | **Ratified**: 2026-02-14 | **Last Amended**: 2026-02-14
