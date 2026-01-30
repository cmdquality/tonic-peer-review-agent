# Architecture Diagrams: GitHub → Lambda → Bedrock Integration

## Overview

This document contains detailed architecture diagrams showing how GitHub Actions, AWS Lambda, and AWS Bedrock work together to power the PR Peer Review Agent system.

---

## 1. Master Architecture Diagram

### Complete System Flow

```mermaid
flowchart TB
    subgraph "Developer Workflow"
        DEV[👨‍💻 Developer]
        IDE[VS Code / IDE]
        GIT[Git Push]
    end

    subgraph "GitHub Platform"
        REPO[📁 Repository<br/>tonic-peer-review-agent]
        PR[📝 Pull Request]
        WEBHOOK[🔗 Webhook<br/>pull_request event]
        GHA[⚙️ GitHub Actions<br/>Workflow Runner]
        COMMENT[💬 PR Comment]
        CHECK[✅ Status Check]
    end

    subgraph "AWS Cloud Platform"
        subgraph "Identity & Access"
            OIDC[🔐 OIDC Provider<br/>GitHub Federation]
            STS[🎫 AWS STS<br/>Temporary Credentials]
            IAM[👤 IAM Role<br/>pr-review-role]
        end

        subgraph "Compute & Orchestration"
            API_GW[🚪 API Gateway<br/>Optional Trigger]
            LAMBDA[⚡ AWS Lambda<br/>Agent Orchestrator<br/>Python 3.11 + aioboto3]
            SQS[📨 SQS Queue<br/>Dead Letter Queue]
        end

        subgraph "AI/ML - Amazon Bedrock"
            BEDROCK[🧠 Bedrock Runtime]
            HAIKU[Claude 3 Haiku<br/>Code Quality Agent<br/>$0.25/1M tokens]
            SONNET[Claude 3.5 Sonnet<br/>Architect Agent<br/>$3/1M tokens]
            SONNET2[Claude 3.5 Sonnet<br/>LLD Alignment Agent<br/>$3/1M tokens]
        end

        subgraph "Storage & Logging"
            S3[📦 S3 Bucket<br/>Review Artifacts]
            DDB[📊 DynamoDB<br/>Review History]
            CW[📋 CloudWatch<br/>Logs & Metrics]
        end
    end

    subgraph "External Services"
        JIRA[🎫 Jira Cloud<br/>Ticket Creation]
        CONFLUENCE[📚 Confluence<br/>Pattern Library]
    end

    %% Developer flow
    DEV --> IDE --> GIT --> REPO
    REPO --> PR
    PR --> WEBHOOK

    %% GitHub Actions flow
    WEBHOOK --> GHA
    GHA -->|"1. Generate OIDC Token"| OIDC
    OIDC -->|"2. Validate Federation"| STS
    STS -->|"3. Issue Temp Creds"| IAM
    IAM -->|"4. Authorized"| GHA

    %% Execution paths
    GHA -->|"Option A: Direct"| LAMBDA
    GHA -->|"Option B: Via API"| API_GW --> LAMBDA

    %% Lambda to Bedrock
    LAMBDA -->|"Parallel Execution"| BEDROCK
    BEDROCK --> HAIKU
    BEDROCK --> SONNET
    BEDROCK --> SONNET2

    %% Lambda storage
    LAMBDA --> S3
    LAMBDA --> DDB
    LAMBDA --> CW
    LAMBDA -.->|"On Failure"| SQS

    %% External integrations
    LAMBDA -->|"On Review Failure"| JIRA
    LAMBDA -->|"Read Patterns"| CONFLUENCE

    %% Results back to GitHub
    LAMBDA -->|"Review Results"| GHA
    GHA --> COMMENT
    GHA --> CHECK
    CHECK --> PR
    COMMENT --> PR

    %% Notifications
    PR -->|"Notification"| DEV

    %% Styling
    style LAMBDA fill:#FF9900,color:#000
    style HAIKU fill:#90EE90,color:#000
    style SONNET fill:#87CEEB,color:#000
    style SONNET2 fill:#87CEEB,color:#000
    style IAM fill:#FFD700,color:#000
    style OIDC fill:#FFD700,color:#000
```

