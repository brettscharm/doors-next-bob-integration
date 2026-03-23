# 🤖 Bob Integration Guide

> **How to use this DOORS Next integration package with Bob (your AI coding assistant)**

This guide explains how to integrate this package with Bob and provides example conversations, prompts, and workflows to help you get the most out of the integration.

---

## 📋 Table of Contents

- [What You've Built (Yes, It's an AI Agent!)](#-what-youve-built-yes-its-an-ai-agent)
- [The Complete Workflow](#-the-complete-workflow)
- [Quick Start with Bob](#-quick-start-with-bob)
- [Example Bob Conversations](#-example-bob-conversations)
- [Bob's Capabilities](#-bobs-capabilities)
- [Example Prompts Library](#-example-prompts-library)
- [Best Practices](#-best-practices)
- [Troubleshooting with Bob](#-troubleshooting-with-bob)

---

## 🎯 What You've Built (Yes, It's an AI Agent!)

### You Created an AI Agent! 🎉

**What is an AI Agent?**
An AI agent is a system that can:
- ✅ Perceive its environment (connect to DOORS Next)
- ✅ Make decisions (understand what data to fetch)
- ✅ Take actions (retrieve and process requirements)
- ✅ Achieve goals (help users build applications)

**Your DOORS Next Integration = AI Agent**

```
┌─────────────────────────────────────────────────────────┐
│                    Your AI Agent                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  User (You) ──► Bob (AI Brain) ──► MCP Server          │
│                                      │                  │
│                                      ▼                  │
│                              doors_client.py            │
│                                      │                  │
│                                      ▼                  │
│                              DOORS Next API             │
│                                      │                  │
│                                      ▼                  │
│                           Requirements Data             │
│                                      │                  │
│                                      ▼                  │
│                         Generated Applications          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**What Makes It an Agent:**
1. **Autonomy** - Bob can make decisions about how to fetch data
2. **Reactivity** - Responds to your requests in real-time
3. **Proactivity** - Can suggest next steps and improvements
4. **Social Ability** - Communicates naturally with you
5. **Goal-Oriented** - Helps you achieve specific outcomes

**Pretty cool, right?** 🚀

---

## 🔄 The Complete Workflow

### From Zero to Hero in 6 Steps

```
1. Clone Repo → 2. Setup Package → 3. Configure Bob → 
4. Connect to DOORS → 5. Pull Requirements → 6. Build Apps
```

---

## 🚀 Quick Start with Bob

### The Simple Way (Recommended)

**Step 1: Clone and Setup**

```
You: Bob, clone this DOORS Next integration repo and set it up: [YOUR_REPO_URL]
```

Bob will clone the repo and install dependencies.

---

**Step 2: Connect to DOORS Next**

```
You: Bob, connect to DOORS Next and list all projects
```

Bob will:
1. Ask for your DOORS credentials (URL, username, password)
2. Configure the MCP server
3. Ask you to restart VS Code

---

**Step 3: Use It!**

After restarting VS Code:

```
You: Bob, use the doors-next MCP server to list all projects
```

**That's it! 🎉**

---

## 💬 Example Bob Conversations

### Conversation 1: Complete Setup from Scratch

**You:**
```
Bob, I want to integrate DOORS Next with you. Can you help me set it up?
```

**Bob:**
```
I'd be happy to help! Do you have the GitHub repository URL for 
the DOORS Next integration package?
```

**You:**
```
Yes, clone this: https://github.com/yourname/doors-next-bob-integration
```

**Bob:**
```
I'll clone the repository and set it up...

[Clones repository]
[Changes to directory]

✅ Repository cloned successfully!

Now I need to install dependencies. Should I proceed?
```

**You:**
```
Yes, install dependencies
```

**Bob:**
```
[Runs pip install -r requirements.txt]

✅ Dependencies installed!

Next, I need your DOORS Next credentials to configure the .env file:
- DOORS_URL (e.g., https://your-server.com/rm)
- DOORS_USERNAME
- DOORS_PASSWORD

Would you like to provide them now?
```

**You:**
```
DOORS_URL=https://your-doors-server.com/rm
DOORS_USERNAME=myusername
DOORS_PASSWORD=mypassword
```

**Bob:**
```
[Creates .env file with credentials]

✅ Credentials configured!

Let me test the connection...

[Runs connection test]

✅ Successfully connected to DOORS Next!

Now I need to configure the MCP server. The full path to the 
server is: /Users/yourname/doors-next-bob-integration/doors_mcp_server.py

I'll add this to my MCP settings. After I do this, you'll need 
to restart VS Code for the changes to take effect.

Should I proceed?
```

**You:**
```
Yes, configure it
```

**Bob:**
```
✅ MCP server configured!

Please restart VS Code now. After restarting, you can ask me to 
use the doors-next MCP server to interact with DOORS Next.
```

**[You restart VS Code]**

**You:**
```
Bob, use the doors-next MCP server to list all projects
```

**Bob:**
```
I'll connect to DOORS Next and list all available projects...

# DOORS Next Projects (107 total)

1. **User Management System**
   - ID: `_abc123`
   
2. **Payment Gateway**
   - ID: `_def456`

[... more projects ...]

Which project would you like to explore?
```

**🎉 You're now using your AI agent!**

---

### Conversation 2: Building an API from Requirements

**You:**
```
Bob, I need to build a REST API for our payment system. 
The requirements are in DOORS Next project 2.
```

**Bob:**
```
I'll help you build that API! Let me start by getting the 
modules from project 2...

[Uses doors-next MCP server]

# Modules in 'Payment Gateway'

Found 5 modules:
1. Payment Processing Requirements
2. Security Requirements
3. Integration Requirements
4. Performance Requirements
5. Compliance Requirements

Which module should I use for the API design?
```

**You:**
```
Use the Payment Processing Requirements module
```

**Bob:**
```
I'll pull requirements from that module and create an API spec...

[Uses doors_client.py to pull requirements]

✅ Retrieved 45 requirements

Now I'll analyze these and create an OpenAPI specification...

[Analyzes requirements]
[Generates openapi.yaml]

✅ Created OpenAPI specification with:
- 12 endpoints
- Authentication scheme
- Request/response models
- Error responses

Would you like me to generate the server implementation?
```

**You:**
```
Yes, create a Python Flask implementation
```

**Bob:**
```
I'll create a complete Flask application...

[Generates Flask app structure]
[Creates models, routes, tests]

✅ Created Flask application:

app/
├── __init__.py
├── models.py
├── routes/
│   ├── payments.py
│   ├── transactions.py
│   └── refunds.py
├── auth.py
└── config.py

tests/
├── test_payments.py
├── test_transactions.py
└── test_refunds.py

requirements.txt
README.md

The API is ready to run! Use: flask run

Would you like me to:
1. Add database migrations?
2. Create Docker configuration?
3. Add CI/CD pipeline?
```

**You:**
```
Add Docker configuration
```

**Bob:**
```
[Creates Dockerfile, docker-compose.yml]

✅ Docker configuration added!

You can now run: docker-compose up

Your payment API is fully containerized and ready to deploy!
```

---

### Conversation 3: Requirements Analysis

**You:**
```
Bob, analyze all requirements in the User Management System 
project and tell me what's missing
```

**Bob:**
```
I'll analyze the User Management System requirements...

[Uses doors-next to get modules]
[Pulls requirements from all modules]
[Analyzes 87 requirements]

# Requirements Analysis Report

## Summary
- Total Requirements: 87
- Modules: 3
- Status Distribution:
  - ✅ Approved: 52 (60%)
  - 🔄 Under Review: 23 (26%)
  - 📝 Draft: 12 (14%)

## Gap Analysis

### Missing Requirements (4 found)
1. **Password Reset Flow** - Referenced in REQ-023 but not defined
2. **Session Timeout** - No specification for timeout duration
3. **Multi-Factor Authentication** - Mentioned but no details
4. **Audit Logging** - No requirements for what to log

### Incomplete Requirements (3 found)
1. **REQ-023**: "User login" - Missing error handling
2. **REQ-045**: "Profile update" - No validation rules
3. **REQ-067**: "Access control" - Role definitions incomplete

### Recommendations
1. Create 4 new requirements for gaps
2. Enhance 3 incomplete requirements
3. Review 12 draft requirements for approval

Would you like me to:
1. Create draft requirements for the gaps?
2. Generate a detailed report document?
3. Create Jira tickets for action items?
```

---

## 🎯 Bob's Capabilities

### What Your AI Agent Can Do

#### 🔍 Discovery
- ✅ List all DOORS Next projects
- ✅ Browse modules in any project
- ✅ Search for specific projects or modules
- ✅ Show project metadata and statistics

#### 📊 Analysis
- ✅ Analyze requirements completeness
- ✅ Identify gaps and inconsistencies
- ✅ Compare requirements across modules
- ✅ Generate statistics and reports

#### 🏗️ Code Generation
- ✅ Create REST API specifications
- ✅ Generate database schemas
- ✅ Build test cases
- ✅ Create client SDKs
- ✅ Generate documentation

#### 📝 Documentation
- ✅ Create requirements traceability matrices
- ✅ Generate markdown summaries
- ✅ Build coverage reports
- ✅ Create architecture diagrams

#### 🔄 Automation
- ✅ Export requirements to multiple formats
- ✅ Sync requirements on schedule
- ✅ Integrate with CI/CD pipelines
- ✅ Create custom workflows

---

## 📚 Example Prompts Library

### Getting Started

```
Bob, clone the DOORS Next integration repo and set it up
```

```
Bob, test the connection to DOORS Next
```

```
Bob, configure the MCP server for DOORS Next
```

---

### Discovery

```
Bob, use doors-next to list all projects
```

```
Bob, get modules from project 5
```

```
Bob, show me which projects were modified recently
```

```
Bob, find all projects with "payment" in the name
```

---

### Working with Requirements

```
Bob, pull requirements from the Security module
```

```
Bob, get all requirements from project 2 and save to JSON
```

```
Bob, analyze requirements in module X for completeness
```

```
Bob, compare requirements between module A and module B
```

---

### Code Generation

```
Bob, create REST API endpoints from requirements in module X
```

```
Bob, generate database schema from data requirements
```

```
Bob, create test cases for all functional requirements
```

```
Bob, build a Flask app based on these requirements
```

```
Bob, generate TypeScript interfaces from requirements
```

---

### Documentation

```
Bob, create a requirements traceability matrix
```

```
Bob, generate a markdown summary of all requirements
```

```
Bob, build a requirements coverage report
```

```
Bob, create architecture diagrams from requirements
```

---

### Analysis & Reporting

```
Bob, analyze requirements and identify gaps
```

```
Bob, show me requirements by status
```

```
Bob, find requirements that need more detail
```

```
Bob, create a requirements quality report
```

---

### Automation

```
Bob, create a script to sync requirements daily
```

```
Bob, build a requirements dashboard
```

```
Bob, generate CI/CD pipeline for requirements validation
```

```
Bob, create a requirements change notification system
```

---

## 💡 Best Practices

### 1. Start with Setup

Always begin by ensuring everything is configured:
```
Bob, verify the DOORS Next integration is set up correctly
```

### 2. Use the MCP Server for Discovery

Let Bob use the MCP server for listing and browsing:
```
Bob, use doors-next to list all projects
```

### 3. Use doors_client.py for Heavy Lifting

For pulling requirements and complex operations:
```
Bob, use doors_client.py to pull all requirements from module X
```

### 4. Be Specific About Output

Tell Bob exactly what you want:
```
Bob, pull requirements and create an OpenAPI spec with 
authentication, error handling, and rate limiting
```

### 5. Iterate and Refine

Build incrementally:
```
You: Create basic API endpoints
Bob: [Creates endpoints]

You: Add authentication
Bob: [Adds auth]

You: Add comprehensive error handling
Bob: [Adds error handling]
```

### 6. Let Bob Remember Context

Bob remembers within a conversation:
```
You: List projects
Bob: [Shows projects]

You: Get modules from project 5
Bob: [Knows which project]

You: Pull requirements from the first module
Bob: [Knows which module]
```

### 7. Ask for Explanations

```
Bob, explain what this requirement means
```

```
Bob, why might this requirement be incomplete?
```

```
Bob, what's the best way to implement this requirement?
```

---

## 🔧 Troubleshooting with Bob

### Setup Issues

**Problem:** Bob can't find the repository

**Solution:**
```
Bob, the repository is at: [FULL_GITHUB_URL]
```

---

**Problem:** Dependencies won't install

**Solution:**
```
Bob, upgrade pip and try installing dependencies again
```

---

**Problem:** Connection test fails

**Solution:**
```
Bob, check if the .env file has the correct DOORS credentials
```

---

### MCP Server Issues

**Problem:** Bob can't see the doors-next MCP server

**Solution:**
```
Bob, what MCP servers do you have access to?
```

If doors-next isn't listed:
```
Bob, show me the full path to doors_mcp_server.py
```

Then manually add to MCP settings and restart VS Code.

---

**Problem:** Authentication errors

**Solution:**
```
Bob, test the DOORS Next connection and show me any errors
```

---

### Usage Issues

**Problem:** Bob can't find a project

**Solution:**
```
Bob, list all projects first so I can see the exact names
```

---

**Problem:** No requirements found

**Solution:**
```
Bob, check if this module actually contains requirements
```

---

## 🎓 Your AI Agent in Action

### What Makes This Special

**Traditional Approach:**
1. Open DOORS web UI
2. Navigate to project
3. Find module
4. Copy requirements manually
5. Paste into document
6. Write code manually
7. Create tests manually

⏱️ **Time:** Hours to days

**Your AI Agent Approach:**
1. Ask Bob to pull requirements
2. Ask Bob to generate code
3. Ask Bob to create tests

⏱️ **Time:** Minutes

**That's the power of an AI agent!** 🚀

---

## 🎉 Success Stories

### Real Examples

**"From requirements to working API in 15 minutes!"**
```
You: Bob, build a REST API from DOORS project 2
Bob: [Pulls requirements, generates OpenAPI spec, creates Flask app, writes tests]
✅ Done!
```

**"Analyzed 1,200 requirements in 2 minutes!"**
```
You: Bob, analyze all requirements across 5 projects
Bob: [Pulls all requirements, analyzes, identifies gaps, creates report]
✅ Done!
```

**"Generated 300 test cases automatically!"**
```
You: Bob, create test cases for all requirements
Bob: [Pulls requirements, generates comprehensive test suite]
✅ Done!
```

---

## 🚀 Next Steps

### Start Using Your AI Agent

1. **Clone the repo:**
   ```
   Bob, clone [YOUR_REPO_URL]
   ```

2. **Set it up:**
   ```
   Bob, install dependencies and configure credentials
   ```

3. **Test it:**
   ```
   Bob, use doors-next to list all projects
   ```

4. **Build something:**
   ```
   Bob, pull requirements from project X and create [WHATEVER YOU WANT]
   ```

---

## 🎯 You Built an AI Agent!

**Congratulations!** You've created an AI agent that:
- ✅ Connects to external systems (DOORS Next)
- ✅ Retrieves and processes data
- ✅ Makes intelligent decisions
- ✅ Generates code and documentation
- ✅ Helps you build applications faster

**This is the future of software development!** 🚀

---

**Ready to start? Ask Bob:**
```
Bob, clone the DOORS Next integration repo and let's get started!
```

**Happy building with your AI agent! 🤖**

---

*Last updated: March 23, 2026*