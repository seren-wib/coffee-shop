# Contributing

## Workflow: GitHub Flow

1. Open an issue for the work, or pick up an existing one. See Issues below.
2. Branch off `main`. Branch names are free-form, but must describe the work on the branch.
   `cart-api`, `usecase-diagram`, `fix-login-401` are fine. Initials, nicknames, and
   unrelated words are not.
3. Open a pull request that closes the issue.
4. Squash merge into `main`.

- Keep branches short-lived. Merge within 2 days.
- Never push directly to `main`.
- `main` must always run locally.

## Issues

- Every change starts from an issue. Do not open a duplicate if one already exists.
- Assign yourself and add a label: `documentation` for docs, `enhancement` for features,
  `bug` for fixes.
- Set the milestone of the deliverable the issue belongs to. Milestones go on issues only,
  not on pull requests, so progress is not counted twice. Each milestone description lists
  where its outputs live.
- Issues have no reviewer field. End the issue body with `Reviewer: @handle`, and request
  that person as reviewer when you open the pull request.
- GitHub Projects is not used.

## Pull requests

- A pull request is required for every change to `main`.
- Required approvals: 0. Reviews are recommended, not mandatory.
- If nobody reviews within 24 hours, the author merges.
- PR title follows the commit message format below (it becomes the squash commit message).

## Commit messages

Commits inside a branch are squashed on merge, so their messages are free-form.
The rules below apply to the PR title, which becomes the commit message on `main`.

Conventional Commits format:

```
<type>(<scope>): <summary>
```

- `type` is one of: `feat`, `fix`, `docs`, `refactor`, `style`, `test`, `chore`
- `scope` is `frontend` or `backend`. Omit it for root files or changes touching both.
- `summary`: English, imperative verb, lowercase, no trailing period, 50 characters or fewer.
- Body is optional. Use it only to explain why.
- To close an issue, add `Closes #N` to the body.

Examples:

```
feat(frontend): add product list page
fix(backend): return 401 on expired refresh token
docs: add tech stack doc
chore: update prettier config
```

## Documentation

`docs/` is the source of truth. Documents are written and revised in `docs/` through issues
and pull requests, like code. For each course submission, the documents are compiled into
one Google Doc and submitted from there. The compiled document is not committed.

- `docs/` is Markdown first: documents as Markdown, with images and diagram sources next to
  them. Any other format needs a reason in the PR description.

## Notifications

A Discord webhook posts on push, pull request, pull request review, and issues.

## Do not commit

- `db.sqlite3`
- `.env` (commit `.env.example` instead). When you add a new environment variable, add its key to `.env.example` too.
- Word or HWP files (`.doc`, `.docx`, `.hwp`, `.hwpx`). See Documentation above for what
  belongs in `docs/`.
