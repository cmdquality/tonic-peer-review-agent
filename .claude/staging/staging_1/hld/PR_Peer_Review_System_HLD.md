# High-Level Design: PR Peer Review System with AWS Bedrock

## Document Information

| Field | Value |
|-------|-------|
| **Document Type** | High-Level Design (HLD) |
| **Version** | 1.0 |
| **Date** | 2026-01-30 |
| **Status** | Draft |
| **Author** | Claude (Agentic Architect Agent) |

---

## 1. Executive Summary

This High-Level Design document describes the architecture of an automated PR Peer Review System that integrates GitHub Actions, AWS Lambda, and AWS Bedrock to execute Claude AI agents for code review automation.

The system provides:
- **Automated code quality analysis** on every pull request
- **Architectural pattern detection** to ensure compliance
- **LLD alignment verification** against design specifications
- **Automated Jira ticket creation** for failed reviews
- **Asynchronous parallel execution** for optimal performance

---

## 2. System Context Diagram

### 2.1 High-Level Context

```mermaid
C4Context
    title System Context Diagram - PR Peer Review System

    Person(dev, "Developer", "Creates pull requests")
    Person(reviewer, "Tech Lead", "Reviews patterns, approves PRs")

    System(prs, "PR Peer Review System", "Automated AI-powered code review")

    System_Ext(github, "GitHub", "Source control and CI/CD")
    System_Ext(aws, "AWS Cloud", "Compute and AI services")
    System_Ext(jira, "Jira", "Issue tracking")
    System_Ext(confluence, "Confluence", "Pattern library documentation")

    Rel(dev, github, "Creates PR")
    Rel(github, prs, "Triggers workflow")
    Rel(prs, aws, "Executes agents")
    Rel(prs, jira, "Creates tickets")
    Rel(prs, confluence, "Reads patterns")
    Rel(prs, github, "Posts review")
    Rel(reviewer, github, "Approves/Rejects")
```

### 2.2 Simplified Context Flow

```mermaid
flowchart LR
    subgraph "Source"
        DEV[Developer] --> PR[Pull Request]
    end

    subgraph "Orchestration"
        PR --> GHA[GitHub Actions]
    end

    subgraph "Execution"
        GHA --> LAMBDA[AWS Lambda]
        LAMBDA --> BEDROCK[AWS Bedrock<br/>Claude Models]
    end

    subgraph "Integration"
        BEDROCK --> RESULTS[Review Results]
        RESULTS --> JIRA[Jira Ticket]
        RESULTS --> GITHUB[GitHub Comment]
    end

    style LAMBDA fill:#FF9900
    style BEDROCK fill:#FF9900
    style GHA fill:#2088FF
```

---

## 3. System Architecture

### 3.1 Complete Architecture Overview

```mermaid
flowchart TB
    subgraph "GitHub Cloud"
        PR[📝 Pull Request<br/>Created/Updated]
        WEBHOOK[🔗 Webhook Event]
        COMMENT[💬 PR Comment<br/>Review Results]
        STATUS[✅ Status Check<br/>Pass/Fail]
    end

    subgraph "GitHub Actions Runner"
        WF[📋 Workflow Engine]
        PF[Pre-Flight<br/>Validation]
        OIDC[🔐 OIDC Token<br/>Generator]
    end

    subgraph "AWS Cloud"
        subgraph "Security Layer"
            IAM[IAM Role<br/>github-pr-review-role]
            STS[AWS STS<br/>AssumeRole]
        end

        subgraph "Compute Layer"
            LAMBDA[⚡ AWS Lambda<br/>Agent Orchestrator]
            SQS[📨 SQS Queue<br/>Agent Tasks]
        end

        subgraph "AI Layer - Bedrock"
            HAIKU[Claude Haiku<br/>Fast Reviews<br/>$0.25/1M tokens]
            SONNET[Claude Sonnet<br/>Complex Analysis<br/>$3/1M tokens]
            OPUS[Claude Opus<br/>Deep Reasoning<br/>Premium]
        end

        subgraph "Storage Layer"
            S3[📁 S3 Bucket<br/>Review Artifacts]
            DDB[📊 DynamoDB<br/>Review History]
        end
    end

    subgraph "External Integrations"
        JIRA[🎫 Jira Cloud<br/>Ticket Creation]
        CONF[📚 Confluence<br/>Pattern Library]
    end

    %% Flow connections
    PR --> WEBHOOK
    WEBHOOK --> WF
    WF --> PF
    PF --> OIDC
    OIDC --> STS
    STS --> IAM
    IAM --> LAMBDA

    LAMBDA --> SQS
    SQS --> LAMBDA

    LAMBDA --> HAIKU
    LAMBDA --> SONNET
    LAMBDA --> OPUS

    LAMBDA --> S3
    LAMBDA --> DDB

    LAMBDA --> JIRA
    LAMBDA --> CONF

    LAMBDA --> COMMENT
    LAMBDA --> STATUS

    %% Styling
    style HAIKU fill:#90EE90
    style SONNET fill:#87CEEB
    style OPUS fill:#DDA0DD
    style LAMBDA fill:#FF9900
    style IAM fill:#FFD700
```

