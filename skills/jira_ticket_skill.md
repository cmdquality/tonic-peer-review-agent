# Jira Ticket Skill

**Created**: 2026-01-28
**Version**: 1.0
**Project**: Tonic Configuration Management Platform
**Skill Type**: Integration Skill

---

## Purpose

The Jira Ticket Skill is a reusable integration skill that provides Jira ticket operations for all agents in the peer review system. This skill encapsulates all Jira API interactions, user lookup logic, caching, rate limiting, and error handling, enabling any agent to create, update, and manage Jira tickets without duplicating code.

**Key Benefits**:
- DRY principle: Single source of truth for Jira operations
- Consistent behavior across all agents
- Centralized rate limiting and caching
- GDPR-compliant user assignment (Account ID based)
- Comprehensive error handling and retry logic
- Complete observability and metrics

---

## When to Load

Load this skill when you need to:

1. **Create Jira tickets** for code violations, LLD deviations, or pattern rejections
2. **Assign tickets** to users by email, GitHub username, or Account ID
3. **Link GitHub PRs** to Jira tickets (bidirectional remote links)
4. **Add comments** to existing tickets
5. **Transition tickets** through workflow states

**Primary Users**:
- Code Best Practises Agent (creates tickets for violations)
- LLD Alignment Review Agent (creates tickets for deviations)
- Peer Review Documentation Agent (creates tickets for pattern rejections)
- PR Orchestrator Agent (coordinates ticket operations)

---

## Table of Contents

