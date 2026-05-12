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

**✨ New:** Click-to-copy branch names and git checkout commands with keyboard shortcuts `c` and `g`!

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

| Command | Description |
|---|---|
| `cb status` | Fetch GitHub + Linear + Slack context for the current branch. |
| `cb status --json` | Output clean JSON instead of rich terminal output. |
| `cb resume` | Resume context from your last session on this branch. |
| `cb export` | Export all context for the current branch to a markdown file. |
| `cb standup` | Generate a daily standup report from the last 24 hours of work. |
| `cb standup --copy` | Copy the standup report to clipboard (for quick Slack posting). |
| `cb standup --export` | Save the standup report to a markdown file. |
| `cb web` | Start local context-bridge web dashboard. |
| `cb init` | Run first-time setup for API tokens and default repo. |
| `cb repo` | Manage saved repos — add, switch, list, or remove. |
| `cb repo add` | Add a new repo and set it as the active one. |
| `cb repo use` | Switch the active repo to one you've already added. |
| `cb repo list` | Show all saved repos. |
| `cb repo current` | Print the currently active repo. |
| `cb repo remove` | Remove a saved repo. |
| `cb notes` | Leave yourself reminders or context tied directly to your active branch session. |
| `cb notes add` | Add a timestamped note to the current branch. |
| `cb notes show` | Display all notes associated with your current branch. |
| `cb notes clear` | Clear all notes attached to your current branch. |
| `cb config` | Manage CLI configuration and API tokens. |
| `cb config show` | Show current config status (tokens and active repo). |
| `cb config set` | Set a specific API token without re-running init. |
| `cb config clear-token` | Remove a specific API token. |
| `cb doctor` | Check cb installation and local configuration health. |

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

**Under the hood:**
- ⚡ **Parallel Execution**: Uses `ThreadPoolExecutor` to fetch GitHub, Linear, and Slack data simultaneously, drastically reducing fetch time.
- 🛡️ **Fault Tolerance**: If one integration fails (e.g., Slack token expired), the other integrations will still load successfully, and you'll see a clear warning instead of a crash.

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

### `cb standup`
**[NEW - Killer Feature] Auto-generate your daily standup from the last 24 hours of work!**

This command aggregates all your branch activity from the past day and generates a beautifully formatted standup report. It pulls real data from GitHub PRs, Linear tickets, and your session history.

```bash
cb standup
```

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DAILY STANDUP — May 08, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ DONE (Yesterday):
- fix/CON-3-api-timeout → Updated timeout config
  CON-3: Implement API timeout handling
  Status: In Progress

🔄 IN PROGRESS (Today):
- feature/CON-5-login-timeout → Resolving PR comments
  CON-5: Login timeout after 30s
  Status: Done
  PR #34 → 2 new comments from Rahul
  CI → Passing ✓

⚠️ BLOCKERS:
- PR #34 needs 1 more approval before merge

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Smart Features:**
- 🧠 Auto-categorizes branches as "Done" (inactive >12hrs) or "In Progress" (recent activity)
- 🔗 Links GitHub PRs with comment counts and CI status
- 🎫 Extracts Linear ticket IDs from branch names (e.g., `fix/CON-5-auth` → pulls ticket CON-5)
- ⚠️ Highlights blockers (PR approvals needed, failed CI, etc.)
- 💪 Works even with just 1 branch active in the last 24 hours
- 🛡️ Gracefully handles missing API tokens or data

#### Use Cases

**Use Case 1: Daily Team Standup**
```bash
cb standup
```
Run this during your daily standup meeting to review everything you worked on in the past 24 hours. All info is organized and ready to present.

**Use Case 2: Quick Slack Update**
```bash
cb standup --copy
```
Automatically copies the entire standup report to your clipboard. Then just paste it into Slack, email, or your team channel:
- ✓ Standup copied to clipboard — paste it in Slack!

**Use Case 3: Archival & Record-Keeping**
```bash
cb standup --export
```
Saves the standup as `standup-2026-05-08.md` in your current directory. Great for:
- Keeping a daily log of what you shipped
- Attaching to sprint retrospectives
- Building your portfolio of completed work
- ✓ Standup exported to standup-2026-05-08.md

**Use Case 4: Full Workflow (Clipboard + File)**
```bash
cb standup --copy --export
```
Both copies to clipboard AND saves to file. Perfect for submitting to Slack while also archiving for records.

#### Report Contents

For each branch active in the last 24 hours, the standup includes:

| Item | Source | Example |
|------|--------|----------|
| **Branch Name** | Git | `feature/CON-5-login-timeout` |
| **Work Summary** | Session history | "Resolving PR comments" |
| **GitHub PR** | API | `#34 → 2 new comments from Rahul` |
| **CI Status** | GitHub Actions | `CI → Passing ✓` |
| **Linear Ticket** | Extracted from branch name | `CON-5: Login timeout fix` |
| **Ticket Status** | Linear API | `Status: In Progress` |
| **Blockers** | PR approval status | `PR #34 needs 1 more approval` |

#### Examples

**Example 1: Yesterday you shipped a feature**
```bash
$ cb standup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DAILY STANDUP — May 08, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ DONE (Yesterday):
- feature/CON-5-login-timeout → Implemented JWT refresh logic
  CON-5: Login timeout after 30s
  Status: Done
  PR #34 → Merged ✓
  CI → Passing ✓
```

**Example 2: Today you're debugging CI failures**
```bash
$ cb standup
🔄 IN PROGRESS (Today):
- fix/CI-timeout-issue → Debugging flaky tests
  CI → Failing ✗
  PR #35 → Changes requested (Sarah: "needs more error handling")

⚠️ BLOCKERS:
- PR #35 needs changes requested fixes
- CI failing on line 84
```

