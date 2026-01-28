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

## Future Development

Skills will be developed as agents are implemented. Priority skills:
1. GitHub API Skill (critical for all agents)
2. Confluence API Skill (critical for pattern management)
3. Jira API Skill (critical for issue tracking)

---

**Note**: This folder serves as a placeholder. Skills will be added during implementation phase.