### 3.2 Deployment Architecture Options

```mermaid
flowchart TB
    subgraph "Option A: GitHub Actions Direct"
        A1[GitHub Actions] --> A2[Python Script]
        A2 --> A3[Bedrock API]
        A2 --> A4[aioboto3 async]
    end

    subgraph "Option B: Lambda Orchestration"
        B1[GitHub Actions] --> B2[Lambda Trigger]
        B2 --> B3[Lambda Function]
        B3 --> B4[Bedrock API]
        B3 --> B5[Parallel Agents]
    end

    subgraph "Option C: Step Functions"
        C1[GitHub Actions] --> C2[API Gateway]
        C2 --> C3[Step Functions]
        C3 --> C4[Lambda Agents]
        C4 --> C5[Bedrock API]
    end

    style A1 fill:#2088FF
    style B1 fill:#2088FF
    style C1 fill:#2088FF
    style B3 fill:#FF9900
    style C3 fill:#FF9900
    style C4 fill:#FF9900
```

---

## 4. Component Architecture

### 4.1 Agent Orchestration Flow

```mermaid
flowchart TD
    START[🚀 PR Event Received] --> PF{Pre-Flight<br/>Validation}

    PF -->|Skip Review| SKIP[Skip - No Code Changes]
    PF -->|Draft PR| SKIP
    PF -->|Proceed| CQ[Code Quality Agent<br/>Claude Haiku]

    CQ -->|PASS| ARCH[Architect Agent<br/>Claude Sonnet]
    CQ -->|FAIL| JIRA_CQ[Create Jira Ticket<br/>Code Violations]

    ARCH -->|No New Pattern| APPROVE[✅ Approve PR]
    ARCH -->|New Pattern Found| LLD[LLD Alignment Agent<br/>Claude Sonnet]

    LLD -->|Compliant| PATTERN_REQ[Request Pattern Approval]
    LLD -->|Deviation| JIRA_LLD[Create Jira Ticket<br/>LLD Deviation]

    JIRA_CQ --> BLOCK[❌ Block PR]
    JIRA_LLD --> BLOCK

    APPROVE --> REPORT[📊 Final Report]
    PATTERN_REQ --> REPORT
    BLOCK --> REPORT

    REPORT --> COMMENT[Post GitHub Comment]

    style CQ fill:#90EE90
    style ARCH fill:#87CEEB
    style LLD fill:#87CEEB
    style APPROVE fill:#90EE90
    style BLOCK fill:#FF6B6B
```

### 4.2 Lambda Function Architecture

