# HCode Agent Quick Start Fix Guide

**Goal:** Get from 68/100 to production-ready in minimum time
**Target:** 95/100 score — reliable, secure, performant
**Timeline:** 7-8 days (MVP) or 3-4 weeks (complete)

---

## 🚨 IMMEDIATE ACTIONS (Day 1)

### Critical Bug Fix #1: NameError Crash (30 minutes)

**File:** `src/hcode/core/phases/verification_handler.py`

**Line 186 - Change:**
```python
# BEFORE (CRASHES):
self._update_hcode_memory(
    context=context,
    test_results=test_results,
    verification_analysis=analysis_response,  # ❌ UNDEFINED
    verdict=verdict
)

# AFTER (FIXED):
self._update_hcode_memory(
    context=context,
    test_results=test_results,
    verification_analysis=verification_analysis,  # ✅ CORRECT
    verdict=verdict
)
```

**Test:**
```bash
# Run verification tests
pytest tests/integration/test_pev_deep_scenario.py::test_verification_handler_thinking_generation -v

# Should pass without NameError
```

---

### Critical Bug Fix #2: AttributeError in Walkthrough (1 hour)

**File:** `src/hcode/core/phases/verification_handler.py`

**Line 904 - Replace entire block:**
```python
# BEFORE (CRASHES):
response = await self.provider.generate(
    messages=[{"role": "user", "content": prompt}],
    max_tokens=2000,
    temperature=0.3,
)

# AFTER (FIXED):
from hcode.providers.base import Message

response = await self.provider.generate_completion(
    messages=[Message(role="user", content=prompt)],
    max_tokens=2000,
    temperature=0.3,
)
```

**Test:**
```bash
# Run full PEV scenario
pytest tests/integration/test_pev_deep_scenario.py -v

# Verification should complete and create walkthrough.md
```

---

### Validate Fixes (30 minutes)

```bash
# Run all PEV tests
pytest tests/integration/test_pev_deep_scenario.py -v
pytest tests/unit/test_refactored_components.py -v

# Run a real task
hcode "Add a simple hello() function to a test file"

# Should complete all 3 phases without crashes
```

**Milestone:** ✅ Agent completes PEV workflow without crashes (75/100)

---

## ⚡ PERFORMANCE OPTIMIZATION (Days 2-3)

### Task #4: Remove Tool Format Duplication (2 hours)

**Files to edit:**

1. **execution_handler.py** (lines 308-316)
```python
# DELETE this block (tool examples are in tool_format.md):
"""
**Available tools:**
- LS: `{{"tool": "LS", "arguments": {{"DirectoryPath": "."}}}}`
- Read: `{{"tool": "Read", "arguments": {{"AbsolutePath": "/full/path"}}}}`
...
"""
```

2. **verification_handler.py** (lines 340-343)
```python
# DELETE similar tool examples block
```

3. **planning_handler.py** (lines 1148-1151)
```python
# KEEP minimal reference, reduce examples to 2-3 only
```

**Test:**
```bash
# Verify prompts still load
python -m pytest tests/unit/test_core_prompt_loader.py -v

# Run planning phase
hcode "Test task"
# Should still work
```

**Savings:** ~600 tokens per phase = 1,800 tokens per task

---

### Task #7: Temperature Optimization (1 hour)

**execution_handler.py** (line 131):
```python
# BEFORE:
response = await self.provider.generate_completion(
    messages=messages,
    system_prompt=system_prompt,
    temperature=0.7,  # ❌ TOO HIGH FOR CODE
    max_tokens=16384,
)

# AFTER:
response = await self.provider.generate_completion(
    messages=messages,
    system_prompt=system_prompt,
    temperature=0.3,  # ✅ DETERMINISTIC CODE GEN
    max_tokens=16384,
)
```

**verification_handler.py** (line 295):
```python
# Change temperature from 0.7 to 0.3
# (Same pattern as above)
```

**Keep planning at 0.7** (exploration benefits from creativity)

**Test:**
```bash
# Run execution phase
hcode "Write a fibonacci function"

# Code should be more consistent across runs
```