---

## 2. Authentication Deep Dive

### OIDC Federation Flow

```mermaid
sequenceDiagram
    autonumber

    participant GHA as GitHub Actions<br/>Workflow Runner
    participant OIDC as AWS OIDC Provider<br/>token.actions.githubusercontent.com
    participant STS as AWS STS<br/>Security Token Service
    participant IAM as IAM Role<br/>github-pr-review-role
    participant Lambda as AWS Lambda
    participant Bedrock as AWS Bedrock

    Note over GHA: Workflow triggered by PR event

    GHA->>GHA: Request OIDC JWT Token
    Note right of GHA: Token contains:<br/>- repo: org/repo<br/>- ref: refs/heads/main<br/>- workflow: review.yml

    GHA->>OIDC: Present JWT Token
    OIDC->>OIDC: Validate Token Signature

    OIDC->>STS: AssumeRoleWithWebIdentity
    Note right of STS: Request contains:<br/>- RoleArn<br/>- WebIdentityToken

    STS->>IAM: Evaluate Trust Policy
    Note right of IAM: Trust Policy checks:<br/>- Federated principal<br/>- Condition: repo match

    IAM-->>STS: Role Assumption Approved

    STS-->>GHA: Return Temporary Credentials
    Note right of GHA: Credentials include:<br/>- AccessKeyId<br/>- SecretAccessKey<br/>- SessionToken<br/>- Expiration (1 hour)

    GHA->>Lambda: Invoke with Credentials

    Lambda->>Bedrock: converse() API Call
    Note right of Bedrock: Using temp credentials<br/>from environment

    Bedrock-->>Lambda: Claude Response
    Lambda-->>GHA: Review Results

    Note over GHA,Bedrock: Credentials auto-expire after session
```

### IAM Policy Structure

```mermaid
flowchart LR
    subgraph "Trust Policy"
        TP[Trust Policy]
        FED[Federated Principal<br/>arn:aws:iam::ACCOUNT:oidc-provider/<br/>token.actions.githubusercontent.com]
        COND[Conditions]
        SUB[StringLike: sub<br/>repo:org/repo:*]
        AUD[StringEquals: aud<br/>sts.amazonaws.com]
    end

    subgraph "Permission Policy"
        PP[Permission Policy]
        BEDROCK_PERM[bedrock:InvokeModel<br/>bedrock:InvokeModelWithResponseStream]
        LAMBDA_PERM[lambda:InvokeFunction]
        LOGS_PERM[logs:*]
        S3_PERM[s3:GetObject<br/>s3:PutObject]
    end

    subgraph "Resources"
        BEDROCK_RES[arn:aws:bedrock:*::foundation-model/anthropic.claude-*]
        LAMBDA_RES[arn:aws:lambda:*:*:function:pr-review-*]
        S3_RES[arn:aws:s3:::pr-review-artifacts/*]
    end

    TP --> FED
    TP --> COND
    COND --> SUB
    COND --> AUD

    PP --> BEDROCK_PERM --> BEDROCK_RES
    PP --> LAMBDA_PERM --> LAMBDA_RES
    PP --> LOGS_PERM
    PP --> S3_PERM --> S3_RES

    style TP fill:#FFD700
    style PP fill:#87CEEB
```

---

## 3. Lambda Execution Architecture

### Internal Lambda Structure

