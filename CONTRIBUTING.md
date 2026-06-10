# Contributing to SuperBrowser

Please read our [Code of Conduct](./CODE_OF_CONDUCT.md) before contributing.

Thank you for contributing to SuperBrowser. This guide explains how to set up the project, propose work, submit pull requests, and follow the expectations for GSSoC contributions.

SuperBrowser combines a FastAPI backend with a React and Electron frontend to provide AI-assisted search, browsing context, and multi-engine search results. Please keep contributions focused, tested, and easy for maintainers to review.

## Contribution Principles

- Work on an issue only after you are assigned.
- Keep each pull request focused on one issue or one clear improvement.
- Explain the problem, approach, and validation in your PR.
- Do not modify unrelated files or reformat large areas of code without a reason.
- Review and test any AI-assisted code before submitting it.
- Be respectful in issue comments, reviews, and maintainer discussions.

## Before You Start
1. Read the issue description and existing comments.
2. Check open pull requests to avoid duplicate work.
3. Comment with a clear implementation approach.
4. Wait for a maintainer to assign the issue.
5. Create a branch from the latest main branch.

Maintainers do not assign issues only on a first-come-first-served basis. A strong proposal should describe the files you expect to touch, the design choice, edge cases, and any expected risks.


If a maintainer asks you to share the approach by email, use `jeetpandya2006@gmail.com`.

## Local Setup

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- A Groq API key
- A SerpAPI key

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

On Windows, activate the virtual environment with:

```bash
venv\Scripts\activate
```

The backend runs at `http://localhost:8000`. FastAPI documentation is available at `http://localhost:8000/docs`.

### Environment Variables

Create `backend/.env` from `backend/.env.example` and set:

```env
SERPAPI_API_KEY=your_serpapi_key
GROQ_API_KEY=your_groq_key
```

`SERPAPI_API_KEY` powers search results. `GROQ_API_KEY` powers AI responses.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend usually runs at `http://localhost:5173`.

### Quick Verification

1. Start the backend.
2. Start the frontend.
3. Open the frontend in your browser.
4. Try a SuperSEO query.
5. Try a SuperAI query after configuring `GROQ_API_KEY`.

If the app shows a missing API key message, check `backend/.env` and restart the backend.

## Development Workflow

### 1. Sync Your Fork

```bash
git checkout main
git pull upstream main
git push origin main
```

If your remote names are different, use the names configured in your fork.

### 2. Create a Branch

Use an issue-based branch name:

```bash
git checkout -b feat/issue-17-contributing-guide
git checkout -b fix/issue-24-search-error-state
```

Recommended patterns:

- `feat/issue-N-short-description`
- `fix/issue-N-short-description`
- `docs/issue-N-short-description`
- `test/issue-N-short-description`
- `refactor/issue-N-short-description`

### 3. Make a Focused Change

- Keep the implementation aligned with the assigned issue.
- Prefer small, readable commits.
- Add or update tests when behavior changes.
- Add screenshots or screen recordings for UI changes.
- Avoid committing local secrets, `.env`, build output, or dependency folders.

### 4. Validate Locally

Use the checks that match your change:

```bash
cd frontend
npm run lint
npm run build
```

```bash
cd backend
python -m compileall .
```

If a command is unavailable or fails because of existing project setup issues, mention that clearly in the PR validation section.

## Code Style

### Backend

- Follow PEP 8.
- Keep FastAPI routes explicit and easy to trace.
- Use async patterns consistently where the existing code uses `httpx` and `asyncio`.
- Handle errors with clear messages.
- Avoid bare `except` blocks.
- Add concise docstrings for new helpers, services, or non-obvious logic.

### Frontend

- Use functional React components and hooks.
- Keep components small and readable.
- Reuse existing styles and components before adding new ones.
- Avoid unrelated UI redesigns inside bug-fix PRs.
- Keep accessibility in mind for buttons, form controls, labels, and keyboard interactions.

### Documentation

- Use clear headings and short steps.
- Prefer commands that contributors can run directly.
- Keep links relative when pointing to files in this repository.
- Update README links when adding important contributor-facing documents.

## GitHub Issue Template Details

When proposing work on an issue, include:

```md
## Approach
- Files or folders I expect to modify:
- Proposed implementation:
- Edge cases:
- Validation plan:

## Notes
- Dependencies or blockers:
- Screenshots or references, if relevant:
```

Good issue comments help maintainers decide whether the issue should be assigned to you. Avoid comments that only say "please assign me" without an approach.

## Pull Request Template Details

Use this structure in your PR description:

```md
## Summary
- What changed?
- Which issue does this close?

## Root Cause
- Why was the change needed?

## Changes Made
- Key implementation details
- Files or areas touched

## Testing
- Commands run
- Manual checks performed
- Screenshots for UI changes, if applicable

## Impact
- User-facing or maintainer-facing benefit
- Any risks or follow-up work

Closes #ISSUE_NUMBER
```

Use a conventional PR title:

```text
docs: add GSSoC contributing guide
fix: handle empty search results
feat: add saved search filters
test: cover context manager edge cases
```

## GSSoC Guidelines

For GSSoC work:

- Start only after assignment.
- Link the issue in the PR body with `Closes #N` or `Fixes #N`.
- Do not split one fix into multiple PRs just for points.
- Do not open duplicate PRs for an issue already covered by someone else.
- Ask for clarification on the issue when requirements are unclear.
- Keep validation honest. If you could not run a check, say why.

### Common Labels and Points

| Label | Meaning |
| --- | --- |
| `gssoc:approved` | Required for GSSoC scoring after maintainer approval |
| `level:beginner` | Beginner difficulty |
| `level:intermediate` | Intermediate difficulty |
| `level:advanced` | Advanced difficulty |
| `level:critical` | Critical difficulty |
| `type:docs` | Documentation work |
| `type:bug` | Bug fix |
| `type:feature` | Feature work |
| `type:testing` | Test coverage |
| `type:security` | Security improvement |
| `type:performance` | Performance improvement |

Labels are managed by maintainers. Contributors should not pressure maintainers for labels, but it is fine to mention the linked issue and expected label context in the PR description.

## Review Process

> ⭐ **Star the repository before your PR can be merged.** Contributors are
> required to star [SuperBrowser](https://github.com/PandyaJeet/SuperBrowser)
> before a pull request is merged. A workflow checks this automatically and
> reports a `star-check` status on your PR — maintainers will not merge a PR
> from a contributor who has not starred the repo.

1. A maintainer reviews the PR.
2. If changes are requested, address them in the same branch.
3. Reply with a short summary of what changed after pushing updates.
4. Make sure you have starred the repository (see the note above).
5. Wait for approval and merge.

Please do not create repeated status comments. One clear follow-up after addressing feedback is enough.

## What Not To Submit

- Unassigned work in assignment-gated issues
- Duplicate PRs
- Large unrelated formatting changes
- Generated files that are not needed
- Secrets, API keys, or local `.env` files
- Untested code copied directly from AI tools
- Changes that only inflate PR count without improving the project

## Helpful Links

- [README](./README.md)
- [Backend environment example](./backend/.env.example)
- [Frontend ESLint config](./frontend/eslint.config.js)
- [Testing guide](./TESTING.md)
- [Context feature guide](./CONTEXT_FEATURE.md)

Thanks for helping improve SuperBrowser.
