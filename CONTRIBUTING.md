# Contributing to context-bridge

Thanks for helping improve context-bridge.

## 1. Ground Rules

- Be respectful and constructive in discussions and code reviews.
- Do not commit secrets (tokens, `.env`, private keys, credentials).
- Keep PRs small and focused on one problem.
- Add or update docs when behavior changes.

## 2. Development Setup

```bash
git clone https://github.com/Harsh-Codes-77/context-bridge
cd context-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create local env values:

```bash
cp .env.example .env
```

Fill your own tokens in `.env`.

## 3. Branch Naming

Use one of these patterns:

- `feat/<ticket-or-topic>-short-description`
- `fix/<ticket-or-topic>-short-description`
- `docs/<topic>`
- `chore/<topic>`

Examples:

- `feat/AUTH-412-resume-panel`
- `fix/BUG-101-linear-status-color`

## 4. Commit Message Style

Use clear imperative messages:

- `feat(cli): add web dashboard command`
- `fix(db): handle cache expiry edge case`
- `docs(readme): add installation steps`

## 5. Validation Before PR

Run these checks before opening a PR:

```bash
cb --help
python storage/db.py
python -m py_compile cli/main.py integrations/github.py integrations/linear.py storage/db.py dashboard/app.py
```

If you changed dashboard behavior, run:

```bash
cb web
```

And verify:

- Home page loads on `http://localhost:4242`
- `/api/sessions` returns JSON
- `/api/status` returns valid response for your current setup

## 6. Pull Request Checklist

Include the following in your PR description:

- What changed
- Why it changed
- How you tested it
- Any screenshots for UI changes
- Any breaking changes

Before submitting, ensure:

- [ ] No secrets in changed files
- [ ] `.env` not committed
- [ ] Docs updated (README/CONTRIBUTING when needed)
- [ ] Commands still work: `cb status`, `cb resume`, `cb web`

## 7. Security and Secrets

- Never paste real tokens in issues, PRs, or screenshots.
- Use test tokens or redact values.
- If a token is exposed, rotate it immediately.

## 8. Reporting Bugs

When filing an issue, include:

- OS and Python version
- Exact command run
- Full error output
- Steps to reproduce
- Expected vs actual behavior

## 9. Suggesting Features

For feature requests, share:

- Use case
- Current pain point
- Proposed behavior
- Any API or UX implications

Thanks again for contributing.
