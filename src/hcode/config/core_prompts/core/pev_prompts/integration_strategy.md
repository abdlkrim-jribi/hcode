# Integration Strategy: Full PEV Handler Coordination

> This document describes how ALL four handlers (init, planning, execution,
> verification) coordinate within the PEV workflow, including state management,
> error recovery, prompt architecture, and performance considerations.

---

## 1. Handler Coordination Overview

### 1.1 Execution Order

```
User runs /init
    └─→ InitHandler.analyze()
         ├─ _programmatic_explore()     ← Python-side codebase scan (no AI)
         ├─ _load_init_prompt()         ← loads init_analysis_prompt.md
         ├─ _get_init_system_prompt()   ← identity + tool_format + phase rules
         └─ _generate_and_execute()     ← multi-round AI loop (24 rounds max)
              └─→ Writes .hcode/hcode.md

User submits a task
    └─→ PlanningPhaseHandler.handle()
         ├─ Clean slate: delete stale artifacts
         ├─ _reset_trackers()           ← UncertaintyTracker, ConfidenceTracker, ResearchSaturationDetector
         ├─ _explore_codebase()         ← file-path inventory (no AI)
         ├─ _build_unified_planning_prompt()
         ├─ _get_planning_system_prompt()  ← identity + tool_format + phases.yaml + hcode.md
         └─ _run_planning_loop()        ← multi-round AI loop (8 rounds max)
              ├─→ Writes .hcode/task.md
              └─→ Writes .hcode/implementation_plan.md

Planning complete → transition to execution
    └─→ ExecutionPhaseHandler.handle()
         ├─ Load implementation_plan.md + task.md
         ├─ _get_next_incomplete_step()  ← find next unchecked task
         ├─ _build_execution_prompt()    ← 4-phase protocol prompt
         ├─ _get_execution_system_prompt() ← identity + tool_format + execution_handler.md
         └─ _generate_and_execute()      ← multi-round AI loop (12 rounds max)
              ├─ Phase 0: Task Selection (parse task.md)
              ├─ Phase 1: Pre-Implementation Analysis (read target files)
              ├─ Phase 2: Code Generation (3-pass: skeleton → logic → polish)
              ├─ Phase 3: Self-Validation (re-read, trace, cross-check)
              └─→ Updates task.md checkboxes, modifies code files

Execution complete → transition to verification
    └─→ VerificationPhaseHandler.handle()
         ├─ _run_tests()                 ← scope-aware test execution
         ├─ _run_verification_analysis() ← AI-driven 5-phase QA (6 rounds max)
         │    ├─ Phase 1: Compliance Verification (plan vs actual)
         │    ├─ Phase 2: Quality Gates (6 metrics scored)
         │    ├─ Phase 3: Integration Testing (mental execution traces)
         │    └─ Phase 4: Final Decision (APPROVED/NEEDS REVISION)
         ├─ _create_walkthrough()        ← structured verification evidence
         ├─ _update_task_status()        ← Phase 5: MANDATORY task.md update
         └─→ Writes .hcode/walkthrough.md
```

### 1.2 Data Flow Between Handlers

```
InitHandler                    PlanningHandler
    │                              │
    │  writes .hcode/hcode.md      │
    │──────────────────────────────▶│  reads .hcode/hcode.md into system prompt
    │                              │  (PROJECT KNOWLEDGE section)
    │                              │
    │  writes file inventory       │
    │  (embedded in prompt)        │  _explore_codebase() generates fresh inventory
    │                              │  (FILE INDEX section in unified prompt)
    │                              │
    └──────────────────────────────┘

PlanningHandler                ExecutionHandler
    │                              │
    │  writes task.md              │
    │──────────────────────────────▶│  reads task.md for Phase 0 (task selection)
    │                              │  parses checkboxes, finds next `- [ ]`
    │                              │
    │  writes implementation_plan  │
    │──────────────────────────────▶│  reads plan into execution prompt
    │                              │  parses steps for progress tracking
    │                              │
    └──────────────────────────────┘

ExecutionHandler               VerificationHandler
    │                              │
    │  modifies code files         │
    │──────────────────────────────▶│  reads modified files for compliance check
    │  (tracked in context)        │  runs tests on modified files
    │                              │
    │  updates task.md             │
    │──────────────────────────────▶│  reads task.md for Phase 5 status update
    │  checkboxes [x]/[/]         │  overwrites with verified true status
    │                              │
    └──────────────────────────────┘
```

