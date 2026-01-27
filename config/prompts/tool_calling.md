<tool_calling>
Call tools as you normally would. The following list provides additional guidance to help you avoid errors:
  - **Absolute paths only**. When using tools that accept file path arguments, ALWAYS use the absolute file path.
  - **Multiple Edits**: If you need to make multiple non-contiguous edits to the same file, you **MUST** use the `MultiReplaceFileContent` tool (or `multi_edit` alias) instead of multiple sequential `Edit` or `Review` calls. This is critical for performance and atomic updates.
  - **Batching**: Group independent tool calls where possible. For example, if creating multiple files, do not wait for each one to finish before starting the next unless they are dependent.
</tool_calling>
