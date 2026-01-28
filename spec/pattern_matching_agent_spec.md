# Agent Specification: Pattern Matching Agent

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**LLD Reference**: lld_1_config_management_platform.md

---

## Question 1: Agent Identity and Purpose

**What is this agent and what problem does it solve?**

The Pattern Matching Agent is a knowledge base management agent that stores, versions, and retrieves approved coding patterns in Confluence. This agent solves the problem of pattern library management by providing a centralized, versioned, and queryable repository of approved architectural and coding patterns.

**Problem Solved**: Without centralized pattern management, patterns are scattered across wikis, code comments, and tribal knowledge. This agent ensures all approved patterns are documented, versioned, searchable, and accessible to all agents and developers.

**Value Provided**:
- Centralized pattern repository for consistent standards
- Version control for pattern evolution tracking
- Fast pattern queries for agent validation workflows
- Pattern metadata management (category, status, approvers)
- Pattern usage tracking across codebase
- Historical audit trail of pattern approvals

---

## Question 2: Core Capabilities

**What are the agent's main capabilities?**

1. **Pattern Storage**: Store new approved patterns in Confluence with metadata
2. **Version Management**: Track pattern versions and evolution history
3. **Pattern Retrieval**: Query patterns by ID, category, language, or keyword
4. **Metadata Management**: Store and update pattern metadata:
   - Pattern ID (unique identifier)
   - Status (DRAFT / APPROVED / DEPRECATED)
   - Version number
   - Category (design pattern / architectural / idiom)
   - Language/framework
   - Approvers (architects who approved)
   - Approval date
   - Usage count (number of instances in codebase)
5. **Pattern Indexing**: Maintain searchable index for fast pattern lookup
6. **Pattern Linking**: Link patterns to LLDs, HLDs, and GitHub PRs
7. **Pattern Deprecation**: Mark patterns as deprecated with replacement guidance
8. **Confluence API Integration**: Create, update, and query Confluence pages

---

## Question 3: Input Requirements

**What inputs does the agent need?**

**Primary Inputs**:
- **New Pattern Data**: Pattern details from LLD Alignment Review Agent
  - Pattern name
  - Pattern type/category
  - Code example
  - Pattern description
  - LLD reference
  - PR number
- **Pattern Action**: STORE_NEW / UPDATE_EXISTING / DEPRECATE / QUERY

**For Pattern Storage**:
- Pattern documentation (markdown format)
- Approver information (from Peer Review Documentation Agent)
- PR metadata (PR number, repository, author)

**For Pattern Query**:
- Query parameters (pattern ID, category, language, keyword)

**Format**: JSON payload from GitHub Actions workflow or agent-to-agent API call

**Preconditions**:
- Confluence API credentials available
- Pattern has passed LLD Alignment Review (for new patterns)
- Pattern has been approved by peer reviewers (for storage)

---

## Question 4: Output Specifications

**What does the agent produce?**

**Primary Outputs**:
- **Pattern Storage Status**: SUCCESS / FAILURE
- **Confluence Page URL**: Link to stored pattern in Confluence
- **Pattern ID**: Unique identifier for the stored pattern
- **Pattern Version**: Version number assigned to pattern

**For Pattern Query**:
- **Pattern Details**: Full pattern data with metadata
- **Pattern List**: List of patterns matching query criteria

**Output Format**:
- JSON response for API calls
- Confluence page (markdown format) for human-readable patterns
- Pattern index (JSON) for fast agent queries

**Artifacts Created**:
- Confluence page in `SCM-PATTERNS` space
- Pattern metadata in page properties
- Version history in Confluence page history
- Pattern index entry for fast lookup
- CloudWatch logs for audit trail

---

## Question 5: Constraints and Limitations

**What are the boundaries and limitations?**

**Operational Constraints**:
- Can only store patterns that have been approved (not draft patterns)
- Cannot modify patterns after approval (only create new versions)
- Limited to Confluence as pattern storage backend (no alternative stores)
- Confluence API rate limits apply (100 requests/minute)

**Limitations**:
- Pattern storage depends on Confluence availability
- Cannot validate pattern quality (only stores approved patterns)
- Search capabilities limited to Confluence search API
- Cannot automatically refactor code to use new patterns
- Pattern versioning follows Confluence page versioning (not semantic versioning)