```mermaid
flowchart TB
    subgraph "Lambda: Agent Orchestrator"
        HANDLER[Lambda Handler<br/>handler.py]

        subgraph "Core Modules"
            CONTEXT[PR Context<br/>Fetcher]
            RUNNER[Async Bedrock<br/>Runner]
            PARSER[Response<br/>Parser]
        end

        subgraph "Agent Definitions"
            CQ_AGENT[Code Quality<br/>Agent]
            ARCH_AGENT[Architect<br/>Agent]
            LLD_AGENT[LLD Alignment<br/>Agent]
            JIRA_AGENT[Jira Integration<br/>Agent]
        end

        subgraph "Utilities"
            CHUNKER[Diff Chunker]
            AGGREGATOR[Result<br/>Aggregator]
            REPORTER[Report<br/>Generator]
        end
    end

    HANDLER --> CONTEXT
    CONTEXT --> RUNNER
    RUNNER --> CQ_AGENT
    RUNNER --> ARCH_AGENT
    RUNNER --> LLD_AGENT
    RUNNER --> JIRA_AGENT
    RUNNER --> PARSER
    PARSER --> AGGREGATOR
    AGGREGATOR --> REPORTER

    RUNNER --> CHUNKER

    style HANDLER fill:#FF9900
    style RUNNER fill:#FF9900
```

---

## 5. Data Flow Architecture

### 5.1 Request/Response Flow

```mermaid
sequenceDiagram
    autonumber
    participant DEV as Developer
    participant GH as GitHub
    participant GHA as GitHub Actions
    participant STS as AWS STS
    participant LAMBDA as Lambda
    participant BEDROCK as Bedrock
    participant JIRA as Jira

    DEV->>GH: Create/Update PR
    GH->>GHA: Webhook: pull_request

    Note over GHA: Pre-Flight Validation

    GHA->>GHA: Generate OIDC Token
    GHA->>STS: AssumeRoleWithWebIdentity
    STS-->>GHA: Temporary Credentials (1hr)

    GHA->>LAMBDA: Invoke (PR Context)

    par Parallel Agent Execution
        LAMBDA->>BEDROCK: Code Quality (Haiku)
        BEDROCK-->>LAMBDA: Quality Report
    and
        LAMBDA->>BEDROCK: Architect (Sonnet)
        BEDROCK-->>LAMBDA: Pattern Analysis
    end

    alt Pattern Found
        LAMBDA->>BEDROCK: LLD Alignment (Sonnet)
        BEDROCK-->>LAMBDA: Alignment Report
    end

    alt Review Failed
        LAMBDA->>JIRA: Create Ticket
        JIRA-->>LAMBDA: Ticket Key
    end

    LAMBDA-->>GHA: Review Results
    GHA->>GH: Post Comment
    GHA->>GH: Set Status Check

    GH-->>DEV: Notification
```

### 5.2 Data Schema

```mermaid
erDiagram
    PR_CONTEXT {
        int pr_number PK
        string title
        string description
        string author
        int additions
        int deletions
        int files_changed
        text diff
        datetime created_at
    }

    AGENT_RESULT {
        string result_id PK
        int pr_number FK
        string agent_type
        string status
        json violations
        json patterns
        json deviations
        int input_tokens
        int output_tokens
        float cost
        datetime executed_at
    }

    REVIEW_REPORT {
        string report_id PK
        int pr_number FK
        string overall_status
        boolean can_merge
        string jira_ticket
        datetime completed_at
    }

    PR_CONTEXT ||--o{ AGENT_RESULT : "has"
    PR_CONTEXT ||--|| REVIEW_REPORT : "produces"
```

---

## 6. AWS Infrastructure Architecture

### 6.1 AWS Resource Topology

