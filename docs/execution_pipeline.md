# Execution Pipeline

## Full Runtime Sequence

```
User Prompt (text string)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ ENTRY POINT                                             │
│ Module: src/hcode/main_cli.py                           │
│ CLI: run_task() or chat_mode()                          │
│ Desktop: main.rs → run_task IPC → daemon stdin          │
│ VSCode: hcodeBridge.runTask() → python -m hcode run     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ TASK CLASSIFICATION                                     │
│ Module: src/hcode/core/classification/task_classifier.py│
│                                                         │
│ Analyzes task complexity:                               │
│ → simple (single file, quick change) → FastHandler      │
│ → complex (multi-file, architecture) → PEV workflow     │
│ → ambiguous → default to PEV                            │
│                                                         │
│ Also checks for explicit mode:                          │
│ → /plan command → force PEV                             │
│ → /fast command → force FastHandler                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ AGENT INITIALIZATION                                    │
│ Module: src/hcode/core/agent.py — HcodeAgent            │
│                                                         │
│ 1. Initialize ResilientProvider (select Anthropic/OpenAI│
│ 2. Initialize ToolManager (register 36+ tools)          │
│ 3. Initialize MemoryManager (load context)              │
│ 4. Initialize ContextManager (SQLite session)           │
│ 5. Build system prompt (identity + tools + memory)      │
│ 6. Delegate to AgentOrchestrator                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ ORCHESTRATION                                           │
│ Module: src/hcode/core/orchestration/agent_orchestrator │
│                                                         │
│ Creates AgentContext:                                    │
│ {task, session_id, working_dir, iteration, token_budget}│
│                                                         │
│ Initializes AgentLoopController (PEV state machine)     │
│ Starts phase loop:                                      │
│                                                         │
│ while not loop_controller.should_stop():                │
│   phase = phase_manager.get_current_phase()             │
│   result = phase_manager.execute_current_phase(ctx)     │
│   if result.can_transition:                             │
│       phase_manager.transition_to_next_phase(ctx)       │
└────────────────────┬────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌────────┐    ┌──────────┐    ┌──────────────┐
│PLANNING│    │EXECUTION │    │VERIFICATION  │
└───┬────┘    └────┬─────┘    └──────┬───────┘
    │              │                  │
    ▼              ▼                  ▼
```

---

## Phase 1: PLANNING

**Module**: `src/hcode/core/phases/planning_handler.py` (772 lines)

```
PlanningPhaseHandler.handle(context, loop_controller)
│
├── Build system prompt
│   ├── Load core_prompts/core/phases.yaml
│   ├── Load pev_prompts/planning_mode.md
│   ├── Inject file memory + session context
│   └── Include tool documentation
│
├── Multi-round LLM loop
│   ├── Send to ResilientProvider.generate_completion()
│   ├── Parse response for tool calls (ToolCallParser)
│   │   Priority: <output> tags → JSON → regex
│   ├── Execute allowed tools only:
│   │   ✅ Read, Glob, Grep, Write (to .hcode/ only)
│   │   ❌ Edit, Bash, Git (blocked during planning)
│   ├── Feed results back as continuation
│   └── Repeat until artifacts created
│
├── Artifact validation
│   ├── task.md: Has headings? 50+ chars?
│   └── implementation_plan.md: Has steps/approach? 100+ chars?
│
└── Output: task.md + implementation_plan.md in .hcode/
```

---

## Phase 2: EXECUTION

**Module**: `src/hcode/core/phases/execution_handler.py` (1595 lines)

