# 🚪 DOORS Next AI Agent

> **An AI Agent for IBM DOORS Next Generation (DNG)**  
> Built by Bob & Brett Scharmett (brett.scharmett@ibm.com)

---

## ⚠️ Disclaimer

**This is NOT an official IBM product.**

This AI agent was created by Bob (AI coding assistant) and Brett Scharmett to demonstrate how to connect Bob to IBM DOORS Next Generation, a professional requirements management tool.

---

## 🎯 What This Agent Does

This AI agent enables Bob to:

✅ **Connect** to DOORS Next with your credentials  
✅ **List** all available projects  
✅ **Browse** modules and folders within projects  
✅ **Retrieve** requirements with full metadata  
✅ **Export** requirements to JSON, CSV, or Markdown  
✅ **Build** applications based on your requirements data  

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Access to a DOORS Next server
- Valid DOORS Next credentials
- Bob (Claude Dev) installed in VS Code

### Installation

```bash
# 1. Clone this repository
git clone https://github.com/brettscharm/doors-next-bob-integration
cd doors-next-bob-integration

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env with your DOORS credentials

# 4. Test connection
python3 -c "from doors_client import DOORSNextClient; c = DOORSNextClient.from_env(); print('✅ Connected!' if c.authenticate() else '❌ Failed')"
```

---

## 🤖 Using with Bob

### Configure Bob's MCP Server

1. Open VS Code Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P`)
2. Type "Bob: Open MCP Settings"
3. Add this configuration:

```json
{
  "mcpServers": {
    "doors-next": {
      "command": "python3",
      "args": [
        "/ABSOLUTE/PATH/TO/doors_mcp_server.py"
      ],
      "env": {
        "DOORS_URL": "https://your-doors-server.com/rm",
        "DOORS_USERNAME": "your_username",
        "DOORS_PASSWORD": "your_password"
      }
    }
  }
}
```

**⚠️ Important:** Replace `/ABSOLUTE/PATH/TO/` with the full path to this directory!

### Example Bob Conversation

```
You: Bob, use the doors-next MCP server to list all projects

Bob: [Shows numbered list of all DOORS Next projects]

You: Get modules from project 5

Bob: [Shows all modules in project 5]

You: Pull requirements from the first module and create an API spec

Bob: [Retrieves requirements and generates OpenAPI specification]
```

---

## 📚 Documentation

- **BOB_INTEGRATION.md** - Detailed Bob integration guide with example prompts
- **DEMO_WORKFLOW_PLAN.md** - Complete workflow documentation
- **FINDING_MODULES_GUIDE.md** - Guide for discovering modules in DOORS

---

## 🔒 Security

**Important Security Notes:**

1. ⚠️ **Never commit `.env`** - It contains your password
2. ✅ The `.env` file is already in `.gitignore`
3. ✅ Use environment variables - Don't hardcode credentials
4. ✅ Rotate passwords regularly
5. ✅ Use read-only accounts when possible

---

## 📁 Project Structure

```
doors-next-bob-integration/
├── README.md                    # This file
├── BOB_INTEGRATION.md           # Bob integration guide
├── DEMO_WORKFLOW_PLAN.md        # Workflow documentation
├── FINDING_MODULES_GUIDE.md     # Module discovery guide
├── requirements.txt             # Python dependencies
├── .env.example                 # Credential template
├── .env                         # Your credentials (DO NOT COMMIT)
├── .gitignore                   # Git ignore rules
├── doors_client.py              # DOORS API client library
└── doors_mcp_server.py          # MCP server for Bob
```

---

## 🆘 Support

For questions or issues:

- **Email:** brett.scharmett@ibm.com
- **GitHub Issues:** [Create an issue](https://github.com/brettscharm/doors-next-bob-integration/issues)

---

## 📄 License

This project is provided as-is for demonstration purposes.

**This is not an official IBM product and is not supported by IBM.**

---

## 🙏 Acknowledgments

Built with:
- **Bob** - AI coding assistant (Claude Dev)
- **Brett Scharmett** - IBM Engineer
- **IBM DOORS Next** - Requirements management platform

---

**Made with ❤️ to demonstrate AI-powered requirements management**

*Last updated: March 23, 2026*