```mermaid
flowchart TB
    subgraph "AWS Account: Production"
        subgraph "Region: us-east-1"
            subgraph "VPC: pr-review-vpc"
                subgraph "Private Subnet"
                    LAMBDA[Lambda Function<br/>pr-review-orchestrator]
                    ENI[ENI]
                end
            end

            subgraph "AWS Services (No VPC)"
                BEDROCK[Bedrock Runtime]
                S3[S3 Bucket<br/>pr-review-artifacts]
                DDB[DynamoDB<br/>pr-review-history]
                CW[CloudWatch Logs]
                SQS[SQS Dead Letter Queue]
            end

            subgraph "Security"
                IAM_ROLE[IAM Role<br/>github-pr-review-role]
                IAM_POLICY[IAM Policy<br/>bedrock-invoke-policy]
                OIDC[OIDC Provider<br/>GitHub Actions]
            end
        end
    end

    subgraph "External"
        GITHUB[GitHub Actions]
    end

    GITHUB --> OIDC
    OIDC --> IAM_ROLE
    IAM_ROLE --> IAM_POLICY
    IAM_ROLE --> LAMBDA

    LAMBDA --> ENI
    ENI --> BEDROCK
    LAMBDA --> S3
    LAMBDA --> DDB
    LAMBDA --> CW
    LAMBDA --> SQS

    style LAMBDA fill:#FF9900
    style BEDROCK fill:#FF9900
    style IAM_ROLE fill:#FFD700
```

### 6.2 IAM Permission Model

```mermaid
flowchart LR
    subgraph "GitHub"
        GHA[GitHub Actions<br/>OIDC Token]
    end

    subgraph "AWS IAM"
        OIDC_PROVIDER[OIDC Provider<br/>token.actions.githubusercontent.com]
        TRUST[Trust Policy<br/>repo:org/repo:*]
        ROLE[IAM Role<br/>github-pr-review-role]

        subgraph "Policies"
            P1[bedrock:InvokeModel]
            P2[logs:CreateLogStream]
            P3[s3:PutObject]
            P4[dynamodb:PutItem]
        end
    end

    subgraph "Resources"
        BEDROCK[Bedrock Models]
        CW[CloudWatch]
        S3[S3 Bucket]
        DDB[DynamoDB]
    end

    GHA --> OIDC_PROVIDER
    OIDC_PROVIDER --> TRUST
    TRUST --> ROLE
    ROLE --> P1 --> BEDROCK
    ROLE --> P2 --> CW
    ROLE --> P3 --> S3
    ROLE --> P4 --> DDB

    style ROLE fill:#FFD700
```

---

## 7. Lambda Function Specifications

### 7.1 Function Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Runtime** | Python 3.11 | aioboto3 compatibility |
| **Memory** | 1024 MB | Parallel agent execution |
| **Timeout** | 300 seconds | Large PR processing |
| **Architecture** | arm64 | Cost optimization |
| **Concurrency** | 100 | Rate limiting protection |

### 7.2 Lambda Layers

```mermaid
flowchart TB
    subgraph "Lambda Function"
        CODE[Function Code<br/>agent_orchestrator.py]
    end

    subgraph "Lambda Layers"
        L1[Layer 1: aioboto3<br/>aioboto3, aiobotocore, aiohttp]
        L2[Layer 2: Common Utils<br/>pydantic, structlog]
    end

    CODE --> L1
    CODE --> L2

    style CODE fill:#FF9900
```

### 7.3 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_REGION` | Bedrock region | `us-east-1` |
| `DEFAULT_MODEL` | Fallback model | `haiku` |
| `CODE_QUALITY_MODEL` | CQ agent model | `haiku` |
| `ARCHITECT_MODEL` | Architect model | `sonnet` |
| `LLD_MODEL` | LLD agent model | `sonnet` |
| `JIRA_BASE_URL` | Jira instance | `https://company.atlassian.net` |
| `CONFLUENCE_BASE_URL` | Confluence instance | `https://company.atlassian.net/wiki` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## 8. Integration Patterns

### 8.1 GitHub Integration

```mermaid
sequenceDiagram
    participant GH as GitHub
    participant WF as Workflow
    participant SCRIPT as Python Script
    participant LAMBDA as Lambda

    Note over GH,LAMBDA: Option A: Direct Execution
    GH->>WF: PR Event
    WF->>SCRIPT: Execute bedrock_agent_runner.py
    SCRIPT->>SCRIPT: asyncio.gather() parallel agents
    SCRIPT-->>WF: JSON Results
    WF->>GH: Post Comment

    Note over GH,LAMBDA: Option B: Lambda Invocation
    GH->>WF: PR Event
    WF->>LAMBDA: aws lambda invoke
    LAMBDA->>LAMBDA: Process agents
    LAMBDA-->>WF: JSON Results
    WF->>GH: Post Comment
```