**Coupling points (filesystem-only):**
- `hcode.md`: init → planning (project knowledge)
- `task.md`: planning → execution → verification (task tracking)
- `implementation_plan.md`: planning → execution → verification (plan compliance)
- `walkthrough.md`: verification → user (verification evidence)
- `context.modified_files`: execution → verification (in-memory, via AgentContext)

### 1.3 Independence Principle

All handlers are **loosely coupled** by design:

- `InitHandler` has NO dependency on any other handler
- `PlanningPhaseHandler` reads only `hcode.md` from init
- `ExecutionPhaseHandler` reads only `task.md` + `implementation_plan.md` from planning
- `VerificationPhaseHandler` reads all artifacts + `context.modified_files` from execution
- Each handler can be tested independently with mock artifacts

---

## 2. State Management

### 2.1 InitHandler State

| State | Location | Lifecycle |
|-------|----------|-----------|
| Codebase snapshot | In-memory (from `_programmatic_explore`) | Per-run, not persisted |
| Synthesis buffer | In-memory list | Per-run, used for fallback extraction |
| Message history | In-memory list of `Message` objects | Per-run, grows with each AI round |
| hcode.md | `.hcode/hcode.md` on filesystem | Persisted until next /init or manual delete |

**State transitions:**
```
START → _programmatic_explore() → snapshot ready
      → Round 1-12: DEEP_READING (tool calls + reads)
      → Round 13-20: SYNTHESIS (text buffers captured)
      → Round 21+: GENERATION (Write tool expected)
      → END: hcode.md exists OR fallback extraction
```

### 2.2 PlanningHandler State

| State | Location | Lifecycle |
|-------|----------|-----------|
| UncertaintyTracker | `self.uncertainty_tracker` | Per-task, reset at start of `handle()` |
| ConfidenceTracker | `self.confidence_tracker` | Per-task, reset at start of `handle()` |
| ResearchSaturationDetector | `self.saturation_detector` | Per-task, reset at start of `handle()` |
| File index | In-memory (from `_explore_codebase`) | Per-task, not persisted |
| Message history | In-memory list | Per-task, grows with each AI round |
| task.md | `.hcode/task.md` | Persisted, deleted at start of each new plan |
| implementation_plan.md | `.hcode/implementation_plan.md` | Persisted, deleted at start of each new plan |

**State transitions:**
```
START → Clean slate (delete stale artifacts)
      → Reset trackers
      → _explore_codebase() → file index ready
      → Phase detection cycle:
          discovery → exploration → consolidation → design → specification
      → END: both artifacts exist and pass validation
```

### 2.3 ExecutionHandler State

| State | Location | Lifecycle |
|-------|----------|-----------|
| Plan content | In-memory (from artifact_manager) | Per-handle(), loaded fresh |
| Task content | In-memory (from artifact_manager) | Per-handle(), loaded fresh |
| Next step | In-memory (from `_get_next_incomplete_step`) | Per-handle(), computed |
| Message history | In-memory list | Per-handle(), grows with each AI round |
| Modified files | `context.modified_files` list | Per-task, persists across phases |
| Completed actions | `context.completed_actions` list | Per-task, persists across phases |

**State transitions:**
```
START → Load plan + task artifacts
      → Find next incomplete step (_get_next_incomplete_step)
      → AI loop (12 rounds max):
          Phase 0: Task selection (read task.md)
          Phase 1: Pre-analysis (read target files)
          Phase 2: Code generation (write/edit tools)
          Phase 3: Self-validation (re-read, verify)
      → _update_task_progress() (file-based checkbox matching)
      → END: _check_execution_complete() (non-artifact files modified)
```

