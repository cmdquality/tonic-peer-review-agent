# Tonic Peer Review Agent

AI-powered peer review agent system for the Tonic Configuration Management Platform.

## Overview

This repository contains the agent definitions and specifications for an automated code quality and architectural review system. The system enforces coding standards, detects new patterns, validates against LLD specifications, and orchestrates peer reviews.

## Repository Structure

```
tonic-peer-review-agent/
├── agents/                              # Agent definition files
│   ├── code_best_practises_agent.md     # Code standards enforcement
│   ├── architect_best_practises_agent.md # Pattern detection
│   ├── lld_alignment_review_agent.md    # LLD compliance validation
│   ├── pattern_matching_agent.md        # Pattern library management
│   ├── peer_review_documentation_agent.md # Review orchestration
│   └── jira_integration_agent.md        # Issue tracking automation
├── skills/                              # Skill documents (future)
│   └── README.md
├── *_spec.md                            # Agent specifications (source)
└── README.md                            # This file
```

## Agents

### 1. Code Best Practises Agent
**Purpose**: Enforce coding standards by analyzing PR code against approved patterns
- Analyzes all PR code against Confluence pattern library
- Blocks non-compliant PRs (non-optional enforcement)
- 30-second SLA for analysis
- **ATSQ**: 75% time savings

### 2. Architect Best Practises Agent
**Purpose**: Detect new coding patterns not in the approved library
- Identifies novel patterns using 85% similarity threshold
- Routes new patterns to architectural review
- 10-second SLA for detection
- **ATSQ**: 80% time savings

### 3. LLD Alignment Review Agent
**Purpose**: Validate code changes against LLD specifications
- Ensures patterns comply with documented design
- Flags deviations with severity classification (CRITICAL/MAJOR/MINOR)
- 20-second SLA for validation
- **ATSQ**: 82.5% time savings

### 4. Pattern Matching Agent
**Purpose**: Manage pattern library in Confluence
- Stores approved patterns with versioning
- Provides fast pattern queries (< 2 seconds)
- Immutable patterns once approved
- **ATSQ**: 95% time savings

### 5. Peer Review Documentation Agent
**Purpose**: Orchestrate human architectural review
- Automated reviewer assignment based on expertise
- 4-hour SLA enforcement with escalation
- Minimum 1 architect approval required
- **ATSQ**: 70% time savings

### 6. Jira Integration Agent
**Purpose**: Create Jira tickets for violations and rejections
- Automatic ticket creation with complete context
- Links tickets to PRs (bidirectional)
- Queues tickets if Jira unavailable (no data loss)
- **ATSQ**: 92% time savings

## Workflow

```
PR Created → Code Best Practises Agent
                    ↓
           [Violations?]
           Yes → Jira Ticket → Block PR
           No ↓
    Architect Best Practises Agent
                    ↓
           [New Pattern?]
           No → Skip to Deployment
           Yes ↓
    LLD Alignment Review Agent
                    ↓
           [LLD Deviation?]
           Yes → Jira Ticket → Require Fix
           No ↓
    Pattern Matching Agent (store)
                    ↓
    Peer Review Documentation Agent
                    ↓
           [Approved?]
           No → Jira Ticket → Close PR
           Yes ↓
    Merge PR → Deploy
```

## Related Documents

- **LLD Reference**: `LLD/lld_1_config_management_platform.md`
- **Agent Builder**: `Agentic_Architect/Agent_Builder.md`
- **DevOps Agent**: `Agentic_Architect/DevOps_agent.md`

## Technology Stack

- **AI Agents**: GenAI-powered analysis (implementation TBD)
- **CI/CD**: GitHub Actions
- **Knowledge Base**: Confluence (patterns, HLD, LLD)
- **Issue Tracking**: Jira
- **Cloud**: AWS (CloudWatch, DynamoDB)
- **Programming Language**: Java with Spring Boot (planned)

## Getting Started

### Prerequisites
- Access to GitHub repository
- Confluence API credentials
- Jira API credentials
- AWS credentials (for CloudWatch logging)

### Implementation Steps
1. Review agent definitions in `agents/` folder
2. Implement agents following the specifications
3. Configure GitHub Actions workflows
4. Set up Confluence pattern library (SCM-PATTERNS space)
5. Configure Jira project (SCM) with required issue types
6. Deploy agents to AWS (Lambda or ECS Fargate)

## Contributing

When adding new agents:
1. Create agent specification using 10-question format (see `*_spec.md` files)
2. Generate agent definition using Agent Builder
3. Place agent definition in `agents/` folder
4. Update this README with agent description

## License

Internal use only - Tonic Configuration Management Platform

---

**Repository**: https://github.com/cmdquality/tonic-peer-review-agent