### 8.2 Jira Integration Pattern

```mermaid
flowchart LR
    subgraph "Lambda"
        AGENT[Jira Agent]
        CLIENT[Jira Client]
    end

    subgraph "Jira Cloud"
        API[REST API v3]
        PROJECT[Project: SCM]
        ISSUE[Bug Issue Type]
    end

    AGENT --> CLIENT
    CLIENT -->|POST /rest/api/3/issue| API
    API --> PROJECT
    PROJECT --> ISSUE

    ISSUE -->|Response| CLIENT
    CLIENT -->|Ticket Key| AGENT

    style AGENT fill:#FF9900
```

---

## 9. Async Execution Model

### 9.1 aioboto3 Parallel Execution

```mermaid
gantt
    title Agent Execution Timeline Comparison
    dateFormat s
    axisFormat %S

    section Sequential (boto3)
    Code Quality Agent    :a1, 0, 30s
    Architect Agent       :a2, 30, 45s
    LLD Alignment Agent   :a3, 75, 45s
    Total: 120s           :milestone, m1, 120, 0s

    section Parallel (aioboto3)
    Code Quality Agent    :b1, 0, 30s
    Architect Agent       :b2, 0, 45s
    LLD Alignment Agent   :b3, 0, 45s
    Total: 45s            :milestone, m2, 45, 0s
```

### 9.2 Async Code Pattern

```python
async def run_parallel_agents(pr_context: dict) -> dict:
    """Execute multiple agents concurrently using aioboto3."""
    session = aioboto3.Session()

    async def run_agent(agent_name: str, model: str) -> dict:
        async with session.client("bedrock-runtime") as client:
            response = await client.converse(
                modelId=model,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 4096, "temperature": 0.2}
            )
            return parse_response(response)

    # Execute all agents in parallel
    results = await asyncio.gather(
        run_agent("code_quality", "anthropic.claude-3-haiku-20240307-v1:0"),
        run_agent("architect", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        run_agent("lld_alignment", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        return_exceptions=True
    )

    return aggregate_results(results)
```

---

## 10. Security Architecture

### 10.1 Authentication Flow

```mermaid
flowchart TB
    subgraph "GitHub Actions"
        RUNNER[Workflow Runner]
        OIDC_TOKEN[OIDC Token<br/>JWT]
    end

    subgraph "AWS"
        OIDC_PROVIDER[OIDC Provider]
        STS[AWS STS]
        CREDS[Temporary Credentials<br/>15min - 1hr]
        ROLE[IAM Role]
    end

    subgraph "Security Controls"
        TRUST[Trust Policy<br/>repo:org/repo:*]
        PERMS[Permission Boundary]
        AUDIT[CloudTrail Logging]
    end

    RUNNER --> OIDC_TOKEN
    OIDC_TOKEN --> OIDC_PROVIDER
    OIDC_PROVIDER --> TRUST
    TRUST --> STS
    STS --> ROLE
    ROLE --> CREDS
    CREDS --> RUNNER

    ROLE --> PERMS
    STS --> AUDIT

    style OIDC_TOKEN fill:#FFD700
    style CREDS fill:#90EE90
```

### 10.2 Security Controls

| Control | Implementation | Purpose |
|---------|----------------|---------|
| **No Stored Secrets** | OIDC authentication | Eliminate credential exposure |
| **Short-lived Tokens** | 15-60 minute credentials | Reduce attack window |
| **Least Privilege** | Minimal IAM permissions | Limit blast radius |
| **Audit Logging** | CloudTrail enabled | Compliance and forensics |
| **Network Isolation** | VPC endpoints (optional) | Private Bedrock access |
| **Input Validation** | Diff size limits | Prevent prompt injection |

---

## 11. Cost Model

### 11.1 Cost Components

```mermaid
pie title Monthly Cost Breakdown (100 PRs)
    "Bedrock (Haiku)" : 25
    "Bedrock (Sonnet)" : 55
    "Lambda Compute" : 10
    "Data Transfer" : 5
    "CloudWatch" : 5
```

