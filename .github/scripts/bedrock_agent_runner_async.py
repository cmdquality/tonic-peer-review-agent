#!/usr/bin/env python3
"""
AWS Bedrock Agent Runner (Async Version) for PR Peer Review

This script executes peer review agents using Claude via AWS Bedrock
with asynchronous operations for improved performance.

Features:
- Async Bedrock calls using aioboto3
- Parallel agent execution with asyncio.gather()
- Parallel chunk processing for large PRs
- Concurrent multi-model ensemble support

Usage:
    python bedrock_agent_runner_async.py --agent code_quality --pr 123
    python bedrock_agent_runner_async.py --parallel --pr 123  # Run all agents in parallel

Requirements:
    aioboto3>=13.1.0
    aiobotocore>=2.13.0
    aiohttp>=3.9.0

Environment Variables:
    AWS_REGION: AWS region for Bedrock (default: us-east-1)
    GITHUB_TOKEN: GitHub token for API access
"""

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Model configurations
MODELS = {
    "haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "sonnet-4": "anthropic.claude-sonnet-4-20250514-v1:0",
    "opus": "anthropic.claude-opus-4-20250514-v1:0",
}

DEFAULT_MODEL = "haiku"

# Agent configurations
AGENTS = {
    "code_quality": {
        "name": "Code Best Practices Agent",
        "prompt_file": "agents/code_best_practises_agent_spec.md",
        "model": "haiku",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "architect": {
        "name": "Architect Best Practices Agent",
        "prompt_file": "agents/architect_best_practises_agent_spec.md",
        "model": "sonnet",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "lld_alignment": {
        "name": "LLD Alignment Review Agent",
        "prompt_file": "agents/lld_alignment_review_agent_spec.md",
        "model": "sonnet",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "pattern_matching": {
        "name": "Pattern Matching Agent",
        "prompt_file": "agents/pattern_matching_agent_spec.md",
        "model": "haiku",
        "temperature": 0.1,
        "max_tokens": 2048,
    },
    "jira_integration": {
        "name": "Jira Integration Agent",
        "prompt_file": "agents/jira_integration_agent.md",
        "model": "haiku",
        "temperature": 0.1,
        "max_tokens": 2048,
    },
}


class AsyncBedrockAgentRunner:
    """Runs peer review agents using AWS Bedrock Claude models asynchronously."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize the async Bedrock client configuration."""
        self.region = region
        self.config = Config(
            retries={
                'max_attempts': 5,
                'mode': 'adaptive'
            },
            connect_timeout=10,
            read_timeout=120
        )
        self.session = aioboto3.Session()
        self.repo_root = self._find_repo_root()

    def _find_repo_root(self) -> Path:
        """Find the repository root directory."""
        current = Path.cwd()
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        return Path.cwd()

    def _load_agent_prompt(self, agent_name: str) -> str:
        """Load the agent specification/prompt from file."""
        if agent_name not in AGENTS:
            raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENTS.keys())}")

        agent_config = AGENTS[agent_name]
        prompt_path = self.repo_root / agent_config["prompt_file"]

        if not prompt_path.exists():
            logger.warning(f"Agent prompt file not found: {prompt_path}")
            return self._get_default_prompt(agent_name)

        return prompt_path.read_text(encoding='utf-8')

    def _get_default_prompt(self, agent_name: str) -> str:
        """Get a default prompt for an agent if file doesn't exist."""
        prompts = {
            "code_quality": """You are an expert code reviewer. Analyze the code for:
1. Code quality and best practices
2. Potential bugs and errors
3. Security vulnerabilities
4. Performance issues
5. Naming conventions and style

Return your analysis as JSON with this structure:
{
    "status": "PASS" or "FAIL",
    "violations_count": number,
    "violations": [
        {
            "type": "bug|security|style|performance",
            "severity": "LOW|MEDIUM|HIGH|CRITICAL",
            "file": "path/to/file",
            "line": line_number,
            "description": "What the issue is",
            "suggestion": "How to fix it"
        }
    ],
    "summary": "Brief overall assessment"
}""",
            "architect": """You are a software architect reviewing code for architectural patterns.
Analyze the code to detect:
1. New architectural patterns not in the approved library
2. Pattern deviations from standards
3. Structural improvements

Return your analysis as JSON with this structure:
{
    "status": "NO_NEW_PATTERN" or "NEW_PATTERN_DETECTED",
    "new_pattern_found": boolean,
    "patterns": [
        {
            "name": "Pattern name",
            "file": "path/to/file",
            "confidence": 0.0-1.0,
            "description": "Pattern description"
        }
    ],
    "summary": "Brief assessment"
}""",
            "lld_alignment": """You are reviewing code for alignment with Low-Level Design specifications.
Check if the implementation matches the documented LLD.

Return your analysis as JSON with this structure:
{
    "status": "LLD_COMPLIANT" or "LLD_DEVIATION_FOUND",
    "deviations": [
        {
            "lld_section": "Section reference",
            "expected": "What LLD specifies",
            "actual": "What was implemented",
            "file": "path/to/file",
            "severity": "LOW|MEDIUM|HIGH"
        }
    ],
    "summary": "Brief assessment"
}""",
        }
        return prompts.get(agent_name, "You are a code review assistant. Analyze the provided code.")

    def _get_pr_context(self, pr_number: int) -> dict:
        """Fetch PR context from GitHub (synchronous - runs once)."""
        try:
            pr_info = subprocess.run(
                ['gh', 'pr', 'view', str(pr_number), '--json',
                 'title,body,additions,deletions,changedFiles,files,author'],
                capture_output=True, text=True, check=True
            )
            pr_data = json.loads(pr_info.stdout)

            diff_result = subprocess.run(
                ['gh', 'pr', 'diff', str(pr_number)],
                capture_output=True, text=True, check=True
            )
            pr_diff = diff_result.stdout

            return {
                "pr_number": pr_number,
                "title": pr_data.get("title", ""),
                "description": pr_data.get("body", ""),
                "author": pr_data.get("author", {}).get("login", "unknown"),
                "additions": pr_data.get("additions", 0),
                "deletions": pr_data.get("deletions", 0),
                "files_changed": pr_data.get("changedFiles", 0),
                "files": [f.get("path") for f in pr_data.get("files", [])],
                "diff": pr_diff
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch PR context: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse PR data: {e}")
            raise

    def _chunk_diff(self, diff: str, max_chars: int = 50000) -> List[str]:
        """Split large diffs into chunks by file."""
        if len(diff) <= max_chars:
            return [diff]

        file_pattern = r'(diff --git a/.*?(?=diff --git a/|\Z))'
        file_diffs = re.findall(file_pattern, diff, re.DOTALL)

        chunks = []
        current_chunk = ""

        for file_diff in file_diffs:
            if len(current_chunk) + len(file_diff) > max_chars and current_chunk:
                chunks.append(current_chunk)
                current_chunk = file_diff
            else:
                current_chunk += file_diff

        if current_chunk:
            chunks.append(current_chunk)

        logger.info(f"Split diff into {len(chunks)} chunks")
        return chunks

    def _create_review_prompt(self, agent_prompt: str, pr_context: dict) -> str:
        """Create the full prompt for the review."""
        return f"""{agent_prompt}

<pull_request>
<metadata>
PR Number: #{pr_context['pr_number']}
Title: {pr_context['title']}
Author: {pr_context['author']}
Files Changed: {pr_context['files_changed']}
Additions: {pr_context['additions']}
Deletions: {pr_context['deletions']}
</metadata>

<description>
{pr_context['description'] or 'No description provided'}
</description>

<files>
{chr(10).join(pr_context['files'][:50])}
</files>

<diff>
{pr_context['diff'][:100000]}
</diff>
</pull_request>

Analyze this pull request and provide your review as valid JSON only. Do not include any markdown formatting or code blocks - just the raw JSON object."""

    async def invoke_agent(
        self,
        agent_name: str,
        pr_context: dict,
        model_override: Optional[str] = None
    ) -> dict:
        """
        Invoke a peer review agent using Bedrock Claude asynchronously.

        Args:
            agent_name: Name of the agent to run
            pr_context: PR context dictionary
            model_override: Optional model to use instead of agent default

        Returns:
            Agent response as dictionary
        """
        agent_config = AGENTS[agent_name]
        model_key = model_override or agent_config["model"]
        model_id = MODELS.get(model_key, MODELS[DEFAULT_MODEL])

        logger.info(f"Running {agent_config['name']} with model {model_id} (async)")

        agent_prompt = self._load_agent_prompt(agent_name)
        full_prompt = self._create_review_prompt(agent_prompt, pr_context)

        # Handle large diffs by chunking
        if len(full_prompt) > 150000:
            logger.warning("Large PR detected, using parallel chunked analysis")
            return await self._invoke_chunked_parallel(agent_name, agent_config, model_id, pr_context)

        async with self.session.client(
            "bedrock-runtime",
            region_name=self.region,
            config=self.config
        ) as client:
            try:
                response = await client.converse(
                    modelId=model_id,
                    messages=[
                        {
                            "role": "user",
                            "content": [{"text": full_prompt}]
                        }
                    ],
                    inferenceConfig={
                        "maxTokens": agent_config["max_tokens"],
                        "temperature": agent_config["temperature"],
                        "topP": 0.9
                    }
                )

                response_text = response['output']['message']['content'][0]['text']

                usage = response.get('usage', {})
                logger.info(f"Tokens used - Input: {usage.get('inputTokens', 'N/A')}, "
                           f"Output: {usage.get('outputTokens', 'N/A')}")

                return self._parse_json_response(response_text, agent_name)

            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ThrottlingException':
                    logger.error("Rate limit exceeded. Retrying with backoff...")
                    # aioboto3 handles retries via config, but we can add custom logic
                elif error_code == 'ValidationException':
                    logger.error(f"Invalid request: {e}")
                elif error_code == 'AccessDeniedException':
                    logger.error("Access denied. Check IAM permissions for Bedrock.")
                raise

    async def _invoke_chunked_parallel(
        self,
        agent_name: str,
        agent_config: dict,
        model_id: str,
        pr_context: dict
    ) -> dict:
        """Handle large PRs by processing chunks in parallel."""
        chunks = self._chunk_diff(pr_context['diff'])
        agent_prompt = self._load_agent_prompt(agent_name)

        async def process_chunk(chunk: str, chunk_num: int) -> dict:
            """Process a single chunk asynchronously."""
            chunk_context = pr_context.copy()
            chunk_context['diff'] = chunk

            full_prompt = self._create_review_prompt(agent_prompt, chunk_context)

            async with self.session.client(
                "bedrock-runtime",
                region_name=self.region,
                config=self.config
            ) as client:
                try:
                    response = await client.converse(
                        modelId=model_id,
                        messages=[
                            {"role": "user", "content": [{"text": full_prompt}]}
                        ],
                        inferenceConfig={
                            "maxTokens": agent_config["max_tokens"],
                            "temperature": agent_config["temperature"],
                            "topP": 0.9
                        }
                    )

                    response_text = response['output']['message']['content'][0]['text']
                    return self._parse_json_response(response_text, agent_name)

                except ClientError as e:
                    logger.error(f"Error processing chunk {chunk_num}: {e}")
                    return {"status": "ERROR", "chunk": chunk_num, "error": str(e)}

        # Process all chunks in parallel
        logger.info(f"Processing {len(chunks)} chunks in parallel...")
        tasks = [process_chunk(chunk, i) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, dict) and r.get("status") != "ERROR"]

        return self._aggregate_chunk_results(valid_results, agent_name)

    async def run_agents_parallel(
        self,
        agent_names: List[str],
        pr_context: dict,
        model_override: Optional[str] = None
    ) -> Dict[str, dict]:
        """
        Run multiple agents in parallel.

        Args:
            agent_names: List of agent names to run
            pr_context: PR context dictionary
            model_override: Optional model override for all agents

        Returns:
            Dictionary mapping agent names to their results
        """
        logger.info(f"Running {len(agent_names)} agents in parallel...")

        async def run_single(agent_name: str) -> tuple:
            result = await self.invoke_agent(agent_name, pr_context, model_override)
            return agent_name, result

        tasks = [run_single(name) for name in agent_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Agent failed with exception: {result}")
            else:
                agent_name, agent_result = result
                output[agent_name] = agent_result

        return output

    def _aggregate_chunk_results(self, results: List[dict], agent_name: str) -> dict:
        """Aggregate results from multiple chunks."""
        if not results:
            return {"status": "ERROR", "error": "No results from chunk processing"}

        if agent_name == "code_quality":
            all_violations = []
            for r in results:
                all_violations.extend(r.get("violations", []))

            status = "FAIL" if all_violations else "PASS"
            return {
                "status": status,
                "violations_count": len(all_violations),
                "violations": all_violations,
                "summary": f"Aggregated review from {len(results)} chunks"
            }

        elif agent_name == "architect":
            all_patterns = []
            for r in results:
                all_patterns.extend(r.get("patterns", []))

            new_pattern_found = any(r.get("new_pattern_found", False) for r in results)
            status = "NEW_PATTERN_DETECTED" if new_pattern_found else "NO_NEW_PATTERN"

            return {
                "status": status,
                "new_pattern_found": new_pattern_found,
                "patterns": all_patterns,
                "summary": f"Aggregated analysis from {len(results)} chunks"
            }

        result = results[0]
        result["_note"] = f"Aggregated from {len(results)} chunks"
        return result

    def _parse_json_response(self, response_text: str, agent_name: str) -> dict:
        """Parse JSON from Claude's response."""
        cleaned = re.sub(r'```(?:json)?\s*', '', response_text)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return self._get_default_response(agent_name, response_text)

    def _get_default_response(self, agent_name: str, raw_text: str) -> dict:
        """Get default response structure when JSON parsing fails."""
        defaults = {
            "code_quality": {
                "status": "ERROR",
                "violations_count": 0,
                "violations": [],
                "summary": "Failed to parse response. Raw output available.",
                "_raw": raw_text[:1000]
            },
            "architect": {
                "status": "ERROR",
                "new_pattern_found": False,
                "patterns": [],
                "summary": "Failed to parse response. Raw output available.",
                "_raw": raw_text[:1000]
            },
            "lld_alignment": {
                "status": "ERROR",
                "deviations": [],
                "summary": "Failed to parse response. Raw output available.",
                "_raw": raw_text[:1000]
            },
        }
        return defaults.get(agent_name, {"status": "ERROR", "_raw": raw_text[:1000]})


async def main_async():
    """Async main entry point."""
    parser = argparse.ArgumentParser(description='Run PR review agent using AWS Bedrock Claude (async)')
    parser.add_argument('--agent', choices=list(AGENTS.keys()),
                       help='Agent to run (single agent mode)')
    parser.add_argument('--parallel', action='store_true',
                       help='Run all agents in parallel')
    parser.add_argument('--agents', nargs='+', choices=list(AGENTS.keys()),
                       help='Specific agents to run in parallel')
    parser.add_argument('--pr', required=True, type=int,
                       help='PR number to review')
    parser.add_argument('--model', choices=list(MODELS.keys()),
                       help='Override model selection')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region (default: us-east-1)')
    parser.add_argument('--output', choices=['json', 'summary'], default='json',
                       help='Output format')

    args = parser.parse_args()

    # Validate arguments
    if not args.agent and not args.parallel and not args.agents:
        parser.error("Must specify --agent, --parallel, or --agents")

    try:
        runner = AsyncBedrockAgentRunner(region=args.region)

        logger.info(f"Fetching PR #{args.pr} context...")
        pr_context = runner._get_pr_context(args.pr)
        logger.info(f"PR: {pr_context['title']} ({pr_context['files_changed']} files, "
                   f"+{pr_context['additions']}/-{pr_context['deletions']})")

        if args.parallel or args.agents:
            # Parallel execution
            agents_to_run = args.agents if args.agents else list(AGENTS.keys())
            results = await runner.run_agents_parallel(agents_to_run, pr_context, args.model)

            if args.output == 'json':
                print(json.dumps(results, indent=2))
            else:
                for agent_name, result in results.items():
                    print(f"\n{agent_name}: {result.get('status', 'UNKNOWN')}")
                    print(f"  Summary: {result.get('summary', 'No summary')}")

            # Determine overall status
            statuses = [r.get('status', 'ERROR') for r in results.values()]
            if any(s in ['FAIL', 'ERROR', 'LLD_DEVIATION_FOUND'] for s in statuses):
                sys.exit(1)
        else:
            # Single agent execution
            result = await runner.invoke_agent(args.agent, pr_context, args.model)

            if args.output == 'json':
                print(json.dumps(result, indent=2))
            else:
                print(f"Status: {result.get('status', 'UNKNOWN')}")
                print(f"Summary: {result.get('summary', 'No summary')}")

            status = result.get('status', 'ERROR')
            if status in ['FAIL', 'ERROR', 'LLD_DEVIATION_FOUND']:
                sys.exit(1)

        sys.exit(0)

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        sys.exit(1)


def main():
    """Synchronous entry point that runs the async main."""
    asyncio.run(main_async())


if __name__ == '__main__':
    main()
