# Pattern Mining Skill

**Version**: 1.0
**Created**: 2026-01-30
**Purpose**: Read-only analysis of codebases to identify design patterns, anti-patterns, and non-pattern code with remediation recommendations

---

## Skill Identity

**Name**: Pattern Mining Skill
**Type**: Code Analysis Skill (Read-Only)
**Domain**: Software Architecture Analysis
**Parent Agent**: Peer Review Agent, Pattern Matching Agent

---

## Purpose

The Pattern Mining Skill enables agents to perform comprehensive read-only analysis of codebases to:

1. **Identify Design Patterns**: Recognize implementation of EIP (Enterprise Integration Patterns), Core Java Patterns, and Gang of Four (GoF) patterns
2. **Detect Anti-Patterns**: Find architectural and design anti-patterns that indicate technical debt
3. **Flag Non-Pattern Code**: Identify code that doesn't follow any established patterns
4. **Generate Recommendations**: Provide actionable guidance to bring violating code into compliance

This skill is essential for peer review processes, architecture assessments, and technical debt analysis. It produces structured finding reports with executive summaries suitable for both technical and business stakeholders.

---

## Core Capabilities

1. **Pattern Detection**: Identify patterns from multiple catalogs:
   - EIP Patterns (Apache Camel 4.14.x): Router, Mapper, Transformer, Adapter, Splitter, Aggregator
   - Core Java Patterns: Facade/Controller, DAO/Repository, DTO/TO/Bean, Entity, Service
   - GoF Patterns: Factory, Abstract Factory, Builder, Singleton, Strategy, Observer

2. **Anti-Pattern Detection**: Identify architectural and design anti-patterns:
   - Architectural: Circular References, Stovepipe, Monolith, Big Ball of Mud
   - Design: God Object, Anemic Domain Model, Copy-Paste Programming
   - Integration: Point-to-Point, Chatty Interface, Sequential Coupling

3. **Non-Pattern Code Identification**: Flag code that:
   - Doesn't follow naming conventions
   - Mixes concerns inappropriately
   - Lacks clear architectural role
   - Uses procedural style in OOP context

4. **Recommendation Generation**: Provide actionable remediation:
   - Pattern-specific refactoring guidance
   - Priority-based recommendations (Critical, High, Medium, Low)
   - Code examples for recommended patterns

5. **Report Generation**: Create structured finding reports:
   - Numbered sections (X.Y.Z format)
   - Executive summary written post-analysis
   - Patterns, Anti-patterns, Recommendations sections

---

## Input Requirements

**Primary Inputs**:
- **Codebase Path**: Root directory of codebase to analyze
- **File Patterns**: Glob patterns for files to include (e.g., `**/*.java`, `**/*.ts`)
- **Exclusion Rules**: Patterns to exclude (e.g., `**/test/**`, `**/generated/**`)

**Optional Inputs**:
- **Focus Areas**: Specific packages/modules to prioritize
- **Pattern Catalog Selection**: Which catalogs to use (EIP, Java, GoF, All)
- **Severity Threshold**: Minimum severity to report (Critical, High, Medium, Low)
- **Previous Report**: For comparison/delta analysis

**Format**: JSON configuration or command-line parameters

**Preconditions**:
- Codebase is readable and accessible
- File patterns match target language/framework
- Agent has read access to all specified paths

---

## Output Specifications

**Primary Output**: `pattern_mining_report_[codebase].md`

**Output Structure**:
```markdown
# Pattern Mining Report: [Codebase Name]

## 1. Executive Summary
   1.1 Analysis Overview
   1.2 Key Findings
   1.3 Risk Assessment
   1.4 Recommendations Summary

## 2. Patterns Identified
   2.1 Enterprise Integration Patterns (EIP)
   2.2 Core Java Patterns
   2.3 GoF Design Patterns
   2.4 Non-Pattern Code

## 3. Anti-Patterns Detected
   3.1 Architectural Anti-Patterns
   3.2 Design Anti-Patterns
   3.3 Integration Anti-Patterns

## 4. Recommendations
   4.1 Critical (Immediate Action Required)
   4.2 High Priority
   4.3 Medium Priority
   4.4 Low Priority (Nice to Have)
```

**Artifacts Created**:
- `pattern_mining_report_[codebase].md` - Main finding report
- Pattern inventory (inline in report)
- Anti-pattern inventory (inline in report)

---

## Constraints and Limitations

**Operational Constraints**:
- **READ-ONLY**: This skill NEVER modifies code
- Analysis time proportional to codebase size
- Maximum codebase size: 10,000 files per analysis
- Supported languages: Java, TypeScript, Python, Go

