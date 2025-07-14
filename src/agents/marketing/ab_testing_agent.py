"""
A/B Testing Agent - Schedules post variants and tracks metrics
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import random
import numpy as np
from scipy import stats

from src.agents.marketing.models import MarketingContent, ContentPerformance, Channel
import structlog

logger = structlog.get_logger()


class ABTestingAgent:
    """Manages A/B testing for marketing content"""
    
    def __init__(self):
        self.active_tests = {}
        self.test_results = {}
        self.confidence_threshold = 0.95  # 95% statistical confidence
        
    async def create_ab_test(
        self,
        original_content: MarketingContent,
        test_name: str,
        variants: List[Dict[str, Any]],
        test_duration_hours: int = 48,
        traffic_split: List[float] = None
    ) -> Dict[str, Any]:
        """Create A/B test with multiple variants"""
        
        test_id = f"test_{datetime.now().timestamp()}"
        
        # Default equal traffic split
        if not traffic_split:
            num_variants = len(variants) + 1  # +1 for control
            traffic_split = [1.0 / num_variants] * num_variants
        
        # Create test configuration
        test_config = {
            "test_id": test_id,
            "test_name": test_name,
            "created_at": datetime.now(),
            "end_time": datetime.now() + timedelta(hours=test_duration_hours),
            "control": self._prepare_control(original_content),
            "variants": self._prepare_variants(original_content, variants),
            "traffic_split": traffic_split,
            "channel": original_content.channel,
            "metrics_tracked": ["impressions", "clicks", "engagement_rate", "conversions"],
            "status": "active",
            "winning_variant": None
        }
        
        # Store active test
        self.active_tests[test_id] = test_config
        
        # Schedule variants
        scheduled_posts = await self._schedule_test_variants(test_config)
        
        return {
            "test_id": test_id,
            "test_name": test_name,
            "variants_count": len(variants) + 1,
            "duration_hours": test_duration_hours,
            "scheduled_posts": scheduled_posts,
            "traffic_split": traffic_split,
            "expected_completion": test_config["end_time"].isoformat()
        }
    
    def _prepare_control(self, original: MarketingContent) -> Dict[str, Any]:
        """Prepare control version"""
        return {
            "variant_id": "control",
            "content": original.content,
            "title": original.title,
            "cta": original.cta,
            "hashtags": original.hashtags,
            "modifications": []
        }
    
    def _prepare_variants(
        self, original: MarketingContent, variants: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare test variants"""
        prepared = []
        
        for i, variant in enumerate(variants):
            variant_data = {
                "variant_id": f"variant_{i+1}",
                "content": variant.get("content", original.content),
                "title": variant.get("title", original.title),
                "cta": variant.get("cta", original.cta),
                "hashtags": variant.get("hashtags", original.hashtags),
                "modifications": variant.get("modifications", [])
            }
            prepared.append(variant_data)
        
        return prepared
    
    async def _schedule_test_variants(
        self, test_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Schedule test variants for posting"""
        scheduled = []
        base_time = datetime.now() + timedelta(minutes=30)
        
        # Schedule control
        scheduled.append({
            "variant_id": "control",
            "scheduled_time": base_time,
            "traffic_percentage": test_config["traffic_split"][0] * 100
        })
        
        # Schedule variants with slight time offsets
        for i, variant in enumerate(test_config["variants"]):
            scheduled.append({
                "variant_id": variant["variant_id"],
                "scheduled_time": base_time + timedelta(minutes=5 * (i + 1)),
                "traffic_percentage": test_config["traffic_split"][i + 1] * 100
            })
        
        return scheduled
    
    async def track_performance(
        self, test_id: str, variant_id: str, metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Track performance for a test variant"""
        
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        # Initialize results storage
        if test_id not in self.test_results:
            self.test_results[test_id] = {}
        
        if variant_id not in self.test_results[test_id]:
            self.test_results[test_id][variant_id] = {
                "impressions": [],
                "clicks": [],
                "engagement_rates": [],
                "conversions": [],
                "timestamps": []
            }
        
        # Store metrics
        results = self.test_results[test_id][variant_id]
        results["impressions"].append(metrics.get("impressions", 0))
        results["clicks"].append(metrics.get("clicks", 0))
        results["engagement_rates"].append(metrics.get("engagement_rate", 0))
        results["conversions"].append(metrics.get("conversions", 0))
        results["timestamps"].append(datetime.now())
        
        # Check if test should conclude
        should_conclude = await self._check_test_conclusion(test_id)
        
        return {
            "test_id": test_id,
            "variant_id": variant_id,
            "metrics_recorded": True,
            "should_conclude": should_conclude,
            "current_leader": self._get_current_leader(test_id) if should_conclude else None
        }
    
    async def _check_test_conclusion(self, test_id: str) -> bool:
        """Check if test should conclude"""
        test_config = self.active_tests.get(test_id)
        if not test_config:
            return False
        
        # Check time limit
        if datetime.now() >= test_config["end_time"]:
            return True
        
        # Check statistical significance
        if test_id in self.test_results and len(self.test_results[test_id]) > 1:
            significance = self._calculate_significance(test_id)
            if significance and significance["is_significant"]:
                return True
        
        return False
    
    def _calculate_significance(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Calculate statistical significance"""
        
        results = self.test_results.get(test_id, {})
        if len(results) < 2:
            return None
        
        # Get control and best variant
        control_data = results.get("control", {})
        if not control_data.get("clicks"):
            return None
        
        control_rate = self._calculate_conversion_rate(control_data)
        
        best_variant = None
        best_rate = control_rate
        best_significance = 0
        
        for variant_id, variant_data in results.items():
            if variant_id == "control":
                continue
                
            variant_rate = self._calculate_conversion_rate(variant_data)
            
            # Perform statistical test
            p_value = self._perform_statistical_test(
                control_data, variant_data
            )
            
            if p_value < (1 - self.confidence_threshold) and variant_rate > best_rate:
                best_variant = variant_id
                best_rate = variant_rate
                best_significance = 1 - p_value
        
        return {
            "is_significant": best_variant is not None,
            "winning_variant": best_variant or "control",
            "control_rate": control_rate,
            "winning_rate": best_rate,
            "confidence": best_significance * 100 if best_variant else 0,
            "lift": ((best_rate - control_rate) / control_rate * 100) if control_rate > 0 else 0
        }
    
    def _calculate_conversion_rate(self, data: Dict[str, List]) -> float:
        """Calculate conversion rate from data"""
        total_impressions = sum(data.get("impressions", [0]))
        total_conversions = sum(data.get("conversions", [0]))
        
        if total_impressions == 0:
            return 0
        
        return total_conversions / total_impressions
    
    def _perform_statistical_test(
        self, control_data: Dict[str, List], 
        variant_data: Dict[str, List]
    ) -> float:
        """Perform statistical significance test"""
        
        # Use Chi-square test for conversion rate comparison
        control_conversions = sum(control_data.get("conversions", [0]))
        control_impressions = sum(control_data.get("impressions", [1]))
        
        variant_conversions = sum(variant_data.get("conversions", [0]))
        variant_impressions = sum(variant_data.get("impressions", [1]))
        
        # Create contingency table
        observed = np.array([
            [control_conversions, control_impressions - control_conversions],
            [variant_conversions, variant_impressions - variant_conversions]
        ])
        
        # Perform chi-square test
        try:
            chi2, p_value, dof, expected = stats.chi2_contingency(observed)
            return p_value
        except:
            return 1.0  # No significance if test fails
    
    def _get_current_leader(self, test_id: str) -> Dict[str, Any]:
        """Get current leading variant"""
        
        results = self.test_results.get(test_id, {})
        if not results:
            return {"variant": "control", "reason": "No data"}
        
        best_variant = "control"
        best_rate = 0
        
        for variant_id, data in results.items():
            rate = self._calculate_conversion_rate(data)
            if rate > best_rate:
                best_variant = variant_id
                best_rate = rate
        
        return {
            "variant": best_variant,
            "conversion_rate": best_rate,
            "impressions": sum(results[best_variant].get("impressions", [0])),
            "conversions": sum(results[best_variant].get("conversions", [0]))
        }
    
    async def conclude_test(self, test_id: str) -> Dict[str, Any]:
        """Conclude A/B test and determine winner"""
        
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        test_config = self.active_tests[test_id]
        
        # Calculate final results
        significance = self._calculate_significance(test_id)
        
        if significance and significance["is_significant"]:
            winner = significance["winning_variant"]
            reason = f"Statistical significance at {significance['confidence']:.1f}% confidence"
        else:
            # Choose based on highest conversion rate
            leader = self._get_current_leader(test_id)
            winner = leader["variant"]
            reason = "Highest conversion rate (not statistically significant)"
        
        # Update test status
        test_config["status"] = "completed"
        test_config["winning_variant"] = winner
        test_config["completed_at"] = datetime.now()
        
        # Generate report
        report = await self._generate_test_report(test_id, winner, reason)
        
        return report
    
    async def _generate_test_report(
        self, test_id: str, winner: str, reason: str
    ) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        test_config = self.active_tests[test_id]
        results = self.test_results.get(test_id, {})
        
        # Calculate metrics for each variant
        variant_metrics = {}
        for variant_id, data in results.items():
            variant_metrics[variant_id] = {
                "impressions": sum(data.get("impressions", [0])),
                "clicks": sum(data.get("clicks", [0])),
                "conversions": sum(data.get("conversions", [0])),
                "conversion_rate": self._calculate_conversion_rate(data),
                "engagement_rate": np.mean(data.get("engagement_rates", [0]))
            }
        
        # Calculate lift
        control_rate = variant_metrics.get("control", {}).get("conversion_rate", 0)
        winner_rate = variant_metrics.get(winner, {}).get("conversion_rate", 0)
        lift = ((winner_rate - control_rate) / control_rate * 100) if control_rate > 0 else 0
        
        return {
            "test_id": test_id,
            "test_name": test_config["test_name"],
            "duration": str(datetime.now() - test_config["created_at"]),
            "winner": winner,
            "reason": reason,
            "lift": f"{lift:.1f}%",
            "variant_performance": variant_metrics,
            "recommendations": self._generate_recommendations(winner, test_config, lift),
            "next_steps": self._suggest_next_tests(test_config, winner)
        }
    
    def _generate_recommendations(
        self, winner: str, test_config: Dict[str, Any], lift: float
    ) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        if winner != "control":
            recommendations.append(f"Implement the winning variant across all {test_config['channel'].value} content")
            
            # Analyze what made it win
            winning_variant = next(
                (v for v in test_config["variants"] if v["variant_id"] == winner), 
                None
            )
            
            if winning_variant and winning_variant.get("modifications"):
                for mod in winning_variant["modifications"]:
                    recommendations.append(f"Apply '{mod}' to future content")
        
        if lift > 20:
            recommendations.append("Significant improvement found - prioritize similar optimizations")
        elif lift < 5:
            recommendations.append("Minimal improvement - test more dramatic variations")
        
        return recommendations
    
    def _suggest_next_tests(
        self, test_config: Dict[str, Any], winner: str
    ) -> List[Dict[str, str]]:
        """Suggest follow-up tests"""
        
        suggestions = []
        
        if winner != "control":
            suggestions.append({
                "test_type": "refinement",
                "description": "Test variations of the winning element",
                "hypothesis": "Further optimization of winning elements can increase lift"
            })
        
        suggestions.extend([
            {
                "test_type": "channel_expansion",
                "description": f"Test winning variant on other channels",
                "hypothesis": "Winning elements may work across channels"
            },
            {
                "test_type": "audience_segmentation",
                "description": "Test variants by audience segment",
                "hypothesis": "Different audiences may respond to different variants"
            }
        ])
        
        return suggestions
    
    async def create_multivariate_test(
        self, base_content: MarketingContent,
        variables: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Create multivariate test with multiple variables"""
        
        # Generate all combinations
        import itertools
        
        variable_names = list(variables.keys())
        variable_values = [variables[name] for name in variable_names]
        
        combinations = list(itertools.product(*variable_values))
        
        # Create variants for each combination
        variants = []
        for combo in combinations:
            variant = {
                "modifications": [f"{name}: {value}" for name, value in zip(variable_names, combo)]
            }
            
            # Apply modifications to content
            modified_content = base_content.content
            for name, value in zip(variable_names, combo):
                if name == "headline":
                    variant["title"] = value
                elif name == "cta":
                    variant["cta"] = value
                elif name == "tone":
                    # Would apply tone transformation
                    pass
            
            variants.append(variant)
        
        # Create test with all variants
        return await self.create_ab_test(
            base_content,
            f"Multivariate: {', '.join(variable_names)}",
            variants,
            test_duration_hours=72  # Longer duration for more variants
        )
    
    def get_test_status(self, test_id: str) -> Dict[str, Any]:
        """Get current test status"""
        
        if test_id not in self.active_tests:
            return {"error": "Test not found"}
        
        test_config = self.active_tests[test_id]
        current_leader = self._get_current_leader(test_id) if test_id in self.test_results else None
        
        return {
            "test_id": test_id,
            "test_name": test_config["test_name"],
            "status": test_config["status"],
            "time_remaining": str(test_config["end_time"] - datetime.now()),
            "variants_count": len(test_config["variants"]) + 1,
            "current_leader": current_leader,
            "can_conclude": current_leader is not None
        }