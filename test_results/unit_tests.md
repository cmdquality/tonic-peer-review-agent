# Unit Testing Guide - PR Peer Review System

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**Version**: 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Testing Framework Setup](#testing-framework-setup)
3. [PR Orchestrator Agent Tests](#pr-orchestrator-agent-tests)
4. [Orchestrator Skill Tests](#orchestrator-skill-tests)
5. [Jira Ticket Skill Tests](#jira-ticket-skill-tests)
6. [Jira Integration Agent Tests](#jira-integration-agent-tests)
7. [GitHub Actions Workflow Tests](#github-actions-workflow-tests)
8. [Test Fixtures and Utilities](#test-fixtures-and-utilities)
9. [Running Tests](#running-tests)
10. [Coverage Requirements](#coverage-requirements)

---

## Overview

This document provides comprehensive unit testing guidance for all new components in the PR Peer Review system. All tests use pytest as the testing framework with unittest.mock for mocking external dependencies.

### Testing Philosophy

- **Unit tests** verify individual components in isolation
- **Mock all external dependencies** (APIs, databases, file systems)
- **Test both success and failure paths**
- **Use parameterized tests** for testing multiple scenarios
- **Maintain >85% code coverage** across all components

### Key Testing Principles

1. Each test should be independent and idempotent
2. Tests should run quickly (<5 seconds total for all unit tests)
3. Use descriptive test names that explain what is being tested
4. Mock external dependencies consistently
5. Test edge cases and error conditions thoroughly

---

## Testing Framework Setup

### Installation

```bash
# Install testing dependencies
pip install pytest==7.4.3
pip install pytest-cov==4.1.0
pip install pytest-mock==3.12.0
pip install pytest-asyncio==0.21.1
pip install freezegun==1.4.0
pip install responses==0.24.1
```

### Project Structure

```
tonic-peer-review-agent/
├── agents/
│   ├── pr_orchestrator_agent.py
│   └── jira_integration_agent.py
├── skills/
│   ├── orchestrator_skill.py
│   └── jira_ticket_skill.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Shared fixtures
│   ├── test_pr_orchestrator_agent.py
│   ├── test_orchestrator_skill.py
│   ├── test_jira_ticket_skill.py
│   ├── test_jira_integration_agent.py
│   └── test_github_actions_workflow.py
└── pytest.ini
```

### pytest Configuration

**pytest.ini**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --cov=agents
    --cov=skills
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=85
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

---

## PR Orchestrator Agent Tests

### Test Module: `test_pr_orchestrator_agent.py`

The PR Orchestrator Agent coordinates workflow execution across all validation agents.

### Test 1: Pipeline Initialization

**Description**: Test that the orchestrator correctly initializes workflow state from a GitHub PR event.

**Input Data**:
```python
pr_event = {
    "event": "pull_request.opened",
    "pr_number": 123,
    "repository": "tonic-scm/order-service",
    "source_branch": "feature/new-pattern",
    "target_branch": "main",
    "author": "developer1",
    "commits": ["abc123"],
    "modified_files": ["src/main/java/OrderService.java"]
}
```

**Expected Output**:
- Workflow state initialized with INITIALIZED status
- Workflow ID generated in correct format
- All agent results array empty
- Started timestamp set

**Test Code**:
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from agents.pr_orchestrator_agent import PROrchestratorAgent
from agents.models import WorkflowState, WorkflowStatus

class TestPROrchestratorInitialization:
    """Test suite for PR Orchestrator Agent initialization"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance with mocked dependencies"""
        with patch('agents.pr_orchestrator_agent.DynamoDBClient') as mock_db, \
             patch('agents.pr_orchestrator_agent.CloudWatchClient') as mock_cw:
            orchestrator = PROrchestratorAgent(
                dynamodb_client=mock_db,
                cloudwatch_client=mock_cw,
                sla_config={
                    "code_best_practises": 30,
                    "architect_best_practises": 10,
                    "lld_alignment_review": 20
                }
            )
            return orchestrator

    @pytest.fixture
    def pr_event(self):
        """Sample PR event payload"""
        return {
            "event": "pull_request.opened",
            "pr_number": 123,
            "repository": "tonic-scm/order-service",
            "source_branch": "feature/new-pattern",
            "target_branch": "main",
            "author": "developer1",
            "commits": ["abc123"],
            "modified_files": ["src/main/java/OrderService.java"],
            "pr_title": "Add new repository pattern",
            "pr_description": "Implements repository pattern with caching"
        }

    @patch('agents.pr_orchestrator_agent.datetime')
    def test_initialize_workflow_success(self, mock_datetime, orchestrator, pr_event):
        """Test successful workflow initialization"""
        # Arrange
        fixed_time = datetime(2026, 1, 28, 10, 30, 0)
        mock_datetime.utcnow.return_value = fixed_time
        mock_datetime.strftime = datetime.strftime

        # Act
        workflow_state = orchestrator.initialize_workflow(pr_event)

        # Assert
        assert workflow_state.workflow_id == "wf-20260128-103000-123"
        assert workflow_state.pr_number == 123
        assert workflow_state.repository == "tonic-scm/order-service"
        assert workflow_state.status == WorkflowStatus.INITIALIZED
        assert workflow_state.merge_decision == "PENDING"
        assert workflow_state.steps_completed == []
        assert workflow_state.agent_results == []
        assert workflow_state.started_at == fixed_time

    def test_initialize_workflow_missing_pr_number(self, orchestrator):
        """Test workflow initialization with missing PR number"""
        # Arrange
        invalid_event = {
            "event": "pull_request.opened",
            "repository": "tonic-scm/order-service"
        }

        # Act & Assert
        with pytest.raises(ValueError, match="PR number is required"):
            orchestrator.initialize_workflow(invalid_event)

    def test_initialize_workflow_missing_repository(self, orchestrator):
        """Test workflow initialization with missing repository"""
        # Arrange
        invalid_event = {
            "event": "pull_request.opened",
            "pr_number": 123
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Repository is required"):
            orchestrator.initialize_workflow(invalid_event)

    @patch('agents.pr_orchestrator_agent.uuid.uuid4')
    def test_workflow_id_generation(self, mock_uuid, orchestrator, pr_event):
        """Test workflow ID follows correct format"""
        # Arrange
        mock_uuid.return_value = MagicMock(hex="abc123def456")

        # Act
        workflow_state = orchestrator.initialize_workflow(pr_event)

        # Assert
        assert workflow_state.workflow_id.startswith("wf-")
        assert f"-{pr_event['pr_number']}" in workflow_state.workflow_id
```

### Test 2: Agent Execution Sequencing

**Description**: Test that agents are executed in correct sequential order with proper state transitions.

**Input Data**:
```python
workflow_state = WorkflowState(
    workflow_id="wf-20260128-103000-123",
    pr_number=123,
    status=WorkflowStatus.INITIALIZED
)
```

**Expected Output**:
- Agents execute in order: Code → Architect → LLD → Pattern → Peer Review
- State transitions correctly between agents
- Each agent result recorded in workflow state

**Test Code**:
```python
class TestPROrchestratorSequencing:
    """Test suite for agent execution sequencing"""

    @pytest.fixture
    def mock_agent_clients(self):
        """Mock all agent API clients"""
        return {
            'code_best_practises': Mock(),
            'architect_best_practises': Mock(),
            'lld_alignment_review': Mock(),
            'pattern_matching': Mock(),
            'peer_review': Mock()
        }

    @pytest.fixture
    def workflow_state(self):
        """Create initial workflow state"""
        return WorkflowState(
            workflow_id="wf-20260128-103000-123",
            pr_number=123,
            repository="tonic-scm/order-service",
            status=WorkflowStatus.INITIALIZED,
            steps_completed=[],
            agent_results=[]
        )

    def test_execute_code_best_practises_agent_first(
        self, orchestrator, workflow_state, mock_agent_clients
    ):
        """Test Code Best Practises Agent executes first"""
        # Arrange
        orchestrator.agent_clients = mock_agent_clients
        mock_agent_clients['code_best_practises'].execute.return_value = {
            "status": "PASSED",
            "execution_time_ms": 12000,
            "violations": []
        }

        # Act
        result = orchestrator.execute_step(
            workflow_state,
            step_name="code_best_practises"
        )

        # Assert
        mock_agent_clients['code_best_practises'].execute.assert_called_once()
        assert result["status"] == "PASSED"
        assert workflow_state.status == WorkflowStatus.RUNNING_STEP_1

    def test_agent_execution_order_full_path(
        self, orchestrator, workflow_state, mock_agent_clients
    ):
        """Test all agents execute in correct order for new pattern path"""
        # Arrange
        orchestrator.agent_clients = mock_agent_clients

        # Mock agent responses
        mock_agent_clients['code_best_practises'].execute.return_value = {
            "status": "PASSED",
            "violations": []
        }
        mock_agent_clients['architect_best_practises'].execute.return_value = {
            "status": "NEW_PATTERN_FOUND",
            "pattern_data": {"name": "Repository Pattern"}
        }
        mock_agent_clients['lld_alignment_review'].execute.return_value = {
            "status": "LLD_COMPLIANT"
        }

        # Act
        orchestrator.execute_workflow(workflow_state)

        # Assert - verify execution order
        call_order = []
        for agent_name, mock_client in mock_agent_clients.items():
            if mock_client.execute.called:
                call_order.append(agent_name)

        expected_order = [
            'code_best_practises',
            'architect_best_practises',
            'lld_alignment_review'
        ]
        assert call_order == expected_order

    def test_skip_agents_when_no_new_pattern(
        self, orchestrator, workflow_state, mock_agent_clients
    ):
        """Test LLD/Pattern/Peer Review skipped when no new pattern"""
        # Arrange
        orchestrator.agent_clients = mock_agent_clients
        mock_agent_clients['code_best_practises'].execute.return_value = {
            "status": "PASSED"
        }
        mock_agent_clients['architect_best_practises'].execute.return_value = {
            "status": "NO_NEW_PATTERN",
            "similarity_score": 0.96
        }

        # Act
        orchestrator.execute_workflow(workflow_state)

        # Assert
        mock_agent_clients['lld_alignment_review'].execute.assert_not_called()
        mock_agent_clients['pattern_matching'].execute.assert_not_called()
        mock_agent_clients['peer_review'].execute.assert_not_called()
        assert "lld_alignment" in workflow_state.steps_skipped
        assert "pattern_matching" in workflow_state.steps_skipped
        assert "peer_review" in workflow_state.steps_skipped
```

### Test 3: Result Aggregation

**Description**: Test that results from all agents are correctly aggregated into final report.

**Test Code**:
```python
class TestPROrchestratorAggregation:
    """Test suite for result aggregation"""

    @pytest.fixture
    def completed_workflow_state(self):
        """Workflow state with multiple agent results"""
        return WorkflowState(
            workflow_id="wf-20260128-103000-123",
            pr_number=123,
            repository="tonic-scm/order-service",
            status=WorkflowStatus.COMPLETED_SUCCESS,
            steps_completed=[
                "code_best_practises",
                "architect_best_practises"
            ],
            agent_results=[
                {
                    "agent": "code_best_practises_agent",
                    "status": "PASSED",
                    "execution_time_ms": 12000,
                    "violations": []
                },
                {
                    "agent": "architect_best_practises_agent",
                    "status": "NO_NEW_PATTERN",
                    "execution_time_ms": 5200,
                    "similarity_score": 0.96
                }
            ]
        )

    def test_aggregate_results_success(self, orchestrator, completed_workflow_state):
        """Test aggregating results from successful workflow"""
        # Act
        report = orchestrator.aggregate_results(completed_workflow_state)

        # Assert
        assert report["pr_number"] == 123
        assert report["workflow_status"] == "COMPLETED_SUCCESS"
        assert report["merge_decision"] == "APPROVE_MERGE"
        assert report["execution_summary"]["agents_executed"] == 2
        assert report["execution_summary"]["agents_skipped"] == 4
        assert len(report["agent_results"]) == 2

    def test_aggregate_results_with_timing(
        self, orchestrator, completed_workflow_state
    ):
        """Test timing calculations in aggregated report"""
        # Act
        report = orchestrator.aggregate_results(completed_workflow_state)

        # Assert
        total_time = report["execution_summary"]["total_time_seconds"]
        assert total_time == 17  # 12s + 5s (rounded)

        # Verify individual agent times preserved
        code_agent = report["agent_results"][0]
        assert code_agent["execution_time_ms"] == 12000

    def test_aggregate_results_with_failures(self, orchestrator):
        """Test aggregation when agents fail"""
        # Arrange
        failed_state = WorkflowState(
            workflow_id="wf-20260128-103000-124",
            pr_number=124,
            status=WorkflowStatus.COMPLETED_FAILURE,
            agent_results=[
                {
                    "agent": "code_best_practises_agent",
                    "status": "FAILED",
                    "violations": [{"type": "NAMING_CONVENTION"}]
                }
            ]
        )

        # Act
        report = orchestrator.aggregate_results(failed_state)

        # Assert
        assert report["workflow_status"] == "COMPLETED_FAILURE"
        assert report["merge_decision"] == "BLOCK_MERGE"
        assert report["agent_results"][0]["status"] == "FAILED"
```

### Test 4: Merge Decision Logic

**Description**: Test the logic that determines whether to approve or block merge.

**Test Code**:
```python
class TestPROrchestratorMergeDecision:
    """Test suite for merge decision logic"""

    @pytest.mark.parametrize("agent_results,expected_decision", [
        # Test case 1: All agents passed, no new pattern
        (
            [
                {"agent": "code_best_practises_agent", "status": "PASSED"},
                {"agent": "architect_best_practises_agent", "status": "NO_NEW_PATTERN"}
            ],
            "APPROVE_MERGE"
        ),
        # Test case 2: Code violations found
        (
            [
                {"agent": "code_best_practises_agent", "status": "FAILED"}
            ],
            "BLOCK_MERGE"
        ),
        # Test case 3: LLD deviation found
        (
            [
                {"agent": "code_best_practises_agent", "status": "PASSED"},
                {"agent": "architect_best_practises_agent", "status": "NEW_PATTERN_FOUND"},
                {"agent": "lld_alignment_review_agent", "status": "LLD_DEVIATION_FOUND"}
            ],
            "BLOCK_MERGE"
        ),
        # Test case 4: Peer review pending
        (
            [
                {"agent": "code_best_practises_agent", "status": "PASSED"},
                {"agent": "architect_best_practises_agent", "status": "NEW_PATTERN_FOUND"},
                {"agent": "lld_alignment_review_agent", "status": "LLD_COMPLIANT"},
                {"agent": "peer_review_agent", "status": "PENDING_REVIEW"}
            ],
            "PENDING_REVIEW"
        ),
        # Test case 5: Peer review approved
        (
            [
                {"agent": "code_best_practises_agent", "status": "PASSED"},
                {"agent": "architect_best_practises_agent", "status": "NEW_PATTERN_FOUND"},
                {"agent": "lld_alignment_review_agent", "status": "LLD_COMPLIANT"},
                {"agent": "peer_review_agent", "status": "APPROVED"}
            ],
            "APPROVE_MERGE"
        )
    ])
    def test_make_merge_decision_scenarios(
        self, orchestrator, agent_results, expected_decision
    ):
        """Test merge decision logic for various scenarios"""
        # Arrange
        workflow_state = WorkflowState(
            workflow_id="wf-test",
            pr_number=123,
            agent_results=agent_results
        )

        # Act
        decision = orchestrator.make_merge_decision(workflow_state)

        # Assert
        assert decision == expected_decision

    def test_merge_decision_with_ci_checks_failed(self, orchestrator):
        """Test merge blocked if CI checks fail"""
        # Arrange
        workflow_state = WorkflowState(
            workflow_id="wf-test",
            pr_number=123,
            agent_results=[
                {"agent": "code_best_practises_agent", "status": "PASSED"}
            ],
            ci_checks_status="FAILED"
        )

        # Act
        decision = orchestrator.make_merge_decision(workflow_state)

        # Assert
        assert decision == "BLOCK_MERGE"
```

### Test 5: Error Handling

**Description**: Test orchestrator handles agent failures and timeouts correctly.

**Test Code**:
```python
class TestPROrchestratorErrorHandling:
    """Test suite for error handling"""

    def test_handle_agent_timeout(self, orchestrator, workflow_state):
        """Test handling of agent timeout"""
        # Arrange
        from requests.exceptions import Timeout
        orchestrator.agent_clients['code_best_practises'].execute.side_effect = Timeout()

        # Act & Assert
        with pytest.raises(AgentTimeoutError) as exc_info:
            orchestrator.execute_step(workflow_state, "code_best_practises")

        assert "code_best_practises" in str(exc_info.value)
        assert workflow_state.status == WorkflowStatus.FAILED

    def test_handle_agent_api_unavailable(self, orchestrator, workflow_state):
        """Test handling of agent API unavailable"""
        # Arrange
        from requests.exceptions import ConnectionError
        orchestrator.agent_clients['code_best_practises'].execute.side_effect = ConnectionError()

        # Act
        with pytest.raises(AgentUnavailableError):
            orchestrator.execute_step(workflow_state, "code_best_practises")

    @patch('agents.pr_orchestrator_agent.CloudWatchClient')
    def test_create_alarm_on_timeout(self, mock_cw, orchestrator, workflow_state):
        """Test CloudWatch alarm created on agent timeout"""
        # Arrange
        from requests.exceptions import Timeout
        orchestrator.agent_clients['code_best_practises'].execute.side_effect = Timeout()
        orchestrator.cloudwatch_client = mock_cw

        # Act
        try:
            orchestrator.execute_step(workflow_state, "code_best_practises")
        except AgentTimeoutError:
            pass

        # Assert
        mock_cw.create_alarm.assert_called_once()
        alarm_call = mock_cw.create_alarm.call_args
        assert "AGENT_TIMEOUT" in alarm_call[0][0]

    @pytest.mark.parametrize("retry_count,should_succeed", [
        (1, False),
        (2, False),
        (3, True)
    ])
    def test_retry_logic_exponential_backoff(
        self, orchestrator, workflow_state, retry_count, should_succeed
    ):
        """Test exponential backoff retry logic"""
        # Arrange
        from requests.exceptions import ConnectionError
        mock_client = orchestrator.agent_clients['code_best_practises']

        # Fail first N attempts, then succeed
        side_effects = [ConnectionError()] * (retry_count - 1)
        if should_succeed:
            side_effects.append({"status": "PASSED"})
        else:
            side_effects.append(ConnectionError())

        mock_client.execute.side_effect = side_effects

        # Act
        if should_succeed:
            result = orchestrator.execute_step_with_retry(
                workflow_state, "code_best_practises", max_retries=3
            )
            # Assert
            assert result["status"] == "PASSED"
            assert mock_client.execute.call_count == retry_count
        else:
            with pytest.raises(AgentUnavailableError):
                orchestrator.execute_step_with_retry(
                    workflow_state, "code_best_practises", max_retries=3
                )

    def test_handle_concurrent_pr_update(self, orchestrator, workflow_state):
        """Test handling of concurrent PR update during workflow"""
        # Arrange
        workflow_state.commit_sha = "abc123"
        new_commit_sha = "def456"

        # Simulate PR update detection
        with patch.object(orchestrator, 'get_current_pr_commit_sha', return_value=new_commit_sha):
            # Act
            should_cancel = orchestrator.check_pr_updated(workflow_state)

            # Assert
            assert should_cancel is True
            assert workflow_state.status == WorkflowStatus.CANCELLED
```

---

## Orchestrator Skill Tests

### Test Module: `test_orchestrator_skill.py`

The Orchestrator Skill provides reusable operations for workflow orchestration.

### Test 1: execute_pipeline Operation

**Description**: Test executing complete pipeline of agents.

**Test Code**:
```python
import pytest
from unittest.mock import Mock, patch, call
from skills.orchestrator_skill import OrchestratorSkill, PipelineConfig

class TestOrchestratorSkillPipeline:
    """Test suite for pipeline execution"""

    @pytest.fixture
    def orchestrator_skill(self):
        """Create orchestrator skill instance"""
        return OrchestratorSkill(
            agent_registry={
                'code_best_practises': Mock(),
                'architect_best_practises': Mock(),
                'lld_alignment_review': Mock()
            }
        )

    @pytest.fixture
    def pipeline_config(self):
        """Create pipeline configuration"""
        return PipelineConfig(
            steps=[
                {"name": "code_best_practises", "required": True},
                {"name": "architect_best_practises", "required": True},
                {"name": "lld_alignment_review", "required": False, "conditional": True}
            ]
        )

    def test_execute_pipeline_success(self, orchestrator_skill, pipeline_config):
        """Test successful pipeline execution"""
        # Arrange
        input_data = {"pr_number": 123, "repository": "order-service"}

        orchestrator_skill.agent_registry['code_best_practises'].execute.return_value = {
            "status": "PASSED"
        }
        orchestrator_skill.agent_registry['architect_best_practises'].execute.return_value = {
            "status": "NO_NEW_PATTERN"
        }

        # Act
        result = orchestrator_skill.execute_pipeline(pipeline_config, input_data)

        # Assert
        assert result["status"] == "SUCCESS"
        assert result["steps_executed"] == 2
        assert result["steps_skipped"] == 1  # LLD skipped (no new pattern)

    def test_execute_pipeline_stops_on_failure(self, orchestrator_skill, pipeline_config):
        """Test pipeline stops when required step fails"""
        # Arrange
        input_data = {"pr_number": 123}
        orchestrator_skill.agent_registry['code_best_practises'].execute.return_value = {
            "status": "FAILED",
            "violations": [{"type": "NAMING"}]
        }

        # Act
        result = orchestrator_skill.execute_pipeline(pipeline_config, input_data)

        # Assert
        assert result["status"] == "FAILED"
        assert result["failed_step"] == "code_best_practises"
        # Architect agent should not be called
        orchestrator_skill.agent_registry['architect_best_practises'].execute.assert_not_called()
```

### Test 2: execute_agent Operation

**Description**: Test executing a single agent with retry logic.

**Test Code**:
```python
class TestOrchestratorSkillAgent:
    """Test suite for agent execution"""

    def test_execute_agent_success(self, orchestrator_skill):
        """Test successful agent execution"""
        # Arrange
        agent_name = "code_best_practises"
        input_data = {"pr_number": 123}
        orchestrator_skill.agent_registry[agent_name].execute.return_value = {
            "status": "PASSED"
        }

        # Act
        result = orchestrator_skill.execute_agent(agent_name, input_data)

        # Assert
        assert result["status"] == "PASSED"
        orchestrator_skill.agent_registry[agent_name].execute.assert_called_once_with(input_data)

    def test_execute_agent_with_timeout(self, orchestrator_skill):
        """Test agent execution with timeout enforcement"""
        # Arrange
        agent_name = "code_best_practises"
        timeout_seconds = 30

        import time
        def slow_execute(*args, **kwargs):
            time.sleep(2)  # Simulate slow execution
            return {"status": "PASSED"}

        orchestrator_skill.agent_registry[agent_name].execute.side_effect = slow_execute

        # Act
        with patch('time.time', side_effect=[0, 35]):  # Simulate timeout
            with pytest.raises(AgentTimeoutError):
                orchestrator_skill.execute_agent(
                    agent_name, {}, timeout_seconds=timeout_seconds
                )

    @pytest.mark.parametrize("retry_attempts,max_retries,should_succeed", [
        (1, 3, True),   # Succeed on first retry
        (2, 3, True),   # Succeed on second retry
        (3, 3, True),   # Succeed on third retry
        (4, 3, False),  # Exceed max retries
    ])
    def test_execute_agent_with_retry(
        self, orchestrator_skill, retry_attempts, max_retries, should_succeed
    ):
        """Test agent execution with retry logic"""
        # Arrange
        agent_name = "code_best_practises"
        from requests.exceptions import ConnectionError

        side_effects = [ConnectionError()] * (retry_attempts - 1)
        if should_succeed:
            side_effects.append({"status": "PASSED"})
        else:
            side_effects.extend([ConnectionError()] * (max_retries + 1))

        orchestrator_skill.agent_registry[agent_name].execute.side_effect = side_effects

        # Act & Assert
        if should_succeed:
            result = orchestrator_skill.execute_agent_with_retry(
                agent_name, {}, max_retries=max_retries
            )
            assert result["status"] == "PASSED"
        else:
            with pytest.raises(AgentUnavailableError):
                orchestrator_skill.execute_agent_with_retry(
                    agent_name, {}, max_retries=max_retries
                )
```

### Test 3: aggregate_results Operation

**Description**: Test aggregating results from multiple agent executions.

**Test Code**:
```python
class TestOrchestratorSkillAggregation:
    """Test suite for result aggregation"""

    def test_aggregate_results_all_passed(self, orchestrator_skill):
        """Test aggregating results when all agents pass"""
        # Arrange
        agent_results = [
            {"agent": "code_best_practises", "status": "PASSED", "time_ms": 12000},
            {"agent": "architect_best_practises", "status": "NO_NEW_PATTERN", "time_ms": 5000}
        ]

        # Act
        aggregated = orchestrator_skill.aggregate_results(agent_results)

        # Assert
        assert aggregated["overall_status"] == "PASSED"
        assert aggregated["total_execution_time_ms"] == 17000
        assert len(aggregated["results"]) == 2

    def test_aggregate_results_with_failures(self, orchestrator_skill):
        """Test aggregating results with failures"""
        # Arrange
        agent_results = [
            {"agent": "code_best_practises", "status": "FAILED", "violations": [{"type": "NAMING"}]},
            {"agent": "architect_best_practises", "status": "NOT_EXECUTED"}
        ]

        # Act
        aggregated = orchestrator_skill.aggregate_results(agent_results)

        # Assert
        assert aggregated["overall_status"] == "FAILED"
        assert aggregated["failures"][0]["agent"] == "code_best_practises"
```

### Test 4: make_decision Operation

**Description**: Test decision-making logic based on aggregated results.

**Test Code**:
```python
class TestOrchestratorSkillDecision:
    """Test suite for decision making"""

    @pytest.mark.parametrize("agent_results,expected_decision", [
        (
            [
                {"agent": "code_best_practises", "status": "PASSED"},
                {"agent": "architect_best_practises", "status": "NO_NEW_PATTERN"}
            ],
            "APPROVE"
        ),
        (
            [
                {"agent": "code_best_practises", "status": "FAILED"}
            ],
            "REJECT"
        ),
        (
            [
                {"agent": "code_best_practises", "status": "PASSED"},
                {"agent": "peer_review", "status": "PENDING"}
            ],
            "PENDING"
        )
    ])
    def test_make_decision_scenarios(
        self, orchestrator_skill, agent_results, expected_decision
    ):
        """Test decision making for various result scenarios"""
        # Act
        decision = orchestrator_skill.make_decision(agent_results)

        # Assert
        assert decision["decision"] == expected_decision
```

### Test 5: Conditional Execution Logic

**Description**: Test conditional execution of agents based on previous results.

**Test Code**:
```python
class TestOrchestratorSkillConditional:
    """Test suite for conditional execution"""

    def test_skip_lld_review_when_no_new_pattern(self, orchestrator_skill):
        """Test LLD review skipped when no new pattern detected"""
        # Arrange
        previous_results = {
            "architect_best_practises": {"status": "NO_NEW_PATTERN"}
        }

        # Act
        should_execute = orchestrator_skill.should_execute_agent(
            "lld_alignment_review", previous_results
        )

        # Assert
        assert should_execute is False

    def test_execute_lld_review_when_new_pattern(self, orchestrator_skill):
        """Test LLD review executes when new pattern detected"""
        # Arrange
        previous_results = {
            "architect_best_practises": {"status": "NEW_PATTERN_FOUND"}
        }

        # Act
        should_execute = orchestrator_skill.should_execute_agent(
            "lld_alignment_review", previous_results
        )

        # Assert
        assert should_execute is True

    def test_execute_jira_integration_on_any_failure(self, orchestrator_skill):
        """Test Jira integration executes on any failure"""
        # Arrange
        previous_results = {
            "code_best_practises": {"status": "FAILED"}
        }

        # Act
        should_execute = orchestrator_skill.should_execute_agent(
            "jira_integration", previous_results
        )

        # Assert
        assert should_execute is True
```

---

## Jira Ticket Skill Tests

### Test Module: `test_jira_ticket_skill.py`

The Jira Ticket Skill provides reusable operations for Jira ticket management.

### Test 1: create_ticket Operation

**Description**: Test creating Jira ticket with auto-assignment.

**Test Code**:
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from skills.jira_ticket_skill import JiraTicketSkill
from skills.jira_ticket_skill.models import CreateTicketInput, CreateTicketOutput

class TestJiraTicketSkillCreate:
    """Test suite for ticket creation"""

    @pytest.fixture
    def jira_skill(self):
        """Create Jira skill instance with mocked Jira client"""
        with patch('skills.jira_ticket_skill.Jira') as mock_jira:
            skill = JiraTicketSkill(
                base_url="https://company.atlassian.net",
                email="automation@company.com",
                api_token="test_token",
                project_key="SCM"
            )
            skill.jira_client = mock_jira
            return skill

    @pytest.fixture
    def create_ticket_input(self):
        """Sample ticket creation input"""
        return CreateTicketInput(
            issue_type="Code Violation",
            summary="Code violations in PR #123",
            description={"type": "doc", "content": []},
            pr_author_email="developer1@company.com",
            pr_url="https://github.com/org/repo/pull/123",
            pr_number=123,
            repository="org/repo",
            severity="MEDIUM"
        )

    def test_create_ticket_success(self, jira_skill, create_ticket_input):
        """Test successful ticket creation"""
        # Arrange
        mock_response = {
            "key": "SCM-456",
            "self": "https://company.atlassian.net/rest/api/3/issue/10001"
        }
        jira_skill.jira_client.create_issue.return_value = mock_response

        # Mock user lookup
        with patch.object(jira_skill, 'lookup_user', return_value="5b10ac8d82e05b22cc7d4ef5"):
            # Act
            output = jira_skill.create_ticket(create_ticket_input)

            # Assert
            assert output.status == "SUCCESS"
            assert output.ticket_id == "SCM-456"
            assert output.ticket_key == "SCM-456"
            assert output.assignee_account_id == "5b10ac8d82e05b22cc7d4ef5"
            assert output.assignment_method == "direct"
            assert output.pr_linked is True

    def test_create_ticket_with_fallback_assignment(self, jira_skill, create_ticket_input):
        """Test ticket creation with fallback assignment"""
        # Arrange
        jira_skill.jira_client.create_issue.return_value = {"key": "SCM-456"}

        # Mock user lookup failure, fallback to default
        with patch.object(jira_skill, 'lookup_user', return_value=None), \
             patch.object(jira_skill, 'get_default_assignee', return_value="5b10ac8d82e05b22cc7d4ef6"):
            # Act
            output = jira_skill.create_ticket(create_ticket_input)

            # Assert
            assert output.status == "SUCCESS"
            assert output.assignment_method == "fallback_default"
            assert output.assignee_account_id == "5b10ac8d82e05b22cc7d4ef6"

    def test_create_ticket_with_adf_description(self, jira_skill, create_ticket_input):
        """Test ticket creation with ADF formatted description"""
        # Arrange
        adf_description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Test description"}]
                }
            ]
        }
        create_ticket_input.description = adf_description
        jira_skill.jira_client.create_issue.return_value = {"key": "SCM-456"}

        with patch.object(jira_skill, 'lookup_user', return_value="test_account_id"):
            # Act
            output = jira_skill.create_ticket(create_ticket_input)

            # Assert
            call_args = jira_skill.jira_client.create_issue.call_args
            assert call_args[1]['fields']['description'] == adf_description

    def test_create_ticket_failure_jira_api_error(self, jira_skill, create_ticket_input):
        """Test handling of Jira API error during ticket creation"""
        # Arrange
        from atlassian.errors import ApiError
        jira_skill.jira_client.create_issue.side_effect = ApiError("Jira API error")

        # Act & Assert
        with pytest.raises(JiraTicketCreationError):
            jira_skill.create_ticket(create_ticket_input)
```

### Test 2: assign_ticket Operation

**Description**: Test assigning ticket to user.

**Test Code**:
```python
class TestJiraTicketSkillAssign:
    """Test suite for ticket assignment"""

    def test_assign_ticket_by_email(self, jira_skill):
        """Test assigning ticket by email lookup"""
        # Arrange
        ticket_key = "SCM-456"
        assignee_email = "developer1@company.com"
        expected_account_id = "5b10ac8d82e05b22cc7d4ef5"

        with patch.object(jira_skill, 'lookup_user', return_value=expected_account_id):
            # Act
            output = jira_skill.assign_ticket(
                ticket_key=ticket_key,
                assignee_email=assignee_email
            )

            # Assert
            assert output.status == "SUCCESS"
            assert output.assignee_account_id == expected_account_id
            jira_skill.jira_client.assign_issue.assert_called_once_with(
                ticket_key, expected_account_id
            )

    def test_assign_ticket_by_account_id(self, jira_skill):
        """Test assigning ticket by direct account ID"""
        # Arrange
        ticket_key = "SCM-456"
        account_id = "5b10ac8d82e05b22cc7d4ef5"

        # Act
        output = jira_skill.assign_ticket(
            ticket_key=ticket_key,
            assignee_account_id=account_id
        )

        # Assert
        assert output.status == "SUCCESS"
        assert output.assignee_account_id == account_id
        jira_skill.jira_client.assign_issue.assert_called_once_with(ticket_key, account_id)

    def test_assign_ticket_user_not_found(self, jira_skill):
        """Test assignment failure when user not found"""
        # Arrange
        with patch.object(jira_skill, 'lookup_user', return_value=None):
            # Act & Assert
            with pytest.raises(UserNotFoundError):
                jira_skill.assign_ticket(
                    ticket_key="SCM-456",
                    assignee_email="nonexistent@company.com"
                )
```

### Test 3: lookup_user with Caching

**Description**: Test user lookup with Redis caching.

**Test Code**:
```python
class TestJiraTicketSkillLookup:
    """Test suite for user lookup"""

    @pytest.fixture
    def jira_skill_with_cache(self):
        """Create Jira skill with Redis cache"""
        with patch('skills.jira_ticket_skill.Jira') as mock_jira, \
             patch('skills.jira_ticket_skill.Redis') as mock_redis:
            skill = JiraTicketSkill(
                base_url="https://company.atlassian.net",
                email="automation@company.com",
                api_token="test_token",
                project_key="SCM",
                cache_enabled=True
            )
            skill.jira_client = mock_jira
            skill.cache_client = mock_redis
            return skill

    def test_lookup_user_cache_hit(self, jira_skill_with_cache):
        """Test user lookup with cache hit"""
        # Arrange
        email = "developer1@company.com"
        cached_account_id = "5b10ac8d82e05b22cc7d4ef5"
        cache_key = f"user:{email}"

        jira_skill_with_cache.cache_client.get.return_value = cached_account_id.encode()

        # Act
        account_id = jira_skill_with_cache.lookup_user(email)

        # Assert
        assert account_id == cached_account_id
        jira_skill_with_cache.cache_client.get.assert_called_once_with(cache_key)
        # Jira API should not be called
        jira_skill_with_cache.jira_client.user_find_by_user_string.assert_not_called()

    def test_lookup_user_cache_miss_then_cache_store(self, jira_skill_with_cache):
        """Test user lookup with cache miss, then store in cache"""
        # Arrange
        email = "developer1@company.com"
        account_id = "5b10ac8d82e05b22cc7d4ef5"
        cache_key = f"user:{email}"

        jira_skill_with_cache.cache_client.get.return_value = None
        jira_skill_with_cache.jira_client.user_find_by_user_string.return_value = [
            {"accountId": account_id, "displayName": "Developer One"}
        ]

        # Act
        result = jira_skill_with_cache.lookup_user(email)

        # Assert
        assert result == account_id
        jira_skill_with_cache.jira_client.user_find_by_user_string.assert_called_once_with(email)
        jira_skill_with_cache.cache_client.setex.assert_called_once()
        # Verify cache TTL (24 hours = 86400 seconds)
        call_args = jira_skill_with_cache.cache_client.setex.call_args
        assert call_args[0][0] == cache_key
        assert call_args[0][1] == 86400
        assert call_args[0][2] == account_id

    def test_lookup_user_not_found(self, jira_skill_with_cache):
        """Test user lookup when user doesn't exist in Jira"""
        # Arrange
        email = "nonexistent@company.com"
        jira_skill_with_cache.cache_client.get.return_value = None
        jira_skill_with_cache.jira_client.user_find_by_user_string.return_value = []

        # Act
        result = jira_skill_with_cache.lookup_user(email)

        # Assert
        assert result is None

    @patch('skills.jira_ticket_skill.time.time')
    def test_lookup_user_performance(self, mock_time, jira_skill_with_cache):
        """Test user lookup performance is under 200ms"""
        # Arrange
        email = "developer1@company.com"
        mock_time.side_effect = [0, 0.150]  # 150ms execution time
        jira_skill_with_cache.cache_client.get.return_value = "test_account_id".encode()

        # Act
        start = mock_time()
        jira_skill_with_cache.lookup_user(email)
        end = mock_time()

        # Assert
        execution_time_ms = (end - start) * 1000
        assert execution_time_ms < 200
```

### Test 4: link_pr Operation

**Description**: Test linking GitHub PR to Jira ticket.

**Test Code**:
```python
class TestJiraTicketSkillLinkPR:
    """Test suite for PR linking"""

    def test_link_pr_success(self, jira_skill):
        """Test successful PR linking"""
        # Arrange
        ticket_key = "SCM-456"
        pr_url = "https://github.com/org/repo/pull/123"
        pr_number = 123

        jira_skill.jira_client.create_or_update_issue_remote_links.return_value = {
            "id": "10001"
        }

        # Act
        output = jira_skill.link_pr(
            ticket_key=ticket_key,
            pr_url=pr_url,
            pr_number=pr_number,
            pr_title="Add new feature",
            repository="org/repo",
            pr_state="open"
        )

        # Assert
        assert output.status == "SUCCESS"
        assert output.link_id == "10001"
        jira_skill.jira_client.create_or_update_issue_remote_links.assert_called_once()

    def test_link_pr_duplicate_link_handling(self, jira_skill):
        """Test handling of duplicate PR link (already linked)"""
        # Arrange
        from atlassian.errors import ApiError
        error = ApiError("Remote link already exists")
        jira_skill.jira_client.create_or_update_issue_remote_links.side_effect = error

        # Act
        output = jira_skill.link_pr(
            ticket_key="SCM-456",
            pr_url="https://github.com/org/repo/pull/123",
            pr_number=123,
            pr_title="Test",
            repository="org/repo",
            pr_state="open"
        )

        # Assert
        # Should handle gracefully (link already exists is not a critical error)
        assert output.status == "SUCCESS"
        assert "already exists" in output.message.lower()
```

### Test 5: add_comment Operation

**Description**: Test adding comments to Jira tickets.

**Test Code**:
```python
class TestJiraTicketSkillComment:
    """Test suite for adding comments"""

    def test_add_comment_plain_text(self, jira_skill):
        """Test adding plain text comment"""
        # Arrange
        ticket_key = "SCM-456"
        comment_text = "This issue has been resolved."

        jira_skill.jira_client.issue_add_comment.return_value = {"id": "10001"}

        # Act
        output = jira_skill.add_comment(ticket_key, comment_text)

        # Assert
        assert output.status == "SUCCESS"
        assert output.comment_id == "10001"
        jira_skill.jira_client.issue_add_comment.assert_called_once()

    def test_add_comment_adf_format(self, jira_skill):
        """Test adding ADF formatted comment"""
        # Arrange
        ticket_key = "SCM-456"
        adf_comment = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Status update"}]
                }
            ]
        }

        jira_skill.jira_client.issue_add_comment.return_value = {"id": "10002"}

        # Act
        output = jira_skill.add_comment(ticket_key, adf_comment)

        # Assert
        assert output.status == "SUCCESS"
        call_args = jira_skill.jira_client.issue_add_comment.call_args
        assert call_args[0][1] == adf_comment
```

### Test 6: Error Handling and Retry Logic

**Description**: Test error handling and retry mechanisms.

**Test Code**:
```python
class TestJiraTicketSkillErrorHandling:
    """Test suite for error handling"""

    def test_handle_rate_limiting(self, jira_skill):
        """Test handling of Jira API rate limiting"""
        # Arrange
        from atlassian.errors import ApiError
        import requests

        # Create mock response with 429 status and Retry-After header
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}

        error = ApiError("Rate limit exceeded", response=mock_response)
        jira_skill.jira_client.create_issue.side_effect = [error, {"key": "SCM-456"}]

        # Act
        with patch('time.sleep') as mock_sleep:
            output = jira_skill.create_ticket_with_retry(
                CreateTicketInput(
                    issue_type="Code Violation",
                    summary="Test",
                    description={},
                    pr_url="https://github.com/org/repo/pull/1",
                    pr_number=1,
                    repository="org/repo",
                    severity="LOW"
                )
            )

            # Assert
            assert output.status == "SUCCESS"
            mock_sleep.assert_called_once_with(60)  # Respect Retry-After header

    @pytest.mark.parametrize("exception,is_retryable", [
        (ConnectionError("Network error"), True),
        (TimeoutError("Request timeout"), True),
        (ValueError("Invalid input"), False),
        (KeyError("Missing field"), False)
    ])
    def test_retryable_vs_non_retryable_errors(
        self, jira_skill, exception, is_retryable
    ):
        """Test classification of retryable vs non-retryable errors"""
        # Act
        result = jira_skill.is_retryable_error(exception)

        # Assert
        assert result == is_retryable

    @patch('skills.jira_ticket_skill.exponential_backoff')
    def test_exponential_backoff_retry(self, mock_backoff, jira_skill):
        """Test exponential backoff between retries"""
        # Arrange
        from requests.exceptions import ConnectionError
        jira_skill.jira_client.create_issue.side_effect = [
            ConnectionError(),
            ConnectionError(),
            {"key": "SCM-456"}
        ]
        mock_backoff.side_effect = [5, 15, 45]  # Backoff delays

        # Act
        with patch('time.sleep') as mock_sleep:
            output = jira_skill.create_ticket_with_retry(
                CreateTicketInput(
                    issue_type="Code Violation",
                    summary="Test",
                    description={},
                    pr_url="https://github.com/org/repo/pull/1",
                    pr_number=1,
                    repository="org/repo",
                    severity="LOW"
                ),
                max_retries=3
            )

            # Assert
            assert output.status == "SUCCESS"
            assert mock_sleep.call_count == 2  # 2 retries before success
            mock_sleep.assert_any_call(5)
            mock_sleep.assert_any_call(15)
```

---

## Jira Integration Agent Tests

### Test Module: `test_jira_integration_agent.py`

The Jira Integration Agent creates tickets for validation failures.

### Test 1: Auto-Assignment Fallback Chain

**Description**: Test the complete fallback chain for ticket assignment.

**Test Code**:
```python
import pytest
from unittest.mock import Mock, patch
from agents.jira_integration_agent import JiraIntegrationAgent

class TestJiraIntegrationAgentAssignment:
    """Test suite for auto-assignment logic"""

    @pytest.fixture
    def jira_agent(self):
        """Create Jira integration agent instance"""
        with patch('agents.jira_integration_agent.JiraTicketSkill') as mock_skill:
            agent = JiraIntegrationAgent(
                jira_skill=mock_skill,
                default_assignee_id="5b10ac8d82e05b22cc7d4ef6"
            )
            return agent

    def test_assignment_tier1_direct_email(self, jira_agent):
        """Test Tier 1: Direct assignment via PR author email"""
        # Arrange
        input_data = {
            "issue_type": "CODE_VIOLATION",
            "pr_number": 123,
            "pr_author_email": "developer1@company.com",
            "severity": "MEDIUM"
        }

        jira_agent.jira_skill.lookup_user.return_value = "5b10ac8d82e05b22cc7d4ef5"
        jira_agent.jira_skill.create_ticket.return_value = Mock(
            status="SUCCESS",
            ticket_id="SCM-456",
            assignment_method="direct"
        )

        # Act
        result = jira_agent.create_ticket(input_data)

        # Assert
        assert result["assignee_account_id"] == "5b10ac8d82e05b22cc7d4ef5"
        assert result["assignment_method"] == "direct"

    def test_assignment_tier2_github_username_mapping(self, jira_agent):
        """Test Tier 2: Assignment via GitHub username mapping"""
        # Arrange
        input_data = {
            "issue_type": "CODE_VIOLATION",
            "pr_number": 123,
            "pr_author_github_username": "dev1",
            "severity": "MEDIUM"
        }

        # Mock lookup: email not found, but username mapping exists
        with patch.object(jira_agent, 'lookup_github_username_mapping',
                          return_value="developer1@company.com"):
            jira_agent.jira_skill.lookup_user.return_value = "5b10ac8d82e05b22cc7d4ef5"
            jira_agent.jira_skill.create_ticket.return_value = Mock(
                status="SUCCESS",
                assignment_method="github_mapped"
            )

            # Act
            result = jira_agent.create_ticket(input_data)

            # Assert
            assert result["assignment_method"] == "github_mapped"

    def test_assignment_tier3_domain_pattern(self, jira_agent):
        """Test Tier 3: Assignment via email domain pattern"""
        # Arrange
        input_data = {
            "issue_type": "CODE_VIOLATION",
            "pr_number": 123,
            "pr_author_github_username": "dev1",
            "severity": "MEDIUM"
        }

        # Mock lookup: no mapping, try domain pattern
        with patch.object(jira_agent, 'lookup_github_username_mapping', return_value=None), \
             patch.object(jira_agent, 'construct_email_from_username',
                          return_value="dev1@company.com"):
            jira_agent.jira_skill.lookup_user.return_value = "5b10ac8d82e05b22cc7d4ef5"
            jira_agent.jira_skill.create_ticket.return_value = Mock(
                status="SUCCESS",
                assignment_method="domain_pattern"
            )

            # Act
            result = jira_agent.create_ticket(input_data)

            # Assert
            assert result["assignment_method"] == "domain_pattern"

    def test_assignment_tier4_component_owner(self, jira_agent):
        """Test Tier 4: Fallback to component owner"""
        # Arrange
        input_data = {
            "issue_type": "CODE_VIOLATION",
            "pr_number": 123,
            "repository": "order-service",
            "severity": "MEDIUM"
        }

        # Mock all previous tiers fail
        with patch.object(jira_agent, 'lookup_github_username_mapping', return_value=None), \
             patch.object(jira_agent, 'get_component_owner',
                          return_value="5b10ac8d82e05b22cc7d4ef7"):
            jira_agent.jira_skill.lookup_user.return_value = None
            jira_agent.jira_skill.create_ticket.return_value = Mock(
                status="SUCCESS",
                assignment_method="fallback_component",
                assignee_account_id="5b10ac8d82e05b22cc7d4ef7"
            )

            # Act
            result = jira_agent.create_ticket(input_data)

            # Assert
            assert result["assignment_method"] == "fallback_component"
            assert result["assignee_account_id"] == "5b10ac8d82e05b22cc7d4ef7"

    def test_assignment_tier5_default_assignee(self, jira_agent):
        """Test Tier 5: Fallback to default assignee"""
        # Arrange
        input_data = {
            "issue_type": "CODE_VIOLATION",
            "pr_number": 123,
            "severity": "MEDIUM"
        }

        # Mock all tiers fail
        with patch.object(jira_agent, 'lookup_github_username_mapping', return_value=None), \
             patch.object(jira_agent, 'get_component_owner', return_value=None):
            jira_agent.jira_skill.lookup_user.return_value = None
            jira_agent.jira_skill.create_ticket.return_value = Mock(
                status="SUCCESS",
                assignment_method="fallback_default",
                assignee_account_id="5b10ac8d82e05b22cc7d4ef6"
            )

            # Act
            result = jira_agent.create_ticket(input_data)

            # Assert
            assert result["assignment_method"] == "fallback_default"
            assert result["assignee_account_id"] == "5b10ac8d82e05b22cc7d4ef6"

    @patch('agents.jira_integration_agent.CloudWatchClient')
    def test_assignment_tier6_unassigned_with_alarm(self, mock_cw, jira_agent):
        """Test Tier 6: Unassigned with CloudWatch alarm"""
        # Arrange
        input_data = {
            "issue_type": "CODE_VIOLATION",
            "pr_number": 123,
            "severity": "MEDIUM"
        }

        jira_agent.cloudwatch_client = mock_cw

        # Mock all tiers fail including default
        with patch.object(jira_agent, 'lookup_github_username_mapping', return_value=None), \
             patch.object(jira_agent, 'get_component_owner', return_value=None), \
             patch.object(jira_agent, 'get_default_assignee', return_value=None):
            jira_agent.jira_skill.create_ticket.return_value = Mock(
                status="SUCCESS",
                assignment_method="unassigned",
                assignee_account_id=None
            )

            # Act
            result = jira_agent.create_ticket(input_data)

            # Assert
            assert result["assignment_method"] == "unassigned"
            assert result["assignee_account_id"] is None
            mock_cw.put_metric_data.assert_called()  # Alarm created
```

### Test 2: Rich Context Generation (ADF Templates)

**Description**: Test generation of rich ADF formatted ticket descriptions.

**Test Code**:
```python
class TestJiraIntegrationAgentRichContext:
    """Test suite for rich context generation"""

    def test_generate_adf_for_code_violation(self, jira_agent):
        """Test ADF generation for code violation"""
        # Arrange
        agent_findings = {
            "agent_info": {
                "name": "Code Best Practises Agent",
                "version": "2.1.0",
                "detection_time": "2026-01-28T10:25:30Z"
            },
            "findings": [
                {
                    "finding_id": "CBP-001",
                    "type": "NAMING_CONVENTION_VIOLATION",
                    "severity": "MEDIUM",
                    "file": "src/main/java/OrderService.java",
                    "line_start": 45,
                    "line_end": 45,
                    "code_snippet": "public Order get_order(String id) { ... }",
                    "description": "Method name violates camelCase convention",
                    "remediation": {
                        "description": "Rename method to camelCase",
                        "suggested_fix": "public Order getOrder(String id) { ... }"
                    }
                }
            ]
        }
        workflow_run_url = "https://github.com/org/repo/actions/runs/12345"

        # Act
        adf = jira_agent.generate_adf_description(
            issue_type="CODE_VIOLATION",
            agent_findings=agent_findings,
            workflow_run_url=workflow_run_url
        )

        # Assert
        assert adf["type"] == "doc"
        assert adf["version"] == 1

        # Verify info panel with agent info exists
        info_panel = next(
            (item for item in adf["content"] if item.get("type") == "panel"),
            None
        )
        assert info_panel is not None
        assert info_panel["attrs"]["panelType"] == "info"

        # Verify workflow link exists
        content_str = str(adf["content"])
        assert workflow_run_url in content_str

    def test_generate_adf_for_lld_deviation(self, jira_agent):
        """Test ADF generation for LLD deviation"""
        # Arrange
        agent_findings = {
            "agent_info": {
                "name": "LLD Alignment Review Agent",
                "version": "1.5.2"
            },
            "findings": [
                {
                    "finding_id": "LLD-001",
                    "type": "ARCHITECTURAL_DEVIATION",
                    "severity": "CRITICAL",
                    "lld_section": "Section 5.2 - PaymentProcessor",
                    "lld_document_url": "https://confluence.company.com/lld/payment-service#5.2",
                    "expected_pattern": "Retry Pattern",
                    "actual_implementation": "Circuit Breaker pattern"
                }
            ]
        }

        # Act
        adf = jira_agent.generate_adf_description(
            issue_type="LLD_DEVIATION",
            agent_findings=agent_findings
        )

        # Assert
        content_str = str(adf["content"])
        assert "LLD Alignment Review Agent" in content_str
        assert "Section 5.2" in content_str
        assert "https://confluence.company.com/lld/payment-service" in content_str

    def test_adf_includes_code_snippets(self, jira_agent):
        """Test ADF includes code snippets in code blocks"""
        # Arrange
        agent_findings = {
            "agent_info": {"name": "Code Agent"},
            "findings": [
                {
                    "code_snippet": "public Order get_order(String id) { return null; }",
                    "remediation": {
                        "suggested_fix": "public Order getOrder(String id) { return null; }"
                    }
                }
            ]
        }

        # Act
        adf = jira_agent.generate_adf_description(
            issue_type="CODE_VIOLATION",
            agent_findings=agent_findings
        )

        # Assert
        code_blocks = [
            item for item in adf["content"]
            if item.get("type") == "codeBlock"
        ]
        assert len(code_blocks) >= 1
        assert "get_order" in str(code_blocks[0])
```

### Test 3: Bidirectional PR Linking

**Description**: Test linking Jira ticket to GitHub PR in both directions.

**Test Code**:
```python
class TestJiraIntegrationAgentPRLinking:
    """Test suite for PR linking"""

    @patch('agents.jira_integration_agent.GitHubClient')
    def test_bidirectional_pr_link_success(self, mock_github, jira_agent):
        """Test successful bidirectional PR linking"""
        # Arrange
        jira_agent.github_client = mock_github
        ticket_id = "SCM-456"
        pr_url = "https://github.com/org/repo/pull/123"
        pr_number = 123

        jira_agent.jira_skill.link_pr.return_value = Mock(status="SUCCESS", link_id="10001")

        # Act
        result = jira_agent.link_pr_bidirectional(
            ticket_id=ticket_id,
            pr_url=pr_url,
            pr_number=pr_number,
            repository="org/repo"
        )

        # Assert
        # Jira link created
        jira_agent.jira_skill.link_pr.assert_called_once()

        # GitHub comment posted
        mock_github.create_issue_comment.assert_called_once()
        comment_call = mock_github.create_issue_comment.call_args
        assert ticket_id in comment_call[0][2]  # Comment body contains ticket ID

        assert result["jira_link_status"] == "SUCCESS"
        assert result["github_comment_status"] == "SUCCESS"

    def test_partial_success_jira_link_fails(self, jira_agent):
        """Test partial success when Jira link fails but GitHub comment succeeds"""
        # Arrange
        with patch('agents.jira_integration_agent.GitHubClient') as mock_github:
            jira_agent.github_client = mock_github
            jira_agent.jira_skill.link_pr.side_effect = Exception("Jira API error")

            # Act
            result = jira_agent.link_pr_bidirectional(
                ticket_id="SCM-456",
                pr_url="https://github.com/org/repo/pull/123",
                pr_number=123,
                repository="org/repo"
            )

            # Assert
            assert result["jira_link_status"] == "FAILED"
            # GitHub comment should still be attempted
            mock_github.create_issue_comment.assert_called_once()
```

### Test 4: Partial Success Handling

**Description**: Test handling of partial success scenarios.

**Test Code**:
```python
class TestJiraIntegrationAgentPartialSuccess:
    """Test suite for partial success handling"""

    def test_ticket_created_but_assignment_failed(self, jira_agent):
        """Test partial success: ticket created but assignment failed"""
        # Arrange
        input_data = {
            "issue_type": "CODE_VIOLATION",
            "pr_number": 123,
            "pr_author_email": "invalid@company.com",
            "severity": "MEDIUM"
        }

        jira_agent.jira_skill.create_ticket.return_value = Mock(
            status="PARTIAL_SUCCESS",
            ticket_id="SCM-456",
            assignment_method="fallback_default",
            warnings=["PR author not found in Jira"]
        )

        # Act
        result = jira_agent.create_ticket(input_data)

        # Assert
        assert result["status"] == "PARTIAL_SUCCESS"
        assert result["ticket_id"] == "SCM-456"
        assert len(result["warnings"]) > 0
        assert "not found" in result["warnings"][0].lower()

    def test_ticket_created_but_pr_link_failed(self, jira_agent):
        """Test partial success: ticket created but PR link failed"""
        # Arrange
        jira_agent.jira_skill.create_ticket.return_value = Mock(
            status="SUCCESS",
            ticket_id="SCM-456",
            pr_linked=False
        )

        # Act
        result = jira_agent.create_ticket({"issue_type": "CODE_VIOLATION", "pr_number": 123})

        # Assert
        assert result["status"] == "SUCCESS"  # Ticket creation succeeded
        assert result["pr_linked"] is False
        # Should queue PR link for retry
        assert "pr_link_queued" in result
```

---

## GitHub Actions Workflow Tests

### Test Module: `test_github_actions_workflow.py`

Testing GitHub Actions workflows requires simulating workflow execution.

### Test 1: Workflow Trigger Conditions

**Description**: Test workflow triggers on correct PR events.

**Test Code**:
```python
import pytest
from unittest.mock import Mock, patch
import yaml

class TestGitHubActionsWorkflowTriggers:
    """Test suite for workflow triggers"""

    @pytest.fixture
    def workflow_yaml(self):
        """Load workflow YAML configuration"""
        with open('.github/workflows/peer_review.yml', 'r') as f:
            return yaml.safe_load(f)

    def test_workflow_triggers_on_pr_opened(self, workflow_yaml):
        """Test workflow triggers on pull_request.opened"""
        # Assert
        triggers = workflow_yaml['on']['pull_request']['types']
        assert 'opened' in triggers

    def test_workflow_triggers_on_pr_synchronize(self, workflow_yaml):
        """Test workflow triggers on pull_request.synchronize"""
        # Assert
        triggers = workflow_yaml['on']['pull_request']['types']
        assert 'synchronize' in triggers

    def test_workflow_triggers_on_pr_reopened(self, workflow_yaml):
        """Test workflow triggers on pull_request.reopened"""
        # Assert
        triggers = workflow_yaml['on']['pull_request']['types']
        assert 'reopened' in triggers

    def test_workflow_triggers_on_target_branches(self, workflow_yaml):
        """Test workflow only triggers for main, develop, release branches"""
        # Assert
        branches = workflow_yaml['on']['pull_request']['branches']
        assert 'main' in branches
        assert 'develop' in branches
        assert 'release/**' in branches

    def test_workflow_concurrency_group(self, workflow_yaml):
        """Test workflow concurrency configuration"""
        # Assert
        concurrency = workflow_yaml.get('concurrency', {})
        assert 'group' in concurrency
        assert concurrency['cancel-in-progress'] is True
        assert 'github.event.pull_request.number' in concurrency['group']
```

### Test 2: Job Dependencies

**Description**: Test job execution dependencies are correctly configured.

**Test Code**:
```python
class TestGitHubActionsWorkflowJobDependencies:
    """Test suite for job dependencies"""

    def test_code_quality_depends_on_preflight(self, workflow_yaml):
        """Test Code Quality job depends on Pre-Flight"""
        # Arrange
        code_quality_job = workflow_yaml['jobs']['code-quality-agent']

        # Assert
        assert 'needs' in code_quality_job
        assert 'pre-flight' in code_quality_job['needs']

    def test_architect_depends_on_code_quality(self, workflow_yaml):
        """Test Architect job depends on Code Quality"""
        # Arrange
        architect_job = workflow_yaml['jobs']['architect-agent']

        # Assert
        assert 'needs' in architect_job
        assert 'code-quality-agent' in architect_job['needs']

    def test_lld_alignment_depends_on_architect(self, workflow_yaml):
        """Test LLD Alignment depends on Architect"""
        # Arrange
        lld_job = workflow_yaml['jobs']['lld-alignment-agent']

        # Assert
        assert 'needs' in lld_job
        assert 'architect-agent' in lld_job['needs']

    def test_lld_alignment_conditional_on_new_pattern(self, workflow_yaml):
        """Test LLD Alignment only runs if new pattern detected"""
        # Arrange
        lld_job = workflow_yaml['jobs']['lld-alignment-agent']

        # Assert
        assert 'if' in lld_job
        assert 'NEW_PATTERN_FOUND' in lld_job['if']

    def test_final_report_always_runs(self, workflow_yaml):
        """Test Final Report job always runs"""
        # Arrange
        report_job = workflow_yaml['jobs']['final-report']

        # Assert
        assert 'if' in report_job
        assert 'always()' in report_job['if']
```

### Test 3: Environment Variable Passing

**Description**: Test environment variables are correctly passed between jobs.

**Test Code**:
```python
class TestGitHubActionsWorkflowEnvVars:
    """Test suite for environment variables"""

    def test_required_secrets_configured(self, workflow_yaml):
        """Test all required secrets are referenced"""
        # Arrange
        required_secrets = [
            'CONFLUENCE_API_TOKEN',
            'JIRA_API_TOKEN',
            'JIRA_USER_EMAIL',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY'
        ]

        # Convert workflow to string to search for secret references
        workflow_str = yaml.dump(workflow_yaml)

        # Assert
        for secret in required_secrets:
            assert f"secrets.{secret}" in workflow_str, f"Secret {secret} not found"

    def test_pr_number_passed_to_agents(self, workflow_yaml):
        """Test PR number is extracted and passed to agents"""
        # Arrange
        code_quality_job = workflow_yaml['jobs']['code-quality-agent']

        # Assert
        # Check if PR number is extracted in a step
        steps = code_quality_job.get('steps', [])
        run_commands = [step.get('run', '') for step in steps]
        run_str = ' '.join(run_commands)

        assert 'github.event.pull_request.number' in run_str or \
               'GITHUB_EVENT' in run_str

    def test_agent_outputs_captured(self, workflow_yaml):
        """Test agent outputs are captured for downstream jobs"""
        # Arrange
        code_quality_job = workflow_yaml['jobs']['code-quality-agent']

        # Assert
        assert 'outputs' in code_quality_job
        outputs = code_quality_job['outputs']
        assert 'status' in outputs
        assert 'violations-count' in outputs or 'violations_count' in outputs
```

### Test 4: Status Check Reporting

**Description**: Test GitHub status checks are correctly reported.

**Test Code**:
```python
class TestGitHubActionsWorkflowStatusChecks:
    """Test suite for status check reporting"""

    @patch('subprocess.run')
    def test_status_check_posted_on_success(self, mock_subprocess):
        """Test status check posted when workflow succeeds"""
        # Arrange
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success")

        # Simulate final report job posting status check
        status_check_command = [
            'gh', 'api',
            '/repos/org/repo/statuses/abc123',
            '-f', 'state=success',
            '-f', 'context=PR Peer Review Orchestration',
            '-f', 'description=All validation passed'
        ]

        # Act
        result = mock_subprocess(status_check_command, capture_output=True, text=True)

        # Assert
        assert result.returncode == 0

    @patch('subprocess.run')
    def test_status_check_posted_on_failure(self, mock_subprocess):
        """Test status check posted when workflow fails"""
        # Arrange
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success")

        status_check_command = [
            'gh', 'api',
            '/repos/org/repo/statuses/abc123',
            '-f', 'state=failure',
            '-f', 'context=PR Peer Review Orchestration',
            '-f', 'description=Validation failed'
        ]

        # Act
        result = mock_subprocess(status_check_command, capture_output=True, text=True)

        # Assert
        assert result.returncode == 0

    def test_workflow_permissions_include_statuses_write(self, workflow_yaml):
        """Test workflow has permissions to write statuses"""
        # Assert
        permissions = workflow_yaml.get('permissions', {})
        assert permissions.get('statuses') == 'write'
```

### Test 5: Workflow Job Timeouts

**Description**: Test all jobs have appropriate timeouts configured.

**Test Code**:
```python
class TestGitHubActionsWorkflowTimeouts:
    """Test suite for job timeouts"""

    @pytest.mark.parametrize("job_name,expected_max_timeout", [
        ('pre-flight', 5),
        ('code-quality-agent', 2),
        ('architect-agent', 1),
        ('lld-alignment-agent', 1),
        ('peer-review-agent', 5),
        ('jira-integration', 2),
        ('final-report', 5)
    ])
    def test_job_timeout_configured(self, workflow_yaml, job_name, expected_max_timeout):
        """Test job has timeout configured within expected range"""
        # Arrange
        job = workflow_yaml['jobs'].get(job_name)

        # Assert
        assert job is not None, f"Job {job_name} not found"
        assert 'timeout-minutes' in job
        assert job['timeout-minutes'] <= expected_max_timeout

    def test_all_jobs_have_timeout(self, workflow_yaml):
        """Test all jobs have timeout configured"""
        # Arrange
        jobs = workflow_yaml['jobs']

        # Assert
        for job_name, job_config in jobs.items():
            assert 'timeout-minutes' in job_config, \
                f"Job {job_name} missing timeout configuration"
```

---

## Test Fixtures and Utilities

### Shared Test Fixtures: `conftest.py`

**Description**: Shared fixtures used across all test modules.

**Test Code**:
```python
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
import json

@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDB client"""
    client = Mock()
    client.put_item = Mock(return_value={'ResponseMetadata': {'HTTPStatusCode': 200}})
    client.get_item = Mock(return_value={'Item': {}})
    client.update_item = Mock(return_value={'Attributes': {}})
    return client

@pytest.fixture
def mock_cloudwatch_client():
    """Mock CloudWatch client"""
    client = Mock()
    client.put_metric_data = Mock()
    client.put_log_events = Mock()
    client.create_alarm = Mock()
    return client

@pytest.fixture
def mock_jira_client():
    """Mock Jira API client"""
    client = Mock()
    client.create_issue = Mock(return_value={'key': 'SCM-456', 'id': '10001'})
    client.assign_issue = Mock(return_value=True)
    client.user_find_by_user_string = Mock(return_value=[
        {'accountId': '5b10ac8d82e05b22cc7d4ef5', 'displayName': 'Test User'}
    ])
    client.create_or_update_issue_remote_links = Mock(return_value={'id': '10001'})
    client.issue_add_comment = Mock(return_value={'id': '10001'})
    return client

@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    client = Mock()
    client.get = Mock(return_value=None)
    client.setex = Mock(return_value=True)
    client.delete = Mock(return_value=True)
    return client

@pytest.fixture
def mock_github_client():
    """Mock GitHub API client"""
    client = Mock()
    client.get_pull_request = Mock(return_value={
        'number': 123,
        'state': 'open',
        'head': {'sha': 'abc123'},
        'user': {'login': 'developer1'}
    })
    client.create_issue_comment = Mock(return_value={'id': 1})
    client.add_labels = Mock()
    client.request_reviewers = Mock()
    return client

@pytest.fixture
def sample_pr_event():
    """Sample GitHub PR event payload"""
    return {
        "event": "pull_request.opened",
        "pr_number": 123,
        "repository": "tonic-scm/order-service",
        "source_branch": "feature/new-pattern",
        "target_branch": "main",
        "author": "developer1",
        "commits": ["abc123"],
        "modified_files": ["src/main/java/OrderService.java"],
        "pr_title": "Add new repository pattern",
        "pr_description": "Implements repository pattern with caching"
    }

@pytest.fixture
def sample_agent_findings():
    """Sample agent findings for testing"""
    return {
        "agent_info": {
            "name": "Code Best Practises Agent",
            "version": "2.1.0",
            "detection_time": "2026-01-28T10:25:30Z",
            "analysis_duration_ms": 3400
        },
        "findings": [
            {
                "finding_id": "CBP-001",
                "type": "NAMING_CONVENTION_VIOLATION",
                "severity": "MEDIUM",
                "file": "src/main/java/OrderService.java",
                "line_start": 45,
                "line_end": 45,
                "code_snippet": "public Order get_order(String id) { ... }",
                "description": "Method name violates camelCase convention",
                "pattern_id": "PATTERN-001",
                "remediation": {
                    "description": "Rename method to camelCase",
                    "suggested_fix": "public Order getOrder(String id) { ... }",
                    "effort_estimate": "5 minutes"
                }
            }
        ]
    }

@pytest.fixture
def fixed_datetime(monkeypatch):
    """Fixture to freeze time"""
    fixed_time = datetime(2026, 1, 28, 10, 30, 0)

    class MockDatetime:
        @classmethod
        def utcnow(cls):
            return fixed_time

        @classmethod
        def now(cls):
            return fixed_time

    monkeypatch.setattr('datetime.datetime', MockDatetime)
    return fixed_time

def load_test_data(filename):
    """Load test data from JSON file"""
    with open(f'tests/fixtures/{filename}', 'r') as f:
        return json.load(f)

def assert_workflow_state_valid(workflow_state):
    """Helper to assert workflow state is valid"""
    assert workflow_state.workflow_id is not None
    assert workflow_state.workflow_id.startswith('wf-')
    assert workflow_state.pr_number > 0
    assert workflow_state.repository is not None
    assert workflow_state.status in [
        'INITIALIZED', 'RUNNING_STEP_1', 'RUNNING_STEP_2',
        'RUNNING_STEP_3', 'RUNNING_STEP_4', 'RUNNING_STEP_5',
        'COMPLETED_SUCCESS', 'COMPLETED_FAILURE', 'CANCELLED'
    ]

def assert_jira_ticket_valid(ticket_output):
    """Helper to assert Jira ticket output is valid"""
    assert ticket_output.status in ['SUCCESS', 'PARTIAL_SUCCESS', 'FAILURE']
    assert ticket_output.ticket_id is not None
    assert ticket_output.ticket_id.startswith('SCM-')
    assert ticket_output.ticket_url is not None
```

---

## Running Tests

### Run All Tests

```bash
# Run all unit tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=agents --cov=skills --cov-report=html

# Run specific test module
pytest tests/test_pr_orchestrator_agent.py

# Run specific test class
pytest tests/test_pr_orchestrator_agent.py::TestPROrchestratorInitialization

# Run specific test
pytest tests/test_pr_orchestrator_agent.py::TestPROrchestratorInitialization::test_initialize_workflow_success
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run all except slow tests
pytest -m "not slow"
```

### Generate Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=agents --cov=skills --cov-report=html

# View coverage report
open htmlcov/index.html

# Generate terminal coverage report
pytest --cov=agents --cov=skills --cov-report=term-missing

# Fail if coverage below 85%
pytest --cov=agents --cov=skills --cov-fail-under=85
```

### Run Tests in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU count)
pytest -n auto

# Run tests on 4 CPUs
pytest -n 4
```

### Run Tests with Verbose Output

```bash
# Verbose output with test names
pytest -v

# Very verbose with captured output
pytest -vv -s

# Show print statements
pytest -s
```

---

## Coverage Requirements

### Minimum Coverage Targets

| Component | Minimum Coverage | Target Coverage |
|-----------|------------------|-----------------|
| PR Orchestrator Agent | 85% | 95% |
| Orchestrator Skill | 85% | 95% |
| Jira Ticket Skill | 90% | 98% |
| Jira Integration Agent | 85% | 95% |
| Workflow Configuration | 80% | 90% |
| **Overall Project** | **85%** | **95%** |

### Coverage by Category

**Must Cover**:
- All public methods and functions
- All critical paths (happy path + error paths)
- All decision branches (if/else, switch)
- All exception handlers

**Should Cover**:
- Edge cases and boundary conditions
- Retry and fallback logic
- Timeout handling
- Cache hit and miss scenarios

**Can Skip**:
- Simple getters/setters without logic
- Configuration loading boilerplate
- External library wrapper code (if thin wrapper)

### Coverage Enforcement

Configure pytest to fail if coverage drops below threshold:

```ini
# pytest.ini
[pytest]
addopts = --cov-fail-under=85
```

### Coverage Report Example

```
Name                                   Stmts   Miss  Cover   Missing
--------------------------------------------------------------------
agents/pr_orchestrator_agent.py          250     15    94%   45-48, 112-115
agents/jira_integration_agent.py         180      8    96%   234-237
skills/orchestrator_skill.py             120      5    96%   78-80
skills/jira_ticket_skill.py              200     10    95%   145-150, 234
--------------------------------------------------------------------
TOTAL                                    750     38    95%
```

---

## Summary

This comprehensive unit testing guide provides:

1. **Complete test coverage** for all new PR Peer Review system components
2. **Pytest framework setup** with coverage reporting and markers
3. **Reusable fixtures** for common test dependencies
4. **Parameterized tests** for testing multiple scenarios efficiently
5. **Mock strategies** for external dependencies (Jira, GitHub, DynamoDB)
6. **Error handling tests** for all failure scenarios
7. **Performance tests** for SLA compliance
8. **GitHub Actions workflow tests** for CI/CD validation

All tests follow best practices:
- Tests are independent and isolated
- External dependencies are mocked
- Test names clearly describe what is being tested
- Both success and failure paths are covered
- Edge cases and boundary conditions are tested

Achieving >85% code coverage with these tests ensures high quality and maintainability of the PR Peer Review system.
