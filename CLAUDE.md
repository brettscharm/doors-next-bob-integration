# DOORS Next AI Agent

This MCP server connects you to IBM DOORS Next Generation (DNG).
All the heavy lifting is done by the MCP tools — you do NOT need to write any code.

## How to Use the MCP Tools

When the user says "connect to DNG" or wants to work with requirements:

### 1. Get Credentials and Connect
Ask the user for their DOORS Next **URL**, **username**, and **password**.
Then call the `connect_to_dng` tool with those values.

The tool will authenticate and return the project count. Tell the user:
> "Successfully connected! There are X projects. Do you want me to list them all, or do you know which one we're working with today?"

### 2. Show Modules
When the user picks a project, call `get_modules` with the project number or name.

### 3. Get Requirements
When the user picks a module, call `get_module_requirements` with the project and module.

### 4. Save
After showing requirements, ask if they want to save them.
If yes, call `save_requirements` with their preferred format (json, csv, or markdown).

## Tools Quick Reference

- `connect_to_dng(url, username, password)` — Connect to DNG
- `list_projects()` — List all projects
- `get_modules(project_identifier)` — Get modules (by number or name)
- `get_module_requirements(project_identifier, module_identifier)` — Get requirements
- `save_requirements(format, filename)` — Save to file (json/csv/markdown)

## Important

- Do NOT write Python code to interact with DNG. Use the MCP tools only.
- Projects and modules can be referenced by number (from listed output) or name (partial match works).
- If `.env` exists with credentials, the tools work without calling `connect_to_dng` first.
