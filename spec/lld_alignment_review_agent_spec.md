# Agent Specification: LLD Alignment Review Agent

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**LLD Reference**: lld_1_config_management_platform.md

---

## Question 1: Agent Identity and Purpose

**What is this agent and what problem does it solve?**

The LLD Alignment Review Agent is an AI-powered validation agent that ensures code changes with new patterns align with the Low-Level Design (LLD) specifications stored in Confluence. This agent solves the problem of architectural drift where developers introduce patterns that contradict or deviate from the documented system design.

**Problem Solved**: Without LLD validation, new patterns can be implemented in ways that violate the documented architecture, leading to inconsistencies between design documents and actual code. This creates maintenance challenges, onboarding difficulties, and potential system integration issues.

**Value Provided**:
- Enforces alignment between code implementation and LLD specifications
- Prevents architectural drift and design document obsolescence
- Catches design violations early in development (at PR stage)
- Ensures new patterns respect system boundaries, interfaces, and contracts
- Maintains traceability between design and implementation

---

## Question 2: Core Capabilities

**What are the agent's main capabilities?**

1. **LLD Retrieval**: Query Confluence API to retrieve relevant LLD documents for the component
2. **Design Specification Parsing**: Extract design constraints, interfaces, contracts, and architectural rules from LLD
3. **Code-to-Design Mapping**: Map code changes to LLD specifications (classes, methods, interfaces)
4. **Deviation Detection**: Identify deviations between code implementation and LLD specifications
5. **Compliance Validation**: Validate that new patterns comply with:
   - Component boundaries and responsibilities
   - Interface contracts and signatures
   - Data models and schemas
   - Non-functional requirements (performance, security)
   - Dependency constraints
6. **Deviation Reporting**: Generate detailed reports of LLD deviations
7. **PR Commentary**: Post actionable feedback to GitHub PR
8. **Jira Integration**: Trigger Jira ticket creation for LLD deviations
9. **Fast Validation**: Complete LLD validation within 20-second SLA

---

## Question 3: Input Requirements

**What inputs does the agent need?**

**Primary Inputs**:
- **Pull Request Data**: PR number, commit SHA, modified files
- **New Pattern Documentation**: Pattern details from Architect Best Practises Agent
- **Code Files**: Source code files with new patterns
- **Component Context**: Repository name, service name, component name

**External Data Sources**:
- **Confluence LLD Documents**: LLD specifications for the component (via Confluence API)
- **GitHub API**: PR metadata, code diff, file structure

**Format**: JSON payload from GitHub Actions workflow (Step 3 in workflow)

**Preconditions**:
- Architect Best Practises Agent detected new pattern (this agent only runs for new patterns)
- LLD document exists in Confluence for the component
- LLD document is up-to-date and accessible
- New pattern documentation is available

---

## Question 4: Output Specifications

**What does the agent produce?**

**Primary Outputs**:
- **Compliance Status**: LLD_COMPLIANT / LLD_DEVIATION_FOUND
- **Deviation Report** (if deviations found):
  - LLD section violated
  - Expected behavior per LLD
  - Actual implementation in code
  - Impact assessment (minor/major/critical)
  - Recommended fix
- **GitHub PR Comment**: Detailed feedback with LLD references
- **Jira Ticket Trigger**: Signal to Jira Integration Agent if deviations found
- **Workflow Decision**: PROCEED_TO_PATTERN_STORAGE / REQUIRE_LLD_FIX

**Output Format**:
- JSON status response for GitHub Actions workflow
- Markdown-formatted PR comment with LLD links
- Jira ticket payload (if deviations found)

**Artifacts Created**:
- PR comment with deviation details and LLD references
- CloudWatch logs for audit trail
- Jira ticket (via Jira Integration Agent) if deviations found

---

## Question 5: Constraints and Limitations

**What are the boundaries and limitations?**

**Operational Constraints**:
- Must complete LLD validation within 20 seconds
- Can only validate against documented LLD specifications (no undocumented design)
- Limited to component-level LLD (not system-wide architectural review)
- Cannot validate business logic correctness (only design alignment)

**Limitations**:
- LLD documents must be up-to-date (agent cannot detect stale LLDs)
- Cannot infer implicit design constraints not documented in LLD
- Requires structured LLD format in Confluence for parsing
- May miss subtle design violations that are semantically incorrect but structurally compliant
- Limited to static analysis (cannot detect runtime behavior deviations)

**Guardrails**:
- NEVER approve code with LLD deviations without human review
- NEVER modify code or LLD documents directly (read-only validation)
- ALWAYS create Jira ticket for LLD deviations before blocking PR
- NEVER skip LLD validation when new patterns are detected