**Limitations**:
- Cannot detect patterns requiring runtime analysis
- Limited to file-based pattern detection (not dynamic behavior)
- May produce false positives on heavily obfuscated code
- Cannot assess pattern appropriateness (only presence)

**Guardrails**:
- NEVER modify source code files
- NEVER delete or move files
- NEVER execute code from analyzed codebase
- ALWAYS report findings, never "fix" automatically
- ALWAYS mark confidence level for pattern identification

---

## Instructions

### Behavioral Guidelines

**Read-Only Principle**:
- This skill ONLY reads and analyzes code
- All output is report-based, never code modification
- If asked to "fix" code, redirect to recommendation section
- Document findings, don't implement changes

**Patience and Thoroughness**:
- Analyze complete codebase before generating report
- Don't rush to conclusions from limited samples
- Cross-reference patterns across multiple files
- Consider context before flagging anti-patterns

**Planning-First Approach**:
- Create analysis plan before starting
- Break large codebases into logical chunks
- Estimate analysis time upfront
- Report progress during long analyses

**Confidence Reporting**:
- Mark high-confidence pattern matches clearly
- Flag uncertain matches for human review
- Explain reasoning for anti-pattern detections
- Provide evidence (file:line references)

### Decision Rules

**When identifying patterns**:
1. Check class/file naming conventions first (fastest)
2. Analyze imports and dependencies
3. Examine method signatures and patterns
4. Cross-reference with pattern catalog signatures
5. Assign confidence level (HIGH, MEDIUM, LOW)

**When detecting anti-patterns**:
1. Run architectural analysis first (package dependencies)
2. Calculate class metrics (LOC, dependencies, methods)
3. Detect code duplication
4. Analyze coupling and cohesion
5. Assign severity (CRITICAL, HIGH, MEDIUM)

**When encountering ambiguous code**:
1. Check if partial pattern implementation
2. Look for commented "TODO" or "FIXME" hints
3. Flag as "Non-Pattern Code" if truly ambiguous
4. Recommend pattern that would best fit

**For report generation**:
1. Write all sections EXCEPT Executive Summary first
2. Aggregate findings and generate summary LAST
3. Order recommendations by severity (Critical → Low)
4. Include specific file:line references

### Workflow Protocol

**Phase 1: Analysis Preparation**
1. Validate codebase path and accessibility
2. Apply file patterns and exclusions
3. Count files to analyze
4. Estimate analysis time
5. Report analysis scope to user

**Phase 2: Pattern Detection**
1. Scan for naming convention matches
2. Analyze class structures and relationships
3. Detect EIP patterns
4. Detect Core Java/GoF patterns
5. Track pattern inventory

**Phase 3: Anti-Pattern Detection**
1. Build package dependency graph
2. Detect circular dependencies
3. Calculate class metrics
4. Run duplicate code detection
5. Identify God Objects and other anti-patterns

**Phase 4: Non-Pattern Code Analysis**
1. Identify files not matching any pattern
2. Categorize by potential pattern fit
3. Flag procedural code in OOP context
4. Document improvement opportunities

**Phase 5: Report Generation**
1. Generate Section 2: Patterns Identified
2. Generate Section 3: Anti-Patterns Detected
3. Generate Section 4: Recommendations
4. Generate Section 1: Executive Summary (LAST)
5. Write final report to output path

### Error Handling

**Error Detection**:
- File access errors (permission denied)
- Unsupported file types
- Corrupted or binary files
- Timeout during analysis
- Memory limits on large codebases

**Error Response**:
- **Access Denied**: Skip file, log warning, continue
- **Unsupported Type**: Exclude file, note in report
- **Corrupted File**: Skip file, log error, continue
- **Timeout**: Report partial results, note incomplete
- **Memory Limit**: Reduce scope, analyze in chunks

**Fallback Strategies**:
- If full analysis fails, report on successfully analyzed subset
- If pattern detection uncertain, flag for human review
- If codebase too large, suggest scoped analysis approach

**Edge Cases**:
- **Empty codebase**: Report "No files to analyze"
- **Only test files**: Report "Only test code found - consider expanding scope"
- **Mixed languages**: Analyze each language separately
- **Generated code**: Flag as "Generated - excluded from analysis"

---

## Success Criteria

The skill has succeeded when:

1. **Complete Analysis**: All files in scope analyzed without errors
2. **Pattern Coverage**: All pattern types checked for each relevant file
3. **Anti-Pattern Coverage**: All anti-pattern types evaluated
4. **Report Completeness**: All 4 main sections present in report
5. **Section Numbering**: Consistent X.Y.Z numbering throughout
6. **Executive Summary**: Written based on complete analysis (not assumptions)
7. **Actionable Recommendations**: Each finding has remediation guidance

