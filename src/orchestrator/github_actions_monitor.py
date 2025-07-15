"""
GitHub Actions Monitor and Auto-Fixer
Monitors CI/CD runs, analyzes failures, and automatically fixes issues
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import aiohttp
import structlog

from src.agents.azure_llm_client import llm_client
from src.common.config import settings

logger = structlog.get_logger()


class WorkflowStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    WAITING = "waiting"
    REQUESTED = "requested"
    PENDING = "pending"


class FailureType(Enum):
    SYNTAX_ERROR = "syntax_error"
    DEPENDENCY_ERROR = "dependency_error"
    TEST_FAILURE = "test_failure"
    BUILD_ERROR = "build_error"
    LINTING_ERROR = "linting_error"
    PERMISSION_ERROR = "permission_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class WorkflowFailure:
    """Details about a workflow failure"""
    workflow_run_id: int
    job_name: str
    step_name: str
    failure_type: FailureType
    error_message: str
    logs: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggested_fix: Optional[str] = None


@dataclass
class FixAttempt:
    """Record of a fix attempt"""
    failure: WorkflowFailure
    fix_description: str
    files_modified: Dict[str, str]  # path -> new content
    success: bool
    new_run_id: Optional[int] = None
    error: Optional[str] = None


class GitHubActionsMonitor:
    """Monitor and auto-fix GitHub Actions workflows"""
    
    def __init__(self, github_token: str, owner: str, repo: str):
        self.token = github_token
        self.owner = owner
        self.repo = repo
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.max_fix_attempts = 5
        self.fix_history: List[FixAttempt] = []
    
    async def monitor_and_fix_workflow(
        self,
        workflow_file: str = ".github/workflows/ci.yml",
        timeout_minutes: int = 30,
        auto_fix: bool = True
    ) -> Dict[str, Any]:
        """
        Monitor a workflow and automatically fix failures
        
        Args:
            workflow_file: Path to the workflow file
            timeout_minutes: Maximum time to spend trying to fix
            auto_fix: Whether to automatically apply fixes
            
        Returns:
            Summary of monitoring session
        """
        start_time = datetime.utcnow()
        timeout = timedelta(minutes=timeout_minutes)
        attempts = 0
        
        logger.info(f"Starting GitHub Actions monitoring for {self.owner}/{self.repo}")
        
        while (datetime.utcnow() - start_time) < timeout and attempts < self.max_fix_attempts:
            attempts += 1
            
            # Get latest workflow run
            run = await self._get_latest_workflow_run(workflow_file)
            if not run:
                logger.warning("No workflow runs found")
                await asyncio.sleep(30)
                continue
            
            status = WorkflowStatus(run["status"])
            conclusion = run.get("conclusion")
            
            logger.info(
                f"Workflow run {run['id']} - Status: {status.value}, "
                f"Conclusion: {conclusion}"
            )
            
            # Wait if still running
            if status in [WorkflowStatus.QUEUED, WorkflowStatus.IN_PROGRESS]:
                logger.info("Workflow still running, waiting...")
                await asyncio.sleep(30)
                continue
            
            # Check if successful
            if conclusion == "success":
                logger.info("Workflow completed successfully!")
                return {
                    "success": True,
                    "attempts": attempts,
                    "fix_history": self.fix_history,
                    "final_run_id": run["id"],
                    "duration": (datetime.utcnow() - start_time).total_seconds()
                }
            
            # Handle failure
            if conclusion in ["failure", "timed_out"] and auto_fix:
                logger.info(f"Workflow failed, attempting to fix (attempt {attempts})")
                
                # Analyze failure
                failures = await self._analyze_workflow_failure(run["id"])
                if not failures:
                    logger.warning("Could not determine failure cause")
                    break
                
                # Attempt fixes for each failure
                fixes_applied = False
                for failure in failures:
                    logger.info(
                        f"Analyzing failure: {failure.failure_type.value} "
                        f"in {failure.job_name}/{failure.step_name}"
                    )
                    
                    # Generate fix using LLM
                    fix_attempt = await self._generate_and_apply_fix(failure)
                    self.fix_history.append(fix_attempt)
                    
                    if fix_attempt.success:
                        fixes_applied = True
                        logger.info(f"Applied fix: {fix_attempt.fix_description}")
                    else:
                        logger.error(f"Failed to apply fix: {fix_attempt.error}")
                
                if fixes_applied:
                    # Wait for new workflow to start
                    logger.info("Fixes applied, waiting for new workflow run...")
                    await asyncio.sleep(60)
                else:
                    logger.error("No fixes could be applied")
                    break
            else:
                # Workflow failed but auto-fix is disabled
                break
        
        # Timeout or max attempts reached
        return {
            "success": False,
            "attempts": attempts,
            "fix_history": self.fix_history,
            "final_run_id": run["id"] if 'run' in locals() else None,
            "duration": (datetime.utcnow() - start_time).total_seconds(),
            "reason": "timeout" if attempts < self.max_fix_attempts else "max_attempts"
        }
    
    async def _get_latest_workflow_run(self, workflow_file: str) -> Optional[Dict[str, Any]]:
        """Get the latest run for a specific workflow"""
        async with aiohttp.ClientSession() as session:
            # First, get workflow ID
            workflows_url = f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/workflows"
            async with session.get(workflows_url, headers=self.headers) as response:
                if response.status != 200:
                    return None
                
                workflows = await response.json()
                workflow_id = None
                for workflow in workflows.get("workflows", []):
                    if workflow["path"] == workflow_file:
                        workflow_id = workflow["id"]
                        break
                
                if not workflow_id:
                    return None
            
            # Get latest run for this workflow
            runs_url = f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_id}/runs"
            async with session.get(runs_url, headers=self.headers) as response:
                if response.status != 200:
                    return None
                
                runs = await response.json()
                if runs.get("workflow_runs"):
                    return runs["workflow_runs"][0]  # Most recent run
                
                return None
    
    async def _analyze_workflow_failure(self, run_id: int) -> List[WorkflowFailure]:
        """Analyze a failed workflow run to identify issues"""
        failures = []
        
        async with aiohttp.ClientSession() as session:
            # Get jobs for this run
            jobs_url = f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/jobs"
            async with session.get(jobs_url, headers=self.headers) as response:
                if response.status != 200:
                    return failures
                
                jobs = await response.json()
                
                for job in jobs.get("jobs", []):
                    if job["conclusion"] != "failure":
                        continue
                    
                    # Get job logs
                    logs_url = f"{self.api_base}/repos/{self.owner}/{self.repo}/actions/jobs/{job['id']}/logs"
                    async with session.get(logs_url, headers=self.headers) as log_response:
                        if log_response.status == 200:
                            logs = await log_response.text()
                        else:
                            logs = ""
                    
                    # Find failed step
                    for step in job.get("steps", []):
                        if step["conclusion"] == "failure":
                            # Analyze the failure
                            failure_analysis = self._parse_failure_logs(
                                job["name"],
                                step["name"],
                                logs
                            )
                            
                            if failure_analysis:
                                failures.append(failure_analysis)
        
        return failures
    
    def _parse_failure_logs(self, job_name: str, step_name: str, logs: str) -> Optional[WorkflowFailure]:
        """Parse logs to identify failure type and details"""
        
        # Common error patterns
        patterns = {
            FailureType.SYNTAX_ERROR: [
                r"SyntaxError: (.+) at (.+):(\d+)",
                r"yaml.scanner.ScannerError: (.+)",
                r"Error: .+ is not valid YAML"
            ],
            FailureType.DEPENDENCY_ERROR: [
                r"ModuleNotFoundError: No module named '(.+)'",
                r"Cannot find module '(.+)'",
                r"Package (.+) is not installed",
                r"npm ERR! (.+)",
                r"go: (.+): unknown import path"
            ],
            FailureType.TEST_FAILURE: [
                r"FAILED (.+) - (.+)",
                r"(\d+) failed, (\d+) passed",
                r"Test failed: (.+)",
                r"AssertionError: (.+)"
            ],
            FailureType.BUILD_ERROR: [
                r"Build failed: (.+)",
                r"Compilation error: (.+)",
                r"error: (.+)",
                r"make: \*\*\* (.+)"
            ],
            FailureType.LINTING_ERROR: [
                r"(.+):(\d+):(\d+): (.+)",  # ESLint style
                r"(.+):(\d+): (.+)",  # Flake8 style
                r"golint: (.+)"
            ],
            FailureType.PERMISSION_ERROR: [
                r"Permission denied",
                r"fatal: Authentication failed",
                r"Error: Insufficient permissions"
            ]
        }
        
        # Search for patterns in logs
        for failure_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, logs, re.MULTILINE)
                if match:
                    # Extract details based on pattern
                    error_message = match.group(0)
                    file_path = None
                    line_number = None
                    
                    # Try to extract file and line number
                    if failure_type == FailureType.LINTING_ERROR and len(match.groups()) >= 2:
                        file_path = match.group(1)
                        try:
                            line_number = int(match.group(2))
                        except:
                            pass
                    
                    return WorkflowFailure(
                        workflow_run_id=0,  # Will be set by caller
                        job_name=job_name,
                        step_name=step_name,
                        failure_type=failure_type,
                        error_message=error_message,
                        logs=logs[-2000:],  # Last 2000 chars
                        file_path=file_path,
                        line_number=line_number
                    )
        
        # Unknown failure
        return WorkflowFailure(
            workflow_run_id=0,
            job_name=job_name,
            step_name=step_name,
            failure_type=FailureType.UNKNOWN,
            error_message="Unknown failure",
            logs=logs[-2000:]
        )
    
    async def _generate_and_apply_fix(self, failure: WorkflowFailure) -> FixAttempt:
        """Generate a fix using LLM and apply it"""
        
        # Generate fix using LLM
        fix_suggestion = await self._generate_fix_with_llm(failure)
        
        if not fix_suggestion["success"]:
            return FixAttempt(
                failure=failure,
                fix_description="Failed to generate fix",
                files_modified={},
                success=False,
                error=fix_suggestion.get("error")
            )
        
        # Apply the fix
        files_modified = {}
        try:
            async with aiohttp.ClientSession() as session:
                for file_path, new_content in fix_suggestion["files_to_modify"].items():
                    # Get current file
                    file_url = f"{self.api_base}/repos/{self.owner}/{self.repo}/contents/{file_path}"
                    async with session.get(file_url, headers=self.headers) as response:
                        if response.status != 200:
                            continue
                        
                        file_data = await response.json()
                        current_sha = file_data["sha"]
                    
                    # Update file
                    import base64
                    update_data = {
                        "message": f"Auto-fix: {fix_suggestion['description']}",
                        "content": base64.b64encode(new_content.encode()).decode(),
                        "sha": current_sha
                    }
                    
                    async with session.put(file_url, headers=self.headers, json=update_data) as response:
                        if response.status in [200, 201]:
                            files_modified[file_path] = new_content
                        else:
                            error = await response.text()
                            logger.error(f"Failed to update {file_path}: {error}")
            
            if files_modified:
                return FixAttempt(
                    failure=failure,
                    fix_description=fix_suggestion["description"],
                    files_modified=files_modified,
                    success=True
                )
            else:
                return FixAttempt(
                    failure=failure,
                    fix_description=fix_suggestion["description"],
                    files_modified={},
                    success=False,
                    error="Failed to modify any files"
                )
                
        except Exception as e:
            return FixAttempt(
                failure=failure,
                fix_description=fix_suggestion["description"],
                files_modified={},
                success=False,
                error=str(e)
            )
    
    async def _generate_fix_with_llm(self, failure: WorkflowFailure) -> Dict[str, Any]:
        """Use LLM to generate a fix for the failure"""
        
        prompt = f"""