### 2.4 VerificationHandler State

| State | Location | Lifecycle |
|-------|----------|-----------|
| Test results | In-memory dict | Per-handle(), from _run_tests() |
| Verification analysis | In-memory string | Per-handle(), from AI analysis |
| Non-artifact files | In-memory list | Per-handle(), computed |
| walkthrough.md | `.hcode/walkthrough.md` on filesystem | Persisted |

**State transitions:**
```
START → _run_tests() (scope-aware: compile check or full suite)
      → _run_verification_analysis() (AI 5-phase QA, 6 rounds max):
          Phase 1: Compliance verification
          Phase 2: Quality gates (6 metrics)
          Phase 3: Integration testing (mental execution)
          Phase 4: Final decision
      → _create_walkthrough() (structured evidence document)
      → _update_task_status() (Phase 5: mandatory task.md update)
      → END: walkthrough.md exists
```

### 2.5 Meta-Cognitive Tracker Details

**UncertaintyTracker:**
- Tracks unknowns at three severity levels: critical, important, minor
- Critical uncertainties BLOCK artifact writing
- Updated by `_build_continuation_prompt()` based on AI responses
- Queried by `_can_write_artifacts()` as a validation gate

**ConfidenceTracker:**
- Tracks confidence (1-5) across 6 dimensions: requirements, architecture, dependencies, edge_cases, testing, patterns
- Requirements ≥ 4 and Architecture ≥ 3 required to proceed
- Updated via `_process_reflection_response()` parsing `dimension: X/5` patterns
- Queried by `_can_write_artifacts()` and `_build_continuation_prompt()`

**ResearchSaturationDetector:**
- Tracks files read per round, insights gained, uncertainty trend, confidence trajectory
- Detects diminishing returns from further research
- Saturation = high confidence (≥ 4.0) sustained for 3 rounds, OR low insights for 2 rounds + high confidence
- Prevents over-research while ensuring sufficient exploration

---

## 3. Error Recovery and Retry Logic

### 3.1 InitHandler Error Recovery

| Failure Mode | Detection | Recovery |
|-------------|-----------|----------|
| AI outputs text instead of tool calls (Phase 1) | No tool calls extracted, round < 12 | Protocol violation message → retry round |
| AI outputs text instead of Write tool (Phase 3) | No tool calls, round ≥ 20 | Generation error message → retry round |
| Write tool not called but markdown present | `_looks_like_markdown_content()` returns True | `_extract_hcode_from_text()` fallback |
| AI exhausts all 24 rounds without hcode.md | `hcode_path.exists()` returns False after loop | Final demand message → one more AI call |
| Final demand also fails | Still no hcode.md | Extract from synthesis buffer or last response |
| Provider call fails | Exception in `generate_completion` | Log error, break loop, return InitResult(success=False) |

**Fallback extraction priority:**
1. JSON Write tool call parsed from response (brace-balanced)
2. Regex extraction of malformed JSON tool call
3. Content inside markdown code block
4. Raw markdown with title + ≥2 ## headers
5. Synthesis buffer (accumulated from Phase 2 rounds)

### 3.2 PlanningHandler Error Recovery

| Failure Mode | Detection | Recovery |
|-------------|-----------|----------|
| Write to non-artifact path | `_execute_tools()` gate check | Block write, return error to AI, continue loop |
| AI stops after task.md only | `_is_planning_complete()` returns False | `_build_specification_prompt()` demands implementation_plan.md |
| task.md fails quality check | `_validate_task_quality()` finds issues | Quality failure prompt with specific issues → retry |
| AI exhausts all 8 rounds | Loop ends, artifacts checked | Return PhaseResult(success=False) with diagnostic |
| Provider call fails | Exception in `generate_completion` | Log error, break loop |
| Both artifacts missing | Post-loop check | Return failure — no template fallbacks (agent must produce) |

**Key design decision:** The planning handler has NO template fallbacks. If the AI fails to produce artifacts, the phase fails. This is intentional — fallback templates produced low-quality plans that caused execution failures.

