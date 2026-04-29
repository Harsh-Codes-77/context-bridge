<div align="center">

```
 ██████╗ ██████╗ ███╗   ██╗████████╗███████╗██╗  ██╗████████╗      ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗
██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔════╝╚██╗██╔╝╚══██╔══╝     ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝
██║     ██║   ██║██╔██╗ ██║   ██║   █████╗   ╚███╔╝    ██║   █████╗██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗  
██║     ██║   ██║██║╚██╗██║   ██║   ██╔══╝   ██╔██╗    ██║   ╚════╝██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝  
╚██████╗╚██████╔╝██║ ╚████║   ██║   ███████╗██╔╝ ██╗   ██║         ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝   ╚═╝         ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝
```

**Your dev tools are scattered. Your focus shouldn't be.**

`context-bridge` links your GitHub PRs, Linear tickets, Slack threads, and CI logs - automatically - so you can stop hunting and start shipping.

<br/>

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-f97316?style=flat-square)](CONTRIBUTING.md)
[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-e11d48?style=flat-square)](https://github.com/Harsh-Codes-77/context-bridge)

<br/>

[🚀 Quick Start](#-quick-start) · [⚡ Commands](#-commands) · [🔌 Integrations](#-integrations) · [🖥️ Dashboard](#️-web-dashboard) · [🤝 Contributing](#-contributing)

</div>

---

## 😤 The Problem Every Developer Faces

You're deep in debugging `fix/auth-timeout`. Then you get pulled into another meeting, another branch, another fire.

When you come back - you open **10 tabs**, scroll through **Slack history**, check **GitHub PR comments**, hunt through **CI logs**, re-read the **Jira ticket**...

**That's 30 minutes wasted before you write a single line of code.**

Multiply that by every context switch. Every day. Every developer on your team.

---

## ✨ The Fix - One Command

```bash
cb status
```

```
╭─────────────────────────────────────────────────────────────╮
│  context-bridge  ·  fix/auth-timeout                        │
├─────────────────────────────────────────────────────────────┤
│  📋  AUTH-412  →  Login timeout after 30s  [In Progress]    │
│  🔁  PR #231   →  2 unresolved comments (Rahul asked smth)  │
│  ❌  CI Failed →  3rd time · Error: timeout on line 84      │
│  💬  Slack     →  Sarah: "might be AWS lambda cold start"   │
│                   #backend · 2 hours ago                    │
╰─────────────────────────────────────────────────────────────╯
  Context fetched in 1.2s  ·  http://localhost:4242
```

**One command. Every tool. Zero tab switching.**

---

## 🚀 Quick Start

```bash
git clone https://github.com/Harsh-Codes-77/context-bridge.git
cd context-bridge

# Windows:
install.bat

# macOS:
chmod +x install-mac.sh && ./install-mac.sh

# Linux:
chmod +x install-linux.sh && ./install-linux.sh

# Then:
cb init
cb status
cb web

# Optional diagnostics:
cb doctor
```

`cb init` saves tokens to `~/.context-bridge/.env`. **Note:** Only the GitHub token is required! Linear and Slack tokens are completely optional and can be freely skipped.
You can manage repos anytime with `cb repo` — no need to re-enter tokens.

---

## ⚡ Commands

### `cb status`
Fetches and displays your complete current context - branch, PR, ticket, CI, Slack - all at once.

```bash
cb status
```

**What it shows:**
- Current git branch
- Linked Linear/Jira ticket (auto-detected from branch name)
- GitHub PR status + unresolved comments
- Latest CI/CD run result (pass/fail + error location)
- Recent relevant Slack messages

**Options:**
- `--json`: Outputs a clean JSON object instead of rich terminal formatting. Perfect for scripting and piping into other tools (e.g., `cb status --json | jq '.github.ci_status'`). Missing tokens or API errors will gracefully output an `"error"` field within the JSON instead of breaking the execution.


---

### `cb resume`
Woke up? Came back from a meeting? This tells you exactly where you left off.

```bash
cb resume
```

```
╭─────────────────────────────────────────────────────────────╮
│  Resuming  ·  fix/auth-timeout                              │
├─────────────────────────────────────────────────────────────┤
│  ⏰  Last active: 6 hours ago                               │
│  📝  You were working on: auth.js (lines 78-92)             │
│                                                             │
│  What changed while you were away:                          │
│  • Rahul commented on PR #231                               │
│  • CI failed 2 more times                                   │
│  • Sarah replied in Slack thread                            │
│                                                             │
│  ▶  Suggested next step: Reply to Rahul's PR comment        │
╰─────────────────────────────────────────────────────────────╯
```

---

### `cb export`
Exports all your branch context (PR info, CI status, Linear ticket, Slack messages, and notes) into a clean Markdown file. Perfect for pasting into pull requests, standup updates, or Jira.

```bash
cb export
# ✓ Exported to context-bridge-export-fix-auth-timeout-2026-04-24.md
```

---

### `cb web`
Opens a local web dashboard with your full project context, beautiful UI, and live refresh.

```bash
cb web
# → Dashboard running at http://localhost:4242
```

---

### `cb init`
Interactive setup wizard. Run once to configure your API tokens.

```bash
cb init
```

Tokens are saved to `~/.context-bridge/.env`. **Linear and Slack tokens are completely optional**—if you only use GitHub, simply press Enter to skip them. You can optionally set a default repo during init,
or skip it and add repos later with `cb repo add`.

---

### `cb repo`
Manage multiple repos without re-entering tokens. Add, switch, list, or remove repos anytime.

#### `cb repo add <owner/repo>`
Add a new repo and set it as the active one.

```bash
cb repo add harsh/my-app
# ✓ Added and set 'harsh/my-app' as active repo

cb repo add harsh/other-project
# ✓ Added and set 'harsh/other-project' as active repo
```

#### `cb repo use <owner/repo>`
Switch the active repo to one you've already added.

```bash
cb repo use harsh/my-app
# ✓ Switched to 'harsh/my-app'
```

#### `cb repo list`
Show all saved repos. The active repo is highlighted in green.

```bash
cb repo list
```
```
                   Saved Repos
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Name          ┃ Full Name           ┃  Status  ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ my-app        │ harsh/my-app        │ Active ✓ │
│ other-project │ harsh/other-project │    -     │
└───────────────┴─────────────────────┴──────────┘
Total repos: 2
```

#### `cb repo current`
Print the currently active repo.

```bash
cb repo current
# Active repo: harsh/my-app
```

#### `cb repo remove <owner/repo>`
Remove a saved repo (asks for confirmation first).

```bash
cb repo remove harsh/other-project
# Remove harsh/other-project? [y/N]: y
# ✓ Removed 'harsh/other-project'
```

---

### `cb notes`
Leave yourself reminders or context tied directly to your active branch session so you never forget where you left off.

#### `cb notes add <text>`
Add a timestamped note to the current branch.
```bash
cb notes add "Need to review auth timeout tests before pushing"
# ✓ Note saved to fix/auth-timeout
```

#### `cb notes show`
Display all notes associated with your current branch.
```bash
cb notes show
```

#### `cb notes clear`
Clear all notes attached to your current branch.

*📝 Fun fact: Notes automatically appear at the bottom of your `cb status` output when they exist for your branch!*

---

### `cb doctor`
Check the health of your installation, local configuration, file paths, and environment settings.

```bash
cb doctor
```

Useful if you are migrating environments, debugging tokens, or just making sure your local setup is perfectly healthy!

---

## 🔌 Integrations

| Tool | What it fetches |
|------|-----------------|
| **GitHub** | Current PR, unresolved comments, CI/CD status, failed job logs |
| **Linear** | Ticket title, status, assignee, priority, recent comments |
| **Jira** | Issue details, status, sprint info *(coming soon)* |
| **Slack** | Messages mentioning your ticket ID or branch name |

### Setting Up Tokens

*(Note: Only the GitHub token is required! Linear and Slack tokens are completely optional, and their summaries will dynamically hide from the dashboard and CLI if not provided.)*

<details>
<summary>📍 GitHub Token</summary>

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Select scopes: `repo`, `workflow`
4. Copy the token → paste in `cb init`

</details>

<details>
<summary>📍 Linear Token</summary>

1. Open Linear → Settings → API
2. Click **"Create new API key"**
3. Copy the key → paste in `cb init`

</details>

<details>
<summary>📍 Slack Token</summary>

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create a new app → **"From scratch"**
3. Add OAuth scopes: `channels:read`, `channels:history`, `groups:read`, `groups:history`, `users:read`
4. Optional (for better search results): `search:read`
5. Install app to workspace
6. Copy **Bot User OAuth Token** (or a user token with search permissions) → paste in `cb init`

If `search.messages` is unavailable for your token type, context-bridge automatically falls back to channel history scanning.

</details>

---

## 🖥️ Web Dashboard

Run `cb web` to get a beautiful local dashboard at `http://localhost:4242`.

**Dashboard features:**
- 🌿 All your active branches as cards
- 📊 GitHub PR, CI status, Linear ticket, and Slack context per branch
- ⏱️ Last active timestamps plus cache age visibility
- 📂 Files you've touched per session
- 🔄 Auto-refresh (sessions every 30s, full context every 120s)
- 🔒 Localhost-only - completely private

---

## 🔒 Privacy First

Everything is **100% local**. Here's what we store and where:

```
~/.context-bridge/
├── data.db          ← SQLite: sessions, context cache, and saved repos
└── .env             ← Your API tokens (written by cb init)

your-project/
└── .env             ← Optional legacy fallback (still supported)
```

- ❌ No cloud sync
- ❌ No analytics
- ❌ No data sent anywhere
- ✅ Your tokens never leave your machine
- ✅ Works fully offline (with cached data)

---

## 📁 Project Structure

```
context-bridge/
│
├── cli/
│   ├── main.py          ← Entry point - all cb commands
│   ├── status.py        ← cb status logic
│   └── resume.py        ← cb resume logic
│
├── integrations/
│   ├── github.py        ← GitHub API integration
│   ├── linear.py        ← Linear API integration
│   └── slack.py         ← Slack API integration
│
├── storage/
│   └── db.py            ← Local SQLite database
│
├── dashboard/
│   ├── app.py           ← Flask local server
│   ├── templates/
│   │   └── index.html   ← Web UI
│   └── static/
│       └── style.css    ← Dashboard styles
│
├── config.py            ← Token management
├── requirements.txt     ← Dependencies
├── setup.py             ← pip install -e . support
└── .env.example         ← Token template
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.9+ |
| CLI framework | [Click](https://click.palletsprojects.com/) |
| Terminal UI | [Rich](https://github.com/Textualize/rich) |
| Web dashboard | [Flask](https://flask.palletsprojects.com/) |
| Local storage | SQLite via `sqlite3` |
| HTTP requests | [Requests](https://requests.readthedocs.io/) |
| Config | [python-dotenv](https://github.com/theskumar/python-dotenv) |

---

## 🗺️ Roadmap

- [x] GitHub integration (PR, CI status, comments)
- [x] Linear integration (tickets, status, assignee)
- [x] Slack integration (relevant messages)
- [x] Local SQLite storage
- [x] `cb status` command
- [x] `cb resume` command
- [x] Local web dashboard
- [x] Multi-repo management (`cb repo`)
- [ ] GitLab support
- [ ] Jira integration
- [ ] VS Code extension
- [ ] Notion integration
- [ ] `cb standup` - auto-generate daily standup from your activity

---

## 🤝 Contributing

Contributions are welcome! This project is built by developers, for developers.

```bash
# Fork & clone
git clone https://github.com/YOUR_USERNAME/context-bridge.git
cd context-bridge

# Install in dev mode
pip install -e .

# Create a branch
git checkout -b feat/your-integration

# Make changes, then PR!
```

**Want to add a new integration?** Check [`integrations/github.py`](integrations/github.py) - it's a good template. Each integration needs:
- A `get_*` function (fetches data from API)
- A `display_*` function (renders using Rich)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

Free to use, modify, and distribute. If this tool helps you ship faster, give it a ⭐ - it means a lot!

---

<div align="center">

**Built with obsession by [Harsh](https://github.com/Harsh-Codes-77)**

*Stop switching tabs. Start shipping.*

⭐ **Star this repo if context-bridge saved your sanity** ⭐

</div>