```
ExecutionPhaseHandler.handle(context, loop_controller)
│
├── Load artifacts
│   ├── Read .hcode/implementation_plan.md
│   └── Read .hcode/task.md
│
├── Build execution system prompt
│   ├── Load pev_prompts/execution_handler.md
│   ├── Embed plan + task content
│   └── Add tool format instructions
│
├── Multi-round execution loop (max 35 rounds)
│   │
│   │ For each round:
│   │
│   ├── a. LLM call via ResilientProvider (stream=False)
│   │
│   ├── b. Tool call extraction
│   │   ├── Try native API response (function_call field)
│   │   ├── Try <output> tag extraction
│   │   ├── Try text-based JSON extraction
│   │   └── Fall back to regex
│   │
│   ├── c. Tool execution
│   │   ├── ToolExecutor validates tool name (auto-correct)
│   │   ├── Normalize arguments (alias mapping)
│   │   ├── Execute with retry (max 2 for transient errors)
│   │   ├── Display result via HcodeDisplay
│   │   └── Record in loop controller
│   │
│   ├── d. Build continuation prompt
│   │   ├── Include tool results
│   │   ├── Detect current sub-phase (0/1/2/3)
│   │   │   Phase 0: Task Selection (pick unchecked item)
│   │   │   Phase 1: Implementation (read, edit, write)
│   │   │   Phase 2: Validation (re-read to verify)
│   │   │   Phase 3: Checkpoint (mark complete, next task)
│   │   └── Provide phase-specific guidance
│   │
│   └── e. Check stopping conditions
│       ├── AI signals "task complete"
│       ├── Max iterations (50) reached
│       ├── CircuitBreaker (3 consecutive errors)
│       └── LoopDetector (3 identical responses)
│
└── Output: Modified files tracked in context.modified_files
```

---

## Phase 3: VERIFICATION

**Module**: `src/hcode/core/phases/verification_handler.py` (1729 lines)

```
VerificationPhaseHandler.handle(context, loop_controller)
│
├── 1. Extract test commands from plan
│   ├── Parse ```bash / ```shell code blocks
│   ├── Parse bullet lines with $ prefix
│   ├── Parse "Run:" / "Execute:" / "Test:" directives
│   └── Deduplicate commands
│
├── 2. Execute tests
│   ├── Run each command via BashTool
│   ├── Capture stdout/stderr/exit_code
│   └── Record pass/fail per command
│
├── 3. AI verification analysis
│   ├── Build verification prompt
│   ├── Include: plan, task, test results, modified files
│   ├── LLM performs 5-phase QA:
│   │   Phase 1: Compliance — matches plan?
│   │   Phase 2: Functional — tests pass?
│   │   Phase 3: Quality — code style, edge cases
│   │   Phase 4: Regression — side effects?
│   │   Phase 5: Reporting — verdict
│   └── Extract overall verdict
│
├── 4. Generate walkthrough.md
│   ├── What was implemented
│   ├── Files modified
│   └── Test results
│
├── 5. Update task.md
│   └── Programmatic checkbox toggle (NOT via AI EditTool)
│
└── Output: walkthrough.md, updated task.md, verdict
```

---

## Module Responsibility Map

| Pipeline Step | Module | Method |
|:---|:---|:---|
| Entry (CLI) | `main_cli.py` | `run_task()`, `chat_mode()` |
| Entry (Desktop) | `main.rs` | `run_task` IPC command |
| Entry (VS Code) | `hcodeBridge.ts` | `runTask()` |
| Classification | `task_classifier.py` | `classify()` |
| Agent init | `agent.py` | `HcodeAgent.__init__()` |
| Orchestration | `agent_orchestrator.py` | `execute_task()` |
| State machine | `agent_loop.py` | `AgentLoopController` |
| Planning | `planning_handler.py` | `handle()` |
| Execution | `execution_handler.py` | `handle()` |
| Verification | `verification_handler.py` | `handle()` |
| Tool parsing | `tool_call_parser.py` | `extract_tool_calls()` |
| Tool dispatch | `tool_executor.py` | `execute_tool_calls()` |
| Tool registry | `tool_manager.py` | `execute_tool()` |
| LLM calls | `resilient_provider.py` | `generate_completion()` |
| Context | `context/manager.py` | `get_messages()` |
| Memory | `memory_manager.py` | `assemble_context()` |
| Artifacts | `artifact_manager.py` | `create_artifact()` |
