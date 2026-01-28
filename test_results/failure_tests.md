# Failure Scenarios Testing Guide

**Version**: 1.0
**Date**: 2026-01-28
**Project**: Tonic PR Peer Review Orchestration System

---

## 1. Overview

This document provides comprehensive failure scenario testing for the PR Peer Review system. It covers agent failures, external service failures, network issues, and recovery mechanisms.

---

## 2. Agent Failure Scenarios

### 2.1 Code Best Practices Agent Violations

**Scenario**: Code violations detected in PR.

**How to Simulate**:
```python
# Create PR with known violations
pr_data = {
    "pr_number": 123,
    "repository": "test-repo",
    "files_changed": ["src/BadCode.java"]  # File with naming violations
}
```

**Expected Behavior**:
- Pipeline continues to Architect Agent
- Violations aggregated in final report
- If severity > threshold: Jira ticket created
- PR comment posted with violation details

**Test Code**:
```python
@pytest.mark.failure
def test_code_violations_trigger_jira_ticket(orchestrator, mock_jira):
    """Test that code violations create Jira ticket."""
    # Arrange
    agent_result = AgentResult(
        agent_name="Code Best Practices Agent",
        status="FAILED",
        findings=[
            Finding(
                type="NAMING_CONVENTION",
                severity="HIGH",
                file="src/OrderService.java",
                line=45,
                description="Class name does not follow convention"
            )
        ]
    )

    # Act
    result = orchestrator.handle_agent_failure(agent_result)

    # Assert
    assert result.jira_ticket_created == True
    assert result.ticket_key.startswith("SCM-")
    mock_jira.create_ticket.assert_called_once()
```

### 2.2 Architect Agent - New Pattern Detection

**Scenario**: Architect detects new pattern requiring LLD review.

**Expected Behavior**:
- LLD Alignment Agent triggered (conditional execution)
- Pattern details passed to LLD Agent
- If LLD misaligned: Jira ticket created

**Test Code**:
```python
@pytest.mark.failure
def test_new_pattern_triggers_lld_review(orchestrator):
    """Test new pattern detection triggers LLD alignment check."""
    architect_result = AgentResult(
        agent_name="Architect Best Practices Agent",
        status="PASSED",
        new_pattern_detected=True,
        pattern_details={
            "name": "CircuitBreakerPattern",
            "file": "src/resilience/CircuitBreaker.java",
            "confidence": 0.95
        }
    )

    next_agent = orchestrator.determine_next_agent(architect_result)

    assert next_agent == "LLD Alignment Review Agent"
    assert orchestrator.state.lld_check_required == True
```

### 2.3 LLD Alignment Agent - Deviation Detected

**Scenario**: Implementation deviates from LLD specification.

**Expected Jira Ticket Content**:
```json
{
    "summary": "LLD deviation in PR #123 (order-service)",
    "issue_type": "LLD Deviation",
    "severity": "HIGH",
    "description": {
        "expected": "Use Repository pattern per LLD Section 4.2",
        "actual": "Direct database access in service layer",
        "impact": "Violates separation of concerns",
        "lld_document_url": "https://confluence/lld-123"
    }
}
```

**Test Code**:
```python
@pytest.mark.failure
def test_lld_deviation_creates_detailed_ticket(jira_agent, mock_jira):
    """Test LLD deviation creates ticket with full context."""
    deviation = {
        "finding_id": "LLD-001",
        "lld_section": "Section 4.2 - Data Access Layer",
        "expected_pattern": "Repository Pattern",
        "actual_implementation": "Direct DAO access",
        "file": "src/services/OrderService.java",
        "line_start": 45,
        "line_end": 67
    }

    result = jira_agent.create_ticket_for_deviation(deviation)

    # Verify rich context in ticket
    call_args = mock_jira.create_issue.call_args
    description = call_args.kwargs["fields"]["description"]

    assert "Section 4.2" in str(description)
    assert "Repository Pattern" in str(description)
    assert "OrderService.java" in str(description)
```