```mermaid
flowchart TB
    subgraph "Lambda Function: pr-review-orchestrator"
        HANDLER[🚀 handler.lambda_handler<br/>Entry Point]

        subgraph "Core Services"
            PR_SVC[PR Context Service<br/>Fetch PR data from GitHub]
            BEDROCK_SVC[Bedrock Service<br/>aioboto3 async client]
            JIRA_SVC[Jira Service<br/>Ticket creation]
        end

        subgraph "Agents"
            CQ[Code Quality Agent<br/>Prompt: code_best_practices.md]
            ARCH[Architect Agent<br/>Prompt: architect_best_practices.md]
            LLD[LLD Alignment Agent<br/>Prompt: lld_alignment.md]
            JIRA_A[Jira Integration Agent<br/>Prompt: jira_integration.md]
        end

        subgraph "Utilities"
            CHUNKER[Diff Chunker<br/>Split large diffs]
            PARSER[Response Parser<br/>JSON extraction]
            AGGREGATOR[Result Aggregator<br/>Combine parallel results]
            REPORTER[Report Generator<br/>Format PR comment]
        end
    end

    subgraph "External"
        GH_API[GitHub API]
        BEDROCK[AWS Bedrock]
        JIRA_API[Jira API]
    end

    HANDLER --> PR_SVC
    PR_SVC --> GH_API

    HANDLER --> BEDROCK_SVC

    BEDROCK_SVC --> CQ
    BEDROCK_SVC --> ARCH
    BEDROCK_SVC --> LLD
    BEDROCK_SVC --> JIRA_A

    CQ --> BEDROCK
    ARCH --> BEDROCK
    LLD --> BEDROCK
    JIRA_A --> BEDROCK

    PR_SVC --> CHUNKER
    CHUNKER --> BEDROCK_SVC

    BEDROCK --> PARSER
    PARSER --> AGGREGATOR
    AGGREGATOR --> REPORTER

    JIRA_A --> JIRA_SVC --> JIRA_API

    style HANDLER fill:#FF9900
    style BEDROCK_SVC fill:#FF9900
```

### Async Execution Timeline

```mermaid
gantt
    title Lambda Agent Execution Timeline
    dateFormat ss
    axisFormat %S s

    section Initialization
    Cold Start (if applicable)    :init, 00, 2s
    Load PR Context               :context, after init, 1s

    section Sequential Approach (boto3)
    Code Quality Agent            :seq_cq, after context, 30s
    Wait for CQ result            :milestone, m1, after seq_cq, 0s
    Architect Agent               :seq_arch, after seq_cq, 45s
    Wait for Arch result          :milestone, m2, after seq_arch, 0s
    LLD Alignment Agent           :seq_lld, after seq_arch, 45s
    Total Sequential: ~123s       :milestone, m3, after seq_lld, 0s

    section Parallel Approach (aioboto3)
    Code Quality Agent            :par_cq, after context, 30s
    Architect Agent               :par_arch, after context, 45s
    LLD Alignment Agent           :par_lld, after context, 45s
    asyncio.gather() completion   :milestone, m4, 48, 0s
    Total Parallel: ~48s          :crit, result, 48, 1s
```

---

## 4. Agent Decision Flow

### Review Pipeline Logic

