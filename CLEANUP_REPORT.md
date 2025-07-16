# QLP Codebase Cleanup Report

## Summary
This report identifies zombie files (unused/unreferenced), stale files (outdated/duplicate), and files that should be cleaned up in the qlp-dev codebase.

## 1. Duplicate Worker Files (High Priority)

The `src/orchestrator/` directory contains multiple versions of worker files that appear to be duplicates or iterations:

### Active Worker Files:
- `worker_production.py` (152KB) - Main production worker currently used
- `worker_production_db.py` (6KB) - Database-aware worker wrapper
- `enterprise_worker.py` - Enterprise features worker (used when ENTERPRISE_MODE=true)

### Likely Zombie Worker Files:
- `worker.py` (10KB) - Old basic worker, not referenced
- `worker_prod.py` (26KB) - Old production worker, not referenced  
- `worker_production_enhanced.py` (18KB) - Enhancement attempt, not actively used
- `worker_production_fixed.py` (46KB) - Bug fix attempt, not actively used

**Recommendation**: Delete the zombie worker files after confirming they're not needed.

## 2. Test Files in Root Directory (Medium Priority)

There are 66 test files scattered in the root directory that should be organized:

### Recent/Active Test Files (keep in tests/ folder):
- `test_enterprise_simple.py`
- `test_severity_comparison.py`
- `test_qdrant_*.py` (batch operations, indexing, search, real data)
- `test_hap_*.py` (debug, technical context, system, etc.)
- `test_azure_llm_client.py`
- `test_full_platform_demo.py`
- `test_nlp_to_production.py`

### Older/One-off Test Files (consider removing or archiving):
- `test_temporal_minimal.py`
- `test_temporal_issue.py`
- `test_execute_endpoint.py`
- `test_docker_simple.py`
- `test_cost_*.py` (multiple cost calculation tests)
- `test_current_api.py`
- `test_api_temporal.py`

**Recommendation**: 
1. Create a proper `tests/` directory structure
2. Move active tests to appropriate subdirectories
3. Archive or delete one-off/debugging tests

## 3. Files That Should Be in .gitignore (High Priority)

The following files are currently tracked but should be gitignored:

### Generated/Temporary Files:
- `.DS_Store` - macOS system file
- `.idea/` - IDE configuration directory
- `workflow_id.txt` - Temporary workflow ID storage
- `test_capsule.zip` - Test output file
- `enhanced_platform.log` - Log file

### Generated Code Directory:
- `generated/` - Contains generated capsule code, should typically be gitignored
- `qlp-cli/generated/` - More generated code

**Recommendation**: Add these patterns to `.gitignore`

## 4. Monitoring Directory (Low Priority)

The `monitoring/` directory appears to be a stub with only config files:
- `monitoring/grafana/dashboards/` - Empty dashboards directory
- `monitoring/prometheus.yml` - Prometheus config

**Recommendation**: Either populate with actual monitoring configs or remove if not used

## 5. Deleted But Tracked Files

From git status, this file was deleted but is still tracked:
- `src/agents/enhanced_confidence_scorer.py` - Deleted file (no references found)

**Recommendation**: Complete the deletion with `git rm`

## 6. Duplicate/Similar Named Files

### GitHub Integration Versions:
- `github_integration.py`
- `github_integration_v2.py`
- `enhanced_github_integration.py`
- `production_github_integration.py`

**Recommendation**: Consolidate to one main integration file

### Capsule-related Files (many variations):
- `enhanced_capsule.py`
- `robust_capsule_generator.py`
- `intelligent_capsule_generator.py`
- `production_capsule_system.py`

**Recommendation**: Review and consolidate capsule generation logic

### Validator Files:
- `enhanced_validator.py`
- `production_validator.py`
- `capsule_validator.py`
- `execution_validator.py`
- `qlcapsule_runtime_validator.py`

**Recommendation**: Consolidate validation logic

## 7. Shell Scripts (Medium Priority)

Multiple shell scripts for similar purposes:
- `demo_improvements.sh`
- `run_enterprise_test.sh`
- `test_enterprise_*.sh`
- `start_enterprise.sh`
- `start_enterprise_worker.sh`

**Recommendation**: Consolidate into fewer, well-documented scripts

## 8. Python Scripts in Root (Low Priority)

Many Python scripts in root that could be organized:
- `monitor_workflow.py`
- `push_to_github.py`
- `download_capsule*.py` (multiple versions)
- `init_database.py`, `init_db_docker.py`, `init_db_simple.py`

**Recommendation**: Move to `scripts/` directory

## Cleanup Priority List

### Immediate Actions:
1. Add entries to `.gitignore` for generated files, logs, and OS files
2. Remove duplicate worker files after verification
3. Complete deletion of `enhanced_confidence_scorer.py`

### Short Term:
1. Organize test files into proper directory structure
2. Consolidate GitHub integration files
3. Clean up shell scripts

### Long Term:
1. Review and consolidate capsule generation modules
2. Consolidate validation modules
3. Organize root-level Python scripts

## Commands to Execute Cleanup

```bash
# Add to .gitignore
echo ".DS_Store" >> .gitignore
echo ".idea/" >> .gitignore
echo "*.log" >> .gitignore
echo "workflow_id.txt" >> .gitignore
echo "test_capsule.zip" >> .gitignore
echo "generated/" >> .gitignore
echo "qlp-cli/generated/" >> .gitignore

# Remove zombie worker files (after verification)
git rm src/orchestrator/worker.py
git rm src/orchestrator/worker_prod.py
git rm src/orchestrator/worker_production_enhanced.py
git rm src/orchestrator/worker_production_fixed.py

# Complete deletion of already removed file
git rm src/agents/enhanced_confidence_scorer.py

# Create test directory structure
mkdir -p tests/{unit,integration,e2e,performance}

# Remove tracked files that should be ignored
git rm -r --cached .idea/
git rm --cached .DS_Store
git rm --cached workflow_id.txt
git rm --cached test_capsule.zip
git rm --cached enhanced_platform.log
```

## Estimated Impact

- **Disk Space Saved**: ~300KB from duplicate worker files
- **Code Clarity**: Significant improvement by removing confusion from multiple versions
- **Maintenance**: Easier to maintain with organized test structure
- **Git History**: Cleaner commits without generated/temporary files