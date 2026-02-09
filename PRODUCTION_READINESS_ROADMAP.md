# HCode Agent: Production Readiness Roadmap to 100%

**Current Status:** 68/100 — CONDITIONAL GO (after fixing P0 bugs)
**Target:** 100/100 — Full Production Ready with Claude Code Performance
**Timeline:** 3-4 weeks for complete implementation

---

## Executive Summary

The HCode PEV (Planning → Execution → Verification) architecture is well-designed but has critical bugs and optimization opportunities. This roadmap provides a clear path to 100% production readiness with performance matching Claude Code.

### Critical Findings

✅ **Strengths:**
- Clean separation of concerns (adapter → orchestrator → phase_manager → handlers)
- Excellent planning write gate prevents unauthorized file creation
- Programmatic codebase exploration before AI (reduces hallucination)
- Phase-aware continuation prompts for multi-round control
- Scope-aware test execution (prevents running 700+ irrelevant tests)

❌ **Critical Bugs (Fix Immediately):**
1. **NameError crash** in verification phase (line 186) — crashes on every successful run
2. **AttributeError** in walkthrough generation (line 904) — AI walkthrough never works

⚠️ **Optimization Needed:**
- 3,500 tokens wasted per PEV cycle due to prompt redundancy
- Meta-cognitive trackers (450 lines) never used by AI
- No token budgeting → worst case 1.6M tokens per task
- InitHandler duplicates 200 lines from BasePhaseHandler
- No loop detection, timeouts, or checkpoint-resume

---

## Implementation Roadmap

### **Sprint 1: Critical Fixes** (2-3 days) 🔴 **PRIORITY 0**

| Task | File | Status | Impact |
|------|------|--------|--------|
| Fix `analysis_response` NameError | `verification_handler.py:186` | **BLOCKING** | Verification crashes on all runs |
| Fix `provider.generate()` call | `verification_handler.py:904` | **BLOCKING** | AI walkthrough never works |
| Add verification unit tests | `tests/unit/test_verification_handler.py` | **REQUIRED** | Prevent regression |

**Acceptance:** All PEV phases complete without crashes. Verification creates AI-driven walkthrough.

---

### **Sprint 2: Prompt Optimization** (3-4 days) 🟡 **PRIORITY 1**

**Goal:** Reduce token usage by 3,500 per task while improving GPT-OSS-120B compatibility.

| Task | Token Savings | Files Modified |
|------|---------------|----------------|
| Remove inline tool docs duplication | ~600/phase | `execution_handler.py`, `verification_handler.py`, `planning_handler.py` |
| Centralize thinking protocol | ~400/phase | `planning_mode.md`, `execution_handler.md`, `verification_handler.md` |
| Add `<output>` tags for structured extraction | Better quality | `execution_handler.md`, `verification_handler.md` |
| Differentiate temperature (0.3 for code, 0.7 for planning) | More deterministic | All phase handlers |

**Acceptance:**
- Token usage reduced by ~3,500 per full PEV cycle
- All prompts use consistent `<thinking>` + `<output>` structure
- Code generation more deterministic (temperature 0.3)

---

### **Sprint 3: Architecture Cleanup** (4-5 days) 🟢 **PRIORITY 1**

**Goal:** Remove dead weight, improve maintainability.

| Task | Lines Removed | Impact |
|------|---------------|--------|
| Remove meta-cognitive trackers | ~450 | Simplifies planning logic |
| Refactor InitHandler → extend BasePhaseHandler | ~200 | Eliminates duplication |
| Add loop detection (response hash) | +30 | Prevents degenerate loops |
| Add execution write gate | +50 | Security boundary |

**Acceptance:**
- 650 lines of dead code removed
- InitHandler properly extends BasePhaseHandler
- Execution phase cannot write unauthorized files
- Loop detection breaks within 2 identical responses

---

### **Sprint 4: Production Hardening** (5-6 days) 🟢 **PRIORITY 2**

**Goal:** Add production-grade reliability and observability.

| Feature | Benefit | Implementation |
|---------|---------|----------------|
| Token counting + budget | Prevent runaway costs | Track in AgentContext, enforce 500K limit |
| Wall-clock timeouts | Prevent hung sessions | 10 min planning, 15 min execution, 5 min verification |
| Checkpoint-resume | Recover from failures | Serialize AgentContext after each subtask |
| Structured telemetry | Production monitoring | JSONL export with tokens, rounds, duration per phase |
| Command sanitization | Prevent injection | Whitelist safe test patterns |

**Acceptance:**
- Token budget enforced (500K per task)
- Phase timeouts prevent infinite hangs
- Failed tasks can resume from checkpoint
- Telemetry exported to `.hcode/telemetry.jsonl`
- Only whitelisted shell commands execute

---

