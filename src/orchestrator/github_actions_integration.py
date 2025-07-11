"""
GitHub Actions Integration for CI/CD Result Tracking and Confidence Scoring
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import structlog
import httpx
from urllib.parse import urlparse

logger = structlog.get_logger()


class GitHubActionsIntegration:
    """
    Integrates with GitHub Actions to track CI/CD results and boost confidence scores
    """
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
    
    async def get_workflow_runs(
        self, 
        repo_url: str, 
        limit: int = 10,
        time_window_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get recent workflow runs for a repository
        
        Args:
            repo_url: Full GitHub repository URL
            limit: Maximum number of runs to retrieve
            time_window_days: Only consider runs from the last N days
            
        Returns:
            List of workflow run data
        """
        try:
            # Parse owner and repo from URL
            owner, repo = self._parse_repo_url(repo_url)
            
            # Calculate time window
            since = (datetime.utcnow() - timedelta(days=time_window_days)).isoformat() + "Z"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/actions/runs",
                    headers=self.headers,
                    params={
                        "per_page": limit,
                        "created": f">{since}"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("workflow_runs", [])
                else:
                    logger.warning(
                        "Failed to get workflow runs",
                        status=response.status_code,
                        repo=f"{owner}/{repo}"
                    )
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting workflow runs: {e}")
            return []
    
    async def calculate_ci_confidence_boost(
        self, 
        repo_url: str,
        capsule_id: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate confidence boost based on CI/CD success rate
        
        Args:
            repo_url: GitHub repository URL
            capsule_id: Optional capsule ID to track specific deployment
            
        Returns:
            Tuple of (confidence_boost, metrics)
            - confidence_boost: 0.0 to 0.2 boost value
            - metrics: Detailed metrics about CI/CD performance
        """
        try:
            # Get recent workflow runs
            runs = await self.get_workflow_runs(repo_url, limit=20)
            
            if not runs:
                return 0.0, {"message": "No workflow runs found"}
            
            # Calculate metrics
            total_runs = len(runs)
            successful_runs = sum(1 for run in runs if run.get("conclusion") == "success")
            failed_runs = sum(1 for run in runs if run.get("conclusion") == "failure")
            
            # Calculate success rate
            success_rate = successful_runs / total_runs if total_runs > 0 else 0.0
            
            # Get average run duration for successful runs
            successful_durations = []
            for run in runs:
                if run.get("conclusion") == "success" and run.get("run_started_at") and run.get("updated_at"):
                    start = datetime.fromisoformat(run["run_started_at"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
                    duration = (end - start).total_seconds()
                    successful_durations.append(duration)
            
            avg_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0
            
            # Calculate confidence boost (max 0.2)
            confidence_boost = 0.0
            
            # Success rate contribution (up to 0.15)
            if success_rate >= 0.9:
                confidence_boost += 0.15
            elif success_rate >= 0.75:
                confidence_boost += 0.10
            elif success_rate >= 0.5:
                confidence_boost += 0.05
            
            # Consistency bonus (up to 0.05)
            if total_runs >= 5 and success_rate >= 0.8:
                confidence_boost += 0.05
            elif total_runs >= 3 and success_rate >= 0.7:
                confidence_boost += 0.03
            
            metrics = {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": round(success_rate, 3),
                "avg_duration_seconds": round(avg_duration, 2),
                "confidence_boost": round(confidence_boost, 3),
                "last_run_status": runs[0].get("conclusion") if runs else None,
                "last_run_date": runs[0].get("created_at") if runs else None
            }
            
            logger.info(
                "Calculated CI/CD confidence boost",
                repo_url=repo_url,
                boost=confidence_boost,
                success_rate=success_rate
            )
            
            return confidence_boost, metrics
            
        except Exception as e:
            logger.error(f"Error calculating CI confidence boost: {e}")
            return 0.0, {"error": str(e)}
    
    async def get_workflow_status_for_commit(
        self,
        repo_url: str,
        commit_sha: str
    ) -> Dict[str, Any]:
        """
        Get workflow status for a specific commit
        
        Args:
            repo_url: GitHub repository URL
            commit_sha: Git commit SHA
            
        Returns:
            Workflow status information
        """
        try:
            owner, repo = self._parse_repo_url(repo_url)
            
            async with httpx.AsyncClient() as client:
                # Get check runs for the commit
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/commits/{commit_sha}/check-runs",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    check_runs = data.get("check_runs", [])
                    
                    # Aggregate status
                    total = len(check_runs)
                    completed = sum(1 for run in check_runs if run.get("status") == "completed")
                    successful = sum(1 for run in check_runs if run.get("conclusion") == "success")
                    
                    return {
                        "commit_sha": commit_sha,
                        "total_checks": total,
                        "completed_checks": completed,
                        "successful_checks": successful,
                        "all_passed": total > 0 and total == successful,
                        "status": "success" if total == successful else "failure" if completed == total else "pending",
                        "check_runs": check_runs
                    }
                else:
                    return {
                        "commit_sha": commit_sha,
                        "error": f"Failed to get check runs: {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"Error getting workflow status for commit: {e}")
            return {
                "commit_sha": commit_sha,
                "error": str(e)
            }
    
    def _parse_repo_url(self, repo_url: str) -> Tuple[str, str]:
        """
        Parse owner and repo name from GitHub URL
        
        Args:
            repo_url: Full GitHub repository URL
            
        Returns:
            Tuple of (owner, repo_name)
        """
        # Handle various GitHub URL formats
        patterns = [
            r"github\.com[:/]([^/]+)/([^/\.]+)",
            r"https?://github\.com/([^/]+)/([^/\.]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, repo_url)
            if match:
                return match.group(1), match.group(2)
        
        # Fallback: assume format is owner/repo
        parts = repo_url.strip("/").split("/")
        if len(parts) >= 2:
            return parts[-2], parts[-1].replace(".git", "")
        
        raise ValueError(f"Could not parse repository URL: {repo_url}")


async def integrate_ci_confidence(
    capsule_id: str,
    github_url: str,
    github_token: str,
    current_confidence: float
) -> Tuple[float, Dict[str, Any]]:
    """
    Convenience function to integrate CI/CD results into confidence scoring
    
    Args:
        capsule_id: The capsule ID
        github_url: GitHub repository URL
        github_token: GitHub access token
        current_confidence: Current confidence score (0.0-1.0)
        
    Returns:
        Tuple of (new_confidence_score, ci_metrics)
    """
    try:
        integration = GitHubActionsIntegration(github_token)
        boost, metrics = await integration.calculate_ci_confidence_boost(github_url, capsule_id)
        
        # Apply boost to current confidence (capped at 1.0)
        new_confidence = min(1.0, current_confidence + boost)
        
        metrics["original_confidence"] = round(current_confidence, 3)
        metrics["new_confidence"] = round(new_confidence, 3)
        metrics["applied_boost"] = round(boost, 3)
        
        logger.info(
            "Applied CI/CD confidence boost",
            capsule_id=capsule_id,
            original=current_confidence,
            boost=boost,
            new=new_confidence
        )
        
        return new_confidence, metrics
        
    except Exception as e:
        logger.error(f"Failed to integrate CI confidence: {e}")
        return current_confidence, {"error": str(e)}