**Guardrails**:
- NEVER store unapproved patterns in pattern library
- NEVER delete patterns (only deprecate with version history)
- NEVER modify approved patterns in-place (create new versions)
- ALWAYS maintain pattern metadata for traceability

---

## Question 6: Behavioral Patterns and Decision Rules

**How should the agent behave and make decisions?**

**Behavioral Patterns**:
- **Immutable Patterns**: Once approved and stored, patterns are immutable (new versions for changes)
- **Metadata First**: Always store comprehensive metadata for traceability
- **Fail-Safe Storage**: If Confluence unavailable, queue pattern for storage (don't lose approved patterns)
- **Audit Trail**: Log all pattern storage, queries, and deprecations

**Decision Rules**:

**When storing new pattern** (from Peer Review Agent approval):
1. Generate unique pattern ID (e.g., `PTN-JAVA-001`)
2. Create Confluence page in `SCM-PATTERNS` space
3. Set pattern status: APPROVED
4. Set version: 1.0
5. Store pattern metadata in page properties
6. Add pattern to searchable index
7. Return Confluence URL and pattern ID

**When updating existing pattern**:
1. Check if pattern ID exists
2. Create new version (increment version number)
3. Create new Confluence page version
4. Link to previous version in version history
5. Update pattern index with new version

**When deprecating pattern**:
1. Update pattern status to DEPRECATED
2. Add deprecation notice to pattern page
3. Link to replacement pattern (if available)
4. Keep pattern searchable with "deprecated" label
5. Do NOT delete pattern (maintain historical record)

**When querying pattern**:
1. Parse query criteria (ID, category, language, keyword)
2. Query Confluence API or local index
3. Filter by status (exclude DEPRECATED unless requested)
4. Return matching patterns with metadata

**If Confluence unavailable**:
1. Use cached pattern index for queries
2. Queue pattern storage operations for retry
3. Create CloudWatch alarm for Confluence connectivity
4. Fail-safe: block new pattern approvals until Confluence restored

---

## Question 7: Error Handling and Edge Cases

**How should the agent handle errors and edge cases?**

**Error Detection**:
- Confluence API failures (timeout, authentication, rate limiting)
- Duplicate pattern ID (collision)
- Pattern page creation failures
- Index update failures
- Invalid pattern format (missing required fields)

**Error Response**:
- **Confluence Failure**: Queue pattern for retry, use cached index for queries, alert ops team
- **Duplicate Pattern ID**: Increment ID counter, retry with new ID
- **Page Creation Failure**: Retry with exponential backoff (3 attempts), then alert ops team
- **Index Update Failure**: Retry index update (non-blocking), log warning
- **Invalid Pattern Format**: Reject pattern storage, notify Peer Review Agent for correction

**Fallback Strategies**:
- Maintain local pattern index cache (synced every 30 minutes)
- Queue pattern storage operations for retry (up to 24 hours)
- Graceful degradation: read-only mode if Confluence unavailable (use cache)

**Edge Cases**:
- **Pattern ID collision**: Auto-increment ID until unique ID found
- **Pattern already exists with same content**: Skip duplicate storage, return existing pattern ID
- **Pattern spans multiple languages**: Create separate patterns per language with cross-references
- **Pattern has multiple versions in same PR**: Store each version separately with chronological ordering
- **Pattern deprecation without replacement**: Allow deprecation, mark as "no replacement" in metadata

---

## Question 8: Success Criteria

**How do you know the agent succeeded?**

The agent has succeeded when:

1. **Successful Storage**: All approved patterns stored in Confluence with complete metadata
2. **Fast Queries**: Pattern queries respond within 2 seconds (P95)
3. **High Availability**: Pattern library accessible 99.9% of the time
4. **Complete Metadata**: All patterns have required metadata fields populated
5. **Version Integrity**: Pattern version history is complete and traceable
6. **Searchability**: All patterns discoverable via Confluence search or agent queries

**Quality Indicators**:
- Pattern storage success rate > 99.5%
- Query response time P95 < 2 seconds
- Zero pattern data loss (all approved patterns eventually stored)
- Pattern metadata completeness = 100%
- Zero duplicate pattern IDs

**Business Value (ATSQ)**:
- **Expected Time Savings**: 95% ATSQ: 4-hour manual pattern documentation reduced to 12 minutes (2 min agent storage + 10 min human verification of metadata completeness)
- **Baseline Assumption**: Manual pattern documentation = 4 hours (includes writing pattern doc, formatting, linking to LLD/HLD, publishing, indexing)
- **Verification Method**: Human verification (10 min review of metadata and formatting)
- **Category**: Labor Elimination (near-complete automation)

---

## Question 9: Usage Context and Workflow

**When and how is this agent used?**

**Invocation Context**:
- Triggered after Peer Review Documentation Agent approves new pattern
- Runs as Step 4 in PR validation workflow (for new patterns)
- Also invoked by other agents for pattern queries (on-demand)

**Workflow Integration**:

**Pattern Storage Workflow**:
1. **LLD Alignment Review Agent validates pattern** → Pattern is LLD-compliant
2. **Peer Review Documentation Agent approves pattern** → PR merged
3. **GitHub Actions calls Pattern Matching Agent** → Store approved pattern
4. **Agent stores pattern in Confluence** → Creates page with metadata
5. **Agent updates pattern index** → Makes pattern searchable
6. **Workflow proceeds to deployment** → GitHub Actions Workflows Hooks (Step 6)

**Pattern Query Workflow** (used by other agents):
- **Code Best Practises Agent**: Queries patterns at PR validation time
- **Architect Best Practises Agent**: Queries patterns for similarity comparison
- **Developers**: Query patterns via Confluence search

**Workflow Position**: Step 4 in Configuration Management Platform workflow (see Activity Diagram in LLD)

---

## Question 10: Example Interaction

**Provide a concrete example of the agent in action**

### Example 1: Store New Approved Pattern

**Input**:
```json
{
  "action": "STORE_NEW",
  "pr_number": 458,
  "repository": "tonic-scm/order-service",
  "pattern": {
    "name": "Repository Pattern with Caching",
    "type": "Data Access Pattern",
    "category": "architectural",
    "language": "Java",
    "description": "Repository pattern implementation with Spring Cache abstraction for read optimization",
    "code_example": "...",
    "lld_reference": "https://confluence.tonic.com/scm/order-service-lld#section-6.1",
    "approvers": ["architect1@tonic.com", "architect2@tonic.com"],
    "approval_date": "2026-01-28"
  }
}
```

**Processing**:
1. Generate pattern ID: `PTN-JAVA-042`
2. Create Confluence page title: `PTN-JAVA-042: Repository Pattern with Caching`
3. Format pattern documentation as Confluence page (markdown converted to Confluence format)
4. Set page properties (metadata):
   - Pattern ID: PTN-JAVA-042
   - Status: APPROVED
   - Version: 1.0
   - Category: architectural
   - Language: Java
   - Approvers: architect1@tonic.com, architect2@tonic.com
   - Approval Date: 2026-01-28
   - Source PR: tonic-scm/order-service#458
5. Create Confluence page in `SCM-PATTERNS` space
6. Add to pattern index for fast queries
7. Tag with labels: `java`, `repository-pattern`, `caching`, `approved`

**Output**:

**JSON Response**:
```json
{
  "status": "SUCCESS",
  "pattern_id": "PTN-JAVA-042",
  "confluence_url": "https://confluence.tonic.com/display/SCM-PATTERNS/PTN-JAVA-042",
  "version": "1.0",
  "stored_at": "2026-01-28T11:00:00Z"
}
```

**Confluence Page Created**:
```markdown
# PTN-JAVA-042: Repository Pattern with Caching

**Status**: ✅ APPROVED
**Version**: 1.0
**Category**: Architectural Pattern
**Language**: Java / Spring Boot
**Approved By**: architect1@tonic.com, architect2@tonic.com
**Approval Date**: 2026-01-28
**Source PR**: [order-service#458](https://github.com/tonic-scm/order-service/pull/458)
**LLD Reference**: [Order Service LLD - Section 6.1](https://confluence.tonic.com/scm/order-service-lld#section-6.1)

---

## Description

Repository pattern implementation with Spring Cache abstraction for read optimization. This pattern separates data access logic from business logic while providing transparent caching for frequently accessed entities.

## Use Cases

- Data access layer for domain entities
- Read-heavy operations requiring caching
- Abstraction over DynamoDB single table design

## Code Example

```java
@Component
public class OrderRepositoryImpl implements OrderRepository {
    private final DynamoDbClient dynamoDb;

    @Cacheable("orders")
    public Order findById(String orderId) {
        // DynamoDB query implementation
        ...
    }

    @CacheEvict("orders")
    public void save(Order order) {
        // DynamoDB put implementation
        ...
    }
}
```

## Design Constraints (per LLD)

- ✅ Must implement Repository Pattern
- ✅ Caching allowed using Spring Cache abstraction
- ✅ Must use DynamoDB single table design

## Related Patterns

- [PTN-JAVA-015: DynamoDB Single Table Design](https://confluence.tonic.com/display/SCM-PATTERNS/PTN-JAVA-015)
- [PTN-JAVA-028: Spring Cache Configuration](https://confluence.tonic.com/display/SCM-PATTERNS/PTN-JAVA-028)

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-28 | architect1@tonic.com | Initial approval |

---

**Tags**: `java`, `repository-pattern`, `caching`, `approved`, `data-access`
```

**Pattern Index Updated**:
```json
{
  "patterns": [
    {
      "pattern_id": "PTN-JAVA-042",
      "name": "Repository Pattern with Caching",
      "category": "architectural",
      "language": "Java",
      "status": "APPROVED",
      "version": "1.0",
      "tags": ["repository-pattern", "caching", "data-access"],
      "confluence_url": "https://confluence.tonic.com/display/SCM-PATTERNS/PTN-JAVA-042",
      "created_at": "2026-01-28T11:00:00Z"
    }
  ]
}
```

**CloudWatch Log**:
```json
{
  "timestamp": "2026-01-28T11:00:00Z",
  "agent": "pattern_matching_agent",
  "action": "STORE_NEW",
  "pattern_id": "PTN-JAVA-042",
  "status": "SUCCESS",
  "pr_number": 458,
  "repository": "tonic-scm/order-service",
  "storage_time_ms": 3500
}
```

---

### Example 2: Query Patterns by Category

**Input** (from Code Best Practises Agent):
```json
{
  "action": "QUERY",
  "query": {
    "category": "architectural",
    "language": "Java",
    "status": "APPROVED"
  }
}
```

**Processing**:
1. Query Confluence API with filters: category=architectural, language=Java, status=APPROVED
2. Retrieve matching patterns from index (fast lookup)
3. Format results with metadata

**Output**:

**JSON Response**:
```json
{
  "status": "SUCCESS",
  "query_time_ms": 850,
  "result_count": 15,
  "patterns": [
    {
      "pattern_id": "PTN-JAVA-042",
      "name": "Repository Pattern with Caching",
      "category": "architectural",
      "language": "Java",
      "status": "APPROVED",
      "version": "1.0",
      "confluence_url": "https://confluence.tonic.com/display/SCM-PATTERNS/PTN-JAVA-042",
      "description": "Repository pattern implementation with Spring Cache abstraction"
    },
    {
      "pattern_id": "PTN-JAVA-035",
      "name": "Service Layer with Transaction Management",
      "category": "architectural",
      "language": "Java",
      "status": "APPROVED",
      "version": "2.0",
      "confluence_url": "https://confluence.tonic.com/display/SCM-PATTERNS/PTN-JAVA-035",
      "description": "Service layer with declarative transaction management"
    },
    ...
  ]
}
```

---

## Implementation Notes

**Technology Stack**:
- **Language**: Java with Spring Boot
- **Confluence API**: Atlassian REST API v2
- **Pattern Index**: Redis cache for fast queries
- **Cloud**: AWS Lambda or ECS Fargate
- **Monitoring**: AWS CloudWatch

**Configuration**:
- Confluence space key: `SCM-PATTERNS`
- Pattern ID format: `PTN-{LANGUAGE}-{SEQUENCE}`
- Index cache TTL: 30 minutes
- Confluence API rate limit: 100 req/min

**Performance Optimization**:
- Pattern index cached in Redis for sub-second queries
- Bulk pattern retrieval for agent startup
- Async pattern storage (non-blocking for workflow)

---

## Questions and TBCs

| ID | Question/TBC | Priority | Owner |
|----|--------------|----------|-------|
| TBC-PM-001 | Pattern ID format and sequence management | HIGH | Architecture Team |
| TBC-PM-002 | Pattern deprecation workflow and notification | MEDIUM | Product Owner |
| TBC-PM-003 | Pattern usage tracking across codebase | MEDIUM | DevOps Team |
| TBC-PM-004 | Pattern versioning strategy (semantic vs chronological) | MEDIUM | Architecture Team |

---

**End of Specification**
