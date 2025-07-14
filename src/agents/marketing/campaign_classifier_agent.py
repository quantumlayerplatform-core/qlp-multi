"""
Campaign Classifier Agent - Tags and analyzes past campaigns for patterns
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import asyncio
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

from src.agents.marketing.models import MarketingCampaign, MarketingContent, ContentType
import structlog

logger = structlog.get_logger()


class CampaignClassifierAgent:
    """Analyzes and classifies marketing campaigns for insights"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(max_features=100)
        self.format_patterns = self._load_format_patterns()
        self.tone_indicators = self._load_tone_indicators()
        self.cta_patterns = self._load_cta_patterns()
        
    def _load_format_patterns(self) -> Dict[str, List[str]]:
        """Load patterns for different content formats"""
        return {
            "listicle": ["ways", "tips", "reasons", "steps", "things", "lessons"],
            "how_to": ["how to", "guide", "tutorial", "walkthrough", "process"],
            "story": ["story", "journey", "learned", "discovered", "realized"],
            "comparison": ["vs", "versus", "better", "compare", "difference"],
            "announcement": ["launching", "introducing", "announcing", "new", "release"],
            "thought_leadership": ["future", "prediction", "trend", "insight", "perspective"],
            "case_study": ["case study", "success story", "results", "achieved", "transformation"],
            "educational": ["explained", "understanding", "learn", "master", "fundamentals"]
        }
    
    def _load_tone_indicators(self) -> Dict[str, List[str]]:
        """Load indicators for different tones"""
        return {
            "inspirational": ["dream", "vision", "possible", "transform", "empower", "achieve"],
            "technical": ["algorithm", "implementation", "architecture", "performance", "optimization"],
            "conversational": ["you", "your", "let's", "we", "hey", "folks"],
            "authoritative": ["must", "proven", "research", "data shows", "experts", "leading"],
            "urgent": ["now", "today", "limited", "last chance", "don't miss", "hurry"],
            "empathetic": ["understand", "feel", "struggle", "pain", "help", "support"]
        }
    
    def _load_cta_patterns(self) -> Dict[str, List[str]]:
        """Load CTA effectiveness patterns"""
        return {
            "direct_action": ["click", "sign up", "start", "try", "get", "download"],
            "soft_engagement": ["learn more", "discover", "explore", "see how", "find out"],
            "social_proof": ["join", "others", "community", "trusted by", "used by"],
            "urgency": ["now", "today", "limited time", "ends soon", "last chance"],
            "value_focused": ["free", "save", "bonus", "exclusive", "unlock"],
            "question": ["ready", "want to", "interested", "curious", "wondering"]
        }
    
    async def classify_campaign(
        self, campaign: MarketingCampaign
    ) -> Dict[str, Any]:
        """Classify a campaign by multiple dimensions"""
        
        # Extract all content text
        all_content = " ".join([
            content.content for content in campaign.content_pieces
        ])
        
        # Classify by format
        format_scores = self._classify_format(campaign.content_pieces)
        
        # Classify by tone
        tone_scores = self._classify_tone(all_content)
        
        # Analyze CTA effectiveness
        cta_analysis = self._analyze_ctas(campaign.content_pieces)
        
        # Channel effectiveness
        channel_analysis = self._analyze_channels(campaign)
        
        # Content clustering
        content_clusters = await self._cluster_content(campaign.content_pieces)
        
        # Performance prediction
        predicted_performance = self._predict_performance(
            format_scores, tone_scores, cta_analysis
        )
        
        return {
            "campaign_id": campaign.campaign_id,
            "classifications": {
                "primary_format": max(format_scores, key=format_scores.get),
                "format_distribution": format_scores,
                "primary_tone": max(tone_scores, key=tone_scores.get),
                "tone_distribution": tone_scores,
                "cta_styles": cta_analysis["styles"],
                "cta_effectiveness_score": cta_analysis["effectiveness_score"]
            },
            "insights": {
                "content_diversity": len(content_clusters),
                "channel_focus": channel_analysis["primary_channels"],
                "message_consistency": self._calculate_consistency(campaign.content_pieces),
                "engagement_hooks": self._identify_engagement_patterns(campaign.content_pieces)
            },
            "recommendations": self._generate_recommendations(
                format_scores, tone_scores, cta_analysis, channel_analysis
            ),
            "predicted_performance": predicted_performance,
            "similar_campaigns": []  # Would be populated from historical data
        }
    
    def _classify_format(self, content_pieces: List[MarketingContent]) -> Dict[str, float]:
        """Classify content format distribution"""
        format_scores = defaultdict(float)
        total_pieces = len(content_pieces)
        
        for content in content_pieces:
            content_lower = content.content.lower()
            
            for format_type, indicators in self.format_patterns.items():
                score = sum(
                    1 for indicator in indicators 
                    if indicator in content_lower
                ) / len(indicators)
                
                format_scores[format_type] += score
        
        # Normalize scores
        for format_type in format_scores:
            format_scores[format_type] /= total_pieces
        
        return dict(format_scores)
    
    def _classify_tone(self, content: str) -> Dict[str, float]:
        """Classify content tone"""
        content_lower = content.lower()
        word_count = len(content_lower.split())
        tone_scores = {}
        
        for tone, indicators in self.tone_indicators.items():
            # Count indicator occurrences
            indicator_count = sum(
                content_lower.count(indicator) 
                for indicator in indicators
            )
            
            # Normalize by content length and number of indicators
            tone_scores[tone] = (indicator_count / word_count) * 100
        
        # Normalize to sum to 1
        total_score = sum(tone_scores.values())
        if total_score > 0:
            for tone in tone_scores:
                tone_scores[tone] /= total_score
        
        return tone_scores
    
    def _analyze_ctas(
        self, content_pieces: List[MarketingContent]
    ) -> Dict[str, Any]:
        """Analyze CTA patterns and effectiveness"""
        cta_styles = defaultdict(int)
        cta_positions = []
        total_ctas = 0
        
        for i, content in enumerate(content_pieces):
            if content.cta:
                total_ctas += 1
                cta_lower = content.cta.lower()
                
                # Classify CTA style
                for style, patterns in self.cta_patterns.items():
                    if any(pattern in cta_lower for pattern in patterns):
                        cta_styles[style] += 1
                
                # Track position
                cta_positions.append(i / len(content_pieces))
        
        # Calculate effectiveness score based on best practices
        effectiveness_score = 0.0
        
        # Variety bonus
        if len(cta_styles) > 1:
            effectiveness_score += 0.2
        
        # Appropriate frequency (not too many CTAs)
        cta_ratio = total_ctas / len(content_pieces)
        if 0.2 <= cta_ratio <= 0.4:
            effectiveness_score += 0.3
        
        # Good distribution (not all at end)
        if cta_positions and np.std(cta_positions) > 0.2:
            effectiveness_score += 0.2
        
        # Action-oriented CTAs
        if cta_styles.get("direct_action", 0) > 0:
            effectiveness_score += 0.3
        
        return {
            "styles": dict(cta_styles),
            "total_ctas": total_ctas,
            "cta_ratio": cta_ratio,
            "position_distribution": cta_positions,
            "effectiveness_score": min(effectiveness_score, 1.0)
        }
    
    def _analyze_channels(self, campaign: MarketingCampaign) -> Dict[str, Any]:
        """Analyze channel distribution and focus"""
        channel_counts = defaultdict(int)
        channel_types = defaultdict(set)
        
        for content in campaign.content_pieces:
            channel_counts[content.channel.value] += 1
            channel_types[content.channel.value].add(content.type.value)
        
        # Find primary channels (top 3)
        sorted_channels = sorted(
            channel_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        primary_channels = [ch[0] for ch in sorted_channels[:3]]
        
        # Calculate channel diversity
        channel_diversity = len(channel_types) / len(ContentType)
        
        return {
            "channel_distribution": dict(channel_counts),
            "primary_channels": primary_channels,
            "channel_diversity": channel_diversity,
            "content_types_per_channel": {
                ch: list(types) for ch, types in channel_types.items()
            }
        }
    
    async def _cluster_content(
        self, content_pieces: List[MarketingContent]
    ) -> List[Dict[str, Any]]:
        """Cluster similar content pieces"""
        if len(content_pieces) < 3:
            return [{"content_ids": [c.content_id for c in content_pieces]}]
        
        # Extract text for clustering
        texts = [content.content for content in content_pieces]
        
        try:
            # TF-IDF vectorization
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Determine optimal number of clusters
            n_clusters = min(5, len(content_pieces) // 3)
            
            # K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(tfidf_matrix)
            
            # Group content by cluster
            cluster_groups = defaultdict(list)
            for i, cluster_id in enumerate(clusters):
                cluster_groups[cluster_id].append({
                    "content_id": content_pieces[i].content_id,
                    "channel": content_pieces[i].channel.value,
                    "type": content_pieces[i].type.value
                })
            
            # Extract cluster themes
            clusters_with_themes = []
            for cluster_id, contents in cluster_groups.items():
                # Get top terms for this cluster
                cluster_indices = [i for i, c in enumerate(clusters) if c == cluster_id]
                cluster_tfidf = tfidf_matrix[cluster_indices].mean(axis=0).A1
                top_indices = cluster_tfidf.argsort()[-5:][::-1]
                feature_names = self.tfidf_vectorizer.get_feature_names_out()
                top_terms = [feature_names[i] for i in top_indices]
                
                clusters_with_themes.append({
                    "cluster_id": int(cluster_id),
                    "content_items": contents,
                    "theme_keywords": top_terms,
                    "size": len(contents)
                })
            
            return clusters_with_themes
            
        except Exception as e:
            logger.error("Content clustering failed", error=str(e))
            return [{"content_ids": [c.content_id for c in content_pieces]}]
    
    def _calculate_consistency(self, content_pieces: List[MarketingContent]) -> float:
        """Calculate message consistency across content"""
        if len(content_pieces) < 2:
            return 1.0
        
        # Extract key terms from each piece
        all_terms = []
        for content in content_pieces:
            # Simple term extraction (in production, use NLP)
            words = content.content.lower().split()
            key_terms = [w for w in words if len(w) > 5][:10]
            all_terms.append(set(key_terms))
        
        # Calculate overlap between consecutive pieces
        consistency_scores = []
        for i in range(len(all_terms) - 1):
            if all_terms[i] and all_terms[i + 1]:
                overlap = len(all_terms[i] & all_terms[i + 1])
                union = len(all_terms[i] | all_terms[i + 1])
                consistency_scores.append(overlap / union if union > 0 else 0)
        
        return np.mean(consistency_scores) if consistency_scores else 0.5
    
    def _identify_engagement_patterns(
        self, content_pieces: List[MarketingContent]
    ) -> List[str]:
        """Identify successful engagement patterns"""
        patterns = []
        
        # Check for questions
        question_count = sum(
            1 for c in content_pieces 
            if "?" in c.content
        )
        if question_count > len(content_pieces) * 0.3:
            patterns.append("question_driven")
        
        # Check for data/statistics
        data_count = sum(
            1 for c in content_pieces 
            if any(char in c.content for char in ["%", "$", "x", "10", "100"])
        )
        if data_count > len(content_pieces) * 0.4:
            patterns.append("data_backed")
        
        # Check for storytelling
        story_count = sum(
            1 for c in content_pieces 
            if any(word in c.content.lower() for word in ["story", "journey", "learned"])
        )
        if story_count > len(content_pieces) * 0.2:
            patterns.append("narrative_focused")
        
        # Check for social proof
        social_count = sum(
            1 for c in content_pieces 
            if any(word in c.content.lower() for word in ["customer", "client", "user", "testimonial"])
        )
        if social_count > len(content_pieces) * 0.3:
            patterns.append("social_proof_heavy")
        
        return patterns
    
    def _predict_performance(
        self, format_scores: Dict[str, float],
        tone_scores: Dict[str, float],
        cta_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict campaign performance based on classification"""
        
        # Base performance score
        base_score = 0.5
        
        # Format bonus
        high_performing_formats = ["how_to", "listicle", "case_study"]
        for format_type in high_performing_formats:
            base_score += format_scores.get(format_type, 0) * 0.1
        
        # Tone bonus
        engaging_tones = ["conversational", "inspirational", "empathetic"]
        for tone in engaging_tones:
            base_score += tone_scores.get(tone, 0) * 0.1
        
        # CTA effectiveness
        base_score += cta_analysis["effectiveness_score"] * 0.2
        
        # Normalize
        performance_score = min(base_score, 1.0)
        
        return {
            "overall_score": performance_score,
            "engagement_prediction": "high" if performance_score > 0.7 else "medium" if performance_score > 0.4 else "low",
            "strengths": self._identify_strengths(format_scores, tone_scores, cta_analysis),
            "improvement_areas": self._identify_improvements(format_scores, tone_scores, cta_analysis)
        }
    
    def _identify_strengths(
        self, format_scores: Dict[str, float],
        tone_scores: Dict[str, float],
        cta_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identify campaign strengths"""
        strengths = []
        
        # Strong formats
        if format_scores.get("how_to", 0) > 0.3:
            strengths.append("Strong educational content")
        if format_scores.get("story", 0) > 0.2:
            strengths.append("Engaging storytelling")
        
        # Effective tone
        if tone_scores.get("conversational", 0) > 0.3:
            strengths.append("Approachable tone")
        if tone_scores.get("authoritative", 0) > 0.3:
            strengths.append("Credible voice")
        
        # Good CTAs
        if cta_analysis["effectiveness_score"] > 0.7:
            strengths.append("Effective calls-to-action")
        
        return strengths
    
    def _identify_improvements(
        self, format_scores: Dict[str, float],
        tone_scores: Dict[str, float],
        cta_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        
        # Format diversity
        if len([f for f, s in format_scores.items() if s > 0.1]) < 3:
            improvements.append("Increase content format variety")
        
        # Tone balance
        if max(tone_scores.values()) > 0.6:
            improvements.append("Balance tone across content")
        
        # CTA improvements
        if cta_analysis["effectiveness_score"] < 0.5:
            improvements.append("Strengthen calls-to-action")
        if cta_analysis["cta_ratio"] < 0.2:
            improvements.append("Add more CTAs throughout campaign")
        
        return improvements
    
    def _generate_recommendations(
        self, format_scores: Dict[str, float],
        tone_scores: Dict[str, float],
        cta_analysis: Dict[str, Any],
        channel_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Format recommendations
        if format_scores.get("how_to", 0) < 0.2:
            recommendations.append("Add more how-to guides - they drive 40% more engagement")
        
        # Tone recommendations
        dominant_tone = max(tone_scores, key=tone_scores.get)
        if dominant_tone == "technical" and tone_scores[dominant_tone] > 0.5:
            recommendations.append("Balance technical content with more conversational pieces")
        
        # CTA recommendations
        if "urgency" not in cta_analysis["styles"]:
            recommendations.append("Test urgency-based CTAs to drive immediate action")
        
        # Channel recommendations
        if channel_analysis["channel_diversity"] < 0.3:
            recommendations.append("Diversify content types within each channel")
        
        return recommendations
    
    async def compare_campaigns(
        self, campaigns: List[MarketingCampaign]
    ) -> Dict[str, Any]:
        """Compare multiple campaigns to identify patterns"""
        
        # Classify all campaigns
        classifications = []
        for campaign in campaigns:
            classification = await self.classify_campaign(campaign)
            classifications.append(classification)
        
        # Identify common patterns
        format_trends = defaultdict(list)
        tone_trends = defaultdict(list)
        performance_scores = []
        
        for cls in classifications:
            for format_type, score in cls["classifications"]["format_distribution"].items():
                format_trends[format_type].append(score)
            for tone, score in cls["classifications"]["tone_distribution"].items():
                tone_trends[tone].append(score)
            performance_scores.append(cls["predicted_performance"]["overall_score"])
        
        # Calculate averages and trends
        format_averages = {
            fmt: np.mean(scores) for fmt, scores in format_trends.items()
        }
        tone_averages = {
            tone: np.mean(scores) for tone, scores in tone_trends.items()
        }
        
        return {
            "total_campaigns": len(campaigns),
            "average_performance": np.mean(performance_scores),
            "top_formats": sorted(
                format_averages.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3],
            "dominant_tones": sorted(
                tone_averages.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3],
            "best_practices": self._extract_best_practices(classifications),
            "evolution_insights": self._analyze_evolution(classifications, campaigns)
        }
    
    def _extract_best_practices(
        self, classifications: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract best practices from high-performing campaigns"""
        
        # Sort by predicted performance
        sorted_campaigns = sorted(
            classifications,
            key=lambda x: x["predicted_performance"]["overall_score"],
            reverse=True
        )
        
        # Get top 20% campaigns
        top_count = max(1, len(sorted_campaigns) // 5)
        top_campaigns = sorted_campaigns[:top_count]
        
        best_practices = []
        
        # Common patterns in top performers
        if all(c["classifications"]["cta_effectiveness_score"] > 0.7 for c in top_campaigns):
            best_practices.append("Strong CTAs are crucial for high performance")
        
        # Format patterns
        common_formats = set()
        for campaign in top_campaigns:
            top_format = campaign["classifications"]["primary_format"]
            common_formats.add(top_format)
        
        if len(common_formats) == 1:
            best_practices.append(f"{list(common_formats)[0]} format consistently performs well")
        
        return best_practices
    
    def _analyze_evolution(
        self, classifications: List[Dict[str, Any]], 
        campaigns: List[MarketingCampaign]
    ) -> Dict[str, Any]:
        """Analyze how campaigns evolved over time"""
        
        # Sort by campaign creation date (would use actual dates in production)
        # For now, assume they're in chronological order
        
        evolution_insights = {
            "format_shifts": [],
            "tone_evolution": [],
            "performance_trend": "improving" if classifications[-1]["predicted_performance"]["overall_score"] > 
                                              classifications[0]["predicted_performance"]["overall_score"] else "declining"
        }
        
        # Detect format shifts
        first_format = classifications[0]["classifications"]["primary_format"]
        last_format = classifications[-1]["classifications"]["primary_format"]
        
        if first_format != last_format:
            evolution_insights["format_shifts"].append(
                f"Shifted from {first_format} to {last_format}"
            )
        
        return evolution_insights