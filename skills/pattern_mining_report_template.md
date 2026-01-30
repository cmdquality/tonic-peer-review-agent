# Pattern Mining Report: [CODEBASE_NAME]

**Report Generated**: [DATE]
**Analysis Tool**: Pattern Mining Skill v1.0
**Codebase Path**: [CODEBASE_PATH]
**Files Analyzed**: [FILE_COUNT]
**Analysis Duration**: [DURATION]

---

## 1. Executive Summary

> **NOTE**: This section is written AFTER all other sections are complete. It synthesizes findings from Sections 2, 3, and 4.

### 1.1 Analysis Overview

| Metric | Value |
|--------|-------|
| **Total Files Analyzed** | [X] |
| **Patterns Identified** | [X] |
| **Anti-Patterns Detected** | [X] |
| **Non-Pattern Files** | [X] |
| **Recommendations Generated** | [X] |

### 1.2 Key Findings

| Finding | Count | Severity |
|---------|-------|----------|
| EIP Patterns Found | [X] | ✅ Good |
| Core Java Patterns Found | [X] | ✅ Good |
| GoF Patterns Found | [X] | ✅ Good |
| Critical Anti-Patterns | [X] | 🔴 Critical |
| High-Severity Anti-Patterns | [X] | 🟠 High |
| Medium-Severity Anti-Patterns | [X] | 🟡 Medium |
| Non-Pattern Code | [X] | ℹ️ Info |

### 1.3 Risk Assessment

**Overall Architecture Health**: [HEALTHY / AT_RISK / CRITICAL]

| Risk Category | Level | Description |
|---------------|-------|-------------|
| Technical Debt | [LOW/MEDIUM/HIGH/CRITICAL] | [Brief explanation] |
| Maintainability | [LOW/MEDIUM/HIGH/CRITICAL] | [Brief explanation] |
| Scalability | [LOW/MEDIUM/HIGH/CRITICAL] | [Brief explanation] |
| Integration Complexity | [LOW/MEDIUM/HIGH/CRITICAL] | [Brief explanation] |

### 1.4 Recommendations Summary

| Priority | Count | Estimated Effort |
|----------|-------|------------------|
| 🔴 Critical | [X] | [X] days |
| 🟠 High | [X] | [X] days |
| 🟡 Medium | [X] | [X] days |
| 🟢 Low | [X] | [X] days |

**Top 3 Recommendations**:
1. [Most critical recommendation]
2. [Second most critical recommendation]
3. [Third most critical recommendation]

---

## 2. Patterns Identified

### 2.1 Enterprise Integration Patterns (EIP)

#### 2.1.1 [PATTERN_NAME]

**Status**: ✅ Correctly Implemented | ⚠️ Partially Implemented | ❌ Incorrectly Implemented

**Location(s)**:
- `[file_path]:[line_number]`
- `[file_path]:[line_number]`

**Description**: [Brief description of how pattern is implemented]

**Confidence**: HIGH | MEDIUM | LOW

**Notes**: [Any relevant observations]

---

#### 2.1.2 [PATTERN_NAME]

**Status**: ✅ | ⚠️ | ❌

**Location(s)**:
- `[file_path]:[line_number]`

**Description**: [Brief description]

**Confidence**: HIGH | MEDIUM | LOW

---

### 2.2 Core Java Patterns

#### 2.2.1 Facade/Controller Pattern

**Status**: ✅ | ⚠️ | ❌

**Location(s)**:
- `[file_path]:[line_number]`

**Description**: [Brief description]

**Confidence**: HIGH | MEDIUM | LOW

---

#### 2.2.2 DAO/Repository Pattern

**Status**: ✅ | ⚠️ | ❌

**Location(s)**:
- `[file_path]:[line_number]`

**Description**: [Brief description]

**Confidence**: HIGH | MEDIUM | LOW

---

#### 2.2.3 DTO/TO/Bean Pattern

**Status**: ✅ | ⚠️ | ❌

**Location(s)**:
- `[file_path]:[line_number]`

**Description**: [Brief description]

**Confidence**: HIGH | MEDIUM | LOW

---

#### 2.2.4 Entity Pattern

**Status**: ✅ | ⚠️ | ❌

**Location(s)**:
- `[file_path]:[line_number]`

**Description**: [Brief description]

**Confidence**: HIGH | MEDIUM | LOW

---

#### 2.2.5 Service Layer Pattern

**Status**: ✅ | ⚠️ | ❌

**Location(s)**:
- `[file_path]:[line_number]`

**Description**: [Brief description]

**Confidence**: HIGH | MEDIUM | LOW

---

#### 2.2.6 Factory Pattern

**Status**: ✅ | ⚠️ | ❌

**Location(s)**:
- `[file_path]:[line_number]`

**Description**: [Brief description]

**Confidence**: HIGH | MEDIUM | LOW

---

#### 2.2.7 Abstract Factory Pattern

**Status**: ✅ | ⚠️ | ❌

