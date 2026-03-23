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

### Installation Steps

```bash
# 1. Clone this repository
git clone <your-repo-url>
cd doors-next-bob-integration

# 2. Install dependencies
pip install -r requirements.txt
```

That's it! Now just ask Bob to connect to DOORS Next.

### Using with Bob

Simply ask Bob:

```
You: Bob, connect to DOORS Next and list all projects
```

Bob will:
1. Ask you for your DOORS Next credentials (URL, username, password)
2. Configure the MCP server automatically
3. Connect and show you all available projects

**Note:** Bob will configure the MCP server with your credentials. You'll need to restart VS Code after the first setup, then Bob can access DOORS Next anytime.

---

## 📚 Documentation

- **[BOB_INTEGRATION.md](BOB_INTEGRATION.md)** - **START HERE!** Complete guide with example conversations, prompts, and workflows for using Bob with DOORS Next
- **[DEMO_WORKFLOW_PLAN.md](DEMO_WORKFLOW_PLAN.md)** - Complete workflow documentation
- **[FINDING_MODULES_GUIDE.md](FINDING_MODULES_GUIDE.md)** - Guide for discovering modules in DOORS

---

## 🔒 Security Best Practices

1. ⚠️ **Never commit `.env`** - It contains your password
2. ✅ The `.env` file is already in `.gitignore`
3. ✅ Use environment variables - Don't hardcode credentials
4. ✅ Rotate passwords regularly
5. ✅ Use read-only accounts when possible

---

## 📁 Project Structure

```
doors-next-bob-integration/
├── README.md                    # This file - Quick start guide
├── BOB_INTEGRATION.md           # Detailed Bob usage guide with examples
├── DEMO_WORKFLOW_PLAN.md        # Workflow documentation
├── FINDING_MODULES_GUIDE.md     # Module discovery guide
├── requirements.txt             # Python dependencies
├── .env.example                 # Credential template (copy to .env)
├── .env                         # Your credentials (DO NOT COMMIT)
├── .gitignore                   # Git ignore rules
├── doors_client.py              # DOORS API client library
└── doors_mcp_server.py          # MCP server for Bob
```

---

## 🆘 Troubleshooting

### Connection Issues

**Problem:** Authentication fails

**Solution:** 
1. Verify your credentials in `.env`
2. Check that your `DOORS_URL` ends with `/rm`
3. Test connection: `python3 -c "from doors_client import DOORSNextClient; c = DOORSNextClient.from_env(); print(c.authenticate())"`

### Installation Issues

**Problem:** `pip install -r requirements.txt` fails

**Solution:**
```bash
# Upgrade pip first
pip install --upgrade pip

# Then try again
pip install -r requirements.txt
```

### MCP Server Issues

**Problem:** Bob can't see the doors-next MCP server

**Solution:**
1. Verify the absolute path in your MCP settings (use `pwd` to get current directory)
2. Restart VS Code after configuration changes
3. Check Bob's available servers: "Bob: Show MCP Servers"

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