### 2.4 Multiple Agent Failures

**Scenario**: Multiple agents detect issues in same PR.

**Expected Behavior**:
- Single Jira ticket with all findings
- Grouped by agent in ticket description
- PR comment summarizes all issues

**Test Code**:
```python
@pytest.mark.failure
def test_multiple_failures_single_ticket(orchestrator, mock_jira):
    """Test multiple agent failures create single comprehensive ticket."""
    failures = [
        AgentResult(agent_name="Code Best Practices", status="FAILED",
                   findings=[{"type": "NAMING", "count": 3}]),
        AgentResult(agent_name="LLD Alignment", status="FAILED",
                   findings=[{"type": "DEVIATION", "count": 1}])
    ]

    result = orchestrator.aggregate_and_create_ticket(failures)

    # Single ticket created
    assert mock_jira.create_issue.call_count == 1

    # Both failures in description
    description = mock_jira.create_issue.call_args.kwargs["fields"]["description"]
    assert "Code Best Practices" in str(description)
    assert "LLD Alignment" in str(description)
```

---

## 3. Jira Ticket Creation on Failure

### 3.1 Ticket Creation for Each Failure Type

| Failure Type | Issue Type | Default Labels | Priority |
|--------------|------------|----------------|----------|
| Code Violation | Bug | code-quality, automated | Based on severity |
| LLD Deviation | Task | lld-deviation, architectural | High |
| Pattern Rejection | Story | pattern-review, needs-discussion | Medium |
| Pipeline Timeout | Bug | pipeline-failure, needs-investigation | Critical |

### 3.2 Auto-Assignment Fallback Chain Test

**Test Code**:
```python
@pytest.mark.failure
@pytest.mark.parametrize("scenario,expected_method", [
    ("email_found", "direct"),
    ("email_not_found_github_mapped", "github_mapped"),
    ("github_not_mapped_domain_pattern", "domain_pattern"),
    ("no_domain_match_component_owner", "fallback_component"),
    ("no_component_owner_default", "fallback_default"),
    ("no_default_configured", "unassigned"),
])
def test_assignment_fallback_chain(jira_skill, scenario, expected_method):
    """Test assignment fallback through all tiers."""
    # Configure mocks based on scenario
    configure_lookup_mocks(jira_skill, scenario)

    result = jira_skill.lookup_and_assign(
        ticket_key="SCM-123",
        pr_author_email="unknown@external.com",
        pr_author_github="unknown-user"
    )

    assert result.assignment_method == expected_method
```

### 3.3 Partial Success Handling

**Scenario**: Ticket created but assignment fails.

**Test Code**:
```python
@pytest.mark.failure
def test_partial_success_ticket_created_assignment_failed(jira_agent):
    """Test ticket creation succeeds even when assignment fails."""
    with patch.object(jira_agent.jira_skill, 'lookup_user') as mock_lookup:
        mock_lookup.side_effect = UserLookupError("User not found")

        result = jira_agent.create_ticket(
            issue_type="Code Violation",
            pr_author_email="nonexistent@company.com"
        )

        assert result.status == "PARTIAL_SUCCESS"
        assert result.ticket_id is not None  # Ticket was created
        assert result.assignment_method == "unassigned"
        assert "Assignment failed" in result.warnings[0]
```

---

## 4. External Service Failures

### 4.1 Jira API Unavailable

**How to Simulate**:
```python
@pytest.fixture
def jira_unavailable():
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://company.atlassian.net/rest/api/3/issue",
            status=503,
            json={"errorMessages": ["Service temporarily unavailable"]}
        )
        yield rsps
```

**Expected Behavior**:
- Request queued to SQS retry queue
- Pipeline marked as "PARTIAL_FAILURE"
- CloudWatch alarm triggered
- PR comment indicates Jira issue pending

