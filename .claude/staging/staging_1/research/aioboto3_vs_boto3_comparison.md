# Research: aioboto3 vs boto3 for AWS Bedrock Integration

## Research Overview

| Field | Value |
|-------|-------|
| **Research Date** | 2026-01-28 |
| **Topic** | Asynchronous vs Synchronous AWS Bedrock SDK |
| **Options Compared** | aioboto3 (async) vs boto3 (sync) |
| **Recommendation** | **aioboto3** for parallel agent execution |

---

## Executive Summary

This research compares synchronous boto3 with asynchronous aioboto3 for invoking Claude models via AWS Bedrock in the PR Peer Review system. The investigation reveals that aioboto3 v13.1.0+ fully supports the Bedrock Converse API, enabling true async operations without thread pool workarounds.

Performance benchmarks show significant advantages for async approaches: aioboto3 achieves 5.3x faster execution than synchronous boto3 for I/O-bound operations like LLM inference. For PR review workflows running multiple agents sequentially, async execution enables parallel invocation—reducing total pipeline time from ~120 seconds (sequential) to ~45 seconds (parallel).

The key architectural benefit is concurrent agent execution. With aioboto3, Code Quality, Architect, and Pattern Matching agents can run simultaneously using `asyncio.gather()`, rather than waiting for each to complete. This is particularly valuable when agents are independent (no data dependencies).

Implementation complexity is minimal: aioboto3 maintains API compatibility with boto3, requiring only `await` prefixes and async context managers. The pattern `async with session.client("bedrock-runtime") as client: await client.converse(...)` directly mirrors synchronous usage.

However, for GitHub Actions workflows where agents run as separate jobs (already parallel at the workflow level), the benefits are reduced. aioboto3's value increases when multiple Bedrock calls occur within a single job—such as chunked diff processing or multi-model ensemble approaches.

**Recommendation**: Adopt aioboto3 for the agent runner implementation. The performance gains for parallel Bedrock calls within jobs justify the minimal added complexity, and it positions the codebase for future enhancements like ensemble reviews or parallel chunk processing.

---

## Table of Contents

