# Tool Capability Matrix

## Legend

| Score | Label | Meaning |
|:---|:---|:---|
| 5 | Reliable | Works correctly in all observed cases |
| 4 | Solid | Works in most cases, rare edge failures |
| 3 | Fragile | Works but has known failure modes |
| 2 | Unreliable | Fails frequently under normal use |
| 1 | Broken | Does not function as intended |

---

## File Tools

| Tool | Purpose | File | Reliability | Known Failure Modes | Fix Priority |
|:---|:---|:---|:---|:---|:---|
| **ReadTool** | Read file contents | `tools/files/file_tools.py` | 5 — Reliable | None significant | — |
| **WriteTool** | Create/overwrite file | `tools/files/file_tools.py` | 4 — Solid | Truncation detection false positives on short files | LOW |
| **EditTool** | String-match edit | `tools/files/file_tools.py` | 3 — Fragile | **~30-40% first-attempt failure**: LLM whitespace mismatch, indentation errors, encoding differences | **CRITICAL** |
| **MultiEditTool** | Multiple edits in one call | `tools/files/file_tools.py` | 3 — Fragile | Same as EditTool, amplified by multiple matches | HIGH |
| **FuzzyEditTool** | Approximate-match edit | `tools/files/fuzzy_edit_tool.py` | 3 — Fragile | Ambiguous matches when multiple similar blocks exist; threshold tuning sensitive | MEDIUM |
| **GrepTool** | Content search | `tools/files/file_tools.py` | 5 — Reliable | None | — |
| **SmartGlobTool** | File pattern search | `tools/files/smart_glob_tool.py` | 5 — Reliable | None | — |
| **ViewFileOutlineTool** | File structure outline | `tools/analysis/outline_tool.py` | 4 — Solid | Language parser coverage varies | LOW |

## Diff Tools

| Tool | Purpose | File | Reliability | Known Failure Modes | Fix Priority |
|:---|:---|:---|:---|:---|:---|
| **DiffPreviewTool** | Preview changes without applying | `tools/files/diff_tools.py` | 5 — Reliable | Preview only, no mutation risk | — |
| **ApplyChangeTool** | Apply a previewed change | `tools/files/diff_tools.py` | 4 — Solid | Depends on valid `proposal_id` | LOW |
| **RejectChangeTool** | Reject a previewed change | `tools/files/diff_tools.py` | 5 — Reliable | None | — |

## Terminal Tools

| Tool | Purpose | File | Reliability | Known Failure Modes | Fix Priority |
|:---|:---|:---|:---|:---|:---|
| **BashTool** | Execute shell commands | `tools/terminal/bash_tools.py` | 4 — Solid | Command sanitization may block legitimate commands; Windows translation edge cases | LOW |
| **BashOutputTool** | Read background shell output | `tools/terminal/bash_tools.py` | 4 — Solid | Buffer overflow on very long output | LOW |
| **KillShellTool** | Terminate background shell | `tools/terminal/bash_tools.py` | 5 — Reliable | None | — |
| **LSTool** | List directory | `tools/terminal/bash_tools.py` | 5 — Reliable | None | — |

## Git Tools

| Tool | Purpose | File | Reliability | Known Failure Modes | Fix Priority |
|:---|:---|:---|:---|:---|:---|
| **GitStatusTool** | Working tree status | `tools/git/git_tools.py` | 5 — Reliable | None | — |
| **GitDiffTool** | File diffs | `tools/git/git_tools.py` | 5 — Reliable | None | — |
| **GitAddTool** | Stage files | `tools/git/git_tools.py` | 5 — Reliable | None | — |
| **GitCommitTool** | Create commit | `tools/git/git_tools.py` | 5 — Reliable | None | — |
| **GitLogTool** | Commit history | `tools/git/git_tools.py` | 5 — Reliable | None | — |
| **GitCheckoutTool** | Switch branches | `tools/git/git_tools.py` | 4 — Solid | Risk of data loss if unsaved changes | LOW |
| **GitBranchTool** | Branch management | `tools/git/git_tools.py` | 5 — Reliable | None | — |

## Web Tools

| Tool | Purpose | File | Reliability | Known Failure Modes | Fix Priority |
|:---|:---|:---|:---|:---|:---|
| **WebFetchTool** | Fetch URL content | `tools/web/web_tools.py` | 3 — Fragile | Rate limiting, timeout, JS-heavy sites fail | LOW |
| **WebSearchTool** | Web search | `tools/web/web_tools.py` | 3 — Fragile | Requires API key, result quality varies | LOW |
| **WebScrapeTool** | Structured scraping | `tools/web/web_tools.py` | 3 — Fragile | CSS selector accuracy depends on site structure | LOW |

## Notebook Tools

| Tool | Purpose | File | Reliability | Known Failure Modes | Fix Priority |
|:---|:---|:---|:---|:---|:---|
| **NotebookReadTool** | Read Jupyter notebook | `tools/notebook/notebook_tools.py` | 4 — Solid | Depends on notebook format | LOW |
| **NotebookEditTool** | Edit notebook cells | `tools/notebook/notebook_tools.py` | 3 — Fragile | Cell index management | LOW |
| **NotebookExecuteTool** | Execute cells | `tools/notebook/interactive_tools.py` | 2 — Unreliable | Requires Jupyter kernel | LOW |

## System/Agent Tools

| Tool | Purpose | File | Reliability | Known Failure Modes | Fix Priority |
|:---|:---|:---|:---|:---|:---|
| **TodoReadTool** | Read task checklist | `tools/todo/todo_read.py` | 5 — Reliable | None | — |
| **TodoWriteTool** | Update tasks | `tools/todo/todo_write.py` | 5 — Reliable | None | — |
| **TaskBoundaryTool** | Signal task boundaries | `tools/system/hcode_tools.py` | 5 — Reliable | None | — |
| **AskUserQuestionTool** | Ask user | (interactive) | 5 — Reliable | None | — |

---

## Critical Path Summary

The **EditTool** is the single highest-impact tool to fix. It is:
- Used in every execution phase
- The most common source of agent retry loops
- The primary reason the CircuitBreaker trips
- The tool most affected by LLM output inconsistency

**Recommended fix**: Replace string-match with line-range addressing (`{file, start_line, end_line, new_content}`).