```mermaid
flowchart TD
    START([🚀 PR Review Triggered]) --> PREFLIGHT{Pre-Flight<br/>Checks}

    PREFLIGHT -->|Draft PR| SKIP([⏭️ Skip Review])
    PREFLIGHT -->|No Code Changes| SKIP
    PREFLIGHT -->|skip-review label| SKIP
    PREFLIGHT -->|✅ Proceed| CQ

    CQ[🔍 Code Quality Agent<br/>Claude Haiku]

    CQ --> CQ_RESULT{Code Quality<br/>Result}

    CQ_RESULT -->|PASS<br/>No Violations| ARCH
    CQ_RESULT -->|FAIL<br/>Violations Found| JIRA_CQ

    ARCH[🏗️ Architect Agent<br/>Claude Sonnet]

    ARCH --> ARCH_RESULT{New Pattern<br/>Detected?}

    ARCH_RESULT -->|NO_NEW_PATTERN| APPROVE
    ARCH_RESULT -->|NEW_PATTERN_DETECTED| LLD

    LLD[📐 LLD Alignment Agent<br/>Claude Sonnet]

    LLD --> LLD_RESULT{LLD Alignment<br/>Check}

    LLD_RESULT -->|LLD_COMPLIANT| PATTERN_REVIEW
    LLD_RESULT -->|LLD_DEVIATION_FOUND| JIRA_LLD

    JIRA_CQ[🎫 Create Jira Ticket<br/>Type: Code Violations]
    JIRA_LLD[🎫 Create Jira Ticket<br/>Type: LLD Deviation]

    JIRA_CQ --> BLOCK
    JIRA_LLD --> BLOCK

    APPROVE([✅ APPROVED<br/>Ready to Merge])
    PATTERN_REVIEW([⏳ WAITING_REVIEW<br/>New Pattern Approval])
    BLOCK([❌ BLOCKED<br/>Fix Required])

    APPROVE --> REPORT
    PATTERN_REVIEW --> REPORT
    BLOCK --> REPORT

    REPORT[📊 Generate Report<br/>Post to GitHub]

    REPORT --> COMMENT[💬 PR Comment]
    REPORT --> STATUS[✅ Status Check]

    style CQ fill:#90EE90
    style ARCH fill:#87CEEB
    style LLD fill:#87CEEB
    style APPROVE fill:#90EE90
    style BLOCK fill:#FF6B6B
    style PATTERN_REVIEW fill:#FFD700
```

---

## 5. Bedrock API Interaction

### Converse API Flow

```mermaid
sequenceDiagram
    autonumber

    participant Lambda as Lambda Function
    participant Client as aioboto3 Client<br/>bedrock-runtime
    participant Bedrock as Bedrock Runtime
    participant Claude as Claude Model<br/>Haiku/Sonnet

    Lambda->>Lambda: Prepare agent prompt
    Note right of Lambda: Combine:<br/>- Agent spec (MD file)<br/>- PR context (diff, metadata)<br/>- Output format instructions

    Lambda->>Client: async with session.client()
    Client->>Bedrock: converse()
    Note right of Bedrock: Request body:<br/>- modelId<br/>- messages[{role, content}]<br/>- inferenceConfig

    Bedrock->>Claude: Forward to model
    Claude->>Claude: Process prompt

    Claude-->>Bedrock: Generated response
    Bedrock-->>Client: ConversationResponse

    Client-->>Lambda: Response object

    Lambda->>Lambda: Parse JSON from response
    Note right of Lambda: Extract:<br/>- output.message.content[0].text<br/>- usage.inputTokens<br/>- usage.outputTokens

    Lambda->>Lambda: Validate JSON structure
    Lambda->>Lambda: Log token usage & cost
```

### Request/Response Structure

```mermaid
flowchart LR
    subgraph "Request"
        REQ[converse() Call]
        MODEL[modelId:<br/>anthropic.claude-3-haiku...]
        MSG[messages:<br/>role: user<br/>content: text]
        CONFIG[inferenceConfig:<br/>maxTokens: 4096<br/>temperature: 0.2<br/>topP: 0.9]
    end

    subgraph "Response"
        RESP[ConversationResponse]
        OUTPUT[output.message.content[0].text:<br/>JSON review result]
        USAGE[usage:<br/>inputTokens: 5000<br/>outputTokens: 800]
        STOP[stopReason:<br/>end_turn]
    end

    REQ --> MODEL
    REQ --> MSG
    REQ --> CONFIG

    REQ ==>|API Call| RESP

    RESP --> OUTPUT
    RESP --> USAGE
    RESP --> STOP

    style REQ fill:#87CEEB
    style RESP fill:#90EE90
```

---

## 6. Error Handling Architecture

### Retry & Circuit Breaker Pattern