Analyze this GitHub Actions workflow failure and provide a fix:

JOB: {failure.job_name}
STEP: {failure.step_name}
FAILURE TYPE: {failure.failure_type.value}
ERROR MESSAGE: {failure.error_message}

LOGS (last 2000 chars):
{failure.logs}

Based on this failure, generate fixes that need to be applied. Consider:
1. The specific error type and message
2. Common fixes for this type of error
3. The context of the CI/CD pipeline

Return a JSON response with:
{{
    "success": true/false,
    "description": "Brief description of the fix",
    "files_to_modify": {{
        "path/to/file": "complete new content of the file",
        ...
    }},
    "explanation": "Detailed explanation of what caused the issue and how the fix addresses it"
}}

IMPORTANT:
- For dependency errors, update requirements.txt, package.json, go.mod, etc.
- For syntax errors, fix the actual syntax issue
- For test failures, fix the test or the code being tested
- For linting errors, fix the code style issues
- For build errors, fix compilation issues or missing files
- Always provide the COMPLETE file content, not just the changes
"""
        
        try:
            model = getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
            
            response = await llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a CI/CD expert who can analyze and fix GitHub Actions failures."
                    },
                    {"role": "user", "content": prompt}
                ],
                model=model,
                temperature=0.3,
                max_tokens=4000
            )
            
            # Parse response
            content = response["content"]
            
            # Extract JSON from response
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            else:
                return {
                    "success": False,
                    "error": "Failed to parse LLM response"
                }
            
        except Exception as e:
            logger.error(f"LLM fix generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


async def monitor_and_fix_github_actions(
    repo_url: str,
    github_token: str,
    workflow_file: str = ".github/workflows/ci.yml",
    max_duration_minutes: int = 30,
    auto_fix: bool = True
) -> Dict[str, Any]:
    """
    Main function to monitor and fix GitHub Actions
    
    Args:
        repo_url: Full GitHub repository URL
        github_token: GitHub personal access token
        workflow_file: Path to workflow file
        max_duration_minutes: Maximum time to spend fixing
        auto_fix: Whether to automatically apply fixes
        
    Returns:
        Summary of monitoring session
    """
    
    # Extract owner and repo from URL
    parts = repo_url.replace("https://github.com/", "").split("/")
    if len(parts) != 2:
        return {
            "success": False,
            "error": "Invalid repository URL"
        }
    
    owner, repo = parts
    
    # Create monitor
    monitor = GitHubActionsMonitor(github_token, owner, repo)
    
    # Run monitoring
    result = await monitor.monitor_and_fix_workflow(
        workflow_file=workflow_file,
        timeout_minutes=max_duration_minutes,
        auto_fix=auto_fix
    )
    
    return result