**Example 3: Quick Slack post**
```bash
$ cb standup --copy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DAILY STANDUP — May 08, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[...full report...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Standup copied to clipboard — paste it in Slack!

# Then in Slack: Cmd+V (or Ctrl+V on Windows/Linux)
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

### `cb config`
Manage your configuration and API tokens without needing to run the full `cb init` wizard again.

#### `cb config show`
Show the status of your configured tokens and active repository. Tokens are safely masked.
```bash
cb config show
```
```
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Token  ┃ Status   ┃ Last 4 chars ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ GitHub │ ✓ Set    │ ...x4f2      │
│ Linear │ ✓ Set    │ ...a9k1      │
│ Slack  │ ✗ Not set│ —            │
└────────┴──────────┴──────────────┘

Active Repo    harsh/my-app
```

#### `cb config set <github-token | linear-token | slack-token>`
Update or add a specific API token. The input prompt is hidden.
```bash
cb config set github-token
# Enter new GitHub Token: 
# ✓ GitHub token updated
```

#### `cb config clear-token <github | linear | slack>`
Remove a specific API token from your configuration.
```bash
cb config clear-token slack
# Remove Slack token? [y/N]: y
# ✓ Slack token removed
```

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

### Dashboard Search & Filter

**Find branches instantly** when you have 10+ active sessions:

- 🔍 **Live Search**: Type to filter branches in real-time (no page reload)
- ⌨️ **Keyboard Shortcut**: Press `/` anywhere to focus the search bar
- 🎯 **Smart Matching**: Filters by branch name, repo name, or files touched (case-insensitive)
- ✨ **Highlighted Results**: Matched text is highlighted in cyan for easy scanning
- 📊 **Result Counter**: Shows "Showing X of Y branches" while filtering
- ✕ **Clear Button**: Click `×` to reset search instantly
- 💬 **Server Fallback**: GET `/api/search?q=<query>` endpoint available for larger datasets

**Example:**
```
→ Press "/" to focus search
→ Type "auth" → instantly shows only branches matching "auth"
→ Type "services" → filters to branches with service-related files touched
→ See "Showing 3 of 12 branches" while filtered
→ Click × or clear input → back to full view
```

### Dashboard Keyboard Shortcuts

**Power users**: Navigate and control the dashboard entirely with your keyboard. No mouse needed.

#### Global Shortcuts

| Key | Action |
|-----|--------|
| **r** | Refresh all context data (shows brief indicator) |
| **/** | Focus search bar instantly |
| **Esc** | Clear search input OR close any dialog/modal |
| **?** | Open keyboard shortcuts help overlay |

#### Card Navigation

| Key | Action |
|-----|--------|
| **j** or **↓** | Move focus to next branch card |
| **k** or **↑** | Move focus to previous branch card |
| **Enter** | Expand focused card to show full details |
| **c** | Copy branch name of focused card |
| **g** | Copy git checkout command of focused card |
| **Delete** or **x** | Prompt to delete focused card's session |

#### Visual Feedback

- **Focused card** gets a bright cyan highlighted border (distinct from mouse hover)
- **Position indicator** shows "3 / 12" in bottom right when navigating with keyboard
- **Smooth scroll** keeps focused card visible and centered
- **Footer hint** displays "Press ? for keyboard shortcuts" for discoverability

### Click-to-Copy Branch Names & Git Commands

**No more manual copy-paste!** Quickly copy branch names and git commands with a single click or keyboard shortcut.

#### Click to Copy

**Branch Name:**
- Hover over the branch name → a copy icon (📋) appears
- Click the branch name or the icon to copy to clipboard
- Inline "✓ Copied!" feedback displays for 2 seconds
- Toast notification shows at bottom-right confirming the copy

**Git Checkout Command:**
- Click the button below the branch name showing `📋 git checkout fix/branch-name`
- Copies the full git command to your clipboard
- Same "✓ Copied!" feedback and toast notification

#### Keyboard Shortcuts for Copying

When a branch card is focused (using `j`/`k` navigation):

| Key | Action |
|-----|--------|
| **c** | Copy branch name to clipboard |
| **g** | Copy git checkout command to clipboard |

Both show inline feedback and toast notifications on success.

#### Fallback for Older Browsers

If your browser doesn't support the modern Clipboard API:
1. **First fallback**: Uses `document.execCommand('copy')` for older browsers
2. **Last resort**: Shows a modal popup with the text pre-selected so you can manually copy with Ctrl+C / Cmd+C

#### Tips

- ✅ Shortcuts **don't fire** while typing in the search box
- ✅ All shortcuts work in **one clean event listener** (no interference)
- ✅ Works great with **tmux/screen** or remote SSH sessions
- ✅ Press **?** anytime to see the help overlay with all available shortcuts

**Example workflow:**
```
→ Press "/" → Type "auth" → See matching branches
→ Press "j" to move down → Focus on "fix/auth-timeout"
→ Press "g" → Copies "git checkout fix/auth-timeout"
→ Paste in terminal, continue coding
→ Back in dashboard, press "r" → Refreshes all context
→ Done without touching the mouse once!
```

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
- [x] `cb standup` - auto-generate daily standup from your activity
- [x] Dashboard search & filter - find branches instantly with `/` keyboard shortcut
- [x] Click-to-copy branch names and git commands with keyboard shortcuts
- [ ] GitLab support
- [ ] Jira integration
- [ ] VS Code extension
- [ ] Notion integration

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
