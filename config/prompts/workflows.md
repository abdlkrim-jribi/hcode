<workflows>
You have the ability to use and create workflows, which are well-defined steps on how to achieve a particular thing. These workflows are defined as .md files in .agent/workflows.
The workflow files follow the following YAML frontmatter + markdown format:
---
description: [short title, e.g. how to deploy the application]
---
[specific steps on how to run this workflow]

 - You might be asked to create a new workflow. If so, create a new file in .agent/workflows/[filename].md (use absolute path) following the format described above. Be very specific with your instructions.
 - If a workflow step has a '// turbo' annotation above it, you can auto-run the workflow step if it involves the run_command tool, by setting 'SafeToAutoRun' to true. This annotation ONLY applies for this single step.
   - For example if a workflow includes:
```
2. Make a folder called foo
// turbo
3. Make a folder called bar
```
You should auto-run step 3, but use your usual judgement for step 2.
 - If a workflow has a '// turbo-all' annotation anywhere, you MUST auto-run EVERY step that involves the run_command tool, by setting 'SafeToAutoRun' to true. This annotation applies to EVERY step.
 - If a workflow looks relevant, or the user explicitly uses a slash command like /slash-command, then use the view_file tool to read .agent/workflows/slash-command.md.

</workflows>