1. [Skill Overview](#skill-overview)
2. [Operations](#operations)
   - [create_ticket](#operation-1-create_ticket)
   - [assign_ticket](#operation-2-assign_ticket)
   - [link_pr](#operation-3-link_pr)
   - [add_comment](#operation-4-add_comment)
   - [lookup_user](#operation-5-lookup_user)
3. [User Lookup Strategy](#user-lookup-strategy)
4. [Rich Context Templates](#rich-context-templates)
5. [Error Handling](#error-handling)
6. [Configuration](#configuration)
7. [Integration Examples](#integration-examples)
8. [Performance and Monitoring](#performance-and-monitoring)

---

## Skill Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Jira Ticket Skill                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │  User Lookup   │  │  Rate Limiter  │  │    Cache     │ │
│  │   & Caching    │  │  (100 req/min) │  │  (Redis/DDB) │ │
│  └────────────────┘  └────────────────┘  └──────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Jira REST API Client                       │ │
│  │  (create, assign, link, comment, transition)           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Error Handling & Retry Logic                  │ │
│  │  (exponential backoff, retry queue)                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

1. **User Lookup with Caching**
   - Lookup Jira Account ID from email or GitHub username
   - 24-hour cache to reduce API calls
   - Multi-tier fallback strategy
   - 90%+ cache hit rate target

2. **Rate Limiting**
   - Token bucket algorithm (100 requests/minute)
   - Automatic queuing of excess requests
   - Prevents Jira API throttling

3. **Error Handling**
   - Classified errors (retryable vs non-retryable)
   - Exponential backoff for transient failures
   - SQS queue for async retry
   - Partial success handling

4. **Rich Context**
   - ADF (Atlassian Document Format) templates
   - Structured findings with line numbers
   - Code snippets and remediation guidance
   - Workflow run links for traceability

5. **Observability**
   - CloudWatch metrics for all operations
   - Structured JSON logging
   - Assignment method tracking
   - Performance monitoring

---

## Operations

### Operation 1: create_ticket

Creates a Jira ticket with automatic user assignment and rich context.

#### Input Schema

```python
class CreateTicketInput(BaseModel):
    # Required fields
    issue_type: Literal["Code Violation", "LLD Deviation", "Pattern Rejection"]
    summary: str  # max 255 characters
    description: dict  # ADF format (Atlassian Document Format)
    pr_url: str
    pr_number: int
    repository: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    # Optional fields for assignment
    pr_author_email: Optional[str] = None
    pr_author_github_username: Optional[str] = None

    # Optional enrichment fields
    labels: Optional[List[str]] = None
    components: Optional[List[str]] = None
    workflow_run_url: Optional[str] = None
    agent_findings: Optional[dict] = None

    # Override defaults
    project_key: Optional[str] = "SCM"  # default from config
    assignee_account_id: Optional[str] = None  # skip auto-lookup if provided
```

#### Output Schema

```python
class CreateTicketOutput(BaseModel):
    status: Literal["SUCCESS", "PARTIAL_SUCCESS", "FAILURE"]
    ticket_id: str  # e.g., "SCM-456"
    ticket_url: str
    ticket_key: str  # same as ticket_id

    # Assignment details
    assignee_account_id: Optional[str]
    assignee_display_name: Optional[str]
    assignment_method: Literal[
        "direct",
        "github_mapped",
        "domain_pattern",
        "fallback_component",
        "fallback_default",
        "unassigned"
    ]

    # Performance metrics
    created_at: str  # ISO 8601 timestamp
    creation_time_ms: int
    assignment_lookup_time_ms: Optional[int]

    # Link status
    pr_linked: bool
    rich_context_included: bool

    # Error/warning details
    error: Optional[str] = None
    warnings: Optional[List[str]] = None
    lookup_attempts: Optional[List[dict]] = None
```

#### Usage Example

```python
from skills.jira_ticket_skill import JiraTicketSkill

# Initialize skill
jira = JiraTicketSkill.from_environment()

# Prepare input
input_data = CreateTicketInput(
    issue_type="Code Violation",
    summary="Code violations in PR #123 (order-service)",
    description=generate_adf_description(agent_findings),
    pr_author_email="developer1@company.com",
    pr_author_github_username="dev1",
    pr_url="https://github.com/tonic-scm/order-service/pull/123",
    pr_number=123,
    repository="tonic-scm/order-service",
    severity="MEDIUM",
    labels=["code-quality", "java", "naming-convention"],
    components=["order-service"],
    workflow_run_url="https://github.com/org/repo/actions/runs/12345",
    agent_findings={
        "agent_info": {
            "name": "Code Best Practises Agent",
            "version": "2.1.0",
            "detection_time": "2026-01-28T10:25:30Z"
        },
        "findings": [...]
    }
)

# Create ticket
output = jira.create_ticket(input_data)

if output.status == "SUCCESS":
    print(f"Ticket created: {output.ticket_url}")
    print(f"Assigned to: {output.assignee_display_name} ({output.assignment_method})")
elif output.status == "PARTIAL_SUCCESS":
    print(f"Ticket created with warnings: {output.warnings}")
else:
    print(f"Failed: {output.error}")
```

---

### Operation 2: assign_ticket

Assigns an existing Jira ticket to a user (by email, GitHub username, or Account ID).

#### Input Schema

```python
class AssignTicketInput(BaseModel):
    ticket_key: str  # Required: e.g., "SCM-456"

    # Provide one of the following (in priority order):
    assignee_account_id: Optional[str] = None  # Direct Account ID (highest priority)
    assignee_email: Optional[str] = None       # Lookup Account ID from email
    github_username: Optional[str] = None      # Lookup via mapping or domain pattern
```

#### Output Schema

```python
class AssignTicketOutput(BaseModel):
    status: Literal["SUCCESS", "FAILURE"]
    ticket_key: str
    assignee_account_id: Optional[str]
    assignee_display_name: Optional[str]
    assignment_method: str
    assigned_at: str  # ISO 8601 timestamp
    error: Optional[str] = None
```

#### Usage Example

```python
# Assign by email
output = jira.assign_ticket(
    AssignTicketInput(
        ticket_key="SCM-456",
        assignee_email="developer1@company.com"
    )
)

# Assign by Account ID (skip lookup)
output = jira.assign_ticket(
    AssignTicketInput(
        ticket_key="SCM-456",
        assignee_account_id="5b10ac8d82e05b22cc7d4ef5"
    )
)
```

---

### Operation 3: link_pr

Creates a remote link between a Jira ticket and a GitHub pull request.

#### Input Schema

```python
class LinkPRInput(BaseModel):
    ticket_key: str  # Required: e.g., "SCM-456"
    pr_url: str      # Required: full GitHub PR URL
    pr_number: int   # Required
    pr_title: str    # Required
    repository: str  # Required: "org/repo" format
    pr_state: Literal["open", "closed", "merged"]  # Required
```

#### Output Schema

```python
class LinkPROutput(BaseModel):
    status: Literal["SUCCESS", "FAILURE"]
    ticket_key: str
    link_id: Optional[str]  # Remote link ID from Jira
    linked_at: str
    error: Optional[str] = None
```

#### Usage Example

```python
output = jira.link_pr(
    LinkPRInput(
        ticket_key="SCM-456",
        pr_url="https://github.com/tonic-scm/order-service/pull/123",
        pr_number=123,
        pr_title="Add order validation logic",
        repository="tonic-scm/order-service",
        pr_state="open"
    )
)
```

---

### Operation 4: add_comment

Adds a comment to an existing Jira ticket.

#### Input Schema

```python
class AddCommentInput(BaseModel):
    ticket_key: str  # Required
    comment: Union[str, dict]  # Plain text or ADF format
    visibility: Optional[dict] = None  # Restrict comment visibility

    # Example visibility restriction:
    # {"type": "role", "value": "Developers"}
```

#### Output Schema

```python
class AddCommentOutput(BaseModel):
    status: Literal["SUCCESS", "FAILURE"]
    ticket_key: str
    comment_id: Optional[str]
    created_at: str
    error: Optional[str] = None
```

#### Usage Example

```python
# Plain text comment
output = jira.add_comment(
    AddCommentInput(
        ticket_key="SCM-456",
        comment="PR has been updated with fixes. Please re-review."
    )
)

# ADF formatted comment
output = jira.add_comment(
    AddCommentInput(
        ticket_key="SCM-456",
        comment={
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Violations fixed in commit "},
                        {"type": "text", "text": "abc123", "marks": [{"type": "code"}]}
                    ]
                }
            ]
        }
    )
)
```

---

### Operation 5: lookup_user

Looks up a Jira Account ID from email or GitHub username (with caching).

#### Input Schema

```python
class LookupUserInput(BaseModel):
    # Provide one of the following:
    email: Optional[str] = None
    github_username: Optional[str] = None

    # Optional: force cache refresh
    bypass_cache: bool = False
```

#### Output Schema

```python
class LookupUserOutput(BaseModel):
    status: Literal["SUCCESS", "FAILURE"]
    account_id: Optional[str]
    display_name: Optional[str]
    email: Optional[str]
    lookup_method: str  # "email_direct", "github_mapped", "domain_pattern", "not_found"
    cached: bool  # Whether result came from cache
    lookup_time_ms: int
    error: Optional[str] = None
```

#### Usage Example

```python
# Lookup by email
output = jira.lookup_user(
    LookupUserInput(email="developer1@company.com")
)

if output.status == "SUCCESS":
    print(f"Found user: {output.display_name} ({output.account_id})")
    print(f"From cache: {output.cached}")
```

---

## User Lookup Strategy

### Lookup Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User Lookup Process                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Has pr_author_   │
                    │     email?       │
                    └──────────────────┘
                         │           │
                     YES │           │ NO
                         ▼           ▼
              ┌──────────────┐  ┌──────────────────┐
              │ Check cache  │  │ Has github_      │
              │ for email    │  │   username?      │
              └──────────────┘  └──────────────────┘
                    │                │           │
              ┌─────┴────┐      YES  │           │ NO
              │          │           ▼           ▼
           CACHE      CACHE    ┌──────────┐  ┌──────────┐
           HIT        MISS     │ Check    │  │ FALLBACK │
              │          │     │ mapping  │  │ STRATEGY │
              ▼          ▼     │ table    │  └──────────┘
         ┌────────┐  ┌───────────────┐   │
         │ Return │  │ Jira API      │   │
         │ cached │  │ user search   │   │
         │ value  │  │ by email      │   │
         └────────┘  └───────────────┘   │
                           │              │
                     ┌─────┴──────┐       │
                     │            │       │
                  FOUND       NOT FOUND   │
                     │            │       │
                     ▼            ▼       ▼
              ┌──────────┐  ┌──────────────────┐
              │ Cache &  │  │ Try mapping or   │
              │  Return  │  │ domain pattern   │
              └──────────┘  └──────────────────┘
                                     │
                             ┌───────┴────────┐
                             │                │
                          FOUND          NOT FOUND
                             │                │
                             ▼                ▼
                      ┌──────────┐     ┌──────────┐
                      │ Cache &  │     │ FALLBACK │
                      │  Return  │     │ STRATEGY │
                      └──────────┘     └──────────┘
```

### Fallback Strategy

**Tier 1: Component Owner Lookup**
- Query DynamoDB table `component-ownership`
- Key: `{repository}#{component}`
- If found: Use owner's Account ID

**Tier 2: Default Assignee**
- Use configured default assignee from environment
- `JIRA_DEFAULT_ASSIGNEE_ACCOUNT_ID`

**Tier 3: Unassigned**
- Create ticket without assignee
- Add comment: "Auto-assignment failed: PR author not found in Jira"
- Add label: `auto-assignment-failed`
- Create CloudWatch alarm for investigation

### Caching Implementation

**Cache Storage**: Redis (ElastiCache)

**Cache Key Format**:
```
user:email:{email}           → Account ID
user:github:{username}       → Account ID
```

**Cache Entry Structure**:
```json
{
  "account_id": "5b10ac8d82e05b22cc7d4ef5",
  "display_name": "Developer One",
  "email": "developer1@company.com",
  "timestamp": 1706440815000,
  "ttl": 86400000
}
```

**Cache TTL**: 24 hours (configurable)

**Cache Invalidation**:
- Automatic expiry after TTL
- Manual invalidation API: `/jira-skill/cache/invalidate`

**Performance Target**:
- Cache hit: <10ms
- Cache miss + API lookup: <200ms
- Cache hit rate: >90%

---

## Rich Context Templates

### ADF Template for Code Violations

```python
def generate_code_violation_adf(agent_findings: dict, pr_data: dict) -> dict:
    """
    Generate ADF (Atlassian Document Format) for Code Best Practises Agent.
    """
    return {
        "type": "doc",
        "version": 1,
        "content": [
            # Info panel: Agent and workflow info
            {
                "type": "panel",
                "attrs": {"panelType": "info"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "Automated detection by "},
                            {
                                "type": "text",
                                "text": f"{agent_findings['agent_info']['name']} v{agent_findings['agent_info']['version']}",
                                "marks": [{"type": "strong"}]
                            },
                            {"type": "text", "text": " | "},
                            {
                                "type": "text",
                                "text": "View Full Logs",
                                "marks": [{
                                    "type": "link",
                                    "attrs": {"href": pr_data.get('workflow_run_url', '#')}
                                }]
                            }
                        ]
                    }
                ]
            },

            # Issue summary
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Issue Summary"}]
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": f"PR: #{pr_data['pr_number']} | Repository: {pr_data['repository']}"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": f"Author: {pr_data.get('author', 'Unknown')} | Severity: {pr_data['severity']}"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": f"Issues Detected: {len(agent_findings['findings'])} violations"}]
                        }]
                    }
                ]
            },

            # Findings section
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Findings"}]
            },

            # Generate finding details for each violation
            *[_generate_finding_section(finding, idx + 1)
              for idx, finding in enumerate(agent_findings['findings'])],

            # Horizontal rule
            {"type": "rule"},

            # Action required section
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Action Required"}]
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": f"Fix all {len(agent_findings['findings'])} violations in the PR"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Verify fixes pass automated validation"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Request re-review after fixes"}]
                        }]
                    }
                ]
            }
        ]
    }

def _generate_finding_section(finding: dict, idx: int) -> List[dict]:
    """Generate ADF nodes for a single finding."""
    return [
        # Finding heading
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": f"Finding {idx}: {finding['type'].replace('_', ' ').title()}"}]
        },

        # Details table
        {
            "type": "table",
            "content": [
                # Header row
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Property"}]}]},
                        {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Value"}]}]}
                    ]
                },
                # File row
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "File"}]}]},
                        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": finding['file']}]}]}
                    ]
                },
                # Line row
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Line"}]}]},
                        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(finding['line_start'])}]}]}
                    ]
                },
                # Pattern row
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Pattern"}]}]},
                        {"type": "tableCell", "content": [{"type": "paragraph", "content": [
                            {
                                "type": "text",
                                "text": finding.get('pattern_id', 'N/A'),
                                "marks": [{"type": "link", "attrs": {"href": finding.get('pattern_url', '#')}}] if finding.get('pattern_url') else []
                            }
                        ]}]}
                    ]
                }
            ]
        },

        # Issue description
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Issue: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": finding['description']}
            ]
        },

        # Current code
        {
            "type": "codeBlock",
            "attrs": {"language": _infer_language(finding['file'])},
            "content": [{"type": "text", "text": f"// Current code (line {finding['line_start']}):\n{finding.get('code_snippet', 'N/A')}"}]
        },

        # Remediation panel
        {
            "type": "panel",
            "attrs": {"panelType": "success"},
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Remediation: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": finding.get('remediation', {}).get('description', 'No remediation provided')}
                    ]
                }
            ]
        },

        # Suggested fix (if available)
        *(
            [
                {
                    "type": "codeBlock",
                    "attrs": {"language": _infer_language(finding['file'])},
                    "content": [{"type": "text", "text": f"// Suggested fix:\n{finding['remediation']['suggested_fix']}"}]
                }
            ] if finding.get('remediation', {}).get('suggested_fix') else []
        )
    ]

def _infer_language(file_path: str) -> str:
    """Infer programming language from file extension."""
    extension_map = {
        '.java': 'java',
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.go': 'go',
        '.cpp': 'cpp',
        '.c': 'c',
        '.rb': 'ruby',
        '.cs': 'csharp'
    }
    ext = file_path[file_path.rfind('.'):] if '.' in file_path else ''
    return extension_map.get(ext, 'text')
```

### ADF Template for LLD Deviations

```python
def generate_lld_deviation_adf(agent_findings: dict, pr_data: dict) -> dict:
    """
    Generate ADF for LLD Alignment Review Agent.
    """
    return {
        "type": "doc",
        "version": 1,
        "content": [
            # Info panel
            {
                "type": "panel",
                "attrs": {"panelType": "warning"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "ARCHITECTURAL DEVIATION DETECTED", "marks": [{"type": "strong"}]},
                            {"type": "text", "text": " | Severity: "},
                            {"type": "text", "text": pr_data['severity'], "marks": [{"type": "strong"}]}
                        ]
                    }
                ]
            },

            # Agent info
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Detected by: "},
                    {"type": "text", "text": f"{agent_findings['agent_info']['name']} v{agent_findings['agent_info']['version']}", "marks": [{"type": "strong"}]}
                ]
            },

            # PR details
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Pull Request Details"}]
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "PR: "},
                                {"type": "text", "text": f"#{pr_data['pr_number']}", "marks": [{"type": "link", "attrs": {"href": pr_data['pr_url']}}]}
                            ]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": f"Repository: {pr_data['repository']}"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": f"Author: {pr_data.get('author', 'Unknown')}"}]
                        }]
                    }
                ]
            },

            # Deviation details for each finding
            *[_generate_lld_deviation_section(finding) for finding in agent_findings['findings']],

            {"type": "rule"},

            # Action required
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Action Required"}]
            },
            {
                "type": "orderedList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Fix deviation by implementing the pattern specified in LLD, OR"}]
                        }]
                    },
                    {
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Request architectural approval to update LLD if implementation is preferred"}]
                        }]
                    }
                ]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Architects: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": "Please review and provide guidance."}
                ]
            }
        ]
    }

def _generate_lld_deviation_section(finding: dict) -> List[dict]:
    """Generate ADF nodes for a single LLD deviation."""
    return [
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Deviation Details"}]
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "LLD Section: "},
                {
                    "type": "text",
                    "text": finding['lld_section'],
                    "marks": [{"type": "link", "attrs": {"href": finding.get('lld_document_url', '#')}}]
                }
            ]
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "LLD Version: "},
                {"type": "text", "text": finding.get('lld_version', 'Unknown'), "marks": [{"type": "strong"}]}
            ]
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "File: "},
                {"type": "text", "text": f"{finding['file']} (lines {finding['line_start']}-{finding['line_end']})", "marks": [{"type": "code"}]}
            ]
        },

        # Expected vs Actual
        {
            "type": "expand",
            "attrs": {"title": "Expected Behavior (per LLD)"},
            "content": [
                {
                    "type": "blockquote",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": finding['expected_pattern']}]}
                    ]
                }
            ]
        },
        {
            "type": "expand",
            "attrs": {"title": "Actual Implementation"},
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": finding['actual_implementation']}]
                }
            ]
        },

        # Impact panel
        {
            "type": "panel",
            "attrs": {"panelType": "error"},
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Impact: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": finding.get('impact', 'Unknown impact')}
                    ]
                }
            ]
        },

        # Remediation
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Remediation"}]
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": finding.get('remediation', {}).get('description', 'No remediation provided')}]
        },
        *(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Suggested Approach: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": finding['remediation']['suggested_approach']}
                    ]
                }
            ] if finding.get('remediation', {}).get('suggested_approach') else []
        ),
        *(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Effort Estimate: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": finding['remediation']['effort_estimate']}
                    ]
                }
            ] if finding.get('remediation', {}).get('effort_estimate') else []
        )
    ]
```

### Template Helper Function

```python
def generate_ticket_description(
    issue_type: str,
    agent_findings: dict,
    pr_data: dict
) -> dict:
    """
    Main entry point for generating ticket descriptions.
    Routes to appropriate template based on issue type.
    """
    templates = {
        "Code Violation": generate_code_violation_adf,
        "LLD Deviation": generate_lld_deviation_adf,
        "Pattern Rejection": generate_pattern_rejection_adf  # Similar structure
    }

    template_func = templates.get(issue_type)
    if not template_func:
        raise ValueError(f"Unknown issue type: {issue_type}")

    return template_func(agent_findings, pr_data)
```

---

## Error Handling

### Error Classification

```python
class JiraSkillError(Exception):
    """Base exception for Jira Skill errors."""
    def __init__(self, message: str, error_code: str, retryable: bool = False):
        self.message = message
        self.error_code = error_code
        self.retryable = retryable
        super().__init__(message)

# Specific error types
class UserLookupError(JiraSkillError):
    """Error during user lookup."""
    pass

class TicketCreationError(JiraSkillError):
    """Error during ticket creation."""
    pass

class AssignmentError(JiraSkillError):
    """Error during ticket assignment."""
    pass

class RateLimitError(JiraSkillError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int):
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after}s",
            "RATE_LIMIT_EXCEEDED",
            retryable=True
        )
        self.retry_after = retry_after
```

### Error Handling Strategies

| Error Type | HTTP Code | Retryable | Strategy |
|------------|-----------|-----------|----------|
| Authentication failure | 401 | No | Critical alarm, fail immediately |
| User not found | 404 | No | Use fallback assignment |
| Rate limit exceeded | 429 | Yes | Wait (Retry-After header) + queue |
| Jira API timeout | 504 | Yes | Exponential backoff (3 attempts) |
| Network error | N/A | Yes | Exponential backoff (3 attempts) |
| Invalid input | 400 | No | Return error to caller |
| Server error | 500 | Yes | Exponential backoff (3 attempts) |

### Retry Logic

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def _call_jira_api(self, endpoint: str, method: str, **kwargs) -> dict:
    """
    Make Jira API call with automatic retry for transient failures.
    """
    try:
        response = self.jira_client.request(method, endpoint, **kwargs)
        return response.json()
    except requests.exceptions.Timeout:
        logger.warning(f"Jira API timeout for {endpoint}")
        raise TimeoutError(f"Jira API timeout: {endpoint}")
    except requests.exceptions.ConnectionError:
        logger.warning(f"Jira connection error for {endpoint}")
        raise ConnectionError(f"Jira connection error: {endpoint}")
```

### Partial Success Handling

When a ticket is created but assignment or linking fails:

```python
def create_ticket(self, input_data: CreateTicketInput) -> CreateTicketOutput:
    """Create ticket with graceful degradation."""
    ticket_id = None
    warnings = []

    try:
        # Step 1: Create ticket (most critical)
        ticket_id = self._create_ticket_in_jira(input_data)

        # Step 2: Assign ticket (best effort)
        try:
            assignee_info = self._assign_ticket(ticket_id, input_data)
        except Exception as e:
            logger.warning(f"Assignment failed: {e}")
            warnings.append(f"Auto-assignment failed: {str(e)}")
            # Use fallback assignment
            assignee_info = self._fallback_assignment(ticket_id, input_data)

        # Step 3: Link PR (best effort)
        try:
            self._link_pr_to_ticket(ticket_id, input_data)
            pr_linked = True
        except Exception as e:
            logger.warning(f"PR linking failed: {e}")
            warnings.append(f"PR link pending: {str(e)}")
            # Queue for retry
            self._queue_pr_link_retry(ticket_id, input_data)
            pr_linked = False

        # Return partial success if any warnings
        status = "PARTIAL_SUCCESS" if warnings else "SUCCESS"

        return CreateTicketOutput(
            status=status,
            ticket_id=ticket_id,
            ticket_url=f"{self.base_url}/browse/{ticket_id}",
            warnings=warnings if warnings else None,
            **assignee_info,
            pr_linked=pr_linked
        )

    except Exception as e:
        logger.error(f"Ticket creation failed: {e}")
        return CreateTicketOutput(
            status="FAILURE",
            error=str(e)
        )
```

---

## Configuration

### Environment Variables

```bash
# Jira API Configuration
JIRA_BASE_URL=https://company.atlassian.net
JIRA_EMAIL=automation@company.com
JIRA_API_TOKEN_SECRET_NAME=jira/api-token  # AWS Secrets Manager
JIRA_PROJECT_KEY=SCM

# Assignment Configuration
JIRA_DEFAULT_ASSIGNEE_ACCOUNT_ID=5b10ac8d82e05b22cc7d4ef6
ORGANIZATION_EMAIL_DOMAIN=company.com

# Cache Configuration
REDIS_HOST=jira-cache.abc123.0001.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
USER_CACHE_TTL_HOURS=24

# Rate Limiting
JIRA_RATE_LIMIT_PER_MINUTE=100

# Retry Configuration
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=5
RETRY_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/jira-retry-queue

# DynamoDB Tables
COMPONENT_OWNERSHIP_TABLE=component-ownership
USERNAME_MAPPING_TABLE=github-username-mapping

# Performance
JIRA_API_TIMEOUT_SECONDS=10
```

### Initialization

```python
# From environment variables
jira = JiraTicketSkill.from_environment()

# With explicit configuration
jira = JiraTicketSkill(
    base_url="https://company.atlassian.net",
    email="automation@company.com",
    api_token="ATATT3xFfGF0...",
    project_key="SCM",
    cache_ttl_hours=24,
    rate_limit_per_minute=100
)
```

---

## Integration Examples

### Example 1: Code Best Practises Agent Integration

```python
# In code_best_practises_agent.py

from skills.jira_ticket_skill import JiraTicketSkill, CreateTicketInput
from skills.jira_ticket_skill.templates import generate_ticket_description

def handle_violations_detected(pr_data: dict, violations: List[dict]):
    """
    Called by Code Best Practises Agent when violations are detected.
    """
    # Initialize Jira skill
    jira = JiraTicketSkill.from_environment()

    # Prepare agent findings
    agent_findings = {
        "agent_info": {
            "name": "Code Best Practises Agent",
            "version": "2.1.0",
            "detection_time": datetime.utcnow().isoformat(),
            "analysis_duration_ms": pr_data.get('analysis_duration_ms')
        },
        "findings": [
            {
                "finding_id": f"CBP-{idx:03d}",
                "type": violation['type'],
                "severity": violation['severity'],
                "file": violation['file'],
                "line_start": violation['line'],
                "line_end": violation['line'],
                "code_snippet": violation['code_snippet'],
                "description": violation['description'],
                "pattern_id": violation.get('pattern_id'),
                "pattern_url": violation.get('pattern_url'),
                "remediation": {
                    "description": violation['suggested_fix'],
                    "suggested_fix": violation.get('corrected_code'),
                    "effort_estimate": "5-10 minutes"
                }
            }
            for idx, violation in enumerate(violations, 1)
        ]
    }

    # Generate ADF description
    description = generate_ticket_description(
        issue_type="Code Violation",
        agent_findings=agent_findings,
        pr_data=pr_data
    )

    # Create ticket
    input_data = CreateTicketInput(
        issue_type="Code Violation",
        summary=f"Code violations in PR #{pr_data['pr_number']} ({pr_data['repository'].split('/')[-1]})",
        description=description,
        pr_author_email=pr_data.get('author_email'),
        pr_author_github_username=pr_data.get('author_username'),
        pr_url=pr_data['pr_url'],
        pr_number=pr_data['pr_number'],
        repository=pr_data['repository'],
        severity=_calculate_overall_severity(violations),
        labels=["code-quality", pr_data.get('language', 'unknown').lower()] +
               list(set([v['type'].lower().replace(' ', '-') for v in violations])),
        components=[pr_data['repository'].split('/')[-1]],
        workflow_run_url=pr_data.get('workflow_run_url'),
        agent_findings=agent_findings
    )

    output = jira.create_ticket(input_data)

    if output.status in ["SUCCESS", "PARTIAL_SUCCESS"]:
        logger.info(f"Jira ticket created: {output.ticket_url}")
        logger.info(f"Assigned to: {output.assignee_display_name} ({output.assignment_method})")

        # Post PR comment
        post_pr_comment(
            pr_data['pr_number'],
            f"Jira ticket [{output.ticket_id}]({output.ticket_url}) created for code violations."
        )

        return output
    else:
        logger.error(f"Failed to create Jira ticket: {output.error}")
        # Still block PR merge, but alert ops team
        create_cloudwatch_alarm("JiraTicketCreationFailed", output.error)
        raise JiraIntegrationError(output.error)

def _calculate_overall_severity(violations: List[dict]) -> str:
    """Calculate overall severity based on violation count and types."""
    critical_count = sum(1 for v in violations if v.get('severity') == 'CRITICAL')
    if critical_count > 0:
        return "CRITICAL"
    elif len(violations) > 10:
        return "HIGH"
    elif len(violations) > 3:
        return "MEDIUM"
    else:
        return "LOW"
```

### Example 2: LLD Alignment Agent Integration

```python
# In lld_alignment_review_agent.py

from skills.jira_ticket_skill import JiraTicketSkill, CreateTicketInput
from skills.jira_ticket_skill.templates import generate_ticket_description

def handle_lld_deviations(pr_data: dict, deviations: List[dict]):
    """
    Called by LLD Alignment Review Agent when deviations are detected.
    """
    jira = JiraTicketSkill.from_environment()

    agent_findings = {
        "agent_info": {
            "name": "LLD Alignment Review Agent",
            "version": "1.5.2",
            "detection_time": datetime.utcnow().isoformat()
        },
        "findings": [
            {
                "finding_id": f"LLD-{idx:03d}",
                "type": "ARCHITECTURAL_DEVIATION",
                "severity": deviation['severity'],
                "lld_section": deviation['lld_section'],
                "lld_document_url": deviation['lld_url'],
                "lld_version": deviation.get('lld_version'),
                "file": deviation['file'],
                "line_start": deviation['line_start'],
                "line_end": deviation['line_end'],
                "expected_pattern": deviation['expected'],
                "actual_implementation": deviation['actual'],
                "deviation_reason": deviation.get('reason'),
                "impact": deviation['impact'],
                "remediation": {
                    "description": deviation['remediation'],
                    "suggested_approach": deviation.get('suggested_approach'),
                    "alternative": deviation.get('alternative'),
                    "effort_estimate": deviation.get('effort_estimate', '2-4 hours')
                }
            }
            for idx, deviation in enumerate(deviations, 1)
        ]
    }

    description = generate_ticket_description(
        issue_type="LLD Deviation",
        agent_findings=agent_findings,
        pr_data=pr_data
    )

    input_data = CreateTicketInput(
        issue_type="LLD Deviation",
        summary=f"LLD deviation in PR #{pr_data['pr_number']} ({pr_data['repository'].split('/')[-1]})",
        description=description,
        pr_author_email=pr_data.get('author_email'),
        pr_author_github_username=pr_data.get('author_username'),
        pr_url=pr_data['pr_url'],
        pr_number=pr_data['pr_number'],
        repository=pr_data['repository'],
        severity=_get_highest_severity(deviations),
        labels=["lld-deviation", "architectural"] + [pr_data['repository'].split('/')[-1]],
        components=[pr_data['repository'].split('/')[-1]],
        workflow_run_url=pr_data.get('workflow_run_url'),
        agent_findings=agent_findings
    )

    output = jira.create_ticket(input_data)

    # Add architects as watchers (additional step)
    if output.status in ["SUCCESS", "PARTIAL_SUCCESS"]:
        _add_architect_watchers(output.ticket_key)

    return output

def _add_architect_watchers(ticket_key: str):
    """Add architects as watchers for LLD deviation tickets."""
    jira = JiraTicketSkill.from_environment()
    architects = get_architect_emails()  # From config
    for architect_email in architects:
        try:
            user_output = jira.lookup_user(LookupUserInput(email=architect_email))
            if user_output.status == "SUCCESS":
                # Use Jira API directly to add watcher (not in skill operations)
                jira.jira_client.add_watcher(ticket_key, user_output.account_id)
        except Exception as e:
            logger.warning(f"Failed to add architect watcher: {e}")
```

### Example 3: Peer Review Documentation Agent Integration

```python
# In peer_review_documentation_agent.py

def handle_pattern_rejection(pr_data: dict, rejection_details: dict):
    """
    Called when a pattern is rejected by reviewers.
    """
    jira = JiraTicketSkill.from_environment()

    agent_findings = {
        "agent_info": {
            "name": "Peer Review Documentation Agent",
            "version": "1.2.0",
            "detection_time": datetime.utcnow().isoformat()
        },
        "findings": [
            {
                "finding_id": "PR-001",
                "type": "PATTERN_REJECTION",
                "severity": "HIGH",
                "pattern_candidate": rejection_details['pattern_name'],
                "file": rejection_details['file'],
                "line_start": rejection_details['line_start'],
                "line_end": rejection_details['line_end'],
                "rejection_reason": rejection_details['reason'],
                "reviewer_comments": rejection_details['comments'],
                "architectural_concerns": rejection_details.get('concerns', []),
                "remediation": {
                    "description": rejection_details['remediation'],
                    "suggested_approach": rejection_details.get('suggested_approach'),
                    "effort_estimate": "1-2 days"
                }
            }
        ]
    }

    description = generate_ticket_description(
        issue_type="Pattern Rejection",
        agent_findings=agent_findings,
        pr_data=pr_data
    )

    input_data = CreateTicketInput(
        issue_type="Pattern Rejection",
        summary=f"Pattern rejection in PR #{pr_data['pr_number']}: {rejection_details['pattern_name']}",
        description=description,
        pr_author_email=pr_data.get('author_email'),
        pr_author_github_username=pr_data.get('author_username'),
        pr_url=pr_data['pr_url'],
        pr_number=pr_data['pr_number'],
        repository=pr_data['repository'],
        severity="MEDIUM",
        labels=["pattern-rejection", "architectural"],
        components=[pr_data['repository'].split('/')[-1]],
        workflow_run_url=pr_data.get('workflow_run_url'),
        agent_findings=agent_findings
    )

    return jira.create_ticket(input_data)
```

---

## Performance and Monitoring

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Ticket Creation Time P95 | <10 seconds | CloudWatch |
| User Lookup Time P95 | <200ms | CloudWatch |
| Cache Hit Rate | >90% | Redis metrics |
| Assignment Success Rate | >95% direct | CloudWatch |
| API Error Rate | <1% | CloudWatch |
| Rate Limit Compliance | 0 throttling errors | CloudWatch |

### CloudWatch Metrics

```python
def _publish_metrics(self, operation: str, metrics: dict):
    """Publish CloudWatch metrics for observability."""
    namespace = "SCM/JiraTicketSkill"

    cloudwatch_client.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": f"{operation}Duration",
                "Value": metrics['duration_ms'],
                "Unit": "Milliseconds",
                "Dimensions": [
                    {"Name": "Operation", "Value": operation},
                    {"Name": "Status", "Value": metrics['status']}
                ]
            },
            {
                "MetricName": f"{operation}SuccessRate",
                "Value": 1 if metrics['status'] == 'SUCCESS' else 0,
                "Unit": "Count",
                "Dimensions": [{"Name": "Operation", "Value": operation}]
            }
        ]
    )

    # Additional metrics for specific operations
    if operation == "create_ticket":
        cloudwatch_client.put_metric_data(
            Namespace=namespace,
            MetricData=[
                {
                    "MetricName": "AssignmentMethod",
                    "Value": 1,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": "Method", "Value": metrics.get('assignment_method', 'unknown')}
                    ]
                },
                {
                    "MetricName": "CacheHitRate",
                    "Value": 1 if metrics.get('cache_hit') else 0,
                    "Unit": "Count"
                }
            ]
        )
```

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

def create_ticket(self, input_data: CreateTicketInput) -> CreateTicketOutput:
    """Create ticket with comprehensive logging."""
    start_time = time.time()

    logger.info(
        "jira_ticket_creation_started",
        issue_type=input_data.issue_type,
        pr_number=input_data.pr_number,
        repository=input_data.repository
    )

    try:
        # ... ticket creation logic ...

        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "jira_ticket_creation_succeeded",
            ticket_id=output.ticket_id,
            ticket_url=output.ticket_url,
            assignee_account_id=output.assignee_account_id,
            assignment_method=output.assignment_method,
            duration_ms=duration_ms,
            pr_linked=output.pr_linked,
            rich_context=output.rich_context_included
        )

        return output

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "jira_ticket_creation_failed",
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=duration_ms,
            pr_number=input_data.pr_number
        )

        raise
```

### CloudWatch Alarms

```yaml
# CloudWatch alarms configuration

HighErrorRate:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: JiraSkill-HighErrorRate
    MetricName: create_ticketSuccessRate
    Namespace: SCM/JiraTicketSkill
    Statistic: Average
    Period: 300
    EvaluationPeriods: 2
    Threshold: 0.99
    ComparisonOperator: LessThanThreshold
    AlarmActions:
      - !Ref OpsTeamSNSTopic

SlowTicketCreation:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: JiraSkill-SlowTicketCreation
    MetricName: create_ticketDuration
    Namespace: SCM/JiraTicketSkill
    Statistic: p95
    Period: 300
    EvaluationPeriods: 2
    Threshold: 10000  # 10 seconds
    ComparisonOperator: GreaterThanThreshold
    AlarmActions:
      - !Ref OpsTeamSNSTopic

LowCacheHitRate:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: JiraSkill-LowCacheHitRate
    MetricName: CacheHitRate
    Namespace: SCM/JiraTicketSkill
    Statistic: Average
    Period: 3600
    EvaluationPeriods: 1
    Threshold: 0.80  # 80%
    ComparisonOperator: LessThanThreshold
    AlarmActions:
      - !Ref OpsTeamSNSTopic
```

---

## Testing Guide

### Unit Tests

```python
# tests/test_jira_ticket_skill.py

import pytest
from unittest.mock import Mock, patch
from skills.jira_ticket_skill import JiraTicketSkill, CreateTicketInput

@pytest.fixture
def jira_skill():
    """Create JiraTicketSkill with mocked dependencies."""
    with patch('skills.jira_ticket_skill.JiraClient') as mock_client:
        skill = JiraTicketSkill(
            base_url="https://test.atlassian.net",
            email="test@company.com",
            api_token="test-token",
            project_key="TEST"
        )
        skill.jira_client = mock_client
        yield skill

def test_create_ticket_success(jira_skill):
    """Test successful ticket creation."""
    # Mock Jira API response
    jira_skill.jira_client.create_issue.return_value = {
        "key": "TEST-123",
        "self": "https://test.atlassian.net/rest/api/3/issue/123"
    }

    input_data = CreateTicketInput(
        issue_type="Code Violation",
        summary="Test ticket",
        description={"type": "doc", "version": 1, "content": []},
        pr_url="https://github.com/test/repo/pull/1",
        pr_number=1,
        repository="test/repo",
        severity="MEDIUM"
    )

    output = jira_skill.create_ticket(input_data)

    assert output.status == "SUCCESS"
    assert output.ticket_id == "TEST-123"
    assert output.ticket_url == "https://test.atlassian.net/browse/TEST-123"

def test_user_lookup_with_cache(jira_skill):
    """Test user lookup with cache hit."""
    # Populate cache
    jira_skill.cache.set(
        "user:email:dev@company.com",
        {
            "account_id": "123",
            "display_name": "Developer",
            "email": "dev@company.com"
        }
    )

    output = jira_skill.lookup_user(LookupUserInput(email="dev@company.com"))

    assert output.status == "SUCCESS"
    assert output.account_id == "123"
    assert output.cached == True

def test_assignment_fallback_to_component_owner(jira_skill):
    """Test fallback to component owner when user not found."""
    # Mock user lookup failure
    jira_skill.jira_client.user_search.return_value = []

    # Mock component owner lookup
    with patch('skills.jira_ticket_skill.dynamodb') as mock_ddb:
        mock_ddb.get_item.return_value = {
            "Item": {
                "owner_email": "owner@company.com",
                "owner_account_id": "456"
            }
        }

        input_data = CreateTicketInput(
            issue_type="Code Violation",
            summary="Test",
            description={},
            pr_author_email="notfound@company.com",
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repository="test/repo",
            severity="MEDIUM"
        )

        output = jira_skill.create_ticket(input_data)

        assert output.assignment_method == "fallback_component"
        assert output.assignee_account_id == "456"
```

### Integration Tests

```python
# tests/integration/test_jira_integration.py

import pytest
import os

@pytest.mark.integration
def test_create_and_link_ticket_e2e():
    """End-to-end test with real Jira test instance."""
    # Requires JIRA_TEST_* environment variables
    jira = JiraTicketSkill(
        base_url=os.getenv("JIRA_TEST_URL"),
        email=os.getenv("JIRA_TEST_EMAIL"),
        api_token=os.getenv("JIRA_TEST_TOKEN"),
        project_key="TEST"
    )

    # Create ticket
    input_data = CreateTicketInput(
        issue_type="Code Violation",
        summary="Integration test ticket",
        description={"type": "doc", "version": 1, "content": []},
        pr_url="https://github.com/test/repo/pull/999",
        pr_number=999,
        repository="test/repo",
        severity="LOW"
    )

    output = jira.create_ticket(input_data)

    assert output.status == "SUCCESS"
    assert output.ticket_id.startswith("TEST-")

    # Verify ticket exists in Jira
    ticket = jira.jira_client.issue(output.ticket_id)
    assert ticket.fields.summary == "Integration test ticket"

    # Cleanup
    jira.jira_client.delete_issue(output.ticket_id)
```

---

## Appendix: DynamoDB Table Schemas

### component-ownership Table

```json
{
  "TableName": "component-ownership",
  "KeySchema": [
    {"AttributeName": "repository", "KeyType": "HASH"},
    {"AttributeName": "component", "KeyType": "RANGE"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "repository", "AttributeType": "S"},
    {"AttributeName": "component", "AttributeType": "S"}
  ],
  "BillingMode": "PAY_PER_REQUEST",
  "Example Item": {
    "repository": "order-service",
    "component": "payment-module",
    "owner_email": "team-lead1@company.com",
    "owner_account_id": "5b10ac8d82e05b22cc7d4ef7",
    "updated_at": "2026-01-28T10:00:00Z"
  }
}
```

### github-username-mapping Table

```json
{
  "TableName": "github-username-mapping",
  "KeySchema": [
    {"AttributeName": "github_username", "KeyType": "HASH"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "github_username", "AttributeType": "S"}
  ],
  "BillingMode": "PAY_PER_REQUEST",
  "Example Item": {
    "github_username": "dev1",
    "jira_email": "developer1@company.com",
    "jira_account_id": "5b10ac8d82e05b22cc7d4ef5",
    "updated_at": "2026-01-28T09:00:00Z"
  }
}
```

---

**End of Jira Ticket Skill Specification**