1. [Comparison Matrix](#1-comparison-matrix)
2. [Performance Benchmarks](#2-performance-benchmarks)
3. [aioboto3 Bedrock Support Status](#3-aioboto3-bedrock-support-status)
4. [Implementation Patterns](#4-implementation-patterns)
5. [Use Case Analysis](#5-use-case-analysis)
6. [Recommendation](#6-recommendation)

---

## 1. Comparison Matrix

### Feature Comparison

| Feature | boto3 (Sync) | aioboto3 (Async) |
|---------|--------------|------------------|
| **Execution Model** | Blocking, sequential | Non-blocking, concurrent |
| **Bedrock Support** | ✅ Full | ✅ Full (v13.1.0+) |
| **Converse API** | ✅ Yes | ✅ Yes |
| **Streaming** | ✅ Yes | ✅ Yes |
| **OIDC Auth** | ✅ Yes | ✅ Yes |
| **API Compatibility** | Native | Drop-in (add `await`) |
| **Parallel Calls** | ThreadPoolExecutor | `asyncio.gather()` |
| **Learning Curve** | Low | Medium |
| **Dependencies** | boto3, botocore | aioboto3, aiobotocore, aiohttp |
| **PyPI Package** | boto3 | aioboto3 (v15.5.0 latest) |

### When to Use Each

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Single Bedrock call per job | **boto3** | Simpler, no async overhead |
| Multiple parallel Bedrock calls | **aioboto3** | True concurrent execution |
| Chunked diff processing | **aioboto3** | Process chunks in parallel |
| Ensemble/multi-model review | **aioboto3** | Call Haiku + Sonnet simultaneously |
| Streaming responses | **Either** | Both support streaming |
| GitHub Actions (separate jobs) | **boto3** | Parallelism at workflow level |
| Lambda with concurrent requests | **aioboto3** | Better resource utilization |

---

## 2. Performance Benchmarks

### Benchmark Results from Research

**Source**: [Joel McCoy - boto3 Performance Adventures](https://joelmccoy.medium.com/python-and-boto3-performance-adventures-synchronous-vs-asynchronous-aws-api-interaction-22f625ec6909)

| Approach | Elapsed Time | Speedup vs Sync |
|----------|--------------|-----------------|
| Synchronous boto3 | 7.62 seconds | 1x (baseline) |
| Async boto3 (ThreadPoolExecutor) | 0.83 seconds | **9.2x faster** |
| Async aioboto3 | 1.43 seconds | **5.3x faster** |

**Analysis**:
- Both async approaches significantly outperform synchronous
- ThreadPoolExecutor can be faster for certain workloads (TLS connection reuse)
- aioboto3 provides cleaner async code without thread management

### DynamoDB Benchmark (I/O Bound Operations)

**Source**: [Aditya Dubey - Faster API Calls for DynamoDB](https://adityadubey.tech/techniques-for-faster-api-calls-for-dynamodb-in-python)

| Approach | Time for 1000 put_item |
|----------|------------------------|
| Synchronous boto3 | ~30 seconds |
| ThreadPoolExecutor | ~8 seconds |
| aioboto3 | **2.9 seconds** |

**Analysis**: For I/O-bound operations (like LLM inference), aioboto3 provides the best performance.

### Estimated Impact for PR Review Pipeline

| Pipeline Configuration | Code Quality | Architect | LLD | Total Time |
|------------------------|--------------|-----------|-----|------------|
| **Sequential (boto3)** | 30s | 45s | 45s | **120s** |
| **Parallel (aioboto3)** | - | - | - | **~45s** |
| **Speedup** | - | - | - | **2.7x** |

*Note: Actual speedup depends on which agents can run in parallel (data dependencies).*

---

## 3. aioboto3 Bedrock Support Status

### Current Status: ✅ Fully Supported

**Source**: [GitHub Issue #341 - Support for Bedrock Converse](https://github.com/terricain/aioboto3/issues/341)

| Feature | Status | Since Version |
|---------|--------|---------------|
| bedrock-runtime service | ✅ Supported | v12.x |
| invoke_model | ✅ Supported | v12.x |
| invoke_model_with_response_stream | ✅ Supported | v12.x |
| **converse** | ✅ Supported | **v13.1.0** |
| converse_stream | ✅ Supported | v13.1.0 |

### Version Requirements

```
aioboto3>=13.1.0    # For Converse API support
aiobotocore>=2.13.0 # Underlying async implementation
aiohttp>=3.9.0      # HTTP client
```

### Known Issues (Resolved)

1. **Issue**: `UnknownServiceError: Unknown service: 'bedrock-runtime'`
   - **Cause**: Old aiobotocore version
   - **Fix**: Update to aioboto3>=13.1.0

2. **Issue**: `converse` method not found
   - **Cause**: aiobotocore dependency too old
   - **Fix**: Bump aioboto3 to v13.1.0+

---

## 4. Implementation Patterns

### Pattern 1: Basic Async Bedrock Call (aioboto3)

```python
import aioboto3
import asyncio

async def invoke_claude_async(prompt: str, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"):
    """Invoke Claude using aioboto3 async client."""
    session = aioboto3.Session()

    async with session.client("bedrock-runtime", region_name="us-east-1") as client:
        response = await client.converse(
            modelId=model_id,
            messages=[
                {"role": "user", "content": [{"text": prompt}]}
            ],
            inferenceConfig={
                "maxTokens": 4096,
                "temperature": 0.2
            }
        )

        return response['output']['message']['content'][0]['text']

# Run
result = asyncio.run(invoke_claude_async("Review this code..."))
```

### Pattern 2: Parallel Agent Execution

```python
import aioboto3
import asyncio
from typing import Dict, Any

async def run_agent(session, agent_name: str, prompt: str, model_id: str) -> Dict[str, Any]:
    """Run a single agent asynchronously."""
    async with session.client("bedrock-runtime", region_name="us-east-1") as client:
        response = await client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 4096, "temperature": 0.2}
        )

        return {
            "agent": agent_name,
            "result": response['output']['message']['content'][0]['text'],
            "usage": response.get('usage', {})
        }

async def run_parallel_agents(pr_context: dict) -> list:
    """Run multiple agents in parallel."""
    session = aioboto3.Session()

    # Define agents to run in parallel
    tasks = [
        run_agent(session, "code_quality", f"Review code quality:\n{pr_context['diff']}",
                  "anthropic.claude-3-haiku-20240307-v1:0"),
        run_agent(session, "security", f"Review security issues:\n{pr_context['diff']}",
                  "anthropic.claude-3-haiku-20240307-v1:0"),
        run_agent(session, "patterns", f"Detect patterns:\n{pr_context['diff']}",
                  "anthropic.claude-3-5-sonnet-20241022-v2:0"),
    ]

    # Execute all agents concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results

# Run parallel agents
results = asyncio.run(run_parallel_agents({"diff": "...code diff..."}))
```

### Pattern 3: Chunked Diff Processing

```python
async def process_chunks_parallel(chunks: list[str], model_id: str) -> list:
    """Process multiple diff chunks in parallel."""
    session = aioboto3.Session()

    async def process_chunk(chunk: str, chunk_num: int):
        async with session.client("bedrock-runtime", region_name="us-east-1") as client:
            response = await client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": f"Review chunk {chunk_num}:\n{chunk}"}]}],
                inferenceConfig={"maxTokens": 4096, "temperature": 0.2}
            )
            return response['output']['message']['content'][0]['text']

    # Process all chunks in parallel
    tasks = [process_chunk(chunk, i) for i, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks)

    return results
```

### Pattern 4: Synchronous Comparison (boto3)

```python
import boto3

def invoke_claude_sync(prompt: str, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"):
    """Invoke Claude using synchronous boto3."""
    client = boto3.client("bedrock-runtime", region_name="us-east-1")

    response = client.converse(
        modelId=model_id,
        messages=[
            {"role": "user", "content": [{"text": prompt}]}
        ],
        inferenceConfig={
            "maxTokens": 4096,
            "temperature": 0.2
        }
    )

    return response['output']['message']['content'][0]['text']
```

### Pattern 5: Hybrid Approach (boto3 + ThreadPoolExecutor)

```python
import boto3
import asyncio
from concurrent.futures import ThreadPoolExecutor

def invoke_claude_sync(client, prompt: str, model_id: str):
    """Synchronous invocation."""
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0.2}
    )
    return response['output']['message']['content'][0]['text']

async def run_parallel_with_threads(prompts: list[str], model_id: str):
    """Run parallel calls using ThreadPoolExecutor."""
    client = boto3.client("bedrock-runtime", region_name="us-east-1")

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = [
            loop.run_in_executor(executor, invoke_claude_sync, client, prompt, model_id)
            for prompt in prompts
        ]
        results = await asyncio.gather(*tasks)

    return results
```

---

## 5. Use Case Analysis

### Use Case 1: GitHub Actions - Separate Jobs (Current Design)

```yaml
jobs:
  code-quality:
    # Runs independently
  architect:
    needs: code-quality
    # Waits for code-quality
  lld-alignment:
    needs: architect
    # Waits for architect
```

**Analysis**:
- Parallelism handled at workflow level
- Each job has single Bedrock call
- **Recommendation**: boto3 sufficient (simpler)

### Use Case 2: Single Job - Multiple Agents

```yaml
jobs:
  review:
    steps:
      - name: Run all agents
        run: python run_all_agents.py
```

**Analysis**:
- Multiple Bedrock calls in single process
- Agents can run concurrently
- **Recommendation**: aioboto3 (significant speedup)

### Use Case 3: Large PR - Chunked Processing

```python
# PR diff is 200KB, split into 4 chunks
chunks = split_diff(pr_diff, max_chars=50000)
# Process all chunks in parallel
results = await process_chunks_parallel(chunks)
# Aggregate results
final_result = aggregate_chunk_results(results)
```

**Analysis**:
- 4 sequential calls = 4 * 30s = 120s
- 4 parallel calls = 30s (+ overhead) ≈ 35s
- **Recommendation**: aioboto3 (3.4x speedup)

### Use Case 4: Ensemble Review (Multi-Model)

```python
# Get opinions from multiple models
results = await asyncio.gather(
    invoke_claude_async(prompt, "anthropic.claude-3-haiku-20240307-v1:0"),
    invoke_claude_async(prompt, "anthropic.claude-3-5-sonnet-20241022-v2:0"),
)
# Combine insights from both models
ensemble_result = combine_model_outputs(results)
```

**Analysis**:
- Sequential: 30s + 45s = 75s
- Parallel: max(30s, 45s) = 45s
- **Recommendation**: aioboto3 (1.7x speedup)

---

## 6. Recommendation

### Decision Matrix

| Factor | boto3 | aioboto3 | Winner |
|--------|-------|----------|--------|
| **Simplicity** | ✅ Simpler | More complex | boto3 |
| **Performance (parallel)** | Needs threads | Native async | **aioboto3** |
| **Bedrock support** | Full | Full | Tie |
| **Future-proofing** | Limited | Extensible | **aioboto3** |
| **Chunk processing** | Sequential | Parallel | **aioboto3** |
| **Ensemble models** | Sequential | Parallel | **aioboto3** |
| **Single call per job** | ✅ Sufficient | Overkill | boto3 |

### Final Recommendation: **Use aioboto3**

**Rationale**:
1. **Performance**: 2-5x speedup for parallel operations
2. **Flexibility**: Enables future enhancements (ensemble, chunking)
3. **Clean async**: Native asyncio without thread pool complexity
4. **API compatibility**: Minimal code changes from boto3
5. **Production ready**: Converse API fully supported since v13.1.0

### Implementation Approach

1. **Update requirements.txt**:
```
aioboto3>=13.1.0
aiobotocore>=2.13.0
aiohttp>=3.9.0
```

2. **Refactor agent runner** to use async patterns
3. **Enable parallel chunk processing** for large PRs
4. **Consider ensemble reviews** as future enhancement

---

## Sources

- [aioboto3 PyPI](https://pypi.org/project/aioboto3/) - Package information
- [aioboto3 GitHub Issue #341](https://github.com/terricain/aioboto3/issues/341) - Converse API support
- [Joel McCoy - boto3 Performance Adventures](https://joelmccoy.medium.com/python-and-boto3-performance-adventures-synchronous-vs-asynchronous-aws-api-interaction-22f625ec6909) - Benchmarks
- [Trek10 - Parallelizing AWS API calls](https://www.trek10.com/blog/aws-lambda-python-asyncio) - Lambda async patterns
- [aioboto3 Usage Documentation](https://aioboto3.readthedocs.io/en/latest/usage.html) - Usage patterns
- [AWS re:Post - Async Bedrock](https://repost.aws/questions/QUbbSmIdRQS9W_xWFW97J5Vg/async-bedrock-invoke-model) - Community discussion

---

**Research Completed**: 2026-01-28