**Test Code**:
```python
@pytest.mark.failure
def test_jira_unavailable_queues_retry(jira_skill, mock_sqs):
    """Test Jira unavailability queues message for retry."""
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, JIRA_API_URL, status=503)

        result = jira_skill.create_ticket(CreateTicketInput(...))

        assert result.status == "FAILURE"
        assert result.error_code == "JIRA_UNAVAILABLE"

        # Verify SQS message queued
        mock_sqs.send_message.assert_called_once()
        message = json.loads(mock_sqs.send_message.call_args.kwargs["MessageBody"])
        assert message["operation"] == "create_ticket"
        assert message["retry_count"] == 0
```

### 4.2 Jira Rate Limit Exceeded

**Test Code**:
```python
@pytest.mark.failure
def test_jira_rate_limit_backoff(jira_skill):
    """Test rate limit triggers exponential backoff."""
    with responses.RequestsMock() as rsps:
        # First request: rate limited
        rsps.add(
            responses.POST, JIRA_API_URL,
            status=429,
            headers={"Retry-After": "60"}
        )
        # Second request: success
        rsps.add(
            responses.POST, JIRA_API_URL,
            status=201,
            json={"key": "SCM-123"}
        )

        result = jira_skill.create_ticket(CreateTicketInput(...))

        assert result.status == "SUCCESS"
        assert len(rsps.calls) == 2
```

### 4.3 GitHub API Failures

**Test Code**:
```python
@pytest.mark.failure
def test_github_comment_failure_non_blocking(orchestrator, mock_github):
    """Test GitHub comment failure doesn't block pipeline."""
    mock_github.create_comment.side_effect = GitHubAPIError("API Error")

    result = orchestrator.post_pr_results(
        pr_number=123,
        results={"status": "PASSED"}
    )

    # Pipeline continues despite comment failure
    assert result.pipeline_status == "COMPLETED"
    assert result.pr_comment_posted == False
    assert "GitHub comment failed" in result.warnings
```

### 4.4 DynamoDB Throttling

**Test Code**:
```python
@pytest.mark.failure
def test_dynamodb_throttling_retry(state_manager, mock_dynamodb):
    """Test DynamoDB throttling triggers retry with backoff."""
    mock_dynamodb.put_item.side_effect = [
        ClientError({"Error": {"Code": "ProvisionedThroughputExceededException"}}, "PutItem"),
        ClientError({"Error": {"Code": "ProvisionedThroughputExceededException"}}, "PutItem"),
        {"ResponseMetadata": {"HTTPStatusCode": 200}}  # Success on 3rd try
    ]

    result = state_manager.save_state(pipeline_id="test-123", state={})

    assert result.success == True
    assert mock_dynamodb.put_item.call_count == 3
```

### 4.5 Redis Cache Unavailable

**Test Code**:
```python
@pytest.mark.failure
def test_redis_unavailable_fallback_to_api(jira_skill, mock_redis):
    """Test Redis failure falls back to direct API lookup."""
    mock_redis.get.side_effect = ConnectionError("Redis unavailable")

    with patch.object(jira_skill, '_lookup_user_from_api') as mock_api:
        mock_api.return_value = {"account_id": "123", "display_name": "Dev"}

        result = jira_skill.lookup_user(email="dev@company.com")

        assert result.status == "SUCCESS"
        assert result.cached == False
        mock_api.assert_called_once()
```

---

## 5. Network and Timeout Failures

### 5.1 Agent Execution Timeout

**Test Code**:
```python
@pytest.mark.failure
@pytest.mark.asyncio
async def test_agent_timeout_handling(orchestrator):
    """Test agent timeout triggers failure handling."""
    async def slow_agent(*args, **kwargs):
        await asyncio.sleep(120)  # Exceed 60s timeout
        return AgentResult(status="PASSED")

    with patch.object(orchestrator, 'execute_agent', slow_agent):
        result = await orchestrator.run_pipeline(pr_data={...})

        assert result.status == "FAILED"
        assert result.failure_reason == "AGENT_TIMEOUT"
        assert "Code Best Practices Agent" in result.failed_agent
```

