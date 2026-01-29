#!/usr/bin/env python3
"""
AWS Bedrock Agent Runner for PR Peer Review

This script executes peer review agents using Claude via AWS Bedrock.
It's designed to run in GitHub Actions with OIDC authentication.

Usage:
    python bedrock_agent_runner.py --agent code_quality --pr 123

Environment Variables:
    AWS_REGION: AWS region for Bedrock (default: us-east-1)
    GITHUB_TOKEN: GitHub token for API access
    BEDROCK_MODEL_ID: Claude model to use (default: anthropic.claude-3-haiku-20240307-v1:0)
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

import boto3
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

# Default model - Haiku for cost efficiency
DEFAULT_MODEL = "haiku"

# Agent configurations
AGENTS = {
    "code_quality": {
        "name": "Code Best Practices Agent",
        "prompt_file": "agents/code_best_practises_agent_spec.md",
        "model": "haiku",  # Fast, cheap for standard reviews
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "architect": {
        "name": "Architect Best Practices Agent",
        "prompt_file": "agents/architect_best_practises_agent_spec.md",
        "model": "sonnet",  # More capable for pattern detection
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


class BedrockAgentRunner:
    """Runs peer review agents using AWS Bedrock Claude models."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize the Bedrock client with retry configuration."""
        self.region = region
        self.config = Config(
            retries={
                'max_attempts': 5,
                'mode': 'adaptive'  # Exponential backoff with jitter
            },
            connect_timeout=10,
            read_timeout=120  # 2 minutes for long responses
        )
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=region,
            config=self.config
        )
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
            # Return a basic prompt if file doesn't exist
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
        """Fetch PR context from GitHub."""
        import subprocess

        try:
            # Get PR details
            pr_info = subprocess.run(
                ['gh', 'pr', 'view', str(pr_number), '--json',
                 'title,body,additions,deletions,changedFiles,files,author'],
                capture_output=True, text=True, check=True
            )
            pr_data = json.loads(pr_info.stdout)

            # Get PR diff
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

    def _chunk_diff(self, diff: str, max_chars: int = 50000) -> list[str]:
        """Split large diffs into chunks by file."""
        if len(diff) <= max_chars:
            return [diff]

        # Split by file boundaries
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

    def invoke_agent(
        self,
        agent_name: str,
        pr_context: dict,
        model_override: Optional[str] = None
    ) -> dict:
        """
        Invoke a peer review agent using Bedrock Claude.

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

        logger.info(f"Running {agent_config['name']} with model {model_id}")

        # Load agent prompt
        agent_prompt = self._load_agent_prompt(agent_name)

        # Create full prompt
        full_prompt = self._create_review_prompt(agent_prompt, pr_context)

        # Handle large diffs by chunking
        if len(full_prompt) > 150000:  # ~37.5K tokens
            logger.warning("Large PR detected, using chunked analysis")
            return self._invoke_chunked(agent_name, agent_config, model_id, pr_context)

        try:
            response = self.client.converse(
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

            # Extract response
            response_text = response['output']['message']['content'][0]['text']

            # Log token usage
            usage = response.get('usage', {})
            logger.info(f"Tokens used - Input: {usage.get('inputTokens', 'N/A')}, "
                       f"Output: {usage.get('outputTokens', 'N/A')}")

            # Parse JSON response
            return self._parse_json_response(response_text, agent_name)

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ThrottlingException':
                logger.error("Rate limit exceeded. Consider using a different model or reducing request frequency.")
            elif error_code == 'ValidationException':
                logger.error(f"Invalid request: {e}")
            elif error_code == 'AccessDeniedException':
                logger.error("Access denied. Check IAM permissions for Bedrock.")
            raise

    def _invoke_chunked(
        self,
        agent_name: str,
        agent_config: dict,
        model_id: str,
        pr_context: dict
    ) -> dict:
        """Handle large PRs by chunking the diff."""
        chunks = self._chunk_diff(pr_context['diff'])
        all_results = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")

            chunk_context = pr_context.copy()
            chunk_context['diff'] = chunk

            agent_prompt = self._load_agent_prompt(agent_name)
            full_prompt = self._create_review_prompt(agent_prompt, chunk_context)

            try:
                response = self.client.converse(
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
                chunk_result = self._parse_json_response(response_text, agent_name)
                all_results.append(chunk_result)

            except ClientError as e:
                logger.error(f"Error processing chunk {i+1}: {e}")
                continue

        # Aggregate results
        return self._aggregate_chunk_results(all_results, agent_name)

    def _aggregate_chunk_results(self, results: list[dict], agent_name: str) -> dict:
        """Aggregate results from multiple chunks."""
        if not results:
            return {"status": "ERROR", "error": "No results from chunk processing"}

        if agent_name == "code_quality":
            # Aggregate violations
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
            # Aggregate patterns
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

        # Default: return first result with note
        result = results[0]
        result["_note"] = f"Aggregated from {len(results)} chunks"
        return result

    def _parse_json_response(self, response_text: str, agent_name: str) -> dict:
        """Parse JSON from Claude's response."""
        # Remove markdown code blocks if present
        cleaned = re.sub(r'```(?:json)?\s*', '', response_text)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}...")

            # Return a default structure based on agent type
            return self._get_default_response(agent_name, response_text)

    def _get_default_response(self, agent_name: str, raw_text: str) -> dict:
        """Get default response structure when JSON parsing fails."""
        defaults = {
            "code_quality": {
                "status": "ERROR",
                "violations_count": 0,
                "violations": [],
                "summary": f"Failed to parse response. Raw output available.",
                "_raw": raw_text[:1000]
            },
            "architect": {
                "status": "ERROR",
                "new_pattern_found": False,
                "patterns": [],
                "summary": f"Failed to parse response. Raw output available.",
                "_raw": raw_text[:1000]
            },
            "lld_alignment": {
                "status": "ERROR",
                "deviations": [],
                "summary": f"Failed to parse response. Raw output available.",
                "_raw": raw_text[:1000]
            },
        }
        return defaults.get(agent_name, {"status": "ERROR", "_raw": raw_text[:1000]})


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(description='Run PR review agent using AWS Bedrock Claude')
    parser.add_argument('--agent', required=True, choices=list(AGENTS.keys()),
                       help='Agent to run')
    parser.add_argument('--pr', required=True, type=int,
                       help='PR number to review')
    parser.add_argument('--model', choices=list(MODELS.keys()),
                       help='Override model selection')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region (default: us-east-1)')
    parser.add_argument('--output', choices=['json', 'summary'], default='json',
                       help='Output format')

    args = parser.parse_args()

    try:
        # Initialize runner
        runner = BedrockAgentRunner(region=args.region)

        # Get PR context
        logger.info(f"Fetching PR #{args.pr} context...")
        pr_context = runner._get_pr_context(args.pr)
        logger.info(f"PR: {pr_context['title']} ({pr_context['files_changed']} files, "
                   f"+{pr_context['additions']}/-{pr_context['deletions']})")

        # Run agent
        result = runner.invoke_agent(args.agent, pr_context, args.model)

        # Output result
        if args.output == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(f"Status: {result.get('status', 'UNKNOWN')}")
            print(f"Summary: {result.get('summary', 'No summary')}")
            if 'violations' in result:
                print(f"Violations: {len(result['violations'])}")
            if 'patterns' in result:
                print(f"Patterns detected: {len(result['patterns'])}")

        # Set exit code based on result
        status = result.get('status', 'ERROR')
        if status in ['FAIL', 'ERROR', 'LLD_DEVIATION_FOUND']:
            sys.exit(1)
        sys.exit(0)

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