### 3.3 ExecutionHandler Error Recovery

| Failure Mode | Detection | Recovery |
|-------------|-----------|----------|
| AI doesn't read before writing | No Read calls in first 2 rounds | Continuation prompt demands reads first |
| AI doesn't update task.md | No task.md edits after code changes | Continuation prompt demands task.md update |
| AI exhausts all 12 rounds | Loop ends | Return PhaseResult with partial results |
| Provider call fails | Exception in `generate_completion` | Log error, break loop |
| No non-artifact files modified | `_check_execution_complete()` False | `can_transition` = False, stays in execution |

**Key design decision:** Execution uses phase-aware continuation prompts to steer the AI through the 4-phase protocol. Early rounds push for reading, middle rounds allow writing, late rounds demand validation and task.md updates.

### 3.4 VerificationHandler Error Recovery

| Failure Mode | Detection | Recovery |
|-------------|-----------|----------|
| Test command fails | Non-zero exit code | Log failure, continue with other tests |
| Test command times out | `asyncio.TimeoutError` after 120s | Kill process, report timeout |
| AI verification analysis fails | Exception in `_run_verification_analysis` | Log error, use empty analysis string |
| No tests to run | No Python files, no test framework | Report "no automated checks", still create walkthrough |
| task.md update fails | artifact_manager error | Log warning, still return result |

**Key design decision:** Verification ALWAYS produces a walkthrough.md, even if individual phases partially fail. The test runner and AI analysis are independent — a test failure doesn't prevent AI analysis, and AI failure doesn't prevent test results from being documented.

### 3.5 Retry Strategy Comparison

| Aspect | InitHandler | PlanningHandler | ExecutionHandler | VerificationHandler |
|--------|------------|-----------------|-----------------|---------------------|
| Max rounds | 24 | 8 | 12 | 6 (AI analysis) |
| Fallback on failure | YES | NO (fail fast) | Partial results | Always produces walkthrough |
| Phase violation | Retry prompt | Block writes | Steering prompts | N/A |
| Quality validation | hcode.md exists | Multi-criteria | Non-artifact modified | walkthrough.md exists |
| Extra chance | YES (final demand) | NO | NO | NO |

**Rationale:**
- Init: runs once, must succeed → aggressive fallbacks
- Planning: per-task, fail-fast → no templates
- Execution: per-task, may need many rounds → generous round budget with steering
- Verification: terminal phase → always produce evidence even if partial

---

## 4. Prompt Architecture

### 4.1 InitHandler Prompt Stack

```
System Prompt = identity.md + tool_format.md + init-specific phase rules
User Prompt   = init_analysis_prompt.md (with {{CODEBASE_SNAPSHOT}} replaced)
Continuations = Phase-aware reminders (_get_phase_message)
```

### 4.2 PlanningHandler Prompt Stack

```
System Prompt = identity.md + tool_format.md + phases.yaml[planning]
              + task.md guidance + implementation_plan.md guidance
              + hcode.md content (PROJECT KNOWLEDGE)
              + working dir + PEV position + tool examples
              + artifact detail requirements
              + worked example (Read → Write task.md → Write plan flow)

User Prompt   = _build_unified_planning_prompt():
              = role framing
              + USER REQUEST (context.task)
              + FILE INDEX (_explore_codebase output)
              + STEP 1: THINK (reasoning framework)
              + STEP 2: READ (tool instructions)
              + STEP 3: SYNTHESIZE (code-level decisions)
              + STEP 4: WRITE task.md (template + rules)
              + STEP 5: WRITE implementation_plan.md (template + rules)
              + SCOPE RULES (hard write boundaries)

Continuations = Phase-specific prompts from _build_continuation_prompt():
              - discovery_prompt (Rounds 1-2)
              - exploration_prompt (Rounds 2-3)
              - consolidation_prompt (Rounds 3-4)
              - design_prompt (Rounds 4-5)
              - specification_prompt (Rounds 5+)
              - reflection_prompt (injected at rounds 2 and 4)
```

### 4.3 ExecutionHandler Prompt Stack