### 5.2 Pipeline Timeout Handling

**Test Code**:
```python
@pytest.mark.failure
def test_pipeline_timeout_creates_ticket(orchestrator, mock_jira):
    """Test pipeline timeout creates investigation ticket."""
    orchestrator.config.pipeline_timeout_seconds = 5

    with patch.object(orchestrator, 'execute_pipeline') as mock_exec:
        mock_exec.side_effect = PipelineTimeoutError("Pipeline exceeded 5s")

        result = orchestrator.run_with_timeout(pr_data={...})

        assert result.status == "TIMEOUT"
        assert mock_jira.create_ticket.called

        ticket_data = mock_jira.create_ticket.call_args.kwargs
        assert ticket_data["issue_type"] == "Bug"
        assert "timeout" in ticket_data["labels"]
```

### 5.3 GitHub Webhook Retry Scenarios

**Test Code**:
```python
@pytest.mark.failure
def test_webhook_idempotency(orchestrator):
    """Test duplicate webhook doesn't create duplicate pipeline."""
    webhook_id = "gh-webhook-12345"

    # First webhook
    result1 = orchestrator.handle_webhook(webhook_id=webhook_id, event="pull_request")

    # Duplicate webhook (GitHub retry)
    result2 = orchestrator.handle_webhook(webhook_id=webhook_id, event="pull_request")

    assert result1.pipeline_id == result2.pipeline_id
    assert result2.status == "ALREADY_PROCESSED"
```

---

## 6. Recovery and Retry Tests

### 6.1 SQS Retry Queue Processing

**Test Code**:
```python
@pytest.mark.failure
def test_sqs_retry_processing(retry_handler, mock_sqs, mock_jira):
    """Test SQS retry queue processes failed operations."""
    # Setup: Failed ticket creation in queue
    message = {
        "operation": "create_ticket",
        "input": {"summary": "Test ticket", "pr_number": 123},
        "retry_count": 1,
        "original_error": "JIRA_UNAVAILABLE"
    }
    mock_sqs.receive_message.return_value = {
        "Messages": [{"Body": json.dumps(message), "ReceiptHandle": "handle-1"}]
    }

    # Jira now available
    mock_jira.create_issue.return_value = {"key": "SCM-456"}

    result = retry_handler.process_retry_queue()

    assert result.processed_count == 1
    assert result.success_count == 1
    mock_sqs.delete_message.assert_called_once()
```

### 6.2 Exponential Backoff Verification

**Test Code**:
```python
@pytest.mark.failure
@pytest.mark.parametrize("retry_count,expected_delay", [
    (0, 5),    # 5 seconds
    (1, 15),   # 15 seconds
    (2, 60),   # 1 minute
    (3, 240),  # 4 minutes
    (4, 1440), # 24 minutes (capped)
])
def test_exponential_backoff_delays(retry_handler, retry_count, expected_delay):
    """Test exponential backoff delay calculation."""
    delay = retry_handler.calculate_backoff_delay(retry_count)
    assert delay == expected_delay
```

### 6.3 Dead Letter Queue Handling

**Test Code**:
```python
@pytest.mark.failure
def test_dlq_after_max_retries(retry_handler, mock_sqs):
    """Test message moves to DLQ after max retries."""
    message = {
        "operation": "create_ticket",
        "retry_count": 5,  # Max retries exceeded
        "input": {...}
    }

    result = retry_handler.handle_message(message)

    assert result.moved_to_dlq == True
    mock_sqs.send_message.assert_called_with(
        QueueUrl=DLQ_URL,
        MessageBody=ANY
    )
```

### 6.4 Pipeline State Recovery