```mermaid
stateDiagram-v2
    [*] --> Normal

    state Normal {
        [*] --> Invoke
        Invoke --> Success: 2xx Response
        Invoke --> CheckError: Error

        state CheckError {
            [*] --> Classify
            Classify --> Retryable: ThrottlingException
            Classify --> Retryable: ServiceUnavailable
            Classify --> Terminal: ValidationException
            Classify --> Terminal: AccessDeniedException
        }

        Retryable --> Backoff: attempts < 3
        Backoff --> Invoke
        Retryable --> DLQ: attempts >= 3
        Terminal --> DefaultResponse
    }

    state "Circuit Open" as Open {
        [*] --> FailFast
        FailFast --> DefaultResponse
    }

    state "Half Open" as HalfOpen {
        [*] --> ProbeInvoke
        ProbeInvoke --> Normal: Success
        ProbeInvoke --> Open: Failure
    }

    Normal --> Open: 5 failures in 1 minute
    Open --> HalfOpen: 30 second timeout
    Success --> [*]
    DLQ --> [*]
    DefaultResponse --> [*]
```

### Error Classification

```mermaid
flowchart TD
    ERROR[Bedrock Error]

    ERROR --> CLASSIFY{Error Code}

    CLASSIFY -->|ThrottlingException| RETRY[Retryable<br/>Exponential Backoff]
    CLASSIFY -->|ServiceUnavailable| RETRY
    CLASSIFY -->|ModelStreamErrorException| RETRY
    CLASSIFY -->|ValidationException| TERMINAL[Terminal Error<br/>Log & Return Default]
    CLASSIFY -->|AccessDeniedException| TERMINAL
    CLASSIFY -->|ResourceNotFoundException| TERMINAL
    CLASSIFY -->|Timeout| DLQ[Send to DLQ<br/>Alert Team]

    RETRY --> BACKOFF[Wait: 2^attempt + jitter<br/>Max 60 seconds]
    BACKOFF --> ATTEMPT{Attempt < 3?}
    ATTEMPT -->|Yes| REINVOKE[Retry Invocation]
    ATTEMPT -->|No| DLQ

    TERMINAL --> LOG[Log Error Details]
    LOG --> DEFAULT[Return Default Response]

    style RETRY fill:#FFD700
    style TERMINAL fill:#FF6B6B
    style DLQ fill:#FF6B6B
```

---

## 7. Monitoring Dashboard

### CloudWatch Metrics Layout

```mermaid
flowchart TB
    subgraph "CloudWatch Dashboard: PR Review System"
        subgraph "Row 1: Lambda Health"
            M1[📊 Invocations<br/>Count per minute]
            M2[⏱️ Duration<br/>p50, p95, p99]
            M3[❌ Errors<br/>Error rate %]
            M4[🚫 Throttles<br/>Concurrent limit hits]
        end

        subgraph "Row 2: Bedrock Usage"
            M5[📈 Bedrock Latency<br/>Response time]
            M6[📥 Input Tokens<br/>Sum per hour]
            M7[📤 Output Tokens<br/>Sum per hour]
            M8[💰 Estimated Cost<br/>USD per day]
        end

        subgraph "Row 3: Business Metrics"
            M9[✅ Reviews Completed<br/>PRs per day]
            M10[📊 Pass Rate<br/>% approved]
            M11[🎫 Jira Tickets<br/>Created per week]
            M12[⏱️ Avg Review Time<br/>Seconds]
        end

        subgraph "Row 4: Alerts"
            A1[🔴 High Error Rate<br/>> 5% in 5 min]
            A2[🟡 Latency Spike<br/>> 60s p95]
            A3[🟠 Cost Anomaly<br/>> 150% daily avg]
        end
    end

    M3 -.->|Triggers| A1
    M2 -.->|Triggers| A2
    M8 -.->|Triggers| A3
```

---

## 8. Deployment Pipeline

### Infrastructure Deployment