### **Sprint 5: Quality & Testing** (3-4 days) 🔵 **PRIORITY 2**

**Goal:** Comprehensive test coverage for confidence in production.

| Test Suite | Coverage | Purpose |
|------------|----------|---------|
| E2E PEV test with multi-round mocking | Full workflow | Catch integration bugs |
| Property-based tests for tool extraction | Edge cases | Harden parser |
| Regression tests for all MEMORY.md issues | Past bugs | Prevent recurrence |

**Acceptance:**
- E2E test validates full planning → execution → verification flow
- Tool extraction handles malformed JSON gracefully
- All 10+ MEMORY.md issues have regression tests

---

### **Sprint 6: Advanced Optimizations** (2-3 days) 🟣 **PRIORITY 3**

**Goal:** Squeeze maximum performance.

| Optimization | Benefit |
|--------------|---------|
| Enhanced continuation prompts (include Read results) | Better AI context awareness |
| Multi-format plan step parsing | Robustness to different plan structures |
| Optimized token budgets (profiling-based) | ~20% cost reduction |

**Acceptance:**
- Continuation prompts show what was just read
- Plan parser handles numbered, block, and checklist formats
- Token budgets right-sized per phase

---

## Performance Targets (Claude Code Parity)

| Metric | Current | Target | Strategy |
|--------|---------|--------|----------|
| **Success Rate** | 75% (crashes in verification) | 95% | Fix bugs, add retry logic |
| **Token Efficiency** | ~1.2M per task | ~500K per task | Deduplicate prompts, optimize budgets |
| **Response Quality** | Good (when works) | Excellent | Add `<output>` tags, optimize temperature |
| **Error Recovery** | None | Checkpoint-resume | Add serialization |
| **Observability** | Basic logging | Structured telemetry | JSONL export |
| **Security** | Partial (planning gate only) | Complete | Add execution write gate, command sanitization |

---

## Validation Checklist for 100% Production Ready

### Reliability ✓
- [ ] Zero crashes in normal operation
- [ ] Graceful error handling in all phases
- [ ] Checkpoint-resume working
- [ ] Loop detection prevents degenerate behavior
- [ ] Timeouts prevent infinite hangs

### Performance ✓
- [ ] Token usage < 500K per task (95th percentile)
- [ ] Task completion < 10 minutes (median)
- [ ] Prompt redundancy eliminated
- [ ] Temperature optimized per phase

### Security ✓
- [ ] Planning write gate enforced
- [ ] Execution write gate enforced
- [ ] Command sanitization active
- [ ] No command injection possible
- [ ] No unauthorized file access

### Quality ✓
- [ ] All phases use GPT-OSS-120B optimized prompts
- [ ] `<thinking>` + `<output>` structure consistent
- [ ] Evidence citations required ([Evidence: file.py:line])
- [ ] Self-validation checklists in all prompts

### Testing ✓
- [ ] E2E test covers full PEV workflow
- [ ] Unit tests for all phase handlers
- [ ] Property-based tests for parsers
- [ ] Regression tests for all known bugs
- [ ] Test coverage > 80%

### Observability ✓
- [ ] Structured telemetry exported
- [ ] Token usage tracked per phase
- [ ] Round counts logged
- [ ] Success/failure rates measurable
- [ ] Performance metrics available

---

## Quick Start: Minimum Viable Production

**If you need production-ready ASAP, execute only these:**

1. **Sprint 1** (Critical Fixes) — 2-3 days
2. **Sprint 2** (Prompt Optimization) — Tasks 4, 5, 7 only — 2 days
3. **Sprint 4** (Production Hardening) — Tasks 12, 13, 16 only — 3 days

**Total: 7-8 days to 85/100 score**

Then iterate on remaining sprints for 100%.

---

## Success Metrics

**Week 1:** Critical bugs fixed, verification works reliably
**Week 2:** Token usage reduced by 60%, prompts optimized
**Week 3:** Production hardening complete (timeouts, budgets, telemetry)
**Week 4:** Full test coverage, all optimizations complete

**Final Target:** 100/100 production-ready score matching Claude Code performance.

---

## Task List Summary

All 22 tasks have been created and prioritized. View with `/tasks` command.

**P0 (Blocking):** 3 tasks — Must complete first
**P1 (High Priority):** 8 tasks — Core improvements
**P2 (Medium Priority):** 9 tasks — Production hardening
**P3 (Low Priority):** 2 tasks — Optimizations

**Total estimated effort:** 3-4 weeks with 1-2 developers

---

## Next Steps

1. Review this roadmap with team
2. Prioritize based on immediate needs
3. Start with Sprint 1 (Critical Fixes)
4. Execute sprints in order
5. Validate against checklist
6. Deploy to production when 100% target achieved

**Questions?** All implementation details are in individual task descriptions.