**Impact:** More deterministic code generation, fewer "creative" bugs

**Milestone:** ✅ Optimized performance (82/100)

---

## 🔒 SECURITY HARDENING (Days 4-5)

### Task #11: Execution Write Gate (4 hours)

**Add to ExecutionPhaseHandler** (`execution_handler.py`):

```python
def _extract_planned_files(self, plan_content: str) -> set:
    """Extract allowed file paths from implementation plan."""
    import re

    allowed = set()

    # [MODIFY] /path/to/file pattern
    allowed.update(re.findall(r'\[MODIFY\]\s+([^\s]+)', plan_content))

    # [NEW] /path/to/file pattern
    allowed.update(re.findall(r'\[NEW\]\s+([^\s]+)', plan_content))

    # file:///path markdown links
    allowed.update(re.findall(r'file:///([^\)]+)', plan_content))

    # Always allow task.md
    allowed.add(".hcode/task.md")

    return allowed

async def _execute_tools(self, tool_calls, context):
    """Override to add write gate."""
    plan = self.artifact_manager.load_artifact("implementation_plan.md", context)
    allowed_files = self._extract_planned_files(plan) if plan else set()

    gated_calls = []

    for tc in tool_calls:
        tool_name = tc.get("tool", "").lower()

        if tool_name in ("write", "writetool"):
            target = tc.get("arguments", {}).get("TargetFile", "")

            if not any(allowed in target for allowed in allowed_files):
                self._display(f"BLOCKED: {target} not in plan", style="error")
                continue  # Skip

        gated_calls.append(tc)

    return await super()._execute_tools(gated_calls, context)
```

**Test:**
```bash
# Create test with AI attempting to write unauthorized file
# Should block and continue
```

**Milestone:** ✅ Security hardened (87/100)

---

## 📊 PRODUCTION SAFEGUARDS (Days 6-7)

### Task #12: Token Budget Enforcement (3 hours)

**Update AgentContext** (`protocols.py`):
```python
@dataclass
class AgentContext:
    # ... existing fields ...
    tokens_used: Dict[str, int] = field(default_factory=dict)
    token_budget: int = 500000  # 500K per task
```

**Add to BasePhaseHandler._generate_and_execute()** (`base_handler.py` after line 596):
```python
# After provider.generate_completion call:

# Estimate tokens (rough)
prompt_tokens = len(enhanced_prompt.split()) * 1.3
response_tokens = len(result.split()) * 1.3
round_tokens = int(prompt_tokens + response_tokens)

# Track
context.tokens_used[self.phase_name] = \
    context.tokens_used.get(self.phase_name, 0) + round_tokens

# Check budget
total_used = sum(context.tokens_used.values())
if total_used > context.token_budget:
    logger.warning(f"Token budget exceeded: {total_used}/{context.token_budget}")
    self._display(f"⚠️ Token budget reached ({total_used} tokens)", style="error")
    break  # Early termination
```

**Test:**
```bash
# Set low budget and verify termination
# Should log warning and stop gracefully
```

---

### Task #13: Phase Timeouts (2 hours)

**Add to BasePhaseHandler._generate_and_execute()** (`base_handler.py`):
```python
async def _generate_and_execute(
    self,
    prompt: str,
    context: AgentContext,
    system_prompt: Optional[str] = None,
    max_rounds: int = 8,
    max_tokens: int = 8192,
    timeout_seconds: int = 600,  # NEW: 10 min default
):
    from datetime import datetime

    start_time = datetime.now()

    for round_num in range(max_rounds):
        # Check timeout
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > timeout_seconds:
            logger.warning(f"Phase timeout after {elapsed:.1f}s")
            self._display(f"⚠️ Phase timeout ({elapsed:.1f}s)", style="error")
            break

        # ... rest of loop ...
```

**Update handler calls:**
- Planning: `timeout_seconds=600` (10 min)
- Execution: `timeout_seconds=900` (15 min)
- Verification: `timeout_seconds=300` (5 min)

**Milestone:** ✅ Production safeguards active (92/100)

---