### 11.2 Cost Projections

| Component | Unit Cost | Usage (100 PRs) | Monthly Cost |
|-----------|-----------|-----------------|--------------|
| **Claude Haiku** | $0.25/$1.25 per 1M tokens | 200K in / 50K out | $0.10 |
| **Claude Sonnet** | $3.00/$15.00 per 1M tokens | 300K in / 75K out | $2.00 |
| **Lambda** | $0.20 per 1M requests | 300 invocations | $0.06 |
| **Data Transfer** | $0.09 per GB | 1 GB | $0.09 |
| **CloudWatch** | $0.50 per GB logs | 500 MB | $0.25 |
| **S3** | $0.023 per GB | 100 MB | $0.01 |
| **DynamoDB** | On-demand pricing | 1000 WCU | $0.50 |
| **Total** | - | - | **~$3.00/month** |

---

## 12. Monitoring & Observability

### 12.1 Metrics Dashboard

```mermaid
flowchart TB
    subgraph "CloudWatch Dashboard"
        subgraph "Lambda Metrics"
            M1[Invocations]
            M2[Duration]
            M3[Errors]
            M4[Throttles]
        end

        subgraph "Bedrock Metrics"
            M5[Latency]
            M6[Input Tokens]
            M7[Output Tokens]
            M8[Throttles]
        end

        subgraph "Business Metrics"
            M9[PRs Reviewed]
            M10[Pass Rate]
            M11[Jira Tickets]
            M12[Avg Review Time]
        end
    end

    subgraph "Alerts"
        A1[High Error Rate]
        A2[Latency Spike]
        A3[Cost Anomaly]
    end

    M3 --> A1
    M5 --> A2
    M6 --> A3
    M7 --> A3
```

### 12.2 Log Structure

```json
{
  "timestamp": "2026-01-30T10:00:00Z",
  "workflow_id": "wf-20260130-pr-123-abc1234",
  "pr_number": 123,
  "agent": "code_quality",
  "model": "anthropic.claude-3-haiku-20240307-v1:0",
  "status": "PASS",
  "duration_ms": 2500,
  "input_tokens": 5000,
  "output_tokens": 800,
  "cost_usd": 0.002,
  "violations_count": 0
}
```

---

## 13. Failure Handling

### 13.1 Error Recovery Flow

```mermaid
flowchart TD
    START[Agent Execution] --> INVOKE[Invoke Bedrock]

    INVOKE --> CHECK{Response OK?}

    CHECK -->|Success| PARSE[Parse Response]
    CHECK -->|ThrottlingException| BACKOFF[Exponential Backoff]
    CHECK -->|ValidationException| TERMINAL[Terminal Error]
    CHECK -->|ServiceException| RETRY[Retry with Backoff]
    CHECK -->|Timeout| DLQ[Send to DLQ]

    BACKOFF --> RETRY_CHECK{Retries < 3?}
    RETRY_CHECK -->|Yes| INVOKE
    RETRY_CHECK -->|No| DLQ

    RETRY --> RETRY_CHECK

    TERMINAL --> LOG[Log Error]
    LOG --> DEFAULT[Return Default Response]

    DLQ --> ALERT[CloudWatch Alarm]

    PARSE --> SUCCESS[Return Result]
    DEFAULT --> SUCCESS

    style SUCCESS fill:#90EE90
    style TERMINAL fill:#FF6B6B
    style DLQ fill:#FFD700
```

### 13.2 Circuit Breaker Pattern

```mermaid
stateDiagram-v2
    [*] --> Closed

    Closed --> Open: Failures >= Threshold
    Closed --> Closed: Success

    Open --> HalfOpen: Timeout Expires

    HalfOpen --> Closed: Probe Success
    HalfOpen --> Open: Probe Failure

    note right of Closed: Normal operation<br/>All requests pass through
    note right of Open: Fail fast<br/>No requests to Bedrock
    note right of HalfOpen: Testing recovery<br/>Limited requests
```

---

