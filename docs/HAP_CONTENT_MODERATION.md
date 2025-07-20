# HAP (Hate, Abuse, Profanity) Content Moderation System

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Detection Mechanisms](#detection-mechanisms)
4. [Technical Context Awareness](#technical-context-awareness)
5. [Categories and Severity Levels](#categories-and-severity-levels)
6. [Implementation Details](#implementation-details)
7. [API Reference](#api-reference)
8. [Configuration](#configuration)
9. [Performance Optimization](#performance-optimization)
10. [Best Practices](#best-practices)
11. [Future Enhancements](#future-enhancements)

## Introduction

The HAP (Hate, Abuse, Profanity) System is an intelligent content moderation solution designed specifically for technical platforms. Unlike traditional moderation systems, HAP understands technical context and can distinguish between legitimate technical terms and actual inappropriate content.

### Key Features

- **Multi-layer Detection**: Combines rule-based, ML-based, and context-aware detection
- **Technical Context Awareness**: Understands programming terminology
- **Real-time Processing**: Sub-100ms response times
- **Configurable Sensitivity**: Adjustable thresholds per deployment
- **Comprehensive Logging**: Full audit trail for compliance
- **Cache Optimization**: Intelligent caching for performance

### Design Philosophy

The HAP system is built on the principle that content moderation in technical contexts requires nuanced understanding. Terms that might be flagged in general contexts (like "kill", "abort", "slave") are often legitimate in programming discussions.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    HAP Service                           │
│                  (FastAPI Server)                        │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                  Detection Pipeline                      │
├──────────────┬──────────────┬──────────────┬──────────┤
│    Input     │   Detection  │  Contextual  │  Output  │
│ Preprocessor │    Layers    │   Analysis   │ Formatter│
└──────────────┴──────────────┴──────────────┴──────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                   Detection Layers                       │
├──────────────┬──────────────┬──────────────┬──────────┤
│  Rule-Based  │   ML Model   │Context-Aware │ Ensemble │
│   Detector   │   Detector   │  Detector   │ Combiner │
└──────────────┴──────────────┴──────────────┴──────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                  Storage & Cache                         │
├──────────────────────┬──────────────────────┬──────────┤
│    Redis Cache       │  PostgreSQL DB       │  Metrics │
└──────────────────────┴──────────────────────┴──────────┘
```

### Core Components

```python
class HAPService:
    def __init__(self):
        self.preprocessor = ContentPreprocessor()
        self.detectors = {
            "rule_based": RuleBasedDetector(),
            "ml_model": MLModelDetector(),
            "context_aware": ContextAwareDetector()
        }
        self.ensemble = EnsembleDetector(self.detectors)
        self.cache = RedisCache()
        self.db = PostgreSQLDB()
        self.metrics = MetricsCollector()
```

## Detection Mechanisms

### 1. Rule-Based Detection

The rule-based detector uses optimized pattern matching for known inappropriate content:

```python
class RuleBasedDetector:
    def __init__(self):
        self.patterns = self._load_patterns()
        self.trie = self._build_trie()  # Efficient string matching
        
    def detect(self, text):
        """Fast pattern-based detection"""
        
        violations = []
        
        # Use Aho-Corasick algorithm for efficient multi-pattern matching
        matches = self.trie.find_all(text.lower())
        
        for match in matches:
            # Check if match is in technical context
            if not self._is_technical_context(text, match):
                violations.append({
                    "type": "rule_based",
                    "pattern": match.pattern,
                    "position": match.position,
                    "severity": match.severity,
                    "category": match.category
                })
        
        return violations
```

### 2. ML Model Detection

Transformer-based model for nuanced detection:

```python
class MLModelDetector:
    def __init__(self):
        self.model = AutoModelForSequenceClassification.from_pretrained(
            "quantum-layer/hap-detector"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            "quantum-layer/hap-detector"
        )
        self.threshold = 0.85
    
    async def detect(self, text):
        """ML-based content classification"""
        
        # Tokenize input
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=-1)
        
        # Extract violations
        violations = []
        for idx, prob in enumerate(probabilities[0]):
            if prob > self.threshold:
                category = self.model.config.id2label[idx]
                if category != "CLEAN":
                    violations.append({
                        "type": "ml_model",
                        "category": category,
                        "confidence": float(prob),
                        "severity": self._calculate_severity(category, prob)
                    })
        
        return violations
```

### 3. Context-Aware Detection

Specialized detector that understands technical context:

```python
class ContextAwareDetector:
    def __init__(self):
        self.technical_terms = self._load_technical_terms()
        self.context_patterns = self._load_context_patterns()
    
    def detect(self, text, detected_issues):
        """Filter out false positives based on context"""
        
        filtered_issues = []
        
        for issue in detected_issues:
            # Extract context around the issue
            context = self._extract_context(text, issue["position"])
            
            # Check if it's technical usage
            if self._is_technical_usage(context, issue["pattern"]):
                # Log for analysis but don't flag
                self.log_technical_usage(context, issue)
                continue
            
            # Check programming patterns
            if self._matches_programming_pattern(context):
                continue
            
            # Keep non-technical violations
            filtered_issues.append(issue)
        
        return filtered_issues
    
    def _is_technical_usage(self, context, term):
        """Determine if term is used in technical context"""
        
        technical_patterns = {
            "kill": [
                r"kill\s+(process|thread|job|task)",
                r"kill\s+-\d+",  # kill -9
                r"(SIGKILL|SIGTERM)"
            ],
            "abort": [
                r"abort\s+(transaction|operation|request)",
                r"(transaction\.abort|abort\(\))"
            ],
            "slave": [
                r"(master|primary)[/-]slave",
                r"slave\s+(node|server|database|replica)"
            ],
            "execute": [
                r"execute\s+(query|command|script|sql)",
                r"\.execute\(",
                r"execution\s+time"
            ]
        }
        
        if term in technical_patterns:
            for pattern in technical_patterns[term]:
                if re.search(pattern, context, re.IGNORECASE):
                    return True
        
        return False
```

### 4. Ensemble Detection

Combines results from all detectors:

```python
class EnsembleDetector:
    def __init__(self, detectors):
        self.detectors = detectors
        self.weights = {
            "rule_based": 0.3,
            "ml_model": 0.5,
            "context_aware": 0.2
        }
    
    async def detect(self, text):
        """Combine results from all detectors"""
        
        # Run all detectors
        results = {}
        for name, detector in self.detectors.items():
            results[name] = await detector.detect(text)
        
        # Apply context filtering
        filtered_results = self.detectors["context_aware"].filter(
            text,
            self._merge_results(results)
        )
        
        # Calculate ensemble score
        final_results = self._ensemble_scoring(filtered_results)
        
        return final_results
```

## Technical Context Awareness

### Technical Term Database

```python
TECHNICAL_TERMS = {
    "programming": {
        "kill": ["process", "thread", "job", "signal"],
        "abort": ["transaction", "operation", "rollback"],
        "execute": ["query", "command", "script", "code"],
        "dump": ["memory", "database", "core", "stack"],
        "crash": ["application", "system", "report", "log"],
        "hack": ["hackathon", "hacker", "hack day"],
        "injection": ["dependency", "sql", "code", "fault"],
        "attack": ["vector", "surface", "mitigation"]
    },
    
    "networking": {
        "slave": ["node", "replica", "server"],
        "master": ["node", "server", "branch"],
        "blacklist": ["ip", "domain", "url"],
        "whitelist": ["ip", "domain", "url"]
    },
    
    "git": {
        "blame": ["git blame", "blame annotation"],
        "master": ["master branch", "master commit"],
        "force": ["force push", "force merge"]
    }
}
```

### Context Analysis

```python
class TechnicalContextAnalyzer:
    def analyze_context(self, text, position, window=50):
        """Analyze surrounding context for technical indicators"""
        
        # Extract context window
        start = max(0, position - window)
        end = min(len(text), position + window)
        context = text[start:end]
        
        indicators = {
            "code_syntax": self._has_code_syntax(context),
            "technical_keywords": self._count_technical_keywords(context),
            "camel_case": self._has_camel_case(context),
            "snake_case": self._has_snake_case(context),
            "function_calls": self._has_function_calls(context),
            "comments": self._has_code_comments(context),
            "imports": self._has_imports(context)
        }
        
        # Calculate technical score
        technical_score = sum(
            1 if v else 0 for v in indicators.values()
        ) / len(indicators)
        
        return {
            "is_technical": technical_score > 0.5,
            "score": technical_score,
            "indicators": indicators
        }
```

## Categories and Severity Levels

### Content Categories

```python
class ContentCategory(Enum):
    HATE_SPEECH = "hate_speech"
    ABUSE = "abuse"
    PROFANITY = "profanity"
    SEXUAL = "sexual"
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    SPAM = "spam"
    MISINFORMATION = "misinformation"
```

### Severity Levels

```python
class SeverityLevel(Enum):
    CLEAN = (0, "No issues detected")
    LOW = (1, "Minor concerns, likely technical")
    MEDIUM = (2, "Moderate concerns, review recommended")
    HIGH = (3, "Serious violations, action required")
    CRITICAL = (4, "Severe violations, immediate action")
    
    def __init__(self, level, description):
        self.level = level
        self.description = description
```

### Severity Calculation

```python
class SeverityCalculator:
    def calculate_severity(self, violations):
        """Calculate overall severity from violations"""
        
        if not violations:
            return SeverityLevel.CLEAN
        
        # Weight different factors
        factors = {
            "max_confidence": max(v.get("confidence", 0) for v in violations),
            "violation_count": len(violations),
            "category_severity": self._get_category_severity(violations),
            "context_score": self._get_context_score(violations)
        }
        
        # Calculate weighted score
        score = (
            factors["max_confidence"] * 0.4 +
            min(factors["violation_count"] / 10, 1) * 0.2 +
            factors["category_severity"] * 0.3 +
            (1 - factors["context_score"]) * 0.1
        )
        
        # Map to severity level
        if score < 0.2:
            return SeverityLevel.CLEAN
        elif score < 0.4:
            return SeverityLevel.LOW
        elif score < 0.6:
            return SeverityLevel.MEDIUM
        elif score < 0.8:
            return SeverityLevel.HIGH
        else:
            return SeverityLevel.CRITICAL
```

## Implementation Details

### Main Service Implementation

```python
@app.post("/check")
async def check_content(request: ContentCheckRequest):
    """Main content checking endpoint"""
    
    # Check cache first
    cache_key = hashlib.md5(request.content.encode()).hexdigest()
    cached_result = await cache.get(cache_key)
    
    if cached_result and not request.skip_cache:
        metrics.record_cache_hit()
        return cached_result
    
    # Preprocess content
    processed = preprocessor.process(request.content)
    
    # Run detection
    violations = await ensemble_detector.detect(processed)
    
    # Calculate severity
    severity = severity_calculator.calculate_severity(violations)
    
    # Format response
    response = {
        "content_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "severity": severity.name,
        "severity_level": severity.level,
        "violations": violations,
        "technical_context": request.technical_context,
        "metadata": {
            "processing_time_ms": processing_time,
            "detectors_used": ["rule_based", "ml_model", "context_aware"],
            "cache_hit": False
        }
    }
    
    # Cache result
    await cache.set(cache_key, response, ttl=3600)
    
    # Log to database
    await db.log_check(request, response)
    
    # Record metrics
    metrics.record_check(response)
    
    return response
```

### Preprocessing Pipeline

```python
class ContentPreprocessor:
    def process(self, content):
        """Preprocess content for detection"""
        
        # Normalize unicode
        content = unicodedata.normalize('NFKC', content)
        
        # Handle special characters
        content = self._handle_special_chars(content)
        
        # Preserve code blocks
        code_blocks = self._extract_code_blocks(content)
        content_with_placeholders = self._replace_code_blocks(content, code_blocks)
        
        # Normalize whitespace
        content = ' '.join(content.split())
        
        return {
            "original": content,
            "processed": content_with_placeholders,
            "code_blocks": code_blocks,
            "metadata": {
                "language": self._detect_language(content),
                "has_code": len(code_blocks) > 0,
                "length": len(content)
            }
        }
```

### Caching Strategy

```python
class HAPCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 3600  # 1 hour
        self.max_size = 10000
    
    async def get(self, key):
        """Get from cache with stats tracking"""
        
        result = await self.redis.get(f"hap:{key}")
        
        if result:
            # Update access stats
            await self.redis.zincrby("hap:popular", 1, key)
            
            # Refresh TTL for popular items
            access_count = await self.redis.zscore("hap:popular", key)
            if access_count > 10:
                await self.redis.expire(f"hap:{key}", self.ttl * 2)
        
        return json.loads(result) if result else None
    
    async def set(self, key, value, ttl=None):
        """Set with eviction policy"""
        
        # Check cache size
        size = await self.redis.dbsize()
        if size > self.max_size:
            await self._evict_least_used()
        
        # Store with TTL
        await self.redis.setex(
            f"hap:{key}",
            ttl or self.ttl,
            json.dumps(value)
        )
```

## API Reference

### Check Content Endpoint

```http
POST /check
Content-Type: application/json

{
    "content": "String to check for inappropriate content",
    "technical_context": true,
    "skip_cache": false,
    "metadata": {
        "user_id": "optional-user-id",
        "source": "api|cli|web",
        "content_type": "code|comment|documentation"
    }
}
```

**Response:**
```json
{
    "content_id": "uuid",
    "timestamp": "2024-01-15T10:00:00Z",
    "severity": "LOW",
    "severity_level": 1,
    "violations": [
        {
            "type": "rule_based",
            "category": "profanity",
            "pattern": "damn",
            "position": 45,
            "confidence": 0.9,
            "technical_context": true,
            "explanation": "Detected in variable name 'damn_this_bug'"
        }
    ],
    "technical_context": true,
    "metadata": {
        "processing_time_ms": 23,
        "detectors_used": ["rule_based", "ml_model", "context_aware"],
        "cache_hit": false
    }
}
```

### Batch Check Endpoint

```http
POST /check/batch
Content-Type: application/json

{
    "contents": [
        {
            "id": "custom-id-1",
            "content": "First content to check"
        },
        {
            "id": "custom-id-2",
            "content": "Second content to check"
        }
    ],
    "technical_context": true
}
```

### Configuration Endpoint

```http
GET /config

Response:
{
    "version": "1.0.0",
    "sensitivity_levels": {
        "current": "MEDIUM",
        "available": ["LOW", "MEDIUM", "HIGH"]
    },
    "categories": ["hate_speech", "abuse", "profanity", ...],
    "technical_context_enabled": true,
    "cache_enabled": true,
    "rate_limits": {
        "requests_per_minute": 1000,
        "requests_per_hour": 50000
    }
}
```

### Statistics Endpoint

```http
GET /stats?period=24h

Response:
{
    "period": "24h",
    "total_checks": 150000,
    "cache_hit_rate": 0.85,
    "severity_distribution": {
        "CLEAN": 0.92,
        "LOW": 0.05,
        "MEDIUM": 0.02,
        "HIGH": 0.008,
        "CRITICAL": 0.002
    },
    "category_distribution": {
        "profanity": 0.04,
        "abuse": 0.02,
        "technical_false_positive": 0.03
    },
    "average_processing_time_ms": 15,
    "technical_context_usage": 0.78
}
```

## Configuration

### Environment Variables

```bash
# Service Configuration
HAP_ENABLED=true
HAP_SERVICE_PORT=8005
HAP_LOG_LEVEL=INFO

# Detection Settings
HAP_TECHNICAL_CONTEXT_AWARE=true
HAP_REQUEST_BLOCKING_THRESHOLD=HIGH
HAP_OUTPUT_BLOCKING_THRESHOLD=HIGH
HAP_PROFANITY_SENSITIVITY=LOW

# Model Configuration
HAP_MODEL_PATH=/models/hap-detector
HAP_MODEL_THRESHOLD=0.85
HAP_ENABLE_ML_DETECTOR=true

# Cache Configuration
HAP_CACHE_ENABLED=true
HAP_CACHE_TTL=3600
HAP_CACHE_MAX_SIZE=10000

# Database Configuration
HAP_DB_ENABLED=true
HAP_DB_LOG_RETENTION_DAYS=30

# Performance
HAP_MAX_WORKERS=4
HAP_REQUEST_TIMEOUT=5
HAP_BATCH_SIZE=100
```

### Configuration File (hap_config.yaml)

```yaml
hap:
  version: "1.0.0"
  
  detection:
    enabled_detectors:
      - rule_based
      - ml_model
      - context_aware
    
    ensemble_weights:
      rule_based: 0.3
      ml_model: 0.5
      context_aware: 0.2
  
  technical_context:
    enabled: true
    confidence_threshold: 0.7
    term_database: "/data/technical_terms.json"
  
  severity_thresholds:
    LOW: 0.2
    MEDIUM: 0.4
    HIGH: 0.6
    CRITICAL: 0.8
  
  categories:
    hate_speech:
      enabled: true
      weight: 1.5
    abuse:
      enabled: true
      weight: 1.2
    profanity:
      enabled: true
      weight: 0.8
      technical_exceptions: true
  
  performance:
    cache:
      provider: redis
      ttl: 3600
      max_size: 10000
    
    rate_limiting:
      enabled: true
      requests_per_minute: 1000
      requests_per_hour: 50000
    
    timeouts:
      detection: 5
      preprocessing: 2
      ml_inference: 3
```

## Performance Optimization

### Optimization Strategies

1. **Intelligent Caching**
```python
class IntelligentCache:
    async def should_cache(self, content, result):
        """Determine if result should be cached"""
        
        # Always cache clean content
        if result["severity"] == "CLEAN":
            return True
        
        # Cache technical false positives
        if result.get("technical_context") and result["severity"] == "LOW":
            return True
        
        # Don't cache high-severity violations (might need review)
        if result["severity"] in ["HIGH", "CRITICAL"]:
            return False
        
        # Cache based on content characteristics
        if len(content) < 1000 and not self._contains_pii(content):
            return True
        
        return False
```

2. **Batch Processing**
```python
class BatchProcessor:
    async def process_batch(self, contents):
        """Process multiple contents efficiently"""
        
        # Group by similar content length
        groups = self._group_by_length(contents)
        
        results = []
        for group in groups:
            # Process group in parallel
            group_results = await asyncio.gather(*[
                self.check_content(content)
                for content in group
            ])
            results.extend(group_results)
        
        return results
```

3. **Model Optimization**
```python
class OptimizedMLDetector:
    def __init__(self):
        # Use quantized model for faster inference
        self.model = self._load_quantized_model()
        
        # Batch inference settings
        self.batch_size = 32
        self.max_sequence_length = 256
        
        # Model warm-up
        self._warmup_model()
```

### Performance Metrics

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "request_duration": Histogram(
                "hap_request_duration_seconds",
                "Request duration",
                buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
            ),
            "cache_hit_rate": Gauge(
                "hap_cache_hit_rate",
                "Cache hit rate"
            ),
            "detection_accuracy": Gauge(
                "hap_detection_accuracy",
                "Detection accuracy"
            )
        }
```

## Best Practices

### 1. Integration Guidelines

```python
# Good: Use technical context flag
result = await hap_client.check(
    content=code_snippet,
    technical_context=True
)

# Good: Batch similar content
results = await hap_client.check_batch(
    contents=code_snippets,
    technical_context=True
)

# Good: Handle results appropriately
if result.severity >= SeverityLevel.HIGH:
    await handle_violation(result)
elif result.severity == SeverityLevel.MEDIUM:
    await flag_for_review(result)
```

### 2. Content Preparation

```python
def prepare_content_for_check(content):
    """Prepare content for HAP checking"""
    
    # Separate code from comments
    code_parts = extract_code(content)
    comment_parts = extract_comments(content)
    
    # Check comments more strictly
    comment_results = await hap_client.check(
        comment_parts,
        technical_context=False
    )
    
    # Check code with technical context
    code_results = await hap_client.check(
        code_parts,
        technical_context=True
    )
    
    return combine_results(comment_results, code_results)
```

### 3. Error Handling

```python
async def safe_content_check(content):
    """Safely check content with fallback"""
    
    try:
        result = await hap_client.check(
            content,
            timeout=5
        )
        return result
        
    except TimeoutError:
        # Fallback to quick rule-based check
        return await quick_check(content)
        
    except HAPServiceError:
        # Log and allow content with warning
        logger.error("HAP service unavailable")
        return {
            "severity": "UNKNOWN",
            "warning": "Content not checked"
        }
```

## Future Enhancements

### Short Term (Q1 2025)

1. **Multilingual Support**
   - Detection in 10+ languages
   - Language-specific technical terms
   - Cultural context awareness

2. **Advanced ML Models**
   - Fine-tuned models per category
   - Few-shot learning for new patterns
   - Explainable AI for decisions

3. **Real-time Learning**
   - Feedback loop integration
   - Pattern updates without restart
   - A/B testing for rules

### Medium Term (Q2-Q3 2025)

1. **Context Enhancement**
   - Repository-wide context
   - User history consideration
   - Project type awareness

2. **Integration Ecosystem**
   - IDE plugins
   - Git hooks
   - CI/CD integration

3. **Advanced Analytics**
   - Trend analysis
   - Predictive violations
   - User behavior patterns

### Long Term (Q4 2025+)

1. **AI-Powered Moderation**
   - Conversational understanding
   - Intent detection
   - Suggestion generation

2. **Federated Learning**
   - Privacy-preserving updates
   - Cross-organization learning
   - Bias detection and mitigation

3. **Autonomous Moderation**
   - Self-improving rules
   - Adaptive thresholds
   - Zero-config deployment

## Conclusion

The HAP Content Moderation System represents a sophisticated approach to content moderation in technical contexts. By combining multiple detection mechanisms with deep technical understanding, it provides accurate, fast, and context-aware moderation that enhances platform safety without hindering legitimate technical discussions.

The system's ability to distinguish between technical usage and actual violations, combined with its performance optimizations and comprehensive configuration options, makes it an essential component of the Quantum Layer Platform's commitment to creating a safe and productive environment for developers.