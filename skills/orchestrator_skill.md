# Orchestrator Skill

**Created**: 2026-01-28
**Version**: 1.0
**Project**: Tonic Configuration Management Platform
**Skill Type**: Pipeline Orchestration Skill

---

## Purpose

The Orchestrator Skill is a reusable pipeline orchestration skill that provides agent pipeline execution, conditional branching, and result aggregation for the peer review system. This skill encapsulates all pipeline management logic, agent coordination, state tracking, and decision-making, enabling any agent to execute complex multi-agent workflows without duplicating orchestration code.

**Key Benefits**:
- DRY principle: Single source of truth for pipeline orchestration
- Consistent workflow execution across all pipelines
- Centralized state management and error recovery
- Conditional agent execution based on runtime decisions
- Comprehensive observability and metrics
- Parallel and sequential agent execution support

---

## When to Load

Load this skill when you need to:

1. **Execute agent pipelines** with multiple agents in sequence or parallel
2. **Coordinate agent workflows** with conditional branching logic
3. **Aggregate results** from multiple agent executions
4. **Make merge/block decisions** based on aggregated agent outputs
5. **Track pipeline state** across long-running workflows
6. **Handle partial failures** with graceful degradation

**Primary Users**:
- PR Orchestrator Agent (coordinates all review agents)
- Custom workflow orchestrators
- Integration testing frameworks
- Pipeline monitoring and observability tools

---

## Table of Contents