## 14. Scalability Considerations

### 14.1 Scaling Architecture

```mermaid
flowchart TB
    subgraph "GitHub"
        PR1[PR 1]
        PR2[PR 2]
        PR3[PR 3]
        PRN[PR N...]
    end

    subgraph "Queue Layer"
        SQS[SQS FIFO Queue<br/>pr-review-tasks.fifo]
    end

    subgraph "Compute Layer"
        LAMBDA1[Lambda 1]
        LAMBDA2[Lambda 2]
        LAMBDA3[Lambda 3]
        LAMBDAN[Lambda N...]
    end

    subgraph "Bedrock"
        QUOTA[Model Quota<br/>Tokens per minute]
    end

    PR1 --> SQS
    PR2 --> SQS
    PR3 --> SQS
    PRN --> SQS

    SQS --> LAMBDA1
    SQS --> LAMBDA2
    SQS --> LAMBDA3
    SQS --> LAMBDAN

    LAMBDA1 --> QUOTA
    LAMBDA2 --> QUOTA
    LAMBDA3 --> QUOTA
    LAMBDAN --> QUOTA

    style SQS fill:#FF9900
```

### 14.2 Scaling Limits

| Resource | Default Limit | Recommended | Notes |
|----------|---------------|-------------|-------|
| **Lambda Concurrency** | 1000 | 100 | Per-function limit |
| **Bedrock TPM (Haiku)** | 100K | Request increase | Tokens per minute |
| **Bedrock TPM (Sonnet)** | 50K | Request increase | Tokens per minute |
| **SQS Message Size** | 256 KB | N/A | PR context may exceed |
| **GitHub API Rate** | 5000/hr | N/A | Use conditional requests |

---

## 15. Deployment Architecture

### 15.1 CI/CD Pipeline

```mermaid
flowchart LR
    subgraph "Source"
        REPO[GitHub Repo]
    end

    subgraph "Build"
        GHA[GitHub Actions]
        TEST[Unit Tests]
        LINT[Linting]
    end

    subgraph "Package"
        ZIP[Lambda Package]
        LAYER[Lambda Layer]
    end

    subgraph "Deploy"
        TF[Terraform]
        CFN[CloudFormation]
    end

    subgraph "Environments"
        DEV[Dev]
        STAGING[Staging]
        PROD[Production]
    end

    REPO --> GHA
    GHA --> TEST
    GHA --> LINT
    TEST --> ZIP
    LINT --> ZIP
    ZIP --> LAYER
    LAYER --> TF
    TF --> DEV
    DEV --> STAGING
    STAGING --> PROD

    style PROD fill:#90EE90
```

### 15.2 Infrastructure as Code

```hcl
# Terraform Resource Overview
resource "aws_lambda_function" "pr_review_orchestrator" {
  function_name = "pr-review-orchestrator"
  runtime       = "python3.11"
  handler       = "handler.lambda_handler"
  memory_size   = 1024
  timeout       = 300

  environment {
    variables = {
      DEFAULT_MODEL = "haiku"
      AWS_REGION    = "us-east-1"
    }
  }
}

resource "aws_iam_role" "github_pr_review" {
  name               = "github-pr-review-role"
  assume_role_policy = data.aws_iam_policy_document.github_oidc.json
}
```

---

## 16. Appendix

### 16.1 Glossary

| Term | Definition |
|------|------------|
| **OIDC** | OpenID Connect - Federated authentication standard |
| **STS** | Security Token Service - AWS temporary credential service |
| **Bedrock** | AWS managed service for foundation models |
| **Converse API** | Unified Bedrock API for chat-based models |
| **aioboto3** | Async Python SDK for AWS services |
| **LLD** | Low-Level Design - Detailed technical specifications |

### 16.2 References

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [Claude on Amazon Bedrock](https://docs.anthropic.com/en/build-with-claude/claude-on-amazon-bedrock)
- [aioboto3 Documentation](https://aioboto3.readthedocs.io/)

---

## 17. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-30 | Claude | Initial HLD document |

---

**End of High-Level Design Document**
