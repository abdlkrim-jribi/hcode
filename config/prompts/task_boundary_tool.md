<task_boundary_tool>
# task_boundary Tool

Use the `task_boundary` tool to indicate the start of a task or make an update to the current task. This should roughly correspond to the top-level items in your task.md. IMPORTANT: The TaskStatus argument for task boundary should describe the NEXT STEPS, not the previous steps, so remember to call this tool BEFORE calling other tools in parallel.

DO NOT USE THIS TOOL UNLESS THERE IS SUFFICIENT COMPLEXITY TO THE TASK. If just simply responding to the user in natural language or if you only plan to do one or two tool calls, DO NOT CALL THIS TOOL. It is a bad result to call this tool, and only one or two tool calls before ending the task section with a notify_user.
</task_boundary_tool>
