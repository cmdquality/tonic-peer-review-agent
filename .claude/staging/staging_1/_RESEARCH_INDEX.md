# Research Index: AWS Bedrock Claude Integration for GitHub Actions

## Research Overview

| Field | Value |
|-------|-------|
| **Research Topic** | Running Claude AI Agents in GitHub Actions using AWS Bedrock |
| **Research Date** | 2026-01-28 (Updated: 2026-01-30) |
| **Research Method** | Technical documentation review, API analysis, implementation |
| **Scope** | Option B: Python Script with AWS Bedrock SDK (aioboto3 async) |
| **Status** | ✅ Complete with implementation and HLD delivered |

---

## Main Deliverables

| File | Description | Location |
|------|-------------|----------|
| **AWS_Bedrock_Claude_GitHub_Actions_Research.md** | Comprehensive research document with executive summary, analysis, and recommendations | `staging_1/` |
| **aioboto3_vs_boto3_comparison.md** | Detailed comparison of async vs sync approaches | `staging_1/research/` |

---

## High-Level Design (HLD) Documents

| File | Description | Location |
|------|-------------|----------|
| **PR_Peer_Review_System_HLD.md** | Complete HLD with system context, architecture, data flow, security, and cost model | `staging_1/hld/` |
| **Architecture_Diagrams.md** | Detailed Mermaid diagrams showing GitHub → Lambda → Bedrock integration | `staging_1/hld/` |

### HLD Sections Include:
- System Context Diagram (C4 style)
- Complete Architecture Overview
- Lambda Function Architecture
- Agent Orchestration Flow
- Data Flow Diagrams
- AWS Infrastructure Topology
- IAM Permission Model
- Async Execution Model (aioboto3)
- Security Architecture (OIDC)
- Error Handling & Circuit Breaker
- Monitoring Dashboard
- Cost Architecture
- Deployment Pipeline

---

## Low-Level Design (LLD) Documents

| File | Description | Location |
|------|-------------|----------|
| **Lambda_Bedrock_LLD.md** | Detailed LLD focusing on Lambda → Bedrock → External Integrations | `staging_1/lld/` |

### LLD Sections Include:
- Lambda Function Package Structure
- Class Diagrams (UML)
- Lambda Handler Implementation
- Bedrock Service (aioboto3 async client)
- Model Configuration & Cost Calculation
- Base Agent & Concrete Implementations
- Agent Orchestrator with Parallel Execution
- Jira Service & ADF Format
- Diff Chunker for Large PRs
- Error Handling & Retry Logic
- Data Models (PRContext, AgentResult, ReviewReport)
- Lambda Layer Configuration
- Environment Variables Reference

---

## Supporting Diagrams

| # | Diagram | Purpose | File |
|---|---------|---------|------|
| 1 | Model Cost Comparison | Compare Haiku/Sonnet/Opus pricing | `diagrams/01_model_cost_comparison.md` |
| 2 | OIDC Authentication Flow | Show secure authentication without secrets | `diagrams/02_authentication_flow.md` |
| 3 | API Comparison | Converse vs InvokeModel API decision | `diagrams/03_api_comparison.md` |
| 4 | System Architecture | End-to-end PR review flow | `diagrams/04_system_architecture.md` |
| 5 | Option Comparison | Why Option B over A, C, D | `diagrams/05_option_comparison.md` |
| 6 | Async vs Sync Comparison | aioboto3 vs boto3 performance | `diagrams/06_async_vs_sync_comparison.md` |

---

## Implementation Files Delivered

| File | Purpose | Location |
|------|---------|----------|
| `bedrock_agent_runner.py` | Synchronous agent execution (boto3) | `.github/scripts/` |
| `bedrock_agent_runner_async.py` | **Async agent execution (aioboto3)** - RECOMMENDED | `.github/scripts/` |
| `peer_review_bedrock.yml` | GitHub Actions workflow | `.github/workflows/` |
| `requirements.txt` | Python dependencies (aioboto3) | `.github/scripts/` |
| `bedrock_setup_guide.md` | Deployment instructions | `docs/` |

---

## Key Research Findings

### 1. Claude Code CLI NOT Viable
- Requires OAuth browser authentication
- Incompatible with headless CI environments
- No non-interactive mode available

### 2. AWS Bedrock is Optimal Choice
- OIDC authentication (no stored secrets)
- Enterprise security integration
- AWS billing consolidation
- Model flexibility (Haiku/Sonnet/Opus)

### 3. Converse API Recommended
- Unified interface across all models
- Simpler code, fewer lines
- Built-in token tracking
- Future-proof for new models

### 4. Cost-Effective Model Selection
- Haiku for high-volume checks ($0.25/1M tokens)
- Sonnet for complex analysis ($3/1M tokens)
- 5-10x savings with smart selection

### 5. aioboto3 Recommended Over boto3 (NEW)
- **2.7x speedup** for parallel agent execution
- Full Bedrock Converse API support (v13.1.0+)
- Native asyncio without thread management
- Parallel chunk processing for large PRs
- Same API as boto3 (just add `await`)

---

## Research Questions Answered

| Question | Answer |
|----------|--------|
| Can Claude Code run in GitHub Actions? | ❌ No - requires browser OAuth |
| What's the best alternative? | AWS Bedrock with OIDC |
| Which API to use? | Converse API (unified) |
| Which model for code review? | Haiku (cost) or Sonnet (capability) |
| How to authenticate? | GitHub OIDC → AWS STS → Bedrock |
| Estimated cost per PR? | $0.005 - $0.20 depending on complexity |

---

## Next Steps for Implementation

1. [ ] Enable Claude models in AWS Bedrock console
2. [ ] Create OIDC provider in AWS IAM
3. [ ] Create IAM role with Bedrock permissions
4. [ ] Add `AWS_BEDROCK_ROLE_ARN` secret to GitHub
5. [ ] Deploy workflow and scripts
6. [ ] Test with sample PR

---

## Sources Referenced

- AWS Bedrock Pricing
- Boto3 Converse API Documentation
- GitHub Actions OIDC with AWS
- Claude on Amazon Bedrock Documentation
- Anthropic Model Overview

---

**Research Completed**: 2026-01-28
**Researcher**: Claude (Agentic Researcher Agent)
**Methodology**: Agentic_Researcher.md v2.0
