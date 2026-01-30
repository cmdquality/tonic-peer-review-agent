# Skills Folder

This folder contains specialized skill documents that provide detailed workflow guidance for the Tonic Peer Review Agent system.

## Purpose

Skills are reusable, focused documents that define specific workflows, techniques, or processes that agents can invoke when performing specialized tasks. Skills complement agent definitions by providing deep-dive procedural knowledge.

## Associated Skills

The following skills are referenced by agents in this system (to be developed):

### 1. GitHub Integration Skill
**Purpose**: GitHub API operations, PR management, webhook handling
**Used By**: All agents for GitHub interactions

### 2. Confluence Integration Skill
**Purpose**: Confluence API operations, pattern library management
**Used By**: Code Best Practises Agent, Pattern Matching Agent

### 3. Jira Integration Skill
**Purpose**: Jira API operations, ticket creation workflows
**Used By**: Jira Integration Agent

### 4. Code Analysis Skill
**Purpose**: AST parsing, pattern matching, code validation techniques
**Used By**: Code Best Practises Agent, Architect Best Practises Agent

### 5. Pattern Mining Skill ✅ IMPLEMENTED
**Purpose**: Read-only codebase analysis to identify design patterns, anti-patterns, and non-pattern code
**Used By**: Pattern Mining Agent, Peer Review Agent, Pattern Matching Agent
**Location**: `pattern_mining_skill.md`
**Report Template**: `pattern_mining_report_template.md`
**Agent**: `../agents/pattern_mining_agent.md`

**Capabilities**:
- EIP Pattern Detection (Apache Camel 4.14.x): Router, Mapper, Transformer, Adapter, Splitter, Aggregator
- Core Java Pattern Detection: Facade/Controller, DAO/Repository, DTO/TO/Bean, Entity, Service, Factory
- GoF Pattern Detection: Strategy, Observer, Command, Builder, Singleton
- Anti-Pattern Detection: Circular References, Stovepipe, Monolith, God Object, Anemic Domain Model
- Non-Pattern Code Identification
- Structured Report Generation with numbered sections (X.Y.Z format)
- Remediation Recommendations by priority (Critical, High, Medium, Low)

**Pattern Catalogs**:
- EIP Patterns: 25+ patterns from Apache Camel
- Core Java Patterns: 15+ patterns including data access and business logic
- Anti-Patterns: 14+ architectural, design, and integration anti-patterns

## Skill File Format

Each skill document should follow this structure:

```markdown
# [Skill Name]

## Purpose
[What this skill enables]

## When to Load
[Conditions for invoking this skill]

## Procedures
[Step-by-step workflows]

## Examples
[Concrete usage examples]

## Integration
[How agents use this skill]
```

## Implemented Skills

| Skill | Status | Location |
|-------|--------|----------|
| Pattern Mining Skill | ✅ Implemented | `pattern_mining_skill.md` |
| Pattern Mining Report Template | ✅ Implemented | `pattern_mining_report_template.md` |
| Jira Ticket Skill | ✅ Implemented | `jira_ticket_skill.md` |
| Orchestrator Skill | ✅ Implemented | `orchestrator_skill.md` |

## Associated Agents

| Agent | Skills Used | Location |
|-------|-------------|----------|
| Pattern Mining Agent | Pattern Mining Skill | `../agents/pattern_mining_agent.md` |

## Future Development

Skills to be developed as agents are implemented:
1. GitHub API Skill (critical for all agents)
2. Confluence API Skill (critical for pattern management)

---

**Last Updated**: 2026-01-30
