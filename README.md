# DOORS Next AI Agent

An MCP server that lets Bob (or any AI coding assistant) pull requirements from IBM DOORS Next Generation.

**This is NOT an official IBM product.** Built by Brett Scharmett and Bob for demo purposes.

---

## What It Does

Bob can connect to your DOORS Next server and:
- List all projects
- Browse modules within a project
- Pull requirements from any module
- Save requirements to JSON, CSV, or Markdown

All through natural conversation — no manual API calls needed.

---

## Setup (One Time)

### 1. Clone and Install

```bash
git clone https://github.com/brettscharm/doors-next-bob-integration.git
cd doors-next-bob-integration
pip install -r requirements.txt
```

### 2. Add MCP Server to Bob

Add this to your Bob/Claude Dev MCP settings (replace the path with your actual path):

```json
{
  "mcpServers": {
    "doors-next": {
      "command": "python3",
      "args": ["doors_mcp_server.py"],
      "cwd": "/absolute/path/to/doors-next-bob-integration"
    }
  }
}
```

To get the absolute path, run `pwd` in the project directory.

### 3. Restart VS Code

The MCP server activates after restart.

---

## Usage

Just tell Bob:

```
Connect to DNG
```

Bob will ask for your credentials (server URL, username, password), connect, and walk you through:

1. **Projects** — "There are 107 projects. Want me to list them?"
2. **Modules** — "What are the modules in [project name]?"
3. **Requirements** — "Get requirements from [module name]"
4. **Save** — "Want me to save these requirements?"

---

## Optional: .env File

If you'd rather not enter credentials every session, create a `.env` file:

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

With a `.env` file, Bob connects automatically without asking for credentials.

---

## Project Structure

```
doors-next-bob-integration/
├── CLAUDE.md              # Instructions for Bob (read automatically)
├── README.md              # This file
├── doors_client.py        # DNG API client (OSLC + Reportable REST)
├── doors_mcp_server.py    # MCP server (5 tools for Bob)
├── requirements.txt       # Python dependencies
├── .env.example           # Credential template
└── .env                   # Your credentials (DO NOT COMMIT)
```

---

## Troubleshooting

**Bob can't see the MCP server?**
- Check the absolute path in your MCP settings is correct
- Restart VS Code after adding the config

**Authentication fails?**
- URL must end with `/rm` (e.g., `https://your-server.com/rm`)
- Check username/password are correct

**No modules or requirements found?**
- Verify you have permission to access the project in DOORS Next
- Some projects may use a different module structure

---

## Support

- GitHub Issues: https://github.com/brettscharm/doors-next-bob-integration/issues
- Email: brett.scharmett@ibm.com