```
System Prompt = identity.md + tool_format.md + execution_handler.md
              + current task.md content (for Phase 0 context)
              + tool call format examples
              + working dir + iteration + modified files count

User Prompt   = _build_execution_prompt():
              = 4-phase protocol instructions
              + implementation_plan.md content
              + task.md content
              + session state (iteration, modified files, recent actions)
              + step-specific context (next incomplete step)

Continuations = Phase-aware prompts from _build_continuation_prompt():
              - Round 0-1: Demand file reads (Phase 0 + 1)
              - Round 2-6: Allow code changes (Phase 2), push for task.md update
              - Round 7+: Demand self-validation (Phase 3) and summary
              - After task.md edit: Check for remaining tasks, restart Phase 0
```

### 4.4 VerificationHandler Prompt Stack

```
System Prompt = identity.md + tool_format.md + verification_handler.md
              + tool call format examples
              + working dir + file counts

User Prompt   = _build_verification_prompt():
              = 5-phase QA protocol instructions
              + task.md content (what should have been done)
              + implementation_plan.md content (how it should have been done)
              + modified files list (what was actually changed)
              + test results (already executed)

Continuations = Phase-aware prompts from _build_continuation_prompt():
              - Round 0: Demand file reads (no verification from memory)
              - Round 1-2: Continue analysis (Phases 1-3)
              - Round 3+: Demand final verdict (Phase 4)
```

### 4.5 Prompt Design Principles for GPT OSS 120B

1. **Explicit role framing** at the start of every prompt
2. **Constraint-first** — state what NOT to do before what TO do
3. **XML tags** for reasoning (`<thinking>`) vs output (`<output>`)
4. **Numbered steps** — never free-form instructions
5. **Self-validation checkpoints** — explicit checklists before moving on
6. **Evidence requirements** — `[Evidence: file.py:line_num]` citations
7. **Few-shot examples** — one complete worked example in each major prompt
8. **Linear reasoning** — avoid nested logic, use "Therefore..." transitions

---

## 5. Performance Considerations

### 5.1 Token Budget

| Component | Estimated Tokens | Notes |
|-----------|-----------------|-------|
| System prompt (init) | ~2,000 | identity + tool_format + phase rules |
| Codebase snapshot (init) | 3,000–15,000 | Scales with project size |
| Init analysis prompt | ~2,500 | Template + quality gate |
| System prompt (planning) | 5,000–20,000 | Includes hcode.md content |
| File index (planning) | 1,000–5,000 | Scales with project size |
| Unified planning prompt | ~3,000 | Fixed template + task text |
| Continuation prompts | ~500–1,500 | Per round |

### 5.2 Round Budget

| Phase | Expected Rounds | Token Cost per Round | Total Budget |
|-------|----------------|---------------------|-------------|
| Init (Deep Reading) | 8-12 | ~4,000 output | ~48,000 |
| Init (Synthesis) | 4-6 | ~2,000 output | ~12,000 |
| Init (Generation) | 1-3 | ~8,000 output | ~16,000 |
| Planning (Discovery) | 1-2 | ~2,000 output | ~4,000 |
| Planning (Exploration) | 2-3 | ~3,000 output | ~9,000 |
| Planning (Design) | 1-2 | ~2,000 output | ~4,000 |
| Planning (Specification) | 2-3 | ~4,000 output | ~12,000 |
| Execution (Phase 0-1) | 1-3 | ~3,000 output | ~9,000 |
| Execution (Phase 2) | 3-6 | ~4,000 output | ~24,000 |
| Execution (Phase 3) | 1-2 | ~2,000 output | ~4,000 |
| Verification (Tests) | 0 | N/A (Python-side) | 0 |
| Verification (AI Analysis) | 3-6 | ~4,000 output | ~24,000 |

### 5.3 Optimization Strategies

1. **Programmatic pre-exploration:** Both handlers run Python-side file scanning before the AI loop. This prevents the AI from wasting rounds on `LS` and `Glob` calls to discover basic structure.

