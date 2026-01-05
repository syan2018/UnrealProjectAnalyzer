# Cursor Rules Instructions
To create or edit a rule:
1. Rules should be stored in the `.cursor/rules` directory
2. Rule files must have a `.mdc` extension (e.g., `my-rule.mdc`)
3. To reference a file in your rule, use the format: `[filename.ext](mdc:filename.ext)` where the path is relative to the workspace root
4. Rules use Markdown format with special Cursor-specific extensions
5. Rules will be shown to the AI to help with codebase navigation and understanding
6. Metadata is stored in frontmatter and controls how the rule is used and must be formatted properly.
Metadata properties are:
 - alwaysApply: true/false # Will apply to every request
 - description: string # A description that allows the agent to fetch the rule
 - globs: string # A comma separated list of gitignore style patterns controlling what files this rule will apply to
Usually only one of these types would be set, though it is valid to have globs and a description.

Example rule that is always applied concerning project structure:
```
---
alwaysApply: true
---
# Project Structure Guide The main entry point is
[index.js](mdc:index.js), which loads configuration from
[config.js](mdc:config.js)
```
    

Example rule that only applies to TypeScript and TypeScript React files:
```
---
globs: *.ts,*.tsx
---
Always use semicolons
```

Example rule that is manually applied by the user:
```
---
alwaysApply: false
---
Lots of information about a particular task
```


You must use these instructions to generate new rules or modify existing ones. Use the conversation history to understand the context of the rule(s) you should generate.