**Quality Indicators**:
- Zero analysis errors on well-formed code
- Pattern confidence levels documented
- Anti-pattern severity levels assigned
- File:line references for all findings
- Report parseable as valid markdown

**Business Value (ATSQ)**:
- **Expected Time Savings**: 87.5% ATSQ: 8-hour manual code review reduced to 1 hour (30 min analysis + 30 min human verification)
- **Baseline Assumption**: Manual pattern/anti-pattern identification = 8 hours for medium codebase
- **Verification Method**: Human verification (30 min review of findings)
- **Category**: Labor Reduction (significant automation with human oversight)

---

## Pattern Catalogs

### EIP Patterns (Apache Camel 4.14.x)

| Pattern | Detection Signature | Confidence Indicators |
|---------|--------------------|-----------------------|
| Content-Based Router | `*Router.java`, switch on message content | `@Router` annotation |
| Message Filter | `*Filter.java`, implements `Predicate` | `.filter()` operations |
| Splitter | `*Splitter.java`, returns `List<Message>` | Iteration over sub-elements |
| Aggregator | `*Aggregator.java`, `AggregationStrategy` | Correlation ID usage |
| Mapper/Translator | `*Mapper.java`, `map(S) → T` | MapStruct, ModelMapper |
| Transformer | `*Transformer.java` | Format conversion logic |
| Adapter | `*Adapter.java`, implements target interface | Wraps adaptee |
| Wire Tap | `*WireTap.java`, logging interceptor | Non-blocking inspection |

### Core Java Patterns

| Pattern | Detection Signature | Confidence Indicators |
|---------|--------------------|-----------------------|
| Facade | `*Facade.java`, coordinates subsystems | Multiple service dependencies |
| Controller | `*Controller.java`, `@RestController` | `@RequestMapping` methods |
| DAO/Repository | `*Repository.java`, `@Repository` | CRUD methods, extends JpaRepository |
| DTO/TO/Bean | `*DTO.java`, `*TO.java`, `*Bean.java` | Only getters/setters |
| Entity | `*Entity.java`, `@Entity` | JPA annotations |
| Service | `*Service.java`, `@Service` | `@Transactional`, business logic |
| Factory | `*Factory.java`, `create*()` methods | Returns interface type |
| Abstract Factory | Multiple `create*()`, factory selector | Family of related objects |

### Anti-Pattern Severity Levels

| Severity | Color | Meaning | Action |
|----------|-------|---------|--------|
| CRITICAL | 🔴 | Major architectural issue | Immediate planning required |
| HIGH | 🟠 | Significant technical debt | Prioritize in next sprint |
| MEDIUM | 🟡 | Code quality issue | Add to refactoring backlog |
| LOW | 🟢 | Minor improvement opportunity | Nice to have |

---

## Usage Examples

### Example 1: Analyze Java Microservice

**Input**:
```json
{
  "codebase_path": "/path/to/order-service",
  "file_patterns": ["**/*.java"],
  "exclusions": ["**/test/**", "**/generated/**"],
  "catalogs": ["EIP", "JAVA", "GOF"],
  "severity_threshold": "MEDIUM"
}
```

**Processing**:
1. Scan 150 Java files
2. Identify 12 pattern implementations
3. Detect 3 anti-patterns
4. Flag 5 non-pattern files
5. Generate 8 recommendations

**Output**: `pattern_mining_report_order-service.md`

### Example 2: Focus on Integration Layer

**Input**:
```json
{
  "codebase_path": "/path/to/integration-layer",
  "file_patterns": ["**/*.java"],
  "focus_areas": ["com.company.integration", "com.company.adapters"],
  "catalogs": ["EIP"],
  "severity_threshold": "HIGH"
}
```

**Output**: Report focused on EIP pattern compliance in integration code

---

## Integration

### With Peer Review Agent
- Skill invoked during PR analysis
- Findings included in review comments
- Anti-patterns flagged as required changes

### With Pattern Matching Agent
- Skill provides pattern inventory for catalog updates
- Newly identified patterns submitted for approval
- Anti-pattern findings trigger pattern enforcement rules

### Standalone Usage
```bash
# Invoke skill directly
claude --skill pattern_mining_skill \
  --codebase /path/to/project \
  --output /path/to/report.md
```

---

## Version History

- **v1.0** (2026-01-30): Initial skill definition

---

**End of Skill Definition**