## 🧪 TESTING (Days 7-8)

### Task #3: Verification Unit Test (2 hours)

**Create:** `tests/unit/test_verification_handler.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock
from hcode.core.phases.verification_handler import VerificationPhaseHandler
from hcode.core.protocols import AgentContext, PhaseResult

@pytest.mark.asyncio
async def test_verification_happy_path_no_crash():
    # Mock dependencies
    artifact_manager = Mock()
    artifact_manager.load_artifact.side_effect = lambda name, ctx: {
        "task.md": "# Task\n- [x] Done",
        "implementation_plan.md": "# Plan\n[MODIFY] file.py",
    }.get(name, "")
    artifact_manager.create_artifact = Mock()

    provider = AsyncMock()
    provider.generate_completion = AsyncMock(return_value=Mock(content="Analysis complete"))

    tool_executor = Mock()
    context_manager = Mock()

    # Create handler
    handler = VerificationPhaseHandler(
        artifact_manager, provider, tool_executor, context_manager
    )

    # Create context
    context = AgentContext(
        task="Test task",
        session_id="test123",
        working_dir="/test",
        iteration=1,
        modified_files=["src/file.py"],
    )

    # Execute
    result = await handler.handle(context, Mock())

    # Assertions
    assert result.success
    assert "walkthrough.md" in result.artifacts_created
    # Should NOT crash with NameError
```

**Run:**
```bash
pytest tests/unit/test_verification_handler.py -v
```

---

### Task #19: Regression Tests (2 hours)

**Create:** `tests/regression/test_memory_md_issues.py`

```python
def test_planning_deletes_stale_artifacts():
    """Regression: Stale artifacts persistence (MEMORY.md)"""
    # Create old task.md with different content
    # Run planning
    # Assert new task.md created (not appended)
    pass

def test_planning_blocks_implementation_files():
    """Regression: AI creates implementation files during planning"""
    # Attempt Write to src/file.py during planning
    # Assert blocked
    pass

def test_verification_scope_aware_testing():
    """Regression: Verification runs full test suite for single file"""
    # 1 modified file → should use py_compile
    # 3+ files → should use pytest
    pass
```

**Milestone:** ✅ Comprehensive testing (95/100)

---

## ✅ VALIDATION CHECKLIST

Before deploying to production:

### Functionality
- [ ] Planning phase creates task.md and implementation_plan.md
- [ ] Execution phase modifies files and updates task.md
- [ ] Verification phase creates walkthrough.md without crashes
- [ ] All 3 phases transition correctly

### Performance
- [ ] Token usage logged per phase
- [ ] Budget enforcement works (test with low limit)
- [ ] Phase timeouts prevent hangs
- [ ] Temperature optimized (0.3 for code, 0.7 for planning)

### Security
- [ ] Planning write gate blocks non-artifact files
- [ ] Execution write gate blocks files not in plan
- [ ] Shell command sanitization (if implemented)

### Quality
- [ ] All integration tests pass
- [ ] No NameError or AttributeError crashes
- [ ] Walkthrough generated by AI (not fallback)
- [ ] Task.md accurately reflects completion status

---

## 🎯 PRODUCTION DEPLOYMENT

**Minimum Viable Production (7-8 days):**
- ✅ Critical bugs fixed (Day 1)
- ✅ Performance optimized (Days 2-3)
- ✅ Security hardened (Days 4-5)
- ✅ Production safeguards (Days 6-7)
- ✅ Testing complete (Day 8)

**Score: 95/100** — Production ready with monitoring

**Complete Roadmap (3-4 weeks):**
- All 22 tasks completed
- Score: 100/100 — Enterprise-grade

---

## 📞 SUPPORT

**Questions?** All detailed implementation specs in:
- `PRODUCTION_READINESS_ROADMAP.md` — Full roadmap
- `ARCHITECTURE_REVIEW_TECHNICAL_SPEC.md` — Technical details
- Task descriptions — View with `/tasks` command

**Issues?** Check `C:\Users\hamdij\.claude\projects\D--workshops-Hcaude\memory\MEMORY.md` for past solutions.
