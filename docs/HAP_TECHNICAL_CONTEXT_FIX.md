# HAP Technical Context Fix - Implementation Summary

## Overview

The HAP (Hate, Abuse, and Profanity) system was blocking legitimate programming terminology like "kill process", "abort thread", and "attack vector". This fix adds technical context awareness to prevent false positives while maintaining safety.

## Changes Made

### 1. Added Technical Context Detection (`src/moderation/hap_service.py`)

Added `_is_technical_context()` method that detects:
- Programming constructs (process, thread, function, class, etc.)
- Code syntax patterns (function calls, JSON, arrays, etc.)
- Command line patterns (shell prompts, flags, pipes)
- File paths and extensions
- Code-like formatting (indentation, comments)

### 2. Modified Rule-Based Checking

Updated `_rule_based_check()` to:
- Check if content is in technical context
- Apply adjusted severity for technical terms:
  - `kill` → LOW severity (was HIGH)
  - `abort` → LOW severity (was MEDIUM)
  - `attack` → LOW severity (was HIGH)
  - `die` → LOW severity (was HIGH)
  - `execute` → CLEAN (was MEDIUM)
  - etc.
- Handle mild insults in technical context (e.g., "dummy data")

### 3. Added Configuration Settings (`src/common/config.py`)

New settings for fine-tuning:
- `HAP_ENABLED`: Enable/disable HAP entirely
- `HAP_TECHNICAL_CONTEXT_AWARE`: Enable technical context detection
- `HAP_REQUEST_BLOCKING_THRESHOLD`: Severity threshold for blocking requests
- `HAP_OUTPUT_BLOCKING_THRESHOLD`: Severity threshold for blocking outputs
- `HAP_PROFANITY_SENSITIVITY`: Adjust profanity detection sensitivity

### 4. Updated Blocking Logic

Modified blocking checks in:
- `src/orchestrator/main.py`: Uses configurable request threshold
- `src/orchestrator/worker_production.py`: Uses configurable thresholds for both requests and outputs

## Technical Context Examples

### Now Allowed (LOW severity or CLEAN):
```bash
# Shell commands
kill -9 12345
ps aux | grep python | kill

# Code
def kill_process(pid):
    os.kill(pid, signal.SIGTERM)

# Documentation
"To terminate a process, use the kill command"
"Common attack vectors in web security"

# Error messages
"Error: Process died unexpectedly"
"Warning: Thread will be terminated"
```

### Still Blocked (HIGH severity):
```
"I will kill you"  # Actual threat
"Go harm yourself"  # Self-harm content
# Other genuinely harmful content
```

## Configuration Examples

### Default (Balanced):
```env
HAP_REQUEST_BLOCKING_THRESHOLD=HIGH  # Only block severe content
HAP_TECHNICAL_CONTEXT_AWARE=true     # Enable tech detection
```

### Strict Mode:
```env
HAP_REQUEST_BLOCKING_THRESHOLD=MEDIUM  # Block more content
HAP_TECHNICAL_CONTEXT_AWARE=false      # No special tech handling
```

### Lenient Mode:
```env
HAP_REQUEST_BLOCKING_THRESHOLD=CRITICAL  # Only block worst content
HAP_PROFANITY_SENSITIVITY=LOW           # Allow mild profanity
```

## Testing

Run the test script to verify:
```bash
python test_hap_technical_context.py
```

The test covers:
- Common shell commands with "kill"
- Programming terminology
- Code examples
- Documentation text
- Variable names with mild terms
- Actual harmful content (should still block)

## Impact

1. **Developers can now**:
   - Discuss process management ("kill process")
   - Write security documentation ("attack vectors")
   - Use common programming terms freely
   - Include error messages with technical terms

2. **System still blocks**:
   - Actual threats and harassment
   - Genuine hate speech
   - Self-harm content
   - Non-technical harmful content

## Migration Notes

- No database changes required
- Configuration is backward compatible
- Default thresholds match previous behavior
- Can be rolled back by setting `HAP_TECHNICAL_CONTEXT_AWARE=false`

## Future Improvements

1. **LLM-Based Context Understanding**: Implement the placeholder LLM check for nuanced analysis
2. **Domain-Specific Dictionaries**: Add specialized term lists for different domains
3. **User Feedback Loop**: Learn from false positives/negatives
4. **Per-Tenant Configuration**: Allow different sensitivity per customer