2. **Inject project knowledge:** The planning handler embeds `hcode.md` directly in the system prompt. This eliminates 3-5 rounds of re-discovery per planning session.

3. **Phase-aware continuations:** Continuation prompts are tailored to the current cognitive phase. This prevents the AI from repeating work or getting stuck in loops.

4. **Max token allocation:** Planning uses `max_tokens=16384` to allow deep reasoning in a single response. Init also uses 16384. This is important for 120B models that benefit from extended reasoning chains.

5. **Saturation detection:** The ResearchSaturationDetector prevents the AI from over-reading when sufficient understanding has been achieved, saving 2-3 rounds on average.

6. **Scope-aware test execution:** Verification handler uses narrow scope (compile + run) for 1-2 modified files, full test suite only for 3+ files. Prevents unrelated test failures from blocking verification.

7. **Execution protocol loading:** ExecutionHandler loads `execution_handler.md` from the config directory. Falls back to an inline condensed protocol if the file is missing, ensuring robustness.

8. **Generous execution rounds:** Execution uses 12 rounds (vs 8 for planning) because code generation requires more back-and-forth: read → write → verify → update task.md → next task.

---

## 6. Testing Strategy

### 6.1 Unit Tests

- `tests/unit/test_refactored_components.py` — Tests core SOLID components
- `tests/unit/test_core_prompt_loader.py` — Tests prompt loading from YAML/MD files

### 6.2 Integration Tests

- `tests/integration/test_pev_deep_scenario.py` — End-to-end PEV workflow test

### 6.3 Manual Verification

To verify handler integration:

```bash
# Run init handler
cd /project && hcode /init

# Verify hcode.md was created
cat .hcode/hcode.md | head -50

# Run a planning task
hcode "add logging to main.py"

# Verify planning artifacts
cat .hcode/task.md
cat .hcode/implementation_plan.md

# Check that implementation_plan.md references real files from hcode.md
grep -c "Evidence:" .hcode/implementation_plan.md
```

---

## 7. Known Limitations and Future Work

### Current Limitations

1. **No persistent conversation memory between /init runs and planning sessions.** The only state transfer is via hcode.md on disk. If the user modifies the codebase significantly between /init and planning, the project knowledge may be stale.

2. **Meta-cognitive trackers are not used by the AI directly.** The UncertaintyTracker, ConfidenceTracker, and ResearchSaturationDetector are Python-side constructs. The AI cannot update them explicitly — updates are inferred from the AI's responses by the handler code.

3. **No incremental hcode.md updates.** Each /init run replaces hcode.md entirely. There is no mechanism to update only changed sections.

4. **Execution handler has no write gate.** Unlike planning (which blocks writes to non-artifact paths), execution allows writes to any path. This is intentional (execution MUST create files), but means the AI could write files not in the plan.

5. **Verification AI analysis is advisory.** The AI's 5-phase QA analysis is included in walkthrough.md but does not programmatically gate the verdict. The programmatic verdict is based solely on test exit codes.

6. **task.md file-matching heuristic is brittle.** Both execution and verification use filename substring matching to associate modified files with task.md checkboxes. Tasks that don't mention filenames won't get auto-checked.

### Future Improvements

1. **Stale knowledge detection:** Compare hcode.md timestamp against recent git commits. Warn the user if project knowledge is outdated.

2. **Explicit tracker integration:** Allow the AI to output structured metadata (e.g., `<uncertainty>...</uncertainty>` tags) that the handler parses to update trackers directly.

3. **Incremental init:** Diff-based hcode.md updates that only re-analyze changed files.

4. **Cross-phase memory:** Allow execution and verification phases to read planning rationale, enabling better error recovery when the plan was based on incorrect assumptions.

5. **Execution write gate (soft):** Track which files the plan mentions and warn (but don't block) when the AI writes to unexpected paths.

6. **Programmatic quality gates:** Parse the AI's verification analysis to extract quality gate scores and use them in the final verdict alongside test results.

7. **Multi-task execution loop:** Currently execution handles one task per `handle()` call. A future improvement could loop through all tasks within a single `handle()` call, reducing overhead.