**Location(s)**:
- `[file_path]:[line_number]`

**Description**: [Brief description]

**Confidence**: HIGH | MEDIUM | LOW

---

### 2.3 GoF Design Patterns

#### 2.3.1 [PATTERN_NAME]

**Status**: ✅ | ⚠️ | ❌

**Location(s)**:
- `[file_path]:[line_number]`

**Description**: [Brief description]

**Confidence**: HIGH | MEDIUM | LOW

---

### 2.4 Non-Pattern Code

> Files that do not follow any recognized design pattern.

#### 2.4.1 [FILE_NAME]

**Location**: `[file_path]`

**Current State**: [Description of what the code does]

**Potential Pattern Fit**: [Suggested pattern that could apply]

**Reason for Non-Pattern Classification**: [Why it doesn't match existing patterns]

---

#### 2.4.2 [FILE_NAME]

**Location**: `[file_path]`

**Current State**: [Description]

**Potential Pattern Fit**: [Suggestion]

**Reason**: [Explanation]

---

## 3. Anti-Patterns Detected

### 3.1 Architectural Anti-Patterns

#### 3.1.1 Circular References

**Severity**: 🔴 CRITICAL | 🟠 HIGH | 🟡 MEDIUM

**Location(s)**:
- Cycle: `[package.A] → [package.B] → [package.C] → [package.A]`

**Evidence**:
```
Package A imports: [package.B]
Package B imports: [package.C]
Package C imports: [package.A]  // Circular!
```

**Impact**: [Description of impact on codebase]

**Remediation**: [Specific guidance to resolve]

---

#### 3.1.2 Stovepipe System

**Severity**: 🔴 | 🟠 | 🟡

**Location(s)**:
- `[module_A/path]`
- `[module_B/path]`

**Evidence**: [Description of duplicated functionality]

**Impact**: [Description of impact]

**Remediation**: [Specific guidance]

---

#### 3.1.3 Monolith

**Severity**: 🔴 | 🟠 | 🟡

**Evidence**:
- Service count: [X]
- Single deployment: [YES/NO]
- Shared database: [YES/NO]
- Build time: [X] minutes

**Impact**: [Description of impact]

**Remediation**: [Specific guidance]

---

### 3.2 Design Anti-Patterns

#### 3.2.1 God Object/Class

**Severity**: 🔴 | 🟠 | 🟡

**Location**: `[file_path]:[class_name]`

**Metrics**:
| Metric | Value | Threshold |
|--------|-------|-----------|
| Lines of Code | [X] | < 500 |
| Dependencies | [X] | < 10 |
| Public Methods | [X] | < 20 |
| Responsibilities | [X] | 1 |

**Impact**: [Description of impact]

**Remediation**: [Specific guidance for splitting]

---

#### 3.2.2 Anemic Domain Model

**Severity**: 🔴 | 🟠 | 🟡

**Location(s)**:
- `[file_path]:[class_name]`

**Evidence**: Entity has [X] getters/setters and [0] business methods

**Impact**: [Description of impact]

**Remediation**: [Specific guidance for enriching domain model]

---

#### 3.2.3 Copy-Paste Programming

**Severity**: 🔴 | 🟠 | 🟡

**Location(s)**:
- `[file_A]:[lines]` ↔ `[file_B]:[lines]`
- Similarity: [X]%

**Evidence**: [Description of duplicated code]

**Impact**: [Description of impact]

**Remediation**: [Specific guidance for extraction]

---

#### 3.2.4 Magic Numbers/Strings

**Severity**: 🔴 | 🟠 | 🟡

**Location(s)**:
- `[file_path]:[line_number]`: `[magic_value]`
- `[file_path]:[line_number]`: `[magic_value]`

**Impact**: [Description of impact]

**Remediation**: Extract to named constants

---

#### 3.2.5 Lava Flow (Dead Code)

**Severity**: 🔴 | 🟠 | 🟡

**Location(s)**:
- `[file_path]`: Unused class
- `[file_path]:[lines]`: Commented code

**Evidence**: [Description of dead code indicators]

**Impact**: [Description of impact]

**Remediation**: Remove dead code (preserved in version control)

---

### 3.3 Integration Anti-Patterns

#### 3.3.1 Point-to-Point Integration

**Severity**: 🔴 | 🟠 | 🟡

**Location**: `[file_path]:[class_name]`

**Evidence**: Service has [X] direct client dependencies

**Dependencies**:
- `[ServiceClient1]`
- `[ServiceClient2]`
- `[ServiceClient3]`

**Impact**: [Description of impact]

**Remediation**: Introduce message broker or event-driven architecture

---

#### 3.3.2 Chatty Interface

**Severity**: 🔴 | 🟠 | 🟡

**Location**: `[file_path]:[method_name]`

**Evidence**: [X] sequential API calls for related data

```java
// Example of chatty interface
Order order = orderService.getOrder(id);
Customer customer = customerService.getCustomer(order.getCustomerId());
Address address = addressService.getAddress(order.getAddressId());
// ... more calls
```

**Impact**: [Description of impact]

**Remediation**: Create aggregate endpoint or use batch operations

---

## 4. Recommendations

### 4.1 Critical (Immediate Action Required)

> These issues pose immediate risk to system stability, security, or correctness.

#### 4.1.1 [RECOMMENDATION_TITLE]

**Related Finding**: [Section reference, e.g., 3.1.1 Circular References]

**Current State**: [Description of current problematic state]

**Target State**: [Description of desired state]

**Action Steps**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Estimated Effort**: [X] days

**Risk if Unaddressed**: [Description of risk]

---

#### 4.1.2 [RECOMMENDATION_TITLE]

**Related Finding**: [Section reference]

**Current State**: [Description]

**Target State**: [Description]

**Action Steps**:
1. [Step 1]
2. [Step 2]

**Estimated Effort**: [X] days

**Risk if Unaddressed**: [Description]

---

### 4.2 High Priority

> These issues significantly impact maintainability, performance, or developer productivity.

#### 4.2.1 [RECOMMENDATION_TITLE]

**Related Finding**: [Section reference]

**Current State**: [Description]

**Target State**: [Description]

**Action Steps**:
1. [Step 1]
2. [Step 2]

**Estimated Effort**: [X] days

---

#### 4.2.2 [RECOMMENDATION_TITLE]

**Related Finding**: [Section reference]

**Current State**: [Description]

**Target State**: [Description]

**Action Steps**:
1. [Step 1]
2. [Step 2]

**Estimated Effort**: [X] days

---

### 4.3 Medium Priority

> These issues represent technical debt that should be addressed in upcoming sprints.

#### 4.3.1 [RECOMMENDATION_TITLE]

**Related Finding**: [Section reference]

**Current State**: [Description]

**Target State**: [Description]

**Action Steps**:
1. [Step 1]
2. [Step 2]

**Estimated Effort**: [X] days

---

#### 4.3.2 [RECOMMENDATION_TITLE]

**Related Finding**: [Section reference]

**Current State**: [Description]

**Target State**: [Description]

**Action Steps**:
1. [Step 1]
2. [Step 2]

**Estimated Effort**: [X] days

---

### 4.4 Low Priority (Nice to Have)

> These are improvement opportunities that would enhance code quality.

#### 4.4.1 [RECOMMENDATION_TITLE]

**Related Finding**: [Section reference]

**Current State**: [Description]

**Target State**: [Description]

**Action Steps**:
1. [Step 1]

**Estimated Effort**: [X] hours

---

#### 4.4.2 [RECOMMENDATION_TITLE]

**Related Finding**: [Section reference]

**Current State**: [Description]

**Target State**: [Description]

**Action Steps**:
1. [Step 1]

**Estimated Effort**: [X] hours

---

## Appendix A: Pattern Inventory

| Pattern Type | Pattern Name | Count | Status |
|--------------|--------------|-------|--------|
| EIP | Content-Based Router | [X] | ✅ |
| EIP | Message Filter | [X] | ✅ |
| EIP | Mapper | [X] | ✅ |
| Java | Repository | [X] | ✅ |
| Java | Service | [X] | ✅ |
| Java | DTO | [X] | ✅ |
| Java | Entity | [X] | ✅ |
| GoF | Factory | [X] | ✅ |
| GoF | Strategy | [X] | ✅ |

---

## Appendix B: Anti-Pattern Summary

| Category | Anti-Pattern | Severity | Count |
|----------|--------------|----------|-------|
| Architectural | Circular References | 🔴 | [X] |
| Architectural | Monolith | 🟠 | [X] |
| Design | God Object | 🔴 | [X] |
| Design | Anemic Domain Model | 🟡 | [X] |
| Integration | Point-to-Point | 🟠 | [X] |

---

## Appendix C: Files Analyzed

<details>
<summary>Click to expand file list ([X] files)</summary>

| File | Patterns Found | Anti-Patterns |
|------|----------------|---------------|
| `[file_path]` | [patterns] | [anti-patterns] |
| `[file_path]` | [patterns] | [anti-patterns] |

</details>

---

## Appendix D: Analysis Configuration

```json
{
  "codebase_path": "[CODEBASE_PATH]",
  "file_patterns": ["**/*.java"],
  "exclusions": ["**/test/**", "**/generated/**"],
  "catalogs": ["EIP", "JAVA", "GOF"],
  "severity_threshold": "MEDIUM",
  "analysis_date": "[DATE]",
  "skill_version": "1.0"
}
```

---

## Report Metadata

| Attribute | Value |
|-----------|-------|
| **Report ID** | [UUID] |
| **Generated By** | Pattern Mining Skill v1.0 |
| **Analysis Date** | [DATE] |
| **Codebase** | [CODEBASE_NAME] |
| **File Count** | [X] |
| **Duration** | [X] minutes |

---

**End of Report**
