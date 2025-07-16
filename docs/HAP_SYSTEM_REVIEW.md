# HAP (Hate, Abuse, and Profanity) System Review

## Executive Summary

The HAP content moderation system is blocking legitimate technical content because it's too context-insensitive. Programming terms like "kill process", "abort thread", or "attack vector" trigger HIGH severity blocks, preventing developers from discussing technical concepts.

## System Overview

### Purpose
HAP (Hate, Abuse, and Profanity) is a content moderation system designed to:
- Prevent harmful content in user requests
- Filter inappropriate agent outputs
- Maintain platform safety standards

### Architecture
```
User Input → HAP Check → Pass/Block → Processing
                              ↓
                            Block → Error Response
Agent Output → HAP Check → Pass/Fail → Delivery
```

## Current Implementation

### 1. Detection Layers

**Rule-Based (Active)**
- Regex pattern matching
- Word list checking  
- Handles leetspeak/unicode
- Categories: hate_speech, abuse, profanity, violence, self_harm

**ML-Based (Placeholder)**
- Currently returns clean results
- Intended for ambiguous cases

**LLM-Based (Placeholder)**
- Currently returns clean results
- Intended for context understanding

### 2. Severity Levels

| Severity | Action | Example Terms |
|----------|--------|---------------|
| LOW | Log only | "stupid", "dumb", "idiot" |
| MEDIUM | Flag + Allow | Context-dependent |
| HIGH | **BLOCK** | "kill", "harm", "attack", "threat" |
| CRITICAL | **BLOCK** | Severe hate speech |

### 3. Integration Points

**Request Input** (`src/orchestrator/main.py`):
```python
hap_result = await hap_service.check_content(request.description)
if hap_result.severity >= Severity.HIGH:
    raise HTTPException(status_code=400, detail="Content blocked by moderation")
```

**Agent Output** (`src/orchestrator/worker_production.py`):
```python
if agent_result.output_type == "code":
    hap_result = await hap_service.check_content(agent_result.output["content"])
    if hap_result.severity >= Severity.HIGH:
        task_results[task.id] = TaskResult(
            task_id=task.id,
            status=TaskStatus.FAILED,
            error="Content blocked by moderation"
        )
```

## Problems Identified

### 1. Technical Terms Blocked

Programming terminology triggers false positives:
- `kill -9 <pid>` → "kill" triggers ABUSE (HIGH) → **BLOCKED**
- `thread.abort()` → "abort" triggers potential violence → **BLOCKED**  
- `attack vector` → "attack" triggers ABUSE (HIGH) → **BLOCKED**
- `die("Error message")` → "die" triggers ABUSE (HIGH) → **BLOCKED**

### 2. Context Insensitivity

The system can't distinguish between:
- Technical usage: "kill the process"
- Harmful usage: actual threats

### 3. Over-Conservative Patterns

Current regex patterns in `hap_service.py`:
```python
'abuse': {
    'patterns': [
        r'\b(kill|hurt|harm|destroy|attack|threat|die|murder)\b',
        # ... more patterns
    ],
    'severity': Severity.HIGH  # This blocks technical discussions!
}
```

### 4. No Domain Awareness

The system treats all content equally:
- Code comments
- Documentation  
- Shell commands
- User descriptions
- Error messages

## Impact on Users

1. **False Rejections**: Legitimate code generation requests blocked
2. **Workarounds Required**: Users must avoid technical terms
3. **Confusion**: "Why is 'kill process' offensive?"
4. **Productivity Loss**: Rewriting requests to avoid triggers

## Comparison with AITL Issue

Both systems share similar problems:

| System | Issue | Impact |
|--------|-------|--------|
| AITL | Treats warnings as failures | Valid code rejected |
| HAP | Treats technical terms as abuse | Valid requests blocked |

## Recommended Fixes

### 1. Immediate Fix: Adjust Blocking Threshold

```python
# In settings
HAP_BLOCKING_THRESHOLD = Severity.CRITICAL  # Only block severe cases
HAP_TECHNICAL_CONTEXT_AWARE = True         # Enable context detection
```

### 2. Add Technical Context Detection

```python
def is_technical_context(text: str) -> bool:
    """Detect if text is in technical/programming context"""
    technical_indicators = [
        r'process|thread|service|daemon',
        r'command|bash|shell|terminal',
        r'function|method|class|module',
        r'error|exception|debug|log',
        r'<.*>|{.*}|\[.*\]',  # Code syntax
    ]
    return any(re.search(pattern, text, re.I) for pattern in technical_indicators)

async def check_content_with_context(self, text: str) -> HAPResult:
    # First check if technical context
    if is_technical_context(text):
        # Apply relaxed rules for technical content
        return self._check_technical_content(text)
    else:
        # Apply standard rules
        return self._check_general_content(text)
```

### 3. Implement Severity Adjustments

```python
# Adjust severity for technical terms
TECHNICAL_ADJUSTMENTS = {
    'kill': {'technical': Severity.LOW, 'general': Severity.HIGH},
    'abort': {'technical': Severity.LOW, 'general': Severity.MEDIUM},
    'attack': {'technical': Severity.LOW, 'general': Severity.HIGH},
    'die': {'technical': Severity.LOW, 'general': Severity.HIGH},
    'crash': {'technical': Severity.LOW, 'general': Severity.MEDIUM},
}
```

### 4. Configuration Options

```python
class HAPConfig:
    # Blocking thresholds
    REQUEST_BLOCKING_THRESHOLD = Severity.CRITICAL
    OUTPUT_BLOCKING_THRESHOLD = Severity.HIGH
    
    # Feature flags
    TECHNICAL_CONTEXT_AWARE = True
    USE_LLM_FOR_CONTEXT = True
    
    # Sensitivity settings
    PROFANITY_SENSITIVITY = "low"  # low, medium, high
    ABUSE_SENSITIVITY = "low"      # low, medium, high
```

### 5. Implement LLM-Based Context Understanding

Replace the placeholder LLM detection with actual implementation:

```python
async def _llm_based_detection(self, text: str, rule_result: Dict) -> Dict:
    """Use LLM to understand context"""
    prompt = f"""
    Analyze if this text contains harmful content or is technical discussion:
    
    Text: "{text}"
    Initial detection: {rule_result}
    
    Consider:
    1. Is this programming/technical context?
    2. Are flagged words used technically (e.g., "kill process")?
    3. What is the actual intent?
    
    Return:
    {{
        "is_harmful": boolean,
        "is_technical": boolean,
        "actual_severity": "LOW|MEDIUM|HIGH|CRITICAL",
        "reasoning": "explanation"
    }}
    """
    
    # Call LLM and parse response
    response = await self.llm_client.analyze(prompt)
    return response
```

## Implementation Priority

1. **High Priority**:
   - Adjust blocking threshold to CRITICAL only
   - Add technical context detection
   - Fix regex patterns for common technical terms

2. **Medium Priority**:
   - Implement LLM-based context understanding
   - Add configuration options
   - Create whitelist for technical domains

3. **Low Priority**:
   - Implement ML-based detection
   - Add per-tenant sensitivity settings
   - Build feedback system for false positives

## Testing Recommendations

Test with common technical phrases:
- "Kill the background process"
- "The server might die under load"
- "Abort the current transaction"
- "Common attack vectors include..."
- "Thread execution was terminated"

## Conclusion

The HAP system is well-architected but needs context awareness to distinguish between technical usage and actual harmful content. Like the AITL system, it's being too conservative and blocking legitimate use cases. The recommended fixes will maintain safety while allowing technical discussions.