```mermaid
flowchart LR
    subgraph "Source"
        CODE[Lambda Code]
        IaC[Terraform/CDK]
    end

    subgraph "CI Pipeline"
        LINT[Lint & Format]
        TEST[Unit Tests]
        SEC[Security Scan]
    end

    subgraph "Build"
        PKG[Package Lambda]
        LAYER[Build Layers]
        ARTIFACT[Upload to S3]
    end

    subgraph "Deploy"
        PLAN[Terraform Plan]
        REVIEW[Manual Review]
        APPLY[Terraform Apply]
    end

    subgraph "Environments"
        DEV[🔧 Dev]
        STAGING[🧪 Staging]
        PROD[🚀 Production]
    end

    CODE --> LINT
    IaC --> LINT
    LINT --> TEST
    TEST --> SEC
    SEC --> PKG
    SEC --> LAYER
    PKG --> ARTIFACT
    LAYER --> ARTIFACT

    ARTIFACT --> PLAN
    PLAN --> REVIEW
    REVIEW --> APPLY

    APPLY --> DEV
    DEV -->|Promote| STAGING
    STAGING -->|Promote| PROD

    style PROD fill:#90EE90
```

---

## 9. Cost Architecture

### Cost Flow Diagram

```mermaid
flowchart TB
    subgraph "Cost Centers"
        PR[PR Event]
    end

    subgraph "Compute Costs"
        LAMBDA_COST[Lambda<br/>$0.20/1M requests<br/>$0.0000166667/GB-s]
    end

    subgraph "AI Costs"
        HAIKU_COST[Haiku<br/>$0.25 input / $1.25 output<br/>per 1M tokens]
        SONNET_COST[Sonnet<br/>$3.00 input / $15.00 output<br/>per 1M tokens]
    end

    subgraph "Storage Costs"
        S3_COST[S3<br/>$0.023/GB]
        DDB_COST[DynamoDB<br/>On-demand pricing]
        CW_COST[CloudWatch<br/>$0.50/GB logs]
    end

    subgraph "Total Per PR"
        SMALL[Small PR<br/>< 10 files<br/>~$0.01]
        MEDIUM[Medium PR<br/>10-30 files<br/>~$0.05]
        LARGE[Large PR<br/>> 50 files<br/>~$0.20]
    end

    PR --> LAMBDA_COST
    LAMBDA_COST --> HAIKU_COST
    LAMBDA_COST --> SONNET_COST
    LAMBDA_COST --> S3_COST
    LAMBDA_COST --> DDB_COST
    LAMBDA_COST --> CW_COST

    HAIKU_COST --> SMALL
    HAIKU_COST --> MEDIUM
    SONNET_COST --> MEDIUM
    SONNET_COST --> LARGE

    style SMALL fill:#90EE90
    style MEDIUM fill:#FFD700
    style LARGE fill:#FF6B6B
```

---

## 10. Quick Reference Card

### System Components at a Glance

| Layer | Component | Technology | Purpose |
|-------|-----------|------------|---------|
| **Trigger** | GitHub Webhook | GitHub Actions | PR event detection |
| **Auth** | OIDC Federation | AWS IAM | Secure authentication |
| **Compute** | Agent Orchestrator | AWS Lambda + Python 3.11 | Agent execution |
| **AI** | Code Quality | Claude Haiku | Fast code review |
| **AI** | Architect | Claude Sonnet | Pattern detection |
| **AI** | LLD Alignment | Claude Sonnet | Design compliance |
| **Integration** | Jira Agent | Jira REST API | Ticket creation |
| **Storage** | Artifacts | S3 | Review data |
| **Monitoring** | Metrics | CloudWatch | Observability |

### Key Configuration Values

| Setting | Value | Notes |
|---------|-------|-------|
| Lambda Memory | 1024 MB | Parallel agent support |
| Lambda Timeout | 300 sec | Large PR processing |
| Bedrock Region | us-east-1 | Best model availability |
| OIDC Token Duration | 1 hour | Auto-refresh |
| Retry Attempts | 3 | With exponential backoff |
| Max Diff Size | 100 KB | Per agent call |

---

**End of Architecture Diagrams**