**Test Code**:
```python
@pytest.mark.failure
def test_pipeline_recovery_after_crash(orchestrator, mock_dynamodb):
    """Test pipeline resumes from last checkpoint after crash."""
    # Setup: Pipeline crashed after Code Best Practices
    saved_state = {
        "pipeline_id": "pipe-123",
        "pr_number": 456,
        "current_stage": "architect_agent",
        "completed_agents": ["code_best_practices"],
        "agent_results": {...}
    }
    mock_dynamodb.get_item.return_value = {"Item": saved_state}

    result = orchestrator.recover_pipeline("pipe-123")

    assert result.resumed_from == "architect_agent"
    assert "code_best_practices" not in result.agents_executed  # Not re-run
```

---

## 7. Chaos Engineering Tests

### 7.1 Random Service Failure Injection

**Test Code**:
```python
@pytest.mark.chaos
def test_random_service_failures(orchestrator):
    """Test system resilience under random failures."""
    from chaos_monkey import ChaosMonkey

    chaos = ChaosMonkey(
        failure_rate=0.3,  # 30% failure rate
        services=["jira", "confluence", "dynamodb"]
    )

    with chaos.enabled():
        results = []
        for i in range(100):
            try:
                result = orchestrator.run_pipeline(pr_data=sample_pr_data())
                results.append(result)
            except Exception as e:
                results.append({"status": "ERROR", "error": str(e)})

        # At least 60% should complete (graceful degradation)
        success_rate = sum(1 for r in results if r.get("status") != "ERROR") / len(results)
        assert success_rate >= 0.6
```

### 7.2 Network Partition Simulation

**Test Code**:
```python
@pytest.mark.chaos
def test_network_partition_recovery(orchestrator, network_simulator):
    """Test recovery after network partition."""
    # Start pipeline
    pipeline_future = orchestrator.run_pipeline_async(pr_data={...})

    # Simulate network partition during execution
    with network_simulator.partition(duration_seconds=10):
        time.sleep(5)  # Wait for partition to affect pipeline

    # Wait for pipeline completion
    result = pipeline_future.result(timeout=120)

    # Pipeline should complete (possibly with retries)
    assert result.status in ["COMPLETED", "PARTIAL_SUCCESS"]
```

---

## 8. Test Execution

### Running Failure Tests

```bash
# Run all failure tests
pytest tests/ -m failure -v

# Run specific failure category
pytest tests/ -m "failure and jira" -v
pytest tests/ -m "failure and timeout" -v

# Run chaos engineering tests (requires additional setup)
pytest tests/ -m chaos -v --chaos-enabled

# Generate failure test report
pytest tests/ -m failure --html=reports/failure_tests.html
```

### CI Integration

```yaml
# .github/workflows/failure-tests.yml
name: Failure Scenario Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  failure-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements-test.txt

      - name: Run failure tests
        run: pytest tests/ -m failure -v --junitxml=failure-results.xml

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: failure-test-results
          path: failure-results.xml
```

---

## 9. Failure Test Checklist

| Category | Test | Status |
|----------|------|--------|
| **Agent Failures** | | |
| | Code violations trigger Jira | [ ] |
| | New pattern triggers LLD check | [ ] |
| | LLD deviation creates ticket | [ ] |
| | Multiple failures single ticket | [ ] |
| **Jira Failures** | | |
| | Jira unavailable queues retry | [ ] |
| | Rate limit triggers backoff | [ ] |
| | Assignment fallback chain | [ ] |
| | Partial success handling | [ ] |
| **External Services** | | |
| | GitHub API failure non-blocking | [ ] |
| | DynamoDB throttling retry | [ ] |
| | Redis fallback to API | [ ] |
| **Timeouts** | | |
| | Agent timeout handling | [ ] |
| | Pipeline timeout creates ticket | [ ] |
| | Webhook idempotency | [ ] |
| **Recovery** | | |
| | SQS retry processing | [ ] |
| | Exponential backoff | [ ] |
| | DLQ after max retries | [ ] |
| | Pipeline state recovery | [ ] |

---

**End of Failure Testing Guide**