1. [Skill Overview](#skill-overview)
2. [Operations](#operations)
   - [execute_pipeline](#operation-1-execute_pipeline)
   - [execute_agent](#operation-2-execute_agent)
   - [aggregate_results](#operation-3-aggregate_results)
   - [make_decision](#operation-4-make_decision)
   - [get_pipeline_status](#operation-5-get_pipeline_status)
   - [cancel_pipeline](#operation-6-cancel_pipeline)
3. [Pipeline Configuration](#pipeline-configuration)
4. [Conditional Execution](#conditional-execution)
5. [Error Handling](#error-handling)
6. [State Management](#state-management)
7. [Integration Examples](#integration-examples)
8. [Performance and Monitoring](#performance-and-monitoring)

---

## Skill Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Orchestrator Skill                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │  Pipeline      │  │  Execution     │  │  State       │ │
│  │  Manager       │  │  Engine        │  │  Manager     │ │
│  │  (Config)      │  │  (Parallel/Seq)│  │  (DDB/Redis) │ │
│  └────────────────┘  └────────────────┘  └──────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Agent Execution Coordinator                     │ │
│  │  - Agent invocation                                     │ │
│  │  - Result collection                                    │ │
│  │  - Timeout management                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Conditional Branching Engine                    │ │
│  │  - Condition evaluation                                 │ │
│  │  - Dynamic agent selection                              │ │
│  │  - Branch execution                                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Result Aggregation & Decision Engine            │ │
│  │  - Result collection                                    │ │
│  │  - Merge/block decision logic                           │ │
│  │  - Severity calculation                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Error Handling & Recovery                       │ │
│  │  - Retry logic                                          │ │
│  │  - Partial failure handling                             │ │
│  │  - Compensation actions                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

1. **Pipeline Execution Modes**
   - Sequential execution: agents run one after another
   - Parallel execution: agents run concurrently
   - Hybrid execution: mix of sequential and parallel stages
   - Conditional branching: skip agents based on runtime conditions

2. **State Management**
   - Persistent state storage in DynamoDB
   - In-memory state cache in Redis
   - State versioning and history tracking
   - State recovery after failures

3. **Conditional Branching**
   - Rule-based conditions (e.g., "if pattern detected")
   - Dynamic agent selection based on PR metadata
   - Conditional agent skipping
   - Branch execution tracking

4. **Result Aggregation**
   - Collect outputs from all agents
   - Calculate overall severity
   - Determine merge/block decision
   - Generate consolidated report

5. **Error Handling**
   - Agent timeout handling
   - Partial failure recovery
   - Retry with exponential backoff
   - Compensation actions (rollback)

6. **Observability**
   - CloudWatch metrics for all operations
   - Structured JSON logging
   - Pipeline execution traces
   - Performance monitoring

---

## Operations

### Operation 1: execute_pipeline

Executes a complete agent pipeline with conditional branching and result aggregation.

#### Input Schema

```python
class ExecutePipelineInput(BaseModel):
    # Required fields
    pipeline_id: str  # Unique pipeline identifier (e.g., "pr-123-review")
    pipeline_config: PipelineConfig  # Pipeline definition (see Pipeline Configuration)

    # Context data for all agents
    context: dict  # Shared context passed to all agents

    # Optional execution options
    execution_mode: Literal["sequential", "parallel", "hybrid"] = "sequential"
    max_parallelism: Optional[int] = 3  # Max concurrent agents in parallel mode
    timeout_seconds: Optional[int] = 1800  # 30 minutes default

    # Error handling options
    fail_fast: bool = False  # Stop on first agent failure
    partial_success_allowed: bool = True  # Allow pipeline to complete with some failures

    # Observability
    trace_id: Optional[str] = None  # For distributed tracing
    workflow_run_url: Optional[str] = None  # GitHub workflow URL


class PipelineConfig(BaseModel):
    """Pipeline configuration defining agent execution order and conditions."""
    name: str  # Pipeline name (e.g., "PR Review Pipeline")
    version: str  # Pipeline version

    stages: List[PipelineStage]  # Ordered list of pipeline stages

    # Global configuration
    default_timeout_per_agent: int = 600  # 10 minutes per agent
    retry_failed_agents: bool = True
    max_retries_per_agent: int = 2


class PipelineStage(BaseModel):
    """A stage in the pipeline (can contain one or more agents)."""
    stage_id: str
    stage_name: str

    # Agents to execute in this stage
    agents: List[AgentConfig]

    # Execution mode for this stage
    execution_mode: Literal["sequential", "parallel"] = "sequential"

    # Conditional execution
    condition: Optional[Condition] = None  # Skip stage if condition not met

    # Error handling for this stage
    required: bool = True  # If False, stage failure doesn't fail pipeline


class AgentConfig(BaseModel):
    """Configuration for a single agent in the pipeline."""
    agent_id: str  # Unique agent identifier
    agent_name: str  # Human-readable name
    agent_type: Literal[
        "code_best_practises",
        "architect_best_practises",
        "lld_alignment",
        "pattern_matching",
        "peer_review_documentation"
    ]

    # Agent invocation
    lambda_function_arn: str  # AWS Lambda ARN for the agent

    # Input configuration
    input_transformer: Optional[Callable] = None  # Transform context to agent input

    # Conditional execution
    condition: Optional[Condition] = None  # Skip agent if condition not met

    # Timeout and retry
    timeout_seconds: Optional[int] = None  # Override default timeout
    max_retries: Optional[int] = None  # Override default retries

    # Dependencies
    depends_on: Optional[List[str]] = None  # Agent IDs that must complete first

    # Criticality
    required: bool = True  # If False, agent failure doesn't fail pipeline


class Condition(BaseModel):
    """Conditional execution rule."""
    type: Literal["always", "never", "if_field", "if_result", "custom"]

    # For if_field type
    field_path: Optional[str] = None  # JSON path in context (e.g., "pr.files_changed")
    operator: Optional[Literal["eq", "ne", "gt", "lt", "contains", "regex"]] = None
    value: Optional[Any] = None

    # For if_result type (check previous agent results)
    agent_id: Optional[str] = None  # Check result of this agent
    result_field: Optional[str] = None  # Field in agent result

    # For custom type
    custom_evaluator: Optional[Callable] = None  # Custom function to evaluate condition
```

#### Output Schema

```python
class ExecutePipelineOutput(BaseModel):
    status: Literal["SUCCESS", "PARTIAL_SUCCESS", "FAILURE", "CANCELLED"]
    pipeline_id: str

    # Execution summary
    total_agents: int
    agents_executed: int
    agents_succeeded: int
    agents_failed: int
    agents_skipped: int

    # Timing
    started_at: str  # ISO 8601 timestamp
    completed_at: str  # ISO 8601 timestamp
    duration_ms: int

    # Stage results
    stage_results: List[StageResult]

    # Aggregated results
    aggregated_result: AggregatedResult

    # Decision
    decision: Literal["MERGE", "BLOCK"]
    decision_reason: str

    # Errors
    errors: Optional[List[dict]] = None
    warnings: Optional[List[str]] = None

    # Traceability
    trace_id: Optional[str] = None
    execution_logs_url: Optional[str] = None


class StageResult(BaseModel):
    stage_id: str
    stage_name: str
    status: Literal["SUCCESS", "PARTIAL_SUCCESS", "FAILURE", "SKIPPED"]

    agent_results: List[AgentResult]

    started_at: str
    completed_at: str
    duration_ms: int

    skipped: bool = False
    skip_reason: Optional[str] = None


class AgentResult(BaseModel):
    agent_id: str
    agent_name: str
    agent_type: str

    status: Literal["SUCCESS", "FAILURE", "TIMEOUT", "SKIPPED"]

    # Agent output
    output: Optional[dict] = None  # Agent-specific output

    # Timing
    started_at: str
    completed_at: str
    duration_ms: int

    # Error details
    error: Optional[str] = None
    retry_count: int = 0

    # Skipping
    skipped: bool = False
    skip_reason: Optional[str] = None


class AggregatedResult(BaseModel):
    """Aggregated results from all agents."""
    overall_severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]

    # Violation counts by severity
    critical_violations: int = 0
    high_violations: int = 0
    medium_violations: int = 0
    low_violations: int = 0

    # Jira tickets created
    jira_tickets: List[dict] = []

    # Agent-specific results
    code_violations_found: bool = False
    code_violations_count: int = 0

    architect_violations_found: bool = False
    architect_violations_count: int = 0

    lld_deviations_found: bool = False
    lld_deviations_count: int = 0

    new_pattern_detected: bool = False
    pattern_details: Optional[dict] = None

    documentation_updated: bool = False

    # Summary
    total_issues_found: int = 0
    blocking_issues_found: bool = False
```

#### Usage Example

```python
from skills.orchestrator_skill import OrchestratorSkill, ExecutePipelineInput, PipelineConfig

# Initialize skill
orchestrator = OrchestratorSkill.from_environment()

# Define pipeline configuration
pipeline_config = PipelineConfig(
    name="PR Review Pipeline",
    version="2.0",
    stages=[
        # Stage 1: Code quality checks (parallel)
        PipelineStage(
            stage_id="code_quality",
            stage_name="Code Quality Analysis",
            execution_mode="parallel",
            agents=[
                AgentConfig(
                    agent_id="code_best_practises",
                    agent_name="Code Best Practises Agent",
                    agent_type="code_best_practises",
                    lambda_function_arn="arn:aws:lambda:us-east-1:123456789:function:code-agent",
                    timeout_seconds=600,
                    required=True
                ),
                AgentConfig(
                    agent_id="architect_best_practises",
                    agent_name="Architect Best Practises Agent",
                    agent_type="architect_best_practises",
                    lambda_function_arn="arn:aws:lambda:us-east-1:123456789:function:architect-agent",
                    timeout_seconds=600,
                    required=True
                )
            ]
        ),

        # Stage 2: Pattern matching (sequential, conditional)
        PipelineStage(
            stage_id="pattern_analysis",
            stage_name="Pattern Analysis",
            execution_mode="sequential",
            agents=[
                AgentConfig(
                    agent_id="pattern_matching",
                    agent_name="Pattern Matching Agent",
                    agent_type="pattern_matching",
                    lambda_function_arn="arn:aws:lambda:us-east-1:123456789:function:pattern-agent",
                    timeout_seconds=300,
                    required=False
                )
            ]
        ),

        # Stage 3: LLD alignment (conditional - only if new pattern detected)
        PipelineStage(
            stage_id="lld_check",
            stage_name="LLD Alignment Check",
            execution_mode="sequential",
            agents=[
                AgentConfig(
                    agent_id="lld_alignment",
                    agent_name="LLD Alignment Review Agent",
                    agent_type="lld_alignment",
                    lambda_function_arn="arn:aws:lambda:us-east-1:123456789:function:lld-agent",
                    timeout_seconds=900,
                    required=False,
                    # Only run if pattern was detected
                    condition=Condition(
                        type="if_result",
                        agent_id="pattern_matching",
                        result_field="new_pattern_detected",
                        operator="eq",
                        value=True
                    )
                )
            ]
        ),

        # Stage 4: Documentation (conditional - only if new pattern and LLD check passed)
        PipelineStage(
            stage_id="documentation",
            stage_name="Peer Review Documentation",
            execution_mode="sequential",
            agents=[
                AgentConfig(
                    agent_id="peer_review_docs",
                    agent_name="Peer Review Documentation Agent",
                    agent_type="peer_review_documentation",
                    lambda_function_arn="arn:aws:lambda:us-east-1:123456789:function:docs-agent",
                    timeout_seconds=300,
                    required=False,
                    condition=Condition(
                        type="if_result",
                        agent_id="lld_alignment",
                        result_field="status",
                        operator="eq",
                        value="SUCCESS"
                    )
                )
            ]
        )
    ],
    default_timeout_per_agent=600,
    retry_failed_agents=True,
    max_retries_per_agent=2
)

# Prepare context
context = {
    "pr": {
        "number": 123,
        "url": "https://github.com/tonic-scm/order-service/pull/123",
        "repository": "tonic-scm/order-service",
        "author_email": "developer1@company.com",
        "author_username": "dev1",
        "title": "Add order validation logic",
        "branch": "feature/order-validation",
        "base_branch": "main",
        "files_changed": ["src/main/java/OrderService.java", "src/test/java/OrderServiceTest.java"]
    },
    "workflow_run_url": "https://github.com/tonic-scm/order-service/actions/runs/12345",
    "triggered_by": "pull_request",
    "github_token": "ghp_xxx"
}

# Execute pipeline
input_data = ExecutePipelineInput(
    pipeline_id=f"pr-{context['pr']['number']}-review",
    pipeline_config=pipeline_config,
    context=context,
    execution_mode="hybrid",  # Mix of sequential and parallel
    max_parallelism=3,
    timeout_seconds=1800,
    partial_success_allowed=True,
    trace_id=f"trace-{context['pr']['number']}"
)

output = orchestrator.execute_pipeline(input_data)

if output.status == "SUCCESS":
    print(f"Pipeline completed: {output.decision}")
    print(f"Agents executed: {output.agents_executed}/{output.total_agents}")
    print(f"Duration: {output.duration_ms}ms")
elif output.status == "PARTIAL_SUCCESS":
    print(f"Pipeline completed with warnings: {output.warnings}")
    print(f"Decision: {output.decision}")
else:
    print(f"Pipeline failed: {output.errors}")
```

---

### Operation 2: execute_agent

Executes a single agent with retry logic and timeout handling.

#### Input Schema

```python
class ExecuteAgentInput(BaseModel):
    # Agent identification
    agent_id: str
    agent_name: str
    agent_type: str

    # Invocation
    lambda_function_arn: str

    # Input payload for the agent
    agent_input: dict

    # Execution options
    timeout_seconds: int = 600
    max_retries: int = 2

    # Observability
    trace_id: Optional[str] = None
    parent_pipeline_id: Optional[str] = None
```

#### Output Schema

```python
class ExecuteAgentOutput(BaseModel):
    status: Literal["SUCCESS", "FAILURE", "TIMEOUT"]

    agent_id: str
    agent_name: str

    # Agent output
    output: Optional[dict] = None

    # Timing
    started_at: str
    completed_at: str
    duration_ms: int

    # Retry information
    retry_count: int = 0

    # Error details
    error: Optional[str] = None
    error_type: Optional[str] = None
```

#### Usage Example

```python
# Execute single agent
agent_output = orchestrator.execute_agent(
    ExecuteAgentInput(
        agent_id="code_best_practises",
        agent_name="Code Best Practises Agent",
        agent_type="code_best_practises",
        lambda_function_arn="arn:aws:lambda:us-east-1:123456789:function:code-agent",
        agent_input={
            "pr_number": 123,
            "repository": "tonic-scm/order-service",
            "files_changed": ["OrderService.java"]
        },
        timeout_seconds=600,
        max_retries=2,
        trace_id="trace-123"
    )
)

if agent_output.status == "SUCCESS":
    print(f"Agent completed in {agent_output.duration_ms}ms")
    print(f"Violations found: {agent_output.output['violations_count']}")
```

---

### Operation 3: aggregate_results

Aggregates results from multiple agent executions and calculates overall metrics.

#### Input Schema

```python
class AggregateResultsInput(BaseModel):
    # Agent results to aggregate
    agent_results: List[AgentResult]

    # Context for aggregation
    context: dict

    # Aggregation options
    severity_calculation_method: Literal["max", "weighted_sum"] = "max"
    blocking_threshold: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM"
```

#### Output Schema

```python
class AggregateResultsOutput(BaseModel):
    status: Literal["SUCCESS", "FAILURE"]

    aggregated_result: AggregatedResult

    # Metrics
    total_violations: int
    total_agents_analyzed: int

    # Performance
    aggregation_time_ms: int
```

#### Usage Example

```python
# Aggregate results from all agents
aggregation_output = orchestrator.aggregate_results(
    AggregateResultsInput(
        agent_results=[
            code_agent_result,
            architect_agent_result,
            pattern_agent_result
        ],
        context=context,
        severity_calculation_method="max",
        blocking_threshold="MEDIUM"
    )
)

print(f"Overall severity: {aggregation_output.aggregated_result.overall_severity}")
print(f"Total issues: {aggregation_output.total_violations}")
```

---

### Operation 4: make_decision

Makes a merge/block decision based on aggregated results and configured policies.

#### Input Schema

```python
class MakeDecisionInput(BaseModel):
    # Aggregated results
    aggregated_result: AggregatedResult

    # Decision policy
    policy: DecisionPolicy

    # Context
    context: dict


class DecisionPolicy(BaseModel):
    """Policy for merge/block decision."""

    # Blocking thresholds
    block_on_critical: bool = True
    block_on_high: bool = True
    block_on_medium: bool = False
    block_on_low: bool = False

    # Violation count thresholds
    max_critical_violations: int = 0
    max_high_violations: int = 5
    max_medium_violations: int = 20
    max_low_violations: int = 100

    # Agent-specific policies
    block_on_code_violations: bool = True
    block_on_architect_violations: bool = True
    block_on_lld_deviations: bool = True
    block_on_pattern_rejection: bool = False

    # Override options
    allow_override_by_label: bool = True  # e.g., "skip-validation" label
    override_labels: List[str] = ["skip-validation", "emergency-deploy"]
```

#### Output Schema

```python
class MakeDecisionOutput(BaseModel):
    status: Literal["SUCCESS", "FAILURE"]

    decision: Literal["MERGE", "BLOCK"]
    decision_reason: str

    # Decision breakdown
    decision_factors: List[dict]  # List of factors that contributed to decision

    # Override information
    override_applied: bool = False
    override_reason: Optional[str] = None

    # Timing
    decision_time_ms: int
```

#### Usage Example

```python
# Make merge/block decision
decision_output = orchestrator.make_decision(
    MakeDecisionInput(
        aggregated_result=aggregation_output.aggregated_result,
        policy=DecisionPolicy(
            block_on_critical=True,
            block_on_high=True,
            block_on_medium=False,
            max_critical_violations=0,
            max_high_violations=5,
            block_on_code_violations=True,
            block_on_architect_violations=True,
            block_on_lld_deviations=True,
            allow_override_by_label=True,
            override_labels=["skip-validation"]
        ),
        context=context
    )
)

print(f"Decision: {decision_output.decision}")
print(f"Reason: {decision_output.decision_reason}")

if decision_output.override_applied:
    print(f"Override applied: {decision_output.override_reason}")
```

---

### Operation 5: get_pipeline_status

Retrieves the current status of an ongoing or completed pipeline.

#### Input Schema

```python
class GetPipelineStatusInput(BaseModel):
    pipeline_id: str

    # Options
    include_agent_details: bool = True
    include_logs: bool = False
```

#### Output Schema

```python
class GetPipelineStatusOutput(BaseModel):
    status: Literal["RUNNING", "SUCCESS", "PARTIAL_SUCCESS", "FAILURE", "CANCELLED", "NOT_FOUND"]

    pipeline_id: str

    # Execution state
    current_stage: Optional[str] = None
    current_agent: Optional[str] = None

    # Progress
    total_agents: int
    agents_completed: int
    agents_in_progress: int
    agents_pending: int

    # Timing
    started_at: Optional[str] = None
    estimated_completion_at: Optional[str] = None
    elapsed_time_ms: Optional[int] = None

    # Results (if completed)
    final_result: Optional[ExecutePipelineOutput] = None

    # Agent details
    agent_statuses: Optional[List[dict]] = None

    # Logs
    recent_logs: Optional[List[str]] = None
```

#### Usage Example

```python
# Check pipeline status
status_output = orchestrator.get_pipeline_status(
    GetPipelineStatusInput(
        pipeline_id="pr-123-review",
        include_agent_details=True,
        include_logs=False
    )
)

print(f"Pipeline status: {status_output.status}")
print(f"Progress: {status_output.agents_completed}/{status_output.total_agents}")

if status_output.status == "RUNNING":
    print(f"Current stage: {status_output.current_stage}")
    print(f"Current agent: {status_output.current_agent}")
    print(f"Estimated completion: {status_output.estimated_completion_at}")
```

---

### Operation 6: cancel_pipeline

Cancels an ongoing pipeline execution.

#### Input Schema

```python
class CancelPipelineInput(BaseModel):
    pipeline_id: str
    reason: str

    # Options
    force: bool = False  # Force cancel even if agents are mid-execution
```

#### Output Schema

```python
class CancelPipelineOutput(BaseModel):
    status: Literal["SUCCESS", "FAILURE"]

    pipeline_id: str
    cancelled_at: str

    # Cancellation details
    agents_cancelled: int
    agents_completed_before_cancel: int

    # Cleanup
    cleanup_performed: bool

    error: Optional[str] = None
```

#### Usage Example

```python
# Cancel pipeline
cancel_output = orchestrator.cancel_pipeline(
    CancelPipelineInput(
        pipeline_id="pr-123-review",
        reason="User requested cancellation",
        force=False
    )
)

print(f"Pipeline cancelled: {cancel_output.cancelled_at}")
print(f"Agents cancelled: {cancel_output.agents_cancelled}")
```

---

## Pipeline Configuration

### Configuration File Format

Pipeline configurations can be defined in YAML or JSON format.

#### YAML Example

```yaml
# pr_review_pipeline.yaml

name: "PR Review Pipeline"
version: "2.0"
default_timeout_per_agent: 600
retry_failed_agents: true
max_retries_per_agent: 2

stages:
  - stage_id: "code_quality"
    stage_name: "Code Quality Analysis"
    execution_mode: "parallel"
    required: true
    agents:
      - agent_id: "code_best_practises"
        agent_name: "Code Best Practises Agent"
        agent_type: "code_best_practises"
        lambda_function_arn: "arn:aws:lambda:us-east-1:123456789:function:code-agent"
        timeout_seconds: 600
        required: true

      - agent_id: "architect_best_practises"
        agent_name: "Architect Best Practises Agent"
        agent_type: "architect_best_practises"
        lambda_function_arn: "arn:aws:lambda:us-east-1:123456789:function:architect-agent"
        timeout_seconds: 600
        required: true

  - stage_id: "pattern_analysis"
    stage_name: "Pattern Analysis"
    execution_mode: "sequential"
    required: false
    agents:
      - agent_id: "pattern_matching"
        agent_name: "Pattern Matching Agent"
        agent_type: "pattern_matching"
        lambda_function_arn: "arn:aws:lambda:us-east-1:123456789:function:pattern-agent"
        timeout_seconds: 300
        required: false

  - stage_id: "lld_check"
    stage_name: "LLD Alignment Check"
    execution_mode: "sequential"
    required: false
    condition:
      type: "if_result"
      agent_id: "pattern_matching"
      result_field: "new_pattern_detected"
      operator: "eq"
      value: true
    agents:
      - agent_id: "lld_alignment"
        agent_name: "LLD Alignment Review Agent"
        agent_type: "lld_alignment"
        lambda_function_arn: "arn:aws:lambda:us-east-1:123456789:function:lld-agent"
        timeout_seconds: 900
        required: false

  - stage_id: "documentation"
    stage_name: "Peer Review Documentation"
    execution_mode: "sequential"
    required: false
    condition:
      type: "if_result"
      agent_id: "lld_alignment"
      result_field: "status"
      operator: "eq"
      value: "SUCCESS"
    agents:
      - agent_id: "peer_review_docs"
        agent_name: "Peer Review Documentation Agent"
        agent_type: "peer_review_documentation"
        lambda_function_arn: "arn:aws:lambda:us-east-1:123456789:function:docs-agent"
        timeout_seconds: 300
        required: false
```

### Loading Pipeline Configuration

```python
from skills.orchestrator_skill import OrchestratorSkill, load_pipeline_config

# From YAML file
pipeline_config = load_pipeline_config("config/pr_review_pipeline.yaml")

# From environment variable (S3 path)
pipeline_config = load_pipeline_config(os.environ["PIPELINE_CONFIG_S3_PATH"])

# From dictionary
pipeline_config = PipelineConfig(**config_dict)
```

---

## Conditional Execution

### Condition Types

#### 1. Always Execute

```python
Condition(type="always")
```

#### 2. Never Execute (Skip)

```python
Condition(type="never")
```

#### 3. Field-Based Condition

Execute if a field in the context matches a condition:

```python
# Execute if files_changed contains Java files
Condition(
    type="if_field",
    field_path="pr.files_changed",
    operator="contains",
    value=".java"
)

# Execute if PR has more than 10 files changed
Condition(
    type="if_field",
    field_path="pr.files_changed.length",
    operator="gt",
    value=10
)

# Execute if PR has a specific label
Condition(
    type="if_field",
    field_path="pr.labels",
    operator="contains",
    value="needs-architecture-review"
)
```

#### 4. Result-Based Condition

Execute if a previous agent's result matches a condition:

```python
# Execute if pattern matching agent detected a new pattern
Condition(
    type="if_result",
    agent_id="pattern_matching",
    result_field="new_pattern_detected",
    operator="eq",
    value=True
)

# Execute if code agent found critical violations
Condition(
    type="if_result",
    agent_id="code_best_practises",
    result_field="critical_violations_count",
    operator="gt",
    value=0
)

# Execute if previous agent succeeded
Condition(
    type="if_result",
    agent_id="lld_alignment",
    result_field="status",
    operator="eq",
    value="SUCCESS"
)
```

#### 5. Custom Condition

Execute based on custom logic:

```python
def custom_evaluator(context: dict, agent_results: List[AgentResult]) -> bool:
    """
    Custom condition: Execute only on weekdays between 9am-5pm
    and if PR author is not a senior developer.
    """
    from datetime import datetime

    now = datetime.utcnow()
    is_weekday = now.weekday() < 5
    is_business_hours = 9 <= now.hour < 17

    pr_author = context.get("pr", {}).get("author_username")
    is_senior = pr_author in ["senior_dev1", "senior_dev2"]

    return is_weekday and is_business_hours and not is_senior

Condition(
    type="custom",
    custom_evaluator=custom_evaluator
)
```

### Condition Evaluation Flow

```
┌─────────────────────────────────────────────────────────────┐
│              Condition Evaluation Process                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Get condition    │
                    │ from agent config│
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ condition.type   │
                    └──────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
    ┌──────────┐      ┌──────────┐      ┌──────────────┐
    │ always   │      │ never    │      │ if_field     │
    │ return   │      │ return   │      │ if_result    │
    │ True     │      │ False    │      │ custom       │
    └──────────┘      └──────────┘      └──────────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │ Evaluate     │
                                        │ condition    │
                                        └──────────────┘
                                                │
                                        ┌───────┴───────┐
                                        │               │
                                      True            False
                                        │               │
                                        ▼               ▼
                                ┌──────────┐    ┌──────────┐
                                │ Execute  │    │ Skip     │
                                │ agent    │    │ agent    │
                                └──────────┘    └──────────┘
```

---

## Error Handling

### Error Types and Strategies

| Error Type | Strategy | Retry | Fail Pipeline |
|------------|----------|-------|---------------|
| Agent timeout | Retry with longer timeout | Yes (2x) | If required agent |
| Agent execution failure | Retry with exponential backoff | Yes (3x) | If required agent |
| Lambda invocation error | Retry immediately | Yes (3x) | If required agent |
| Network error | Retry with backoff | Yes (5x) | No |
| Invalid agent output | No retry, mark as failed | No | If required agent |
| State save failure | Retry immediately | Yes (3x) | Yes |
| Condition evaluation error | Skip agent, log warning | No | No |

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
    wait=wait_exponential(multiplier=2, min=4, max=60),
    reraise=True
)
def _invoke_agent(self, agent_config: AgentConfig, agent_input: dict) -> dict:
    """
    Invoke agent Lambda function with automatic retry.
    """
    try:
        response = self.lambda_client.invoke(
            FunctionName=agent_config.lambda_function_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(agent_input)
        )

        if response['StatusCode'] == 200:
            return json.loads(response['Payload'].read())
        else:
            raise AgentExecutionError(f"Agent returned status {response['StatusCode']}")

    except self.lambda_client.exceptions.TooManyRequestsException:
        logger.warning(f"Lambda throttling for {agent_config.agent_id}, retrying...")
        raise ConnectionError("Lambda throttling")

    except Exception as e:
        logger.error(f"Agent invocation failed: {e}")
        raise
```

### Partial Failure Handling

```python
def execute_pipeline(self, input_data: ExecutePipelineInput) -> ExecutePipelineOutput:
    """
    Execute pipeline with graceful degradation for non-critical agent failures.
    """
    stage_results = []
    agent_results = []
    errors = []
    warnings = []

    for stage in input_data.pipeline_config.stages:
        # Evaluate stage condition
        if not self._evaluate_condition(stage.condition, input_data.context, agent_results):
            stage_results.append(StageResult(
                stage_id=stage.stage_id,
                stage_name=stage.stage_name,
                status="SKIPPED",
                skipped=True,
                skip_reason="Stage condition not met"
            ))
            continue

        # Execute stage
        try:
            stage_result = self._execute_stage(stage, input_data.context)
            stage_results.append(stage_result)
            agent_results.extend(stage_result.agent_results)

            # Check if required agent failed
            for agent_result in stage_result.agent_results:
                if agent_result.status == "FAILURE":
                    agent_config = self._get_agent_config(stage, agent_result.agent_id)

                    if agent_config.required and not input_data.partial_success_allowed:
                        # Fail entire pipeline
                        raise PipelineExecutionError(
                            f"Required agent {agent_result.agent_id} failed: {agent_result.error}"
                        )
                    elif agent_config.required:
                        # Mark as partial success
                        warnings.append(
                            f"Required agent {agent_result.agent_id} failed but partial_success_allowed is True"
                        )
                    else:
                        # Non-critical agent failed
                        warnings.append(
                            f"Non-critical agent {agent_result.agent_id} failed: {agent_result.error}"
                        )

        except Exception as e:
            if stage.required and not input_data.partial_success_allowed:
                raise
            else:
                errors.append({
                    "stage": stage.stage_id,
                    "error": str(e)
                })
                warnings.append(f"Stage {stage.stage_id} failed but is not required")

    # Aggregate results even with partial failures
    aggregated_result = self._aggregate_results(agent_results, input_data.context)

    # Make decision
    decision_output = self._make_decision(aggregated_result, input_data.context)

    # Determine overall status
    if errors:
        status = "PARTIAL_SUCCESS" if warnings else "FAILURE"
    else:
        status = "SUCCESS"

    return ExecutePipelineOutput(
        status=status,
        stage_results=stage_results,
        aggregated_result=aggregated_result,
        decision=decision_output.decision,
        decision_reason=decision_output.decision_reason,
        errors=errors if errors else None,
        warnings=warnings if warnings else None
    )
```

### Compensation Actions

When a pipeline fails, compensation actions can be executed to rollback changes:

```python
class CompensationAction(BaseModel):
    """Defines a compensation action to rollback changes."""
    action_type: Literal["delete_jira_ticket", "remove_label", "delete_file", "revert_commit"]
    target: str  # Target resource (e.g., ticket ID, file path)
    parameters: Optional[dict] = None


def _execute_compensation_actions(self, pipeline_id: str):
    """
    Execute compensation actions to rollback changes from failed pipeline.
    """
    # Get pipeline state
    state = self.state_manager.get_state(pipeline_id)

    # Execute compensation actions in reverse order
    for action in reversed(state.get('compensation_actions', [])):
        try:
            if action['action_type'] == 'delete_jira_ticket':
                jira_skill = JiraTicketSkill.from_environment()
                jira_skill.delete_ticket(action['target'])

            elif action['action_type'] == 'remove_label':
                github_client.remove_label(
                    action['parameters']['pr_number'],
                    action['target']
                )

            logger.info(f"Compensation action executed: {action['action_type']}")

        except Exception as e:
            logger.error(f"Compensation action failed: {e}")
```

---

## State Management

### State Storage

Pipeline state is stored in DynamoDB for persistence and Redis for fast access.

#### DynamoDB Schema

```json
{
  "TableName": "orchestrator-pipeline-state",
  "KeySchema": [
    {"AttributeName": "pipeline_id", "KeyType": "HASH"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "pipeline_id", "AttributeType": "S"}
  ],
  "BillingMode": "PAY_PER_REQUEST",
  "TimeToLiveSpecification": {
    "AttributeName": "ttl",
    "Enabled": true
  },
  "Example Item": {
    "pipeline_id": "pr-123-review",
    "status": "RUNNING",
    "current_stage": "pattern_analysis",
    "current_agent": "pattern_matching",
    "started_at": "2026-01-28T10:30:00Z",
    "updated_at": "2026-01-28T10:35:00Z",
    "context": {...},
    "stage_results": [...],
    "agent_results": [...],
    "compensation_actions": [...],
    "ttl": 1738070100
  }
}
```

#### Redis Cache

```python
# Cache key format
pipeline_state:{pipeline_id} → Pipeline state dict

# Cache TTL: 1 hour (state is persisted in DynamoDB)
PIPELINE_STATE_CACHE_TTL = 3600
```

### State Updates

```python
class PipelineStateManager:
    """Manages pipeline state with DynamoDB persistence and Redis caching."""

    def __init__(self):
        self.ddb = boto3.resource('dynamodb')
        self.table = self.ddb.Table('orchestrator-pipeline-state')
        self.redis = redis.Redis(
            host=os.environ['REDIS_HOST'],
            port=6379,
            db=0
        )

    def save_state(self, pipeline_id: str, state: dict):
        """Save pipeline state to DynamoDB and Redis."""
        state['updated_at'] = datetime.utcnow().isoformat()
        state['ttl'] = int(time.time()) + 86400  # 24 hours TTL

        # Save to DynamoDB
        self.table.put_item(Item=state)

        # Cache in Redis
        self.redis.setex(
            f"pipeline_state:{pipeline_id}",
            PIPELINE_STATE_CACHE_TTL,
            json.dumps(state)
        )

    def get_state(self, pipeline_id: str) -> Optional[dict]:
        """Get pipeline state from Redis cache or DynamoDB."""
        # Try cache first
        cached = self.redis.get(f"pipeline_state:{pipeline_id}")
        if cached:
            return json.loads(cached)

        # Fallback to DynamoDB
        response = self.table.get_item(Key={'pipeline_id': pipeline_id})
        if 'Item' in response:
            state = response['Item']

            # Populate cache
            self.redis.setex(
                f"pipeline_state:{pipeline_id}",
                PIPELINE_STATE_CACHE_TTL,
                json.dumps(state)
            )

            return state

        return None

    def update_stage(self, pipeline_id: str, stage_id: str, stage_result: StageResult):
        """Update stage result in pipeline state."""
        state = self.get_state(pipeline_id)
        if not state:
            raise StateNotFoundError(f"Pipeline state not found: {pipeline_id}")

        # Update stage results
        stage_results = state.get('stage_results', [])
        stage_results.append(stage_result.dict())
        state['stage_results'] = stage_results

        # Update current stage
        state['current_stage'] = stage_id

        self.save_state(pipeline_id, state)

    def update_agent(self, pipeline_id: str, agent_result: AgentResult):
        """Update agent result in pipeline state."""
        state = self.get_state(pipeline_id)
        if not state:
            raise StateNotFoundError(f"Pipeline state not found: {pipeline_id}")

        # Update agent results
        agent_results = state.get('agent_results', [])
        agent_results.append(agent_result.dict())
        state['agent_results'] = agent_results

        # Update current agent
        state['current_agent'] = agent_result.agent_id

        self.save_state(pipeline_id, state)
```

### State Recovery

```python
def recover_pipeline(self, pipeline_id: str) -> ExecutePipelineOutput:
    """
    Recover and resume a failed pipeline from its last saved state.
    """
    # Get saved state
    state = self.state_manager.get_state(pipeline_id)
    if not state:
        raise StateNotFoundError(f"Cannot recover pipeline {pipeline_id}: state not found")

    # Reconstruct pipeline config and context
    pipeline_config = PipelineConfig(**state['pipeline_config'])
    context = state['context']

    # Determine where to resume
    completed_stages = set([sr['stage_id'] for sr in state.get('stage_results', [])])
    completed_agents = set([ar['agent_id'] for ar in state.get('agent_results', [])])

    # Resume execution from next incomplete stage
    for stage in pipeline_config.stages:
        if stage.stage_id in completed_stages:
            continue

        # Execute stage
        stage_result = self._execute_stage(stage, context, completed_agents)
        self.state_manager.update_stage(pipeline_id, stage.stage_id, stage_result)

    # Complete pipeline
    return self._finalize_pipeline(pipeline_id)
```

---

## Integration Examples

### Example 1: PR Orchestrator Agent Integration

```python
# In pr_orchestrator_agent.py

from skills.orchestrator_skill import (
    OrchestratorSkill,
    ExecutePipelineInput,
    PipelineConfig,
    load_pipeline_config
)

def lambda_handler(event, context):
    """
    PR Orchestrator Agent entry point.
    Coordinates all review agents for a pull request.
    """
    # Parse GitHub webhook event
    pr_number = event['pull_request']['number']
    repository = event['repository']['full_name']

    # Initialize orchestrator
    orchestrator = OrchestratorSkill.from_environment()

    # Load pipeline configuration
    pipeline_config = load_pipeline_config(
        os.environ['PIPELINE_CONFIG_S3_PATH']
    )

    # Prepare context
    pr_context = {
        "pr": {
            "number": pr_number,
            "url": event['pull_request']['html_url'],
            "repository": repository,
            "author_email": event['pull_request']['user']['email'],
            "author_username": event['pull_request']['user']['login'],
            "title": event['pull_request']['title'],
            "branch": event['pull_request']['head']['ref'],
            "base_branch": event['pull_request']['base']['ref'],
            "files_changed": get_changed_files(pr_number, repository),
            "labels": [label['name'] for label in event['pull_request']['labels']]
        },
        "workflow_run_url": f"https://github.com/{repository}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        "triggered_by": event['action'],
        "github_token": os.environ['GITHUB_TOKEN']
    }

    # Execute pipeline
    pipeline_input = ExecutePipelineInput(
        pipeline_id=f"pr-{pr_number}-review",
        pipeline_config=pipeline_config,
        context=pr_context,
        execution_mode="hybrid",
        max_parallelism=3,
        timeout_seconds=1800,
        partial_success_allowed=True,
        trace_id=f"trace-{pr_number}-{int(time.time())}",
        workflow_run_url=pr_context['workflow_run_url']
    )

    try:
        output = orchestrator.execute_pipeline(pipeline_input)

        # Post results to PR
        post_pipeline_results_to_pr(pr_number, repository, output)

        # Update branch protection status check
        update_status_check(
            pr_number,
            repository,
            state="success" if output.decision == "MERGE" else "failure",
            description=output.decision_reason,
            context="peer-review/orchestrator"
        )

        # Log metrics
        log_pipeline_metrics(output)

        return {
            "statusCode": 200,
            "body": {
                "decision": output.decision,
                "pipeline_status": output.status,
                "agents_executed": output.agents_executed,
                "duration_ms": output.duration_ms
            }
        }

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)

        # Post error to PR
        post_error_to_pr(pr_number, repository, str(e))

        # Fail status check
        update_status_check(
            pr_number,
            repository,
            state="error",
            description=f"Pipeline error: {str(e)}",
            context="peer-review/orchestrator"
        )

        raise


def post_pipeline_results_to_pr(pr_number: int, repository: str, output: ExecutePipelineOutput):
    """Post formatted pipeline results as a PR comment."""

    # Generate markdown summary
    comment = f"""
## Peer Review Results

**Decision**: {":white_check_mark: MERGE" if output.decision == "MERGE" else ":x: BLOCK"}

**Reason**: {output.decision_reason}

### Summary

- **Overall Severity**: {output.aggregated_result.overall_severity}
- **Total Issues**: {output.aggregated_result.total_issues_found}
- **Agents Executed**: {output.agents_executed}/{output.total_agents}
- **Duration**: {output.duration_ms / 1000:.1f}s

### Violations by Severity

| Severity | Count |
|----------|-------|
| Critical | {output.aggregated_result.critical_violations} |
| High | {output.aggregated_result.high_violations} |
| Medium | {output.aggregated_result.medium_violations} |
| Low | {output.aggregated_result.low_violations} |

### Agent Results

"""

    for stage_result in output.stage_results:
        comment += f"\n#### {stage_result.stage_name}\n\n"

        for agent_result in stage_result.agent_results:
            status_emoji = {
                "SUCCESS": ":white_check_mark:",
                "FAILURE": ":x:",
                "TIMEOUT": ":clock3:",
                "SKIPPED": ":fast_forward:"
            }[agent_result.status]

            comment += f"- {status_emoji} **{agent_result.agent_name}**: {agent_result.status}"

            if agent_result.status == "FAILURE":
                comment += f" ({agent_result.error})"
            elif agent_result.status == "SKIPPED":
                comment += f" ({agent_result.skip_reason})"

            comment += f" ({agent_result.duration_ms}ms)\n"

    # Add Jira tickets section
    if output.aggregated_result.jira_tickets:
        comment += "\n### Jira Tickets Created\n\n"
        for ticket in output.aggregated_result.jira_tickets:
            comment += f"- [{ticket['ticket_id']}]({ticket['ticket_url']}): {ticket['summary']}\n"

    # Add footer
    comment += f"\n---\n*Pipeline ID*: `{output.pipeline_id}` | [View Logs]({output.execution_logs_url})*\n"

    # Post comment
    github_client.create_issue_comment(
        owner=repository.split('/')[0],
        repo=repository.split('/')[1],
        issue_number=pr_number,
        body=comment
    )
```

### Example 2: Custom Pipeline for Hotfix PRs

```python
# hotfix_pipeline.py

def create_hotfix_pipeline() -> PipelineConfig:
    """
    Simplified pipeline for hotfix PRs with faster execution.
    Skips non-critical checks and allows emergency overrides.
    """
    return PipelineConfig(
        name="Hotfix Review Pipeline",
        version="1.0",
        stages=[
            # Only critical checks
            PipelineStage(
                stage_id="critical_checks",
                stage_name="Critical Security and Compliance Checks",
                execution_mode="parallel",
                agents=[
                    AgentConfig(
                        agent_id="code_best_practises",
                        agent_name="Code Best Practises Agent",
                        agent_type="code_best_practises",
                        lambda_function_arn="arn:aws:lambda:us-east-1:123456789:function:code-agent",
                        timeout_seconds=300,  # Faster timeout
                        required=True
                    )
                ]
            )
        ],
        default_timeout_per_agent=300,  # 5 minutes
        retry_failed_agents=False  # No retries for speed
    )

def execute_hotfix_review(pr_number: int, context: dict):
    """Execute hotfix review with emergency override support."""

    orchestrator = OrchestratorSkill.from_environment()

    # Check for emergency override label
    if "emergency-deploy" in context['pr']['labels']:
        logger.warning(f"Emergency override applied for PR #{pr_number}")

        return ExecutePipelineOutput(
            status="SUCCESS",
            decision="MERGE",
            decision_reason="Emergency override applied - manual review required post-deployment",
            pipeline_id=f"pr-{pr_number}-hotfix",
            agents_executed=0,
            warnings=["Pipeline bypassed due to emergency-deploy label"]
        )

    # Execute streamlined pipeline
    pipeline_input = ExecutePipelineInput(
        pipeline_id=f"pr-{pr_number}-hotfix",
        pipeline_config=create_hotfix_pipeline(),
        context=context,
        execution_mode="parallel",
        timeout_seconds=600,
        fail_fast=True  # Stop immediately on critical failure
    )

    return orchestrator.execute_pipeline(pipeline_input)
```

### Example 3: Pipeline Monitoring Dashboard

```python
# pipeline_monitor.py

from skills.orchestrator_skill import OrchestratorSkill, GetPipelineStatusInput

def get_active_pipelines_status():
    """
    Get status of all active pipelines for monitoring dashboard.
    """
    orchestrator = OrchestratorSkill.from_environment()

    # Get all active pipeline IDs from DynamoDB
    active_pipelines = get_active_pipeline_ids()

    pipeline_statuses = []

    for pipeline_id in active_pipelines:
        status_output = orchestrator.get_pipeline_status(
            GetPipelineStatusInput(
                pipeline_id=pipeline_id,
                include_agent_details=True,
                include_logs=False
            )
        )

        pipeline_statuses.append({
            "pipeline_id": pipeline_id,
            "status": status_output.status,
            "progress": f"{status_output.agents_completed}/{status_output.total_agents}",
            "current_stage": status_output.current_stage,
            "current_agent": status_output.current_agent,
            "elapsed_time_ms": status_output.elapsed_time_ms,
            "estimated_completion": status_output.estimated_completion_at
        })

    return pipeline_statuses


def render_dashboard():
    """Render real-time pipeline monitoring dashboard."""
    statuses = get_active_pipelines_status()

    print("=" * 100)
    print("PIPELINE MONITORING DASHBOARD")
    print("=" * 100)
    print(f"{'Pipeline ID':<30} {'Status':<15} {'Progress':<15} {'Current Stage':<25} {'Elapsed':<10}")
    print("-" * 100)

    for status in statuses:
        elapsed_sec = status['elapsed_time_ms'] / 1000 if status['elapsed_time_ms'] else 0

        print(
            f"{status['pipeline_id']:<30} "
            f"{status['status']:<15} "
            f"{status['progress']:<15} "
            f"{status['current_stage'] or 'N/A':<25} "
            f"{elapsed_sec:.1f}s"
        )

    print("-" * 100)
    print(f"Total Active Pipelines: {len(statuses)}")
    print("=" * 100)
```

---

## Performance and Monitoring

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pipeline Execution Time P95 | <15 minutes | CloudWatch |
| Agent Invocation Time P95 | <30 seconds | CloudWatch |
| State Save Time P95 | <100ms | CloudWatch |
| Pipeline Success Rate | >98% | CloudWatch |
| Agent Timeout Rate | <2% | CloudWatch |
| Conditional Evaluation Time | <10ms | CloudWatch |

### CloudWatch Metrics

```python
def _publish_pipeline_metrics(self, pipeline_id: str, output: ExecutePipelineOutput):
    """Publish comprehensive CloudWatch metrics for pipeline execution."""

    namespace = "SCM/OrchestratorSkill"

    metrics = [
        # Pipeline duration
        {
            "MetricName": "PipelineExecutionDuration",
            "Value": output.duration_ms,
            "Unit": "Milliseconds",
            "Dimensions": [
                {"Name": "PipelineID", "Value": pipeline_id},
                {"Name": "Status", "Value": output.status}
            ]
        },

        # Pipeline success rate
        {
            "MetricName": "PipelineSuccessRate",
            "Value": 1 if output.status == "SUCCESS" else 0,
            "Unit": "Count",
            "Dimensions": [{"Name": "Decision", "Value": output.decision}]
        },

        # Agent execution metrics
        {
            "MetricName": "AgentsExecuted",
            "Value": output.agents_executed,
            "Unit": "Count",
            "Dimensions": [{"Name": "PipelineID", "Value": pipeline_id}]
        },
        {
            "MetricName": "AgentsFailed",
            "Value": output.agents_failed,
            "Unit": "Count",
            "Dimensions": [{"Name": "PipelineID", "Value": pipeline_id}]
        },
        {
            "MetricName": "AgentsSkipped",
            "Value": output.agents_skipped,
            "Unit": "Count",
            "Dimensions": [{"Name": "PipelineID", "Value": pipeline_id}]
        },

        # Decision metrics
        {
            "MetricName": "MergeDecision",
            "Value": 1 if output.decision == "MERGE" else 0,
            "Unit": "Count",
            "Dimensions": [
                {"Name": "Decision", "Value": output.decision},
                {"Name": "Severity", "Value": output.aggregated_result.overall_severity}
            ]
        }
    ]

    # Per-agent metrics
    for stage_result in output.stage_results:
        for agent_result in stage_result.agent_results:
            metrics.extend([
                {
                    "MetricName": "AgentExecutionDuration",
                    "Value": agent_result.duration_ms,
                    "Unit": "Milliseconds",
                    "Dimensions": [
                        {"Name": "AgentType", "Value": agent_result.agent_type},
                        {"Name": "Status", "Value": agent_result.status}
                    ]
                },
                {
                    "MetricName": "AgentSuccessRate",
                    "Value": 1 if agent_result.status == "SUCCESS" else 0,
                    "Unit": "Count",
                    "Dimensions": [{"Name": "AgentType", "Value": agent_result.agent_type}]
                }
            ])

    # Publish metrics in batches (CloudWatch limit: 20 metrics per call)
    for i in range(0, len(metrics), 20):
        batch = metrics[i:i+20]
        cloudwatch_client.put_metric_data(
            Namespace=namespace,
            MetricData=batch
        )
```

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

def execute_pipeline(self, input_data: ExecutePipelineInput) -> ExecutePipelineOutput:
    """Execute pipeline with comprehensive logging."""

    logger.info(
        "pipeline_execution_started",
        pipeline_id=input_data.pipeline_id,
        pipeline_name=input_data.pipeline_config.name,
        total_stages=len(input_data.pipeline_config.stages),
        execution_mode=input_data.execution_mode,
        trace_id=input_data.trace_id
    )

    try:
        # Execute pipeline stages
        for stage in input_data.pipeline_config.stages:
            logger.info(
                "stage_execution_started",
                pipeline_id=input_data.pipeline_id,
                stage_id=stage.stage_id,
                stage_name=stage.stage_name,
                agent_count=len(stage.agents)
            )

            # Execute agents in stage
            for agent in stage.agents:
                logger.info(
                    "agent_execution_started",
                    pipeline_id=input_data.pipeline_id,
                    agent_id=agent.agent_id,
                    agent_type=agent.agent_type
                )

                # ... agent execution logic ...

                logger.info(
                    "agent_execution_completed",
                    pipeline_id=input_data.pipeline_id,
                    agent_id=agent.agent_id,
                    status=agent_result.status,
                    duration_ms=agent_result.duration_ms,
                    retry_count=agent_result.retry_count
                )

            logger.info(
                "stage_execution_completed",
                pipeline_id=input_data.pipeline_id,
                stage_id=stage.stage_id,
                status=stage_result.status,
                duration_ms=stage_result.duration_ms
            )

        logger.info(
            "pipeline_execution_completed",
            pipeline_id=input_data.pipeline_id,
            status=output.status,
            decision=output.decision,
            agents_executed=output.agents_executed,
            duration_ms=output.duration_ms,
            trace_id=input_data.trace_id
        )

        return output

    except Exception as e:
        logger.error(
            "pipeline_execution_failed",
            pipeline_id=input_data.pipeline_id,
            error=str(e),
            error_type=type(e).__name__,
            trace_id=input_data.trace_id,
            exc_info=True
        )
        raise
```

### CloudWatch Alarms

```yaml
# CloudWatch alarms configuration

HighPipelineFailureRate:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: Orchestrator-HighPipelineFailureRate
    MetricName: PipelineSuccessRate
    Namespace: SCM/OrchestratorSkill
    Statistic: Average
    Period: 300
    EvaluationPeriods: 2
    Threshold: 0.95
    ComparisonOperator: LessThanThreshold
    AlarmActions:
      - !Ref OpsTeamSNSTopic

SlowPipelineExecution:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: Orchestrator-SlowPipelineExecution
    MetricName: PipelineExecutionDuration
    Namespace: SCM/OrchestratorSkill
    Statistic: p95
    Period: 300
    EvaluationPeriods: 2
    Threshold: 900000  # 15 minutes
    ComparisonOperator: GreaterThanThreshold
    AlarmActions:
      - !Ref OpsTeamSNSTopic

HighAgentTimeoutRate:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: Orchestrator-HighAgentTimeoutRate
    MetricName: AgentSuccessRate
    Namespace: SCM/OrchestratorSkill
    Statistic: Average
    Period: 600
    EvaluationPeriods: 2
    Threshold: 0.98
    ComparisonOperator: LessThanThreshold
    Dimensions:
      - Name: Status
        Value: TIMEOUT
    AlarmActions:
      - !Ref OpsTeamSNSTopic

StateSaveFailures:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: Orchestrator-StateSaveFailures
    MetricName: StateSaveSuccessRate
    Namespace: SCM/OrchestratorSkill
    Statistic: Average
    Period: 300
    EvaluationPeriods: 1
    Threshold: 0.99
    ComparisonOperator: LessThanThreshold
    AlarmActions:
      - !Ref CriticalAlertSNSTopic
```

### Distributed Tracing

```python
# Integration with AWS X-Ray for distributed tracing

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch all supported libraries
patch_all()

@xray_recorder.capture('execute_pipeline')
def execute_pipeline(self, input_data: ExecutePipelineInput) -> ExecutePipelineOutput:
    """Execute pipeline with X-Ray tracing."""

    # Add pipeline metadata to trace
    xray_recorder.put_metadata('pipeline_id', input_data.pipeline_id)
    xray_recorder.put_metadata('pipeline_name', input_data.pipeline_config.name)
    xray_recorder.put_metadata('trace_id', input_data.trace_id)

    # Execute stages
    for stage in input_data.pipeline_config.stages:
        with xray_recorder.in_subsegment(f'stage_{stage.stage_id}') as subsegment:
            subsegment.put_metadata('stage_name', stage.stage_name)
            subsegment.put_metadata('agent_count', len(stage.agents))

            # Execute agents
            for agent in stage.agents:
                with xray_recorder.in_subsegment(f'agent_{agent.agent_id}') as agent_subsegment:
                    agent_subsegment.put_metadata('agent_type', agent.agent_type)

                    # Agent execution
                    agent_result = self._execute_agent(agent, input_data.context)

                    agent_subsegment.put_metadata('status', agent_result.status)
                    agent_subsegment.put_metadata('duration_ms', agent_result.duration_ms)

    return output
```

---

## Configuration

### Environment Variables

```bash
# Pipeline Configuration
PIPELINE_CONFIG_S3_PATH=s3://scm-config/pipelines/pr_review_pipeline.yaml
PIPELINE_STATE_TABLE=orchestrator-pipeline-state

# Redis Cache
REDIS_HOST=orchestrator-cache.abc123.0001.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
PIPELINE_STATE_CACHE_TTL=3600

# Execution Limits
MAX_PIPELINE_DURATION_SECONDS=1800
MAX_AGENT_DURATION_SECONDS=600
MAX_CONCURRENT_AGENTS=5

# Retry Configuration
AGENT_RETRY_ENABLED=true
MAX_AGENT_RETRIES=2
RETRY_BACKOFF_MULTIPLIER=2

# Error Handling
PARTIAL_SUCCESS_ALLOWED=true
FAIL_FAST_ON_CRITICAL=true

# Performance
LAMBDA_INVOCATION_TIMEOUT=30
STATE_SAVE_TIMEOUT=5

# Observability
CLOUDWATCH_NAMESPACE=SCM/OrchestratorSkill
XRAY_TRACING_ENABLED=true
LOG_LEVEL=INFO
```

### Initialization

```python
# From environment variables
orchestrator = OrchestratorSkill.from_environment()

# With explicit configuration
orchestrator = OrchestratorSkill(
    pipeline_state_table="orchestrator-pipeline-state",
    redis_host="localhost",
    redis_port=6379,
    max_pipeline_duration=1800,
    max_agent_duration=600,
    retry_enabled=True,
    max_retries=2
)
```

---

## Testing Guide

### Unit Tests

```python
# tests/test_orchestrator_skill.py

import pytest
from unittest.mock import Mock, patch
from skills.orchestrator_skill import (
    OrchestratorSkill,
    ExecutePipelineInput,
    PipelineConfig,
    PipelineStage,
    AgentConfig
)

@pytest.fixture
def orchestrator():
    """Create OrchestratorSkill with mocked dependencies."""
    with patch('skills.orchestrator_skill.boto3'), \
         patch('skills.orchestrator_skill.redis'):

        skill = OrchestratorSkill(
            pipeline_state_table="test-table",
            redis_host="localhost",
            redis_port=6379
        )

        # Mock Lambda client
        skill.lambda_client = Mock()

        yield skill

def test_execute_pipeline_sequential(orchestrator):
    """Test sequential pipeline execution."""

    # Mock agent responses
    orchestrator.lambda_client.invoke.return_value = {
        'StatusCode': 200,
        'Payload': Mock(read=lambda: json.dumps({
            'status': 'SUCCESS',
            'violations_count': 0
        }).encode())
    }

    # Create simple pipeline
    pipeline_config = PipelineConfig(
        name="Test Pipeline",
        version="1.0",
        stages=[
            PipelineStage(
                stage_id="test_stage",
                stage_name="Test Stage",
                execution_mode="sequential",
                agents=[
                    AgentConfig(
                        agent_id="test_agent",
                        agent_name="Test Agent",
                        agent_type="code_best_practises",
                        lambda_function_arn="arn:aws:lambda:test",
                        required=True
                    )
                ]
            )
        ]
    )

    input_data = ExecutePipelineInput(
        pipeline_id="test-pipeline",
        pipeline_config=pipeline_config,
        context={"pr": {"number": 123}},
        execution_mode="sequential"
    )

    output = orchestrator.execute_pipeline(input_data)

    assert output.status == "SUCCESS"
    assert output.agents_executed == 1
    assert output.agents_succeeded == 1

def test_conditional_agent_skipping(orchestrator):
    """Test conditional agent execution."""

    # Create pipeline with conditional agent
    pipeline_config = PipelineConfig(
        name="Conditional Pipeline",
        version="1.0",
        stages=[
            PipelineStage(
                stage_id="stage1",
                stage_name="Stage 1",
                agents=[
                    AgentConfig(
                        agent_id="conditional_agent",
                        agent_name="Conditional Agent",
                        agent_type="lld_alignment",
                        lambda_function_arn="arn:aws:lambda:test",
                        condition=Condition(
                            type="if_field",
                            field_path="pr.files_changed",
                            operator="contains",
                            value=".java"
                        )
                    )
                ]
            )
        ]
    )

    # Context without Java files
    input_data = ExecutePipelineInput(
        pipeline_id="test-conditional",
        pipeline_config=pipeline_config,
        context={"pr": {"files_changed": ["test.py", "test.js"]}},
        execution_mode="sequential"
    )

    output = orchestrator.execute_pipeline(input_data)

    assert output.agents_skipped == 1
    assert output.agents_executed == 0

def test_partial_failure_handling(orchestrator):
    """Test partial failure with non-critical agent."""

    # Mock agent failure
    orchestrator.lambda_client.invoke.return_value = {
        'StatusCode': 500,
        'FunctionError': 'Unhandled',
        'Payload': Mock(read=lambda: json.dumps({
            'errorMessage': 'Agent failed'
        }).encode())
    }

    pipeline_config = PipelineConfig(
        name="Partial Failure Pipeline",
        version="1.0",
        stages=[
            PipelineStage(
                stage_id="stage1",
                stage_name="Stage 1",
                agents=[
                    AgentConfig(
                        agent_id="non_critical_agent",
                        agent_name="Non-Critical Agent",
                        agent_type="pattern_matching",
                        lambda_function_arn="arn:aws:lambda:test",
                        required=False  # Non-critical
                    )
                ]
            )
        ]
    )

    input_data = ExecutePipelineInput(
        pipeline_id="test-partial",
        pipeline_config=pipeline_config,
        context={"pr": {"number": 123}},
        partial_success_allowed=True
    )

    output = orchestrator.execute_pipeline(input_data)

    assert output.status == "PARTIAL_SUCCESS"
    assert output.agents_failed == 1
    assert len(output.warnings) > 0
```

### Integration Tests

```python
# tests/integration/test_orchestrator_integration.py

@pytest.mark.integration
def test_full_pipeline_execution():
    """
    End-to-end test with real Lambda functions.
    Requires test Lambda functions to be deployed.
    """
    orchestrator = OrchestratorSkill.from_environment()

    # Load real pipeline config
    pipeline_config = load_pipeline_config("tests/fixtures/test_pipeline.yaml")

    # Execute pipeline
    output = orchestrator.execute_pipeline(
        ExecutePipelineInput(
            pipeline_id="integration-test-123",
            pipeline_config=pipeline_config,
            context={
                "pr": {
                    "number": 999,
                    "repository": "test/repo",
                    "files_changed": ["test.java"]
                }
            },
            execution_mode="sequential",
            timeout_seconds=300
        )
    )

    assert output.status in ["SUCCESS", "PARTIAL_SUCCESS"]
    assert output.agents_executed > 0

    # Verify state was saved
    state = orchestrator.state_manager.get_state("integration-test-123")
    assert state is not None
    assert state['status'] in ["SUCCESS", "PARTIAL_SUCCESS"]
```

---

**End of Orchestrator Skill Specification**