---

## Question 6: Behavioral Patterns and Decision Rules

**How should the agent behave and make decisions?**

**Behavioral Patterns**:
- **Strict Validation**: Any deviation from LLD is flagged (no tolerance for "close enough")
- **Actionable Feedback**: PR comments must include LLD section references and specific fix guidance
- **Non-Blocking for Minor Deviations**: Allow architectural review to decide (don't auto-block PR)
- **Link to Source**: Always provide Confluence links to LLD sections in violation reports

**Decision Rules**:

**When new pattern is detected (from Architect Agent)**:
1. Retrieve relevant LLD document from Confluence (based on repository/component)
2. Parse LLD for design constraints, interfaces, contracts
3. Map new pattern to LLD specifications
4. Validate alignment:
   - Component boundaries respected?
   - Interface contracts honored?
   - Data models consistent?
   - NFRs (performance, security) met?
   - Dependencies allowed per LLD?
5. If deviations found → Generate report, post PR comment, trigger Jira ticket → REQUIRE_LLD_FIX
6. If LLD compliant → PROCEED_TO_PATTERN_STORAGE

**Deviation Severity Classification**:
- **CRITICAL**: Violates interface contract, breaks component boundaries, security violation
- **MAJOR**: Performance requirement violation, data model inconsistency, disallowed dependency
- **MINOR**: Naming convention deviation, documentation inconsistency, non-breaking enhancement

**If LLD document not found**:
1. Create CloudWatch alarm (missing LLD is critical failure)
2. Block PR with explanation: "LLD document required for component"
3. Create Jira ticket for architecture team to create LLD

**If LLD document is ambiguous or incomplete**:
1. Flag ambiguity in PR comment
2. Request architectural clarification in Jira ticket
3. Allow PR to proceed to Peer Review (human architects will resolve)

---

## Question 7: Error Handling and Edge Cases

**How should the agent handle errors and edge cases?**

**Error Detection**:
- Confluence API failures (timeout, authentication)
- LLD document missing or corrupted
- LLD document parsing errors (unstructured format)
- Code-to-LLD mapping failures (cannot find relevant LLD section)
- Validation timeout (>20 seconds)

**Error Response**:
- **Confluence Failure**: Block PR with explanation, create CloudWatch alarm
- **Missing LLD**: Block PR and require LLD creation before proceeding
- **LLD Parsing Error**: Flag in PR comment, route to human architectural review
- **Mapping Failure**: Proceed with warning (cannot validate without mapping)
- **Timeout**: Block PR with explanation, create CloudWatch alarm for investigation

**Fallback Strategies**:
- Maintain cached LLD documents (refreshed every hour)
- If primary LLD validation fails, use simpler structural validation (interfaces, dependencies)
- Graceful degradation: partial validation better than no validation

**Edge Cases**:
- **LLD allows multiple implementation approaches**: Accept any compliant approach, document which was chosen
- **New pattern introduces breaking change**: Flag as CRITICAL deviation, require architectural review
- **Test code not in LLD scope**: Skip LLD validation for test files (or use test-specific LLD)
- **Refactoring without new patterns**: This agent should not be invoked (Architect Agent skips to deployment)
- **Pattern partially compliant**: Flag as MAJOR deviation, provide specific non-compliant aspects

---

## Question 8: Success Criteria

**How do you know the agent succeeded?**

The agent has succeeded when:

1. **Fast Validation**: LLD alignment validated within 20-second SLA
2. **Accurate Deviation Detection**: All LLD deviations correctly identified with zero false positives
3. **Clear Reporting**: Developers receive actionable feedback with LLD references and fix guidance
4. **Proper Routing**: LLD-compliant patterns proceed to Pattern Matching Agent, deviations create Jira tickets
5. **Jira Integration**: Deviation tickets created with PR links and LLD references
6. **Audit Trail**: All validation results logged to CloudWatch

**Quality Indicators**:
- LLD deviation detection accuracy > 95% (validated by architectural reviews)
- Analysis time P95 < 18 seconds, P99 < 20 seconds
- Architect review confirms all flagged deviations are valid (low false positive rate)
- Zero LLD-violating patterns merged without detection

**Business Value (ATSQ)**:
- **Expected Time Savings**: 82.5% ATSQ: 4-hour LLD alignment review reduced to 42 minutes (20 sec agent validation + 41.67 min human architectural review)
- **Baseline Assumption**: Manual LLD review = 4 hours (includes LLD document reading, code comparison, deviation identification)
- **Verification Method**: Human verification by architects (design alignment requires architectural judgment)
- **Category**: Labor Reduction

---

## Question 9: Usage Context and Workflow

**When and how is this agent used?**

**Invocation Context**:
- Triggered automatically by GitHub Actions when Architect Best Practises Agent detects new pattern
- Runs as Step 3 in PR validation workflow (conditional step)
- Non-interactive: runs automatically without human intervention

**Workflow Integration**:

1. **Architect Best Practises Agent detects new pattern** → GitHub Actions calls LLD Alignment Review Agent
2. **Agent retrieves LLD document** → Queries Confluence API for component's LLD
3. **Agent validates alignment** → Compares code to LLD specifications
4. **If LLD_DEVIATION_FOUND**:
   - Agent posts PR comment with deviation details
   - Agent triggers Jira Integration Agent
   - PR requires LLD fix or architectural approval
   - Developer updates PR or architects approve deviation (loop back to validation)
5. **If LLD_COMPLIANT**:
   - Agent reports success
   - Workflow proceeds to **Pattern Matching Agent** (Step 4)

**Workflow Position**: Step 3 in Configuration Management Platform workflow (see Activity Diagram in LLD)

**Conditional Execution**: Only runs when Architect Agent finds new patterns (not for every PR)

---

## Question 10: Example Interaction

**Provide a concrete example of the agent in action**

### Example 1: LLD Deviation Detected

**Input**:
```json
{
  "event": "architect_agent.new_pattern_found",
  "pr_number": 456,
  "repository": "tonic-scm/payment-service",
  "component": "PaymentProcessor",
  "new_pattern": {
    "name": "Circuit Breaker with Gateway Composition",
    "type": "Resilience Pattern",
    "files": ["src/main/java/com/tonic/payment/PaymentProcessor.java"]
  }
}
```

**LLD Specification (from Confluence)**:
```markdown
## PaymentProcessor Component (LLD Section 5.2)

### Design Constraints
- Must use Retry Pattern for external service calls (max 3 retries)
- Circuit Breaker NOT allowed (conflicts with centralized resilience service)
- All external calls must go through PaymentGatewayProxy

### Interface Contract
```java
public interface PaymentGateway {
    PaymentResult charge(Payment payment) throws PaymentException;
}
```
```

**Code Implementation**:
```java
public class PaymentProcessor {
    private final CircuitBreaker circuitBreaker; // ❌ Deviation
    private final PaymentGateway gateway;

    public PaymentResult processPayment(Payment payment) {
        return circuitBreaker.execute(() -> {
            return gateway.charge(payment);
        });
    }
}
```

**Processing**:
1. Agent retrieves `payment-service` LLD from Confluence (page: "LLD: Payment Service")
2. Parses LLD Section 5.2 for PaymentProcessor design constraints
3. Identifies constraint: "Circuit Breaker NOT allowed"
4. Maps code to LLD: Detects CircuitBreaker usage in PaymentProcessor
5. Determines: LLD_DEVIATION_FOUND (CRITICAL severity)

**Output**:

**GitHub PR Comment**:
```markdown
## ❌ LLD Alignment Review - DEVIATIONS FOUND

**Analysis Time**: 15 seconds
**LLD Document**: [Payment Service LLD - Section 5.2](https://confluence.tonic.com/scm/payment-service-lld#section-5.2)

### Critical Deviations

#### Deviation 1: Disallowed Pattern Usage
**File**: `src/main/java/com/tonic/payment/PaymentProcessor.java`
**Line**: 23

**LLD Specification**:
> Circuit Breaker NOT allowed (conflicts with centralized resilience service)
> Must use Retry Pattern for external service calls (max 3 retries)

**Actual Implementation**:
```java
private final CircuitBreaker circuitBreaker; // ❌ Not allowed per LLD
```

**Impact**: CRITICAL - Violates architectural decision to centralize resilience logic

**Recommended Fix**:
1. Remove CircuitBreaker from PaymentProcessor
2. Use RetryTemplate with max 3 retries (as specified in LLD)
3. Example:
```java
private final RetryTemplate retryTemplate;

public PaymentResult processPayment(Payment payment) {
    return retryTemplate.execute(context -> {
        return gateway.charge(payment);
    });
}
```

**Action Required**:
- Fix LLD deviation before PR can be merged, OR
- Request architectural approval to update LLD if Circuit Breaker is the preferred approach

**Jira Ticket**: SCM-789 created for tracking and architectural review.
```

**GitHub Actions Status**: ⚠️ LLD DEVIATION - Requires fix or architectural approval

**Jira Ticket Created**: SCM-789 "LLD deviation in PR #456: Disallowed Circuit Breaker usage" with link to PR, LLD, and deviation details

**CloudWatch Log**:
```json
{
  "timestamp": "2026-01-28T10:50:00Z",
  "agent": "lld_alignment_review_agent",
  "pr_number": 456,
  "status": "LLD_DEVIATION_FOUND",
  "deviation_count": 1,
  "severity": "CRITICAL",
  "analysis_time_ms": 15000,
  "lld_document": "payment-service-lld"
}
```

---

### Example 2: LLD Compliant (No Deviations)

**Input**:
```json
{
  "event": "architect_agent.new_pattern_found",
  "pr_number": 458,
  "repository": "tonic-scm/order-service",
  "component": "OrderRepository",
  "new_pattern": {
    "name": "Repository Pattern with Caching",
    "type": "Data Access Pattern",
    "files": ["src/main/java/com/tonic/order/OrderRepository.java"]
  }
}
```

**LLD Specification (from Confluence)**:
```markdown
## OrderRepository Component (LLD Section 6.1)

### Design Constraints
- Must implement Repository Pattern for data access
- Caching allowed using Spring Cache abstraction
- Must use DynamoDB single table design

### Interface Contract
```java
public interface OrderRepository {
    Order findById(String orderId);
    void save(Order order);
}
```
```

**Code Implementation**:
```java
@Component
public class OrderRepositoryImpl implements OrderRepository {
    private final DynamoDbClient dynamoDb;

    @Cacheable("orders")
    public Order findById(String orderId) {
        // DynamoDB query implementation
    }

    @CacheEvict("orders")
    public void save(Order order) {
        // DynamoDB put implementation
    }
}
```

**Processing**:
1. Agent retrieves `order-service` LLD from Confluence
2. Parses LLD Section 6.1 for OrderRepository design constraints
3. Validates implementation:
   - ✅ Implements Repository Pattern
   - ✅ Uses Spring Cache abstraction (@Cacheable)
   - ✅ Uses DynamoDB (DynamoDbClient)
   - ✅ Honors interface contract
4. Determines: LLD_COMPLIANT

**Output**:

**GitHub PR Comment**:
```markdown
## ✅ LLD Alignment Review - COMPLIANT

**Analysis Time**: 12 seconds
**LLD Document**: [Order Service LLD - Section 6.1](https://confluence.tonic.com/scm/order-service-lld#section-6.1)

**New Pattern**: Repository Pattern with Caching

All design constraints satisfied:
- ✅ Repository Pattern implemented
- ✅ Spring Cache abstraction used
- ✅ DynamoDB single table design
- ✅ Interface contract honored

**Next Step**: Proceeding to Pattern Matching Agent for pattern storage.
```

**GitHub Actions Status**: ✅ PASSED - LLD compliant, proceeding to pattern storage

**Workflow Routing**: → Pattern Matching Agent (Step 4)

**CloudWatch Log**:
```json
{
  "timestamp": "2026-01-28T10:55:00Z",
  "agent": "lld_alignment_review_agent",
  "pr_number": 458,
  "status": "LLD_COMPLIANT",
  "analysis_time_ms": 12000,
  "lld_document": "order-service-lld",
  "next_step": "pattern_matching"
}
```

---

## Implementation Notes

**Technology Stack**:
- **Language**: Java with Spring Boot
- **LLD Parsing**: Markdown parser + custom DSL for design constraints
- **Cloud**: AWS Lambda or ECS Fargate
- **Monitoring**: AWS CloudWatch

**Configuration**:
- Confluence space key: `SCM-LLD`
- LLD cache TTL: 60 minutes (LLDs change infrequently)
- Validation timeout: 20 seconds
- Severity thresholds: configurable per component

**LLD Document Structure Requirements**:
- Must use structured sections: "Design Constraints", "Interface Contract", "NFRs"
- Design constraints must be machine-parsable (keywords: "MUST", "NOT allowed", "required")
- Interface contracts in code blocks for validation

---

## Questions and TBCs

| ID | Question/TBC | Priority | Owner |
|----|--------------|----------|-------|
| TBC-LLD-001 | Standardized LLD format for machine parsing | HIGH | Architecture Team |
| TBC-LLD-002 | Deviation severity classification rules | HIGH | Product Owner |
| TBC-LLD-003 | Handling of LLD updates (versioning, backward compatibility) | MEDIUM | DevOps Team |
| TBC-LLD-004 | Process for architectural approval of LLD deviations | MEDIUM | Architecture Team |

---

**End of Specification**
