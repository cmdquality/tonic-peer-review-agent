# Integration Testing Documentation: PR Peer Review System

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**Version**: 1.0
**Test Framework**: pytest with pytest-asyncio, pytest-mock

---

## Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Full Pipeline Integration Tests](#full-pipeline-integration-tests)
4. [Agent-to-Agent Integration Tests](#agent-to-agent-integration-tests)
5. [GitHub Actions Integration Tests](#github-actions-integration-tests)
6. [Jira Integration Tests](#jira-integration-tests)
7. [State Management Integration Tests](#state-management-integration-tests)
8. [Test Fixtures and Utilities](#test-fixtures-and-utilities)
9. [Running the Tests](#running-the-tests)
10. [CI/CD Integration](#cicd-integration)

---

## Overview

This document provides comprehensive integration testing strategies for the PR Peer Review Orchestration System. Integration tests validate end-to-end workflows, agent interactions, external service integrations, and state management across the entire system.

### Test Categories

- **Full Pipeline Tests**: End-to-end PR validation workflows
- **Agent-to-Agent Tests**: Inter-agent communication and handoffs
- **GitHub Actions Tests**: Workflow triggers and PR interactions
- **Jira Tests**: Ticket creation and bidirectional linking
- **State Management Tests**: DynamoDB persistence and Redis caching

### Test Coverage Goals

- **Pipeline Coverage**: 100% of workflow paths (happy path, violations, new patterns, failures)
- **Agent Integration**: 100% of agent handoff scenarios
- **Error Handling**: 100% of failure modes and recovery paths
- **API Integration**: All external service interactions

---

## Test Environment Setup

### Prerequisites

```bash
# Install Python dependencies
pip install pytest pytest-asyncio pytest-mock pytest-cov
pip install boto3 moto redis fakeredis
pip install requests-mock responses
pip install python-dotenv pyyaml

# Install AWS CLI for LocalStack
pip install awscli-local

# Install LocalStack for AWS service mocking
pip install localstack
```

### Environment Configuration

Create `.env.test` file:

```bash
# GitHub Configuration
GITHUB_TOKEN=test_github_token_12345
GITHUB_OWNER=tonic-scm
GITHUB_REPO=test-repo

# Confluence Configuration
CONFLUENCE_BASE_URL=https://test-confluence.atlassian.net
CONFLUENCE_API_TOKEN=test_confluence_token_12345
CONFLUENCE_SPACE_PATTERNS=SCM-PATTERNS
CONFLUENCE_SPACE_LLD=SCM-LLD

# Jira Configuration
JIRA_BASE_URL=https://test-jira.atlassian.net
JIRA_USER_EMAIL=automation@test.com
JIRA_API_TOKEN=test_jira_token_12345
JIRA_PROJECT=SCM
JIRA_DEFAULT_ASSIGNEE=test-lead@test.com

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
DYNAMODB_TABLE_NAME=pr-review-state-test
DYNAMODB_ENDPOINT=http://localhost:4566

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# Agent SLA Configuration
CODE_AGENT_SLA=30
ARCHITECT_AGENT_SLA=10
LLD_AGENT_SLA=20
PEER_REVIEW_SLA=14400
```

### Test Infrastructure Setup

```python
# tests/conftest.py
import pytest
import boto3
import redis
import os
from moto import mock_dynamodb
from fakeredis import FakeRedis
from dotenv import load_dotenv

# Load test environment variables
load_dotenv('.env.test')

@pytest.fixture(scope="session")
def aws_credentials():
    """Mock AWS credentials for testing."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'

@pytest.fixture(scope="function")
def dynamodb_table(aws_credentials):
    """Create mock DynamoDB table for testing."""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        table = dynamodb.create_table(
            TableName='pr-review-state-test',
            KeySchema=[
                {'AttributeName': 'pr_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pr_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield table

@pytest.fixture(scope="function")
def redis_client():
    """Create mock Redis client for testing."""
    client = FakeRedis(decode_responses=True)
    yield client
    client.flushall()

@pytest.fixture(scope="function")
def mock_github_api(requests_mock):
    """Mock GitHub API responses."""
    base_url = "https://api.github.com"

    # Mock PR data
    requests_mock.get(
        f"{base_url}/repos/tonic-scm/test-repo/pulls/123",
        json={
            "number": 123,
            "title": "Add authentication feature",
            "state": "open",
            "user": {"login": "developer1", "email": "dev1@test.com"},
            "base": {"ref": "main", "repo": {"name": "test-repo"}},
            "head": {"ref": "feature/auth", "sha": "abc123"},
            "html_url": "https://github.com/tonic-scm/test-repo/pull/123",
            "changed_files": 3,
            "additions": 150,
            "deletions": 20
        }
    )

    # Mock PR files
    requests_mock.get(
        f"{base_url}/repos/tonic-scm/test-repo/pulls/123/files",
        json=[
            {
                "filename": "src/auth/AuthService.java",
                "status": "added",
                "additions": 100,
                "deletions": 0,
                "patch": "@@ ... @@"
            }
        ]
    )

    # Mock PR comments
    requests_mock.post(
        f"{base_url}/repos/tonic-scm/test-repo/issues/123/comments",
        json={"id": 1, "body": "Test comment"}
    )

    yield requests_mock

@pytest.fixture(scope="function")
def mock_confluence_api(requests_mock):
    """Mock Confluence API responses."""
    base_url = "https://test-confluence.atlassian.net/rest/api"

    # Mock pattern library query
    requests_mock.get(
        f"{base_url}/content/search",
        json={
            "results": [
                {
                    "id": "12345",
                    "title": "Java Naming Conventions",
                    "body": {"storage": {"value": "Pattern content..."}}
                }
            ]
        }
    )

    yield requests_mock

@pytest.fixture(scope="function")
def mock_jira_api(requests_mock):
    """Mock Jira API responses."""
    base_url = "https://test-jira.atlassian.net/rest/api/3"

    # Mock user search
    requests_mock.get(
        f"{base_url}/user/search",
        json=[
            {
                "accountId": "5b10ac8d82e05b22cc7d4ef5",
                "emailAddress": "dev1@test.com",
                "displayName": "Developer One"
            }
        ]
    )

    # Mock issue creation
    requests_mock.post(
        f"{base_url}/issue",
        json={"id": "10000", "key": "SCM-456", "self": f"{base_url}/issue/10000"}
    )

    # Mock remote link creation
    requests_mock.post(
        f"{base_url}/issue/SCM-456/remotelink",
        json={"id": 10001}
    )

    yield requests_mock
```

---

## Full Pipeline Integration Tests

### Test 1: Happy Path - PR with No Violations

**Scenario**: PR contains clean code with no violations and no new patterns.

**Pre-conditions**:
- GitHub PR exists and is open
- Confluence pattern library is accessible
- All agents are operational

**Test Steps**:
1. Trigger workflow with PR event
2. Pre-flight validation checks PR is valid
3. Code Quality Agent validates code (PASS)
4. Architect Agent checks for new patterns (NO_NEW_PATTERN)
5. Final report posted to PR
6. PR merge allowed

**Expected Outcome**:
- All agents return SUCCESS status
- No Jira tickets created
- PR comment shows all checks passed
- PR merge not blocked

**Test Implementation**:

```python
# tests/integration/test_full_pipeline.py
import pytest
import asyncio
from unittest.mock import Mock, patch
from src.orchestrator import PipelineOrchestrator
from src.agents import CodeQualityAgent, ArchitectAgent

@pytest.mark.integration
@pytest.mark.asyncio
async def test_happy_path_no_violations(
    dynamodb_table,
    redis_client,
    mock_github_api,
    mock_confluence_api
):
    """Test complete pipeline with clean code and no violations."""

    # Arrange
    pr_number = 123
    orchestrator = PipelineOrchestrator(
        dynamodb=dynamodb_table,
        redis=redis_client
    )

    # Act
    result = await orchestrator.execute_pipeline(
        pr_number=pr_number,
        repository="tonic-scm/test-repo",
        event_type="pull_request.opened"
    )

    # Assert
    assert result['status'] == 'PASSED'
    assert result['pre_flight']['has_code_changes'] is True
    assert result['code_quality']['status'] == 'PASSED'
    assert result['code_quality']['violations_count'] == 0
    assert result['architect']['status'] == 'NO_NEW_PATTERN'
    assert result['lld_alignment']['status'] == 'SKIPPED'
    assert result['peer_review']['status'] == 'SKIPPED'
    assert result['jira_ticket_created'] is False

    # Verify PR comment posted
    assert mock_github_api.called
    comment_calls = [
        call for call in mock_github_api.request_history
        if 'comments' in call.url and call.method == 'POST'
    ]
    assert len(comment_calls) == 1
    assert 'All checks passed' in comment_calls[0].json()['body']

    # Verify state persisted to DynamoDB
    state = dynamodb_table.get_item(
        Key={'pr_id': f'PR-{pr_number}', 'timestamp': result['timestamp']}
    )
    assert state['Item']['status'] == 'PASSED'

    # Verify pattern cache updated in Redis
    cached_patterns = redis_client.get('confluence:patterns:latest')
    assert cached_patterns is not None


@pytest.mark.integration
@pytest.mark.performance
async def test_happy_path_performance_sla(
    dynamodb_table,
    redis_client,
    mock_github_api,
    mock_confluence_api
):
    """Verify happy path completes within performance SLA."""

    import time

    pr_number = 124
    orchestrator = PipelineOrchestrator(
        dynamodb=dynamodb_table,
        redis=redis_client
    )

    start_time = time.time()
    result = await orchestrator.execute_pipeline(
        pr_number=pr_number,
        repository="tonic-scm/test-repo",
        event_type="pull_request.opened"
    )
    elapsed_time = time.time() - start_time

    # Assert overall pipeline completes in < 2 minutes
    assert elapsed_time < 120

    # Assert individual agent SLAs
    assert result['code_quality']['execution_time'] < 30
    assert result['architect']['execution_time'] < 10

    print(f"Pipeline completed in {elapsed_time:.2f} seconds")
```

---

### Test 2: PR with Code Violations

**Scenario**: PR contains code that violates approved patterns.

**Pre-conditions**:
- PR contains code with naming convention violations
- Confluence pattern library contains naming standards

**Test Steps**:
1. Code Quality Agent analyzes PR
2. Violations detected
3. Jira Integration Agent creates ticket
4. PR comment posted with violation details
5. PR merge blocked

**Expected Outcome**:
- Code Quality Agent returns FAILED
- Jira ticket created with violation details
- PR comment shows violations
- GitHub status check FAILED
- PR merge blocked

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_pr_with_code_violations(
    dynamodb_table,
    redis_client,
    mock_github_api,
    mock_confluence_api,
    mock_jira_api
):
    """Test pipeline with code violations triggers Jira ticket creation."""

    # Arrange
    pr_number = 125
    orchestrator = PipelineOrchestrator(
        dynamodb=dynamodb_table,
        redis=redis_client
    )

    # Mock code with violations
    with patch('src.agents.code_quality.CodeQualityAgent.analyze') as mock_analyze:
        mock_analyze.return_value = {
            'status': 'FAILED',
            'violations_count': 3,
            'violations': [
                {
                    'file': 'src/auth/AuthService.java',
                    'line': 45,
                    'type': 'NAMING_CONVENTION',
                    'pattern': 'Java Method Naming (camelCase)',
                    'found': 'get_user()',
                    'expected': 'getUser()',
                    'severity': 'MAJOR'
                },
                {
                    'file': 'src/auth/AuthService.java',
                    'line': 45,
                    'type': 'DOCUMENTATION',
                    'pattern': 'Public Method JavaDoc Required',
                    'found': 'Missing JavaDoc',
                    'severity': 'MINOR'
                },
                {
                    'file': 'src/auth/AuthService.java',
                    'line': 78,
                    'type': 'EXCEPTION_HANDLING',
                    'pattern': 'Specific Exception Handling',
                    'found': 'catch (Exception e)',
                    'expected': 'catch (AuthenticationException e)',
                    'severity': 'CRITICAL'
                }
            ]
        }

        # Act
        result = await orchestrator.execute_pipeline(
            pr_number=pr_number,
            repository="tonic-scm/test-repo",
            event_type="pull_request.opened"
        )

    # Assert
    assert result['status'] == 'FAILED'
    assert result['code_quality']['status'] == 'FAILED'
    assert result['code_quality']['violations_count'] == 3
    assert result['jira_ticket_created'] is True
    assert result['jira_ticket_key'] == 'SCM-456'

    # Verify Jira ticket created
    jira_create_calls = [
        call for call in mock_jira_api.request_history
        if '/issue' in call.url and call.method == 'POST'
    ]
    assert len(jira_create_calls) == 1

    ticket_data = jira_create_calls[0].json()
    assert ticket_data['fields']['summary'] == 'Code violations in PR #125'
    assert 'AuthService.java' in str(ticket_data['fields']['description'])
    assert ticket_data['fields']['labels'] == ['code-quality', 'pr-125']

    # Verify PR comment with violations
    comment_calls = [
        call for call in mock_github_api.request_history
        if 'comments' in call.url and call.method == 'POST'
    ]
    comment_body = comment_calls[0].json()['body']
    assert '❌ Code Best Practises Analysis - FAILED' in comment_body
    assert 'Violations Found: 3' in comment_body
    assert 'get_user()' in comment_body

    # Verify GitHub status check set to FAILED
    status_calls = [
        call for call in mock_github_api.request_history
        if '/statuses/' in call.url
    ]
    assert status_calls[0].json()['state'] == 'failure'
```

---

### Test 3: PR with New Pattern Detection

**Scenario**: PR introduces a new coding pattern requiring LLD alignment and peer review.

**Pre-conditions**:
- PR contains new pattern not in Confluence library
- Pattern is LLD compliant
- Reviewers are available

**Test Steps**:
1. Code Quality Agent passes
2. Architect Agent detects new pattern
3. LLD Alignment Agent validates pattern
4. Peer Review Agent assigns reviewers
5. PR awaits human review

**Expected Outcome**:
- Architect Agent returns NEW_PATTERN_FOUND
- LLD Alignment Agent returns LLD_COMPLIANT
- Peer Review Agent assigns 2-3 reviewers
- PR status is PENDING_REVIEW
- PR merge blocked until review approved

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_pr_with_new_pattern_lld_compliant(
    dynamodb_table,
    redis_client,
    mock_github_api,
    mock_confluence_api
):
    """Test pipeline with new pattern requiring peer review."""

    # Arrange
    pr_number = 126
    orchestrator = PipelineOrchestrator(
        dynamodb=dynamodb_table,
        redis=redis_client
    )

    # Mock new pattern detection
    with patch('src.agents.architect.ArchitectAgent.analyze') as mock_architect, \
         patch('src.agents.lld_alignment.LLDAlignmentAgent.validate') as mock_lld, \
         patch('src.agents.peer_review.PeerReviewAgent.assign_reviewers') as mock_peer_review:

        mock_architect.return_value = {
            'status': 'NEW_PATTERN_FOUND',
            'new_pattern_detected': True,
            'pattern_data': {
                'type': 'Builder Pattern',
                'language': 'Java',
                'similarity_score': 0.72,
                'files': ['src/builder/OrderBuilder.java']
            }
        }

        mock_lld.return_value = {
            'status': 'LLD_COMPLIANT',
            'lld_compliant': True,
            'deviations_count': 0,
            'lld_references': [
                'https://confluence.test.com/lld/order-service#builder-patterns'
            ]
        }

        mock_peer_review.return_value = {
            'status': 'REVIEWERS_ASSIGNED',
            'reviewers_assigned': ['architect1', 'senior-dev1', 'component-owner'],
            'review_deadline': '2026-01-28T14:30:00Z'
        }

        # Act
        result = await orchestrator.execute_pipeline(
            pr_number=pr_number,
            repository="tonic-scm/test-repo",
            event_type="pull_request.opened"
        )

    # Assert
    assert result['status'] == 'PENDING_REVIEW'
    assert result['code_quality']['status'] == 'PASSED'
    assert result['architect']['status'] == 'NEW_PATTERN_FOUND'
    assert result['lld_alignment']['status'] == 'LLD_COMPLIANT'
    assert result['peer_review']['status'] == 'REVIEWERS_ASSIGNED'
    assert len(result['peer_review']['reviewers_assigned']) >= 2

    # Verify PR label added
    label_calls = [
        call for call in mock_github_api.request_history
        if '/labels' in call.url and call.method == 'POST'
    ]
    assert any('new-pattern-detected' in str(call.json()) for call in label_calls)

    # Verify reviewers assigned
    reviewer_calls = [
        call for call in mock_github_api.request_history
        if '/requested_reviewers' in call.url
    ]
    assert len(reviewer_calls) == 1
    assert 'architect1' in reviewer_calls[0].json()['reviewers']

    # Verify PR comment with review request
    comment_calls = [
        call for call in mock_github_api.request_history
        if 'comments' in call.url and call.method == 'POST'
    ]
    comment_body = comment_calls[-1].json()['body']
    assert 'New Pattern Detected' in comment_body
    assert 'Builder Pattern' in comment_body
    assert 'peer review' in comment_body.lower()
```

---

### Test 4: PR with Multiple Agent Failures

**Scenario**: Multiple agents fail due to various issues (violations + LLD deviation).

**Pre-conditions**:
- PR has code violations
- PR also introduces LLD-non-compliant pattern

**Test Steps**:
1. Code Quality Agent detects violations
2. Architect Agent detects new pattern
3. LLD Alignment Agent detects deviations
4. Multiple Jira tickets created
5. PR blocked

**Expected Outcome**:
- Multiple agents return FAILED
- Multiple Jira tickets created (one per failure type)
- PR comment aggregates all failures
- PR merge blocked

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_pr_with_multiple_agent_failures(
    dynamodb_table,
    redis_client,
    mock_github_api,
    mock_confluence_api,
    mock_jira_api
):
    """Test pipeline handling multiple simultaneous failures."""

    # Arrange
    pr_number = 127
    orchestrator = PipelineOrchestrator(
        dynamodb=dynamodb_table,
        redis=redis_client
    )

    # Mock multiple failures
    with patch('src.agents.code_quality.CodeQualityAgent.analyze') as mock_code, \
         patch('src.agents.architect.ArchitectAgent.analyze') as mock_architect, \
         patch('src.agents.lld_alignment.LLDAlignmentAgent.validate') as mock_lld:

        mock_code.return_value = {
            'status': 'FAILED',
            'violations_count': 2,
            'violations': [
                {'file': 'Test.java', 'line': 10, 'type': 'NAMING', 'severity': 'MAJOR'}
            ]
        }

        mock_architect.return_value = {
            'status': 'NEW_PATTERN_FOUND',
            'new_pattern_detected': True,
            'pattern_data': {'type': 'Singleton', 'language': 'Java'}
        }

        mock_lld.return_value = {
            'status': 'LLD_DEVIATION_FOUND',
            'lld_compliant': False,
            'deviations_count': 3,
            'deviations': [
                {
                    'type': 'INTERFACE_VIOLATION',
                    'severity': 'CRITICAL',
                    'description': 'Component boundary breach',
                    'lld_section': 'Section 4.2: Component Interfaces'
                },
                {
                    'type': 'DEPENDENCY_VIOLATION',
                    'severity': 'MAJOR',
                    'description': 'Disallowed dependency on legacy module',
                    'lld_section': 'Section 3.1: Dependency Constraints'
                }
            ]
        }

        # Act
        result = await orchestrator.execute_pipeline(
            pr_number=pr_number,
            repository="tonic-scm/test-repo",
            event_type="pull_request.opened"
        )

    # Assert
    assert result['status'] == 'FAILED'
    assert result['code_quality']['status'] == 'FAILED'
    assert result['lld_alignment']['status'] == 'LLD_DEVIATION_FOUND'
    assert result['jira_ticket_created'] is True

    # Verify multiple Jira tickets created
    jira_create_calls = [
        call for call in mock_jira_api.request_history
        if '/issue' in call.url and call.method == 'POST'
    ]
    assert len(jira_create_calls) == 2  # One for code violations, one for LLD deviation

    # Verify tickets have different issue types
    ticket_summaries = [call.json()['fields']['summary'] for call in jira_create_calls]
    assert any('Code violations' in summary for summary in ticket_summaries)
    assert any('LLD deviation' in summary for summary in ticket_summaries)

    # Verify comprehensive PR comment
    comment_calls = [
        call for call in mock_github_api.request_history
        if 'comments' in call.url and call.method == 'POST'
    ]
    final_comment = comment_calls[-1].json()['body']
    assert 'Code Quality: ❌ FAILED' in final_comment
    assert 'LLD Alignment: ❌ FAILED' in final_comment
    assert 'Jira Tickets Created:' in final_comment
    assert 'SCM-456' in final_comment
```

---

## Agent-to-Agent Integration Tests

### Test 5: Code Quality to Architect Agent Handoff

**Scenario**: Validate data handoff from Code Quality Agent to Architect Agent.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_code_quality_to_architect_handoff(
    dynamodb_table,
    redis_client,
    mock_confluence_api
):
    """Test data handoff between Code Quality and Architect agents."""

    from src.agents import CodeQualityAgent, ArchitectAgent

    # Arrange
    pr_data = {
        'pr_number': 128,
        'repository': 'tonic-scm/test-repo',
        'modified_files': ['src/NewPattern.java']
    }

    code_agent = CodeQualityAgent(redis=redis_client)
    architect_agent = ArchitectAgent(redis=redis_client)

    # Act - Code Quality Agent analysis
    code_result = await code_agent.analyze(pr_data)

    # Verify handoff data structure
    assert 'analyzed_files' in code_result
    assert 'patterns_checked' in code_result

    # Act - Architect Agent receives handoff
    architect_result = await architect_agent.analyze(
        pr_data=pr_data,
        code_quality_result=code_result
    )

    # Assert - Architect can access Code Quality outputs
    assert architect_result['code_quality_status'] == code_result['status']
    assert architect_result['files_to_analyze'] == code_result['analyzed_files']

    # Verify Redis cache shared between agents
    cached_pr_data = redis_client.get(f'pr:{pr_data["pr_number"]}:code_quality')
    assert cached_pr_data is not None

    cached_architect_data = redis_client.get(f'pr:{pr_data["pr_number"]}:architect')
    assert cached_architect_data is not None
```

---

### Test 6: Architect to LLD Alignment Conditional Execution

**Scenario**: LLD Alignment Agent only runs when new pattern detected.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_architect_to_lld_conditional_execution(
    dynamodb_table,
    redis_client
):
    """Test LLD Alignment Agent conditionally executes based on Architect result."""

    from src.agents import ArchitectAgent, LLDAlignmentAgent
    from src.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(dynamodb=dynamodb_table, redis=redis_client)

    # Test Case 1: No new pattern - LLD skipped
    with patch('src.agents.architect.ArchitectAgent.analyze') as mock_architect:
        mock_architect.return_value = {
            'status': 'NO_NEW_PATTERN',
            'new_pattern_detected': False
        }

        result = await orchestrator.execute_pipeline(
            pr_number=129,
            repository="tonic-scm/test-repo",
            event_type="pull_request.opened"
        )

        assert result['architect']['status'] == 'NO_NEW_PATTERN'
        assert result['lld_alignment']['status'] == 'SKIPPED'
        assert result['lld_alignment']['reason'] == 'No new pattern detected'

    # Test Case 2: New pattern - LLD executes
    with patch('src.agents.architect.ArchitectAgent.analyze') as mock_architect, \
         patch('src.agents.lld_alignment.LLDAlignmentAgent.validate') as mock_lld:

        mock_architect.return_value = {
            'status': 'NEW_PATTERN_FOUND',
            'new_pattern_detected': True,
            'pattern_data': {'type': 'Observer', 'language': 'Java'}
        }

        mock_lld.return_value = {
            'status': 'LLD_COMPLIANT',
            'lld_compliant': True
        }

        result = await orchestrator.execute_pipeline(
            pr_number=130,
            repository="tonic-scm/test-repo",
            event_type="pull_request.opened"
        )

        assert result['architect']['status'] == 'NEW_PATTERN_FOUND'
        assert result['lld_alignment']['status'] == 'LLD_COMPLIANT'
        assert result['lld_alignment']['pattern_analyzed'] == 'Observer'
```

---

### Test 7: Result Aggregation Across All Agents

**Scenario**: Final Report aggregates results from all executed agents.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_result_aggregation_across_agents(
    dynamodb_table,
    redis_client,
    mock_github_api
):
    """Test final report aggregates results from all agents."""

    from src.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(dynamodb=dynamodb_table, redis=redis_client)

    # Mock all agents
    with patch('src.agents.code_quality.CodeQualityAgent.analyze') as mock_code, \
         patch('src.agents.architect.ArchitectAgent.analyze') as mock_architect, \
         patch('src.agents.lld_alignment.LLDAlignmentAgent.validate') as mock_lld, \
         patch('src.agents.peer_review.PeerReviewAgent.assign_reviewers') as mock_peer:

        mock_code.return_value = {
            'status': 'PASSED',
            'violations_count': 0,
            'execution_time': 15.2
        }

        mock_architect.return_value = {
            'status': 'NEW_PATTERN_FOUND',
            'new_pattern_detected': True,
            'execution_time': 8.5
        }

        mock_lld.return_value = {
            'status': 'LLD_COMPLIANT',
            'lld_compliant': True,
            'execution_time': 18.3
        }

        mock_peer.return_value = {
            'status': 'REVIEWERS_ASSIGNED',
            'reviewers_assigned': ['reviewer1', 'reviewer2'],
            'execution_time': 3.1
        }

        # Act
        result = await orchestrator.execute_pipeline(
            pr_number=131,
            repository="tonic-scm/test-repo",
            event_type="pull_request.opened"
        )

    # Assert aggregated results
    assert result['status'] == 'PENDING_REVIEW'
    assert 'code_quality' in result
    assert 'architect' in result
    assert 'lld_alignment' in result
    assert 'peer_review' in result

    # Verify execution times aggregated
    total_execution_time = (
        result['code_quality']['execution_time'] +
        result['architect']['execution_time'] +
        result['lld_alignment']['execution_time'] +
        result['peer_review']['execution_time']
    )
    assert total_execution_time < 120  # Under 2 minute SLA

    # Verify final PR comment includes all agent results
    comment_calls = [
        call for call in mock_github_api.request_history
        if 'comments' in call.url and call.method == 'POST'
    ]
    final_comment = comment_calls[-1].json()['body']

    assert 'Code Quality: ✅ PASSED' in final_comment
    assert 'Architect: 🔍 NEW_PATTERN_FOUND' in final_comment
    assert 'LLD Alignment: ✅ LLD_COMPLIANT' in final_comment
    assert 'Peer Review: ⏳ PENDING_REVIEW' in final_comment
    assert 'reviewers assigned' in final_comment.lower()
```

---

## GitHub Actions Integration Tests

### Test 8: Workflow Triggers on PR Events

**Scenario**: Validate workflow triggers correctly on PR open, synchronize, and reopen events.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_triggers_on_pr_events(mock_github_api, dynamodb_table, redis_client):
    """Test workflow triggers on correct PR events."""

    from src.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(dynamodb=dynamodb_table, redis=redis_client)

    # Test Case 1: PR opened event
    result_opened = await orchestrator.handle_github_event({
        'action': 'opened',
        'pull_request': {
            'number': 132,
            'state': 'open',
            'title': 'Test PR',
            'base': {'ref': 'main', 'repo': {'name': 'test-repo'}},
            'head': {'ref': 'feature/test'}
        }
    })

    assert result_opened['triggered'] is True
    assert result_opened['event_type'] == 'pull_request.opened'

    # Test Case 2: PR synchronize event (new commits)
    result_sync = await orchestrator.handle_github_event({
        'action': 'synchronize',
        'pull_request': {
            'number': 132,
            'state': 'open'
        }
    })

    assert result_sync['triggered'] is True
    assert result_sync['event_type'] == 'pull_request.synchronize'

    # Test Case 3: PR reopened event
    result_reopen = await orchestrator.handle_github_event({
        'action': 'reopened',
        'pull_request': {
            'number': 132,
            'state': 'open'
        }
    })

    assert result_reopen['triggered'] is True
    assert result_reopen['event_type'] == 'pull_request.reopened'

    # Test Case 4: PR closed event (should NOT trigger)
    result_closed = await orchestrator.handle_github_event({
        'action': 'closed',
        'pull_request': {
            'number': 132,
            'state': 'closed'
        }
    })

    assert result_closed['triggered'] is False
    assert result_closed['reason'] == 'Event not in trigger list'
```

---

### Test 9: Branch Protection Status Checks

**Scenario**: Verify status checks are set correctly for branch protection.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_branch_protection_status_checks(mock_github_api, dynamodb_table, redis_client):
    """Test GitHub status checks for branch protection integration."""

    from src.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(dynamodb=dynamodb_table, redis=redis_client)

    # Mock successful pipeline
    with patch('src.orchestrator.PipelineOrchestrator.execute_pipeline') as mock_pipeline:
        mock_pipeline.return_value = {
            'status': 'PASSED',
            'code_quality': {'status': 'PASSED'},
            'architect': {'status': 'NO_NEW_PATTERN'}
        }

        await orchestrator.handle_github_event({
            'action': 'opened',
            'pull_request': {
                'number': 133,
                'head': {'sha': 'abc123'},
                'base': {'repo': {'name': 'test-repo'}}
            }
        })

    # Verify status check API calls
    status_calls = [
        call for call in mock_github_api.request_history
        if '/statuses/' in call.url and call.method == 'POST'
    ]

    assert len(status_calls) >= 1

    # Verify status check structure
    status_data = status_calls[-1].json()
    assert status_data['state'] == 'success'
    assert status_data['context'] == 'PR Peer Review Orchestration'
    assert status_data['description'] == 'All checks passed'
    assert 'target_url' in status_data

    # Test failure scenario
    with patch('src.orchestrator.PipelineOrchestrator.execute_pipeline') as mock_pipeline:
        mock_pipeline.return_value = {
            'status': 'FAILED',
            'code_quality': {'status': 'FAILED', 'violations_count': 5}
        }

        await orchestrator.handle_github_event({
            'action': 'synchronize',
            'pull_request': {
                'number': 133,
                'head': {'sha': 'def456'}
            }
        })

    # Verify failure status
    failure_calls = [
        call for call in mock_github_api.request_history
        if '/statuses/def456' in call.url
    ]

    failure_data = failure_calls[-1].json()
    assert failure_data['state'] == 'failure'
    assert '5 violations' in failure_data['description']
```

---

### Test 10: PR Comment Posting

**Scenario**: Verify PR comments are posted correctly with formatted results.

**Test Implementation**:

```python
@pytest.mark.integration
def test_pr_comment_posting_format(mock_github_api):
    """Test PR comment formatting and posting."""

    from src.reporters import PRCommentReporter

    reporter = PRCommentReporter()

    # Create test results
    pipeline_result = {
        'status': 'PASSED',
        'pr_number': 134,
        'code_quality': {
            'status': 'PASSED',
            'violations_count': 0,
            'files_analyzed': 5,
            'execution_time': 12.5
        },
        'architect': {
            'status': 'NO_NEW_PATTERN',
            'patterns_checked': 42,
            'execution_time': 7.8
        }
    }

    # Act
    reporter.post_comment(
        repository='tonic-scm/test-repo',
        pr_number=134,
        result=pipeline_result
    )

    # Assert
    comment_calls = [
        call for call in mock_github_api.request_history
        if 'comments' in call.url and call.method == 'POST'
    ]

    assert len(comment_calls) == 1
    comment_body = comment_calls[0].json()['body']

    # Verify markdown formatting
    assert '## PR Peer Review Results' in comment_body
    assert '### Summary' in comment_body
    assert '✅ PASSED' in comment_body

    # Verify table format
    assert '| Agent | Status | Details |' in comment_body
    assert '| Code Quality | ✅ PASSED | 0 violations, 5 files analyzed |' in comment_body
    assert '| Architect | ℹ️ NO_NEW_PATTERN | 42 patterns checked |' in comment_body

    # Verify execution times
    assert 'Total Execution Time: 20.3 seconds' in comment_body
```

---

## Jira Integration Tests

### Test 11: Ticket Creation from Agent Failures

**Scenario**: Verify Jira tickets are created when agents fail.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_jira_ticket_creation_from_failures(mock_jira_api, redis_client):
    """Test Jira ticket creation triggered by agent failures."""

    from src.agents.jira_integration import JiraIntegrationAgent

    jira_agent = JiraIntegrationAgent(redis=redis_client)

    # Test Case 1: Code violation ticket
    code_failure_data = {
        'pr_number': 135,
        'repository': 'tonic-scm/test-repo',
        'pr_url': 'https://github.com/tonic-scm/test-repo/pull/135',
        'author': 'developer1',
        'author_email': 'dev1@test.com',
        'failure_type': 'CODE_VIOLATION',
        'violations': [
            {
                'file': 'Test.java',
                'line': 10,
                'type': 'NAMING',
                'severity': 'MAJOR',
                'description': 'Method name violates camelCase convention'
            }
        ]
    }

    # Act
    ticket_result = await jira_agent.create_ticket(code_failure_data)

    # Assert
    assert ticket_result['success'] is True
    assert ticket_result['ticket_key'] == 'SCM-456'

    # Verify Jira API calls
    user_search_calls = [
        call for call in mock_jira_api.request_history
        if '/user/search' in call.url
    ]
    assert len(user_search_calls) == 1
    assert 'dev1@test.com' in user_search_calls[0].url

    create_calls = [
        call for call in mock_jira_api.request_history
        if '/issue' in call.url and call.method == 'POST'
    ]
    assert len(create_calls) == 1

    ticket_data = create_calls[0].json()
    assert ticket_data['fields']['project']['key'] == 'SCM'
    assert ticket_data['fields']['issuetype']['name'] == 'Bug'
    assert 'Code violations in PR #135' in ticket_data['fields']['summary']
    assert ticket_data['fields']['assignee']['accountId'] == '5b10ac8d82e05b22cc7d4ef5'
    assert 'code-quality' in ticket_data['fields']['labels']
    assert 'pr-135' in ticket_data['fields']['labels']

    # Verify ADF description format
    description = ticket_data['fields']['description']
    assert description['type'] == 'doc'
    assert description['version'] == 1
    assert len(description['content']) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jira_ticket_for_lld_deviation(mock_jira_api, redis_client):
    """Test Jira ticket creation for LLD deviations."""

    from src.agents.jira_integration import JiraIntegrationAgent

    jira_agent = JiraIntegrationAgent(redis=redis_client)

    lld_failure_data = {
        'pr_number': 136,
        'repository': 'tonic-scm/payment-service',
        'pr_url': 'https://github.com/tonic-scm/payment-service/pull/136',
        'author': 'developer2',
        'author_email': 'dev2@test.com',
        'failure_type': 'LLD_DEVIATION',
        'deviations': [
            {
                'type': 'INTERFACE_VIOLATION',
                'severity': 'CRITICAL',
                'description': 'Component boundary breach in PaymentProcessor',
                'lld_section': 'Section 4.2: Component Interfaces',
                'lld_url': 'https://confluence.test.com/lld/payment#interfaces'
            }
        ]
    }

    # Act
    ticket_result = await jira_agent.create_ticket(lld_failure_data)

    # Assert
    assert ticket_result['success'] is True

    create_calls = [
        call for call in mock_jira_api.request_history
        if '/issue' in call.url and call.method == 'POST'
    ]

    ticket_data = create_calls[0].json()
    assert 'LLD deviation' in ticket_data['fields']['summary']
    assert ticket_data['fields']['priority']['name'] == 'High'
    assert 'lld-deviation' in ticket_data['fields']['labels']

    # Verify LLD links in description
    description_text = str(ticket_data['fields']['description'])
    assert 'Section 4.2: Component Interfaces' in description_text
    assert 'confluence.test.com/lld/payment' in description_text
```

---

### Test 12: Auto-Assignment to PR Author

**Scenario**: Verify Jira tickets are automatically assigned to PR author.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_jira_auto_assignment_to_pr_author(mock_jira_api, redis_client):
    """Test Jira ticket auto-assignment to PR author."""

    from src.agents.jira_integration import JiraIntegrationAgent

    jira_agent = JiraIntegrationAgent(redis=redis_client)

    # Arrange
    failure_data = {
        'pr_number': 137,
        'author': 'developer3',
        'author_email': 'dev3@test.com',
        'failure_type': 'CODE_VIOLATION',
        'violations': []
    }

    # Act
    ticket_result = await jira_agent.create_ticket(failure_data)

    # Assert - Verify account ID lookup
    user_search_calls = [
        call for call in mock_jira_api.request_history
        if '/user/search' in call.url
    ]
    assert len(user_search_calls) == 1
    assert 'query=dev3@test.com' in user_search_calls[0].url

    # Verify assignment in ticket creation
    create_calls = [
        call for call in mock_jira_api.request_history
        if '/issue' in call.url and call.method == 'POST'
    ]
    ticket_data = create_calls[0].json()
    assert 'assignee' in ticket_data['fields']
    assert ticket_data['fields']['assignee']['accountId'] == '5b10ac8d82e05b22cc7d4ef5'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jira_fallback_assignee_when_author_not_found(mock_jira_api, redis_client):
    """Test fallback to default assignee when PR author not found in Jira."""

    from src.agents.jira_integration import JiraIntegrationAgent

    # Mock user not found
    mock_jira_api.get(
        'https://test-jira.atlassian.net/rest/api/3/user/search',
        json=[]  # Empty result - user not found
    )

    jira_agent = JiraIntegrationAgent(redis=redis_client)

    failure_data = {
        'pr_number': 138,
        'author': 'external-contributor',
        'author_email': 'external@other.com',
        'failure_type': 'CODE_VIOLATION',
        'violations': []
    }

    # Act
    ticket_result = await jira_agent.create_ticket(failure_data)

    # Assert - Should use default assignee
    assert ticket_result['success'] is True
    assert ticket_result['assignee'] == 'default'

    create_calls = [
        call for call in mock_jira_api.request_history
        if '/issue' in call.url and call.method == 'POST'
    ]
    ticket_data = create_calls[0].json()
    # Verify fallback to default assignee from env config
    assert ticket_data['fields']['assignee']['emailAddress'] == 'test-lead@test.com'
```

---

### Test 13: PR-Jira Bidirectional Linking

**Scenario**: Verify bidirectional links between GitHub PR and Jira ticket.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_pr_jira_bidirectional_linking(mock_github_api, mock_jira_api, redis_client):
    """Test bidirectional linking between PR and Jira ticket."""

    from src.agents.jira_integration import JiraIntegrationAgent

    jira_agent = JiraIntegrationAgent(redis=redis_client)

    # Arrange
    pr_data = {
        'pr_number': 139,
        'repository': 'tonic-scm/test-repo',
        'pr_url': 'https://github.com/tonic-scm/test-repo/pull/139',
        'pr_title': 'Add new feature',
        'author_email': 'dev@test.com',
        'failure_type': 'CODE_VIOLATION',
        'violations': []
    }

    # Act
    ticket_result = await jira_agent.create_ticket(pr_data)

    # Assert Jira -> GitHub link (remote link)
    remote_link_calls = [
        call for call in mock_jira_api.request_history
        if '/remotelink' in call.url and call.method == 'POST'
    ]
    assert len(remote_link_calls) == 1

    link_data = remote_link_calls[0].json()
    assert link_data['globalId'] == 'system=github&id=tonic-scm/test-repo/pull/139'
    assert link_data['relationship'] == 'Pull Request'
    assert link_data['object']['url'] == pr_data['pr_url']
    assert link_data['object']['title'] == 'PR #139: Add new feature'

    # Assert GitHub -> Jira link (PR comment)
    pr_comment_calls = [
        call for call in mock_github_api.request_history
        if 'comments' in call.url and call.method == 'POST'
    ]
    assert len(pr_comment_calls) >= 1

    comment_body = pr_comment_calls[-1].json()['body']
    assert 'SCM-456' in comment_body
    assert 'https://test-jira.atlassian.net/browse/SCM-456' in comment_body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jira_link_update_on_pr_status_change(mock_jira_api, redis_client):
    """Test Jira remote link updates when PR status changes."""

    from src.agents.jira_integration import JiraIntegrationAgent

    jira_agent = JiraIntegrationAgent(redis=redis_client)

    # Create initial link (PR open)
    await jira_agent.create_remote_link(
        issue_key='SCM-456',
        pr_number=140,
        pr_url='https://github.com/tonic-scm/test-repo/pull/140',
        pr_title='Test PR',
        pr_state='open'
    )

    # Update link (PR closed)
    await jira_agent.update_remote_link(
        issue_key='SCM-456',
        pr_number=140,
        pr_state='closed'
    )

    # Verify link updated
    link_update_calls = [
        call for call in mock_jira_api.request_history
        if '/remotelink' in call.url and call.method == 'POST'
    ]

    # Latest call should have resolved=true
    latest_link = link_update_calls[-1].json()
    assert latest_link['object']['status']['resolved'] is True
```

---

### Test 14: Jira API Rate Limiting

**Scenario**: Verify rate limit handling for Jira API calls.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_jira_api_rate_limiting_handling(requests_mock, redis_client):
    """Test handling of Jira API rate limits with retry logic."""

    from src.agents.jira_integration import JiraIntegrationAgent
    import time

    # Mock rate limit response followed by success
    requests_mock.post(
        'https://test-jira.atlassian.net/rest/api/3/issue',
        [
            {
                'status_code': 429,
                'json': {'errorMessages': ['Rate limit exceeded']},
                'headers': {'Retry-After': '2'}
            },
            {
                'status_code': 429,
                'json': {'errorMessages': ['Rate limit exceeded']},
                'headers': {'Retry-After': '2'}
            },
            {
                'status_code': 201,
                'json': {'id': '10000', 'key': 'SCM-457'}
            }
        ]
    )

    jira_agent = JiraIntegrationAgent(redis=redis_client)

    # Act
    start_time = time.time()
    ticket_result = await jira_agent.create_ticket({
        'pr_number': 141,
        'author_email': 'dev@test.com',
        'failure_type': 'CODE_VIOLATION',
        'violations': []
    })
    elapsed_time = time.time() - start_time

    # Assert
    assert ticket_result['success'] is True
    assert ticket_result['ticket_key'] == 'SCM-457'
    assert ticket_result['retry_count'] == 2

    # Verify exponential backoff respected Retry-After header
    assert elapsed_time >= 4  # At least 2+2 seconds from Retry-After headers

    # Verify all 3 attempts made
    issue_create_calls = [
        call for call in requests_mock.request_history
        if '/issue' in call.url and call.method == 'POST'
    ]
    assert len(issue_create_calls) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jira_api_circuit_breaker(requests_mock, redis_client):
    """Test circuit breaker pattern for Jira API failures."""

    from src.agents.jira_integration import JiraIntegrationAgent

    # Mock consecutive failures
    requests_mock.post(
        'https://test-jira.atlassian.net/rest/api/3/issue',
        status_code=503,
        json={'errorMessages': ['Service unavailable']}
    )

    jira_agent = JiraIntegrationAgent(redis=redis_client)

    # Trigger circuit breaker by multiple failures
    failure_count = 0
    for i in range(5):
        try:
            await jira_agent.create_ticket({
                'pr_number': 142 + i,
                'author_email': 'dev@test.com',
                'failure_type': 'CODE_VIOLATION',
                'violations': []
            })
        except Exception:
            failure_count += 1

    # Verify circuit breaker opened
    assert failure_count == 5
    assert jira_agent.circuit_breaker.state == 'OPEN'

    # Verify subsequent calls fail immediately without API call
    with pytest.raises(Exception, match='Circuit breaker is OPEN'):
        await jira_agent.create_ticket({
            'pr_number': 999,
            'author_email': 'dev@test.com',
            'failure_type': 'CODE_VIOLATION',
            'violations': []
        })
```

---

## State Management Integration Tests

### Test 15: DynamoDB State Persistence

**Scenario**: Verify PR review state is persisted to DynamoDB.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_dynamodb_state_persistence(dynamodb_table, redis_client):
    """Test PR review state persistence to DynamoDB."""

    from src.state.dynamodb_store import DynamoDBStateStore
    import time

    state_store = DynamoDBStateStore(table=dynamodb_table)

    # Create test state
    pr_state = {
        'pr_id': 'PR-143',
        'pr_number': 143,
        'repository': 'tonic-scm/test-repo',
        'status': 'IN_PROGRESS',
        'code_quality': {
            'status': 'PASSED',
            'timestamp': time.time()
        },
        'architect': {
            'status': 'NEW_PATTERN_FOUND',
            'timestamp': time.time()
        }
    }

    # Act - Save state
    await state_store.save_state(pr_state)

    # Act - Retrieve state
    retrieved_state = await state_store.get_state('PR-143')

    # Assert
    assert retrieved_state is not None
    assert retrieved_state['pr_number'] == 143
    assert retrieved_state['status'] == 'IN_PROGRESS'
    assert 'code_quality' in retrieved_state
    assert 'architect' in retrieved_state

    # Verify DynamoDB item structure
    response = dynamodb_table.get_item(
        Key={
            'pr_id': 'PR-143',
            'timestamp': pr_state['code_quality']['timestamp']
        }
    )

    assert 'Item' in response
    assert response['Item']['repository'] == 'tonic-scm/test-repo'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dynamodb_state_update(dynamodb_table, redis_client):
    """Test updating existing PR state in DynamoDB."""

    from src.state.dynamodb_store import DynamoDBStateStore

    state_store = DynamoDBStateStore(table=dynamodb_table)

    # Initial state
    initial_state = {
        'pr_id': 'PR-144',
        'pr_number': 144,
        'status': 'IN_PROGRESS',
        'code_quality': {'status': 'PASSED'}
    }

    await state_store.save_state(initial_state)

    # Update state with LLD result
    updated_state = {
        **initial_state,
        'status': 'PENDING_REVIEW',
        'lld_alignment': {'status': 'LLD_COMPLIANT'},
        'peer_review': {'status': 'REVIEWERS_ASSIGNED'}
    }

    await state_store.update_state('PR-144', updated_state)

    # Retrieve and verify
    final_state = await state_store.get_state('PR-144')

    assert final_state['status'] == 'PENDING_REVIEW'
    assert 'lld_alignment' in final_state
    assert 'peer_review' in final_state
    assert final_state['code_quality']['status'] == 'PASSED'  # Original data preserved
```

---

### Test 16: Redis Caching Behavior

**Scenario**: Verify Redis caching for frequently accessed data.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_caching_behavior(redis_client, mock_confluence_api):
    """Test Redis caching for Confluence patterns."""

    from src.cache.redis_cache import RedisCache

    cache = RedisCache(redis_client)

    # Test Case 1: Cache miss - fetch from Confluence
    patterns = await cache.get_or_fetch(
        key='confluence:patterns:java',
        fetch_func=lambda: fetch_confluence_patterns('java'),
        ttl=3600
    )

    assert patterns is not None
    assert len(patterns) > 0

    # Verify Confluence API called
    confluence_calls = [
        call for call in mock_confluence_api.request_history
        if 'confluence' in call.hostname
    ]
    initial_call_count = len(confluence_calls)

    # Test Case 2: Cache hit - no Confluence call
    cached_patterns = await cache.get_or_fetch(
        key='confluence:patterns:java',
        fetch_func=lambda: fetch_confluence_patterns('java'),
        ttl=3600
    )

    assert cached_patterns == patterns

    # Verify no additional Confluence calls
    final_call_count = len([
        call for call in mock_confluence_api.request_history
        if 'confluence' in call.hostname
    ])
    assert final_call_count == initial_call_count  # No new calls

    # Test Case 3: Cache invalidation
    await cache.invalidate('confluence:patterns:java')

    patterns_after_invalidation = await cache.get_or_fetch(
        key='confluence:patterns:java',
        fetch_func=lambda: fetch_confluence_patterns('java'),
        ttl=3600
    )

    # Verify Confluence called again after invalidation
    post_invalidation_calls = len([
        call for call in mock_confluence_api.request_history
        if 'confluence' in call.hostname
    ])
    assert post_invalidation_calls == initial_call_count + 1


def fetch_confluence_patterns(language):
    """Mock Confluence pattern fetch."""
    return [
        {'name': 'Naming Conventions', 'language': language},
        {'name': 'Exception Handling', 'language': language}
    ]


@pytest.mark.integration
def test_redis_cache_ttl_expiration(redis_client):
    """Test Redis cache TTL expiration."""

    from src.cache.redis_cache import RedisCache
    import time

    cache = RedisCache(redis_client)

    # Set cache with 2 second TTL
    cache.set('test:key', {'data': 'value'}, ttl=2)

    # Immediate retrieval succeeds
    result = cache.get('test:key')
    assert result == {'data': 'value'}

    # Wait for expiration
    time.sleep(3)

    # Retrieval after TTL returns None
    expired_result = cache.get('test:key')
    assert expired_result is None
```

---

### Test 17: State Recovery After Failures

**Scenario**: Verify state can be recovered after agent failures.

**Test Implementation**:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_state_recovery_after_agent_failure(dynamodb_table, redis_client):
    """Test state recovery and workflow resumption after agent failure."""

    from src.orchestrator import PipelineOrchestrator
    from src.state.dynamodb_store import DynamoDBStateStore

    orchestrator = PipelineOrchestrator(dynamodb=dynamodb_table, redis=redis_client)
    state_store = DynamoDBStateStore(table=dynamodb_table)

    # Simulate partial execution with failure
    with patch('src.agents.lld_alignment.LLDAlignmentAgent.validate') as mock_lld:
        mock_lld.side_effect = Exception('LLD Agent timeout')

        try:
            await orchestrator.execute_pipeline(
                pr_number=145,
                repository="tonic-scm/test-repo",
                event_type="pull_request.opened"
            )
        except Exception:
            pass  # Expected failure

    # Verify partial state saved
    saved_state = await state_store.get_state('PR-145')
    assert saved_state is not None
    assert saved_state['code_quality']['status'] == 'PASSED'
    assert saved_state['architect']['status'] == 'NEW_PATTERN_FOUND'
    assert saved_state['lld_alignment']['status'] == 'FAILED'

    # Act - Resume from saved state
    with patch('src.agents.lld_alignment.LLDAlignmentAgent.validate') as mock_lld:
        mock_lld.return_value = {
            'status': 'LLD_COMPLIANT',
            'lld_compliant': True
        }

        result = await orchestrator.resume_pipeline('PR-145')

    # Assert - Workflow completed successfully
    assert result['status'] == 'PENDING_REVIEW'
    assert result['resumed_from_state'] is True
    assert result['lld_alignment']['status'] == 'LLD_COMPLIANT'

    # Verify only LLD and downstream agents re-executed
    assert result['code_quality']['re_executed'] is False
    assert result['architect']['re_executed'] is False
    assert result['lld_alignment']['re_executed'] is True
```

---

## Test Fixtures and Utilities

### Common Test Fixtures

```python
# tests/fixtures/pr_data.py
"""Common PR data fixtures for testing."""

def get_sample_pr_data(pr_number=100, **overrides):
    """Generate sample PR data with optional overrides."""
    default_data = {
        "number": pr_number,
        "title": f"Test PR #{pr_number}",
        "state": "open",
        "user": {
            "login": "test-developer",
            "email": "dev@test.com"
        },
        "base": {
            "ref": "main",
            "repo": {
                "name": "test-repo",
                "full_name": "tonic-scm/test-repo",
                "owner": {"login": "tonic-scm"}
            }
        },
        "head": {
            "ref": "feature/test",
            "sha": f"abc{pr_number}"
        },
        "html_url": f"https://github.com/tonic-scm/test-repo/pull/{pr_number}",
        "changed_files": 3,
        "additions": 100,
        "deletions": 20,
        "body": "Test PR description"
    }

    return {**default_data, **overrides}


def get_sample_violations(count=3):
    """Generate sample code violations."""
    return [
        {
            'file': f'src/File{i}.java',
            'line': 10 + i,
            'type': 'NAMING_CONVENTION',
            'severity': 'MAJOR',
            'description': f'Violation {i}',
            'pattern': 'Java Naming Convention'
        }
        for i in range(count)
    ]
```

### Test Utilities

```python
# tests/utils/test_helpers.py
"""Test helper utilities."""

import asyncio
from functools import wraps

def async_timeout(seconds):
    """Decorator to enforce timeout on async tests."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=seconds
            )
        return wrapper
    return decorator


def assert_pr_comment_contains(mock_github, pr_number, expected_text):
    """Assert PR comment contains expected text."""
    comment_calls = [
        call for call in mock_github.request_history
        if f'/issues/{pr_number}/comments' in call.url and call.method == 'POST'
    ]

    assert len(comment_calls) > 0, "No PR comments posted"

    comment_bodies = [call.json()['body'] for call in comment_calls]
    assert any(expected_text in body for body in comment_bodies), \
        f"Expected text '{expected_text}' not found in any PR comment"


def assert_jira_ticket_created(mock_jira, expected_summary_substring):
    """Assert Jira ticket was created with expected summary."""
    create_calls = [
        call for call in mock_jira.request_history
        if '/issue' in call.url and call.method == 'POST'
    ]

    assert len(create_calls) > 0, "No Jira tickets created"

    summaries = [
        call.json()['fields']['summary']
        for call in create_calls
    ]

    assert any(expected_summary_substring in summary for summary in summaries), \
        f"Expected summary substring '{expected_summary_substring}' not found"
```

---

## Running the Tests

### Local Execution

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/test_full_pipeline.py -v

# Run tests with specific marker
pytest -m integration -v
pytest -m performance -v

# Run with coverage report
pytest tests/integration/ --cov=src --cov-report=html

# Run tests in parallel
pytest tests/integration/ -n auto
```

### Environment Setup Script

```bash
#!/bin/bash
# scripts/setup_test_env.sh

echo "Setting up integration test environment..."

# Start LocalStack for AWS services
docker run -d --name localstack \
  -p 4566:4566 \
  -e SERVICES=dynamodb,sqs \
  localstack/localstack

# Wait for LocalStack to be ready
sleep 5

# Create DynamoDB table
aws --endpoint-url=http://localhost:4566 dynamodb create-table \
  --table-name pr-review-state-test \
  --attribute-definitions \
    AttributeName=pr_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=N \
  --key-schema \
    AttributeName=pr_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# Start Redis
docker run -d --name redis-test -p 6379:6379 redis:7

echo "Test environment ready!"
```

### Teardown Script

```bash
#!/bin/bash
# scripts/teardown_test_env.sh

echo "Tearing down test environment..."

# Stop and remove containers
docker stop localstack redis-test
docker rm localstack redis-test

echo "Test environment cleaned up!"
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    services:
      localstack:
        image: localstack/localstack
        ports:
          - 4566:4566
        env:
          SERVICES: dynamodb,sqs

      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Setup test environment
        run: |
          chmod +x scripts/setup_test_env.sh
          ./scripts/setup_test_env.sh

      - name: Run integration tests
        env:
          DYNAMODB_ENDPOINT: http://localhost:4566
          REDIS_HOST: localhost
          REDIS_PORT: 6379
        run: |
          pytest tests/integration/ \
            -v \
            --cov=src \
            --cov-report=xml \
            --cov-report=html \
            --junitxml=test-results/junit.xml

      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: integration

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: test-results/

      - name: Teardown test environment
        if: always()
        run: |
          chmod +x scripts/teardown_test_env.sh
          ./scripts/teardown_test_env.sh
```

### Test Configuration

```ini
# pytest.ini
[pytest]
markers =
    integration: Integration tests requiring external services
    performance: Performance and SLA validation tests
    slow: Slow-running tests (>5 seconds)
    skip_ci: Tests to skip in CI environment

testpaths = tests/integration
python_files = test_*.py
python_classes = Test*
python_functions = test_*

asyncio_mode = auto

# Logging
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# Coverage
addopts =
    --strict-markers
    --tb=short
    --disable-warnings
```

---

## Cleanup Procedures

### Test Data Cleanup

```python
# tests/conftest.py (additional fixtures)

@pytest.fixture(scope="function", autouse=True)
def cleanup_test_data(dynamodb_table, redis_client):
    """Automatically cleanup test data after each test."""
    yield

    # Cleanup DynamoDB
    try:
        scan = dynamodb_table.scan()
        for item in scan.get('Items', []):
            dynamodb_table.delete_item(
                Key={
                    'pr_id': item['pr_id'],
                    'timestamp': item['timestamp']
                }
            )
    except Exception as e:
        print(f"DynamoDB cleanup error: {e}")

    # Cleanup Redis
    try:
        redis_client.flushdb()
    except Exception as e:
        print(f"Redis cleanup error: {e}")
```

### Mock Cleanup

```python
@pytest.fixture(scope="function", autouse=True)
def reset_mocks(mock_github_api, mock_confluence_api, mock_jira_api):
    """Reset all mocks between tests."""
    yield

    mock_github_api.reset()
    mock_confluence_api.reset()
    mock_jira_api.reset()
```

---

## Summary

This integration testing documentation provides:

1. **Comprehensive Test Coverage**: All major integration points covered
2. **Realistic Test Scenarios**: Happy path, failures, edge cases, and performance tests
3. **Production-Ready Infrastructure**: LocalStack, FakeRedis, comprehensive mocking
4. **CI/CD Integration**: GitHub Actions workflow with proper service containers
5. **Maintainability**: Reusable fixtures, utilities, and cleanup procedures

### Test Execution Matrix

| Test Category | Test Count | Avg Duration | Critical Path |
|---------------|------------|--------------|---------------|
| Full Pipeline | 4 | 15s | Yes |
| Agent-to-Agent | 3 | 8s | Yes |
| GitHub Actions | 3 | 5s | Yes |
| Jira Integration | 4 | 10s | Yes |
| State Management | 3 | 6s | No |
| **Total** | **17** | **~2 min** | - |

### Next Steps

1. Implement test fixtures in `tests/fixtures/`
2. Set up LocalStack and Redis test containers
3. Configure CI/CD pipeline with GitHub Actions
4. Run initial test suite and address failures
5. Establish coverage benchmarks (target: >90% for integration tests)
6. Document test failure triage process

---

**End of Integration Testing Documentation**
