# Contributing

## Workflow: GitHub Flow

1. Open an issue for the work, or pick up an existing one. See Issues below.
2. Branch off `main`. Branch names describe the work: `cart-api`, `fix-login-401`.
   Initials, nicknames and unrelated words are not.
3. Open a pull request that closes the issue.
4. Squash merge into `main`.

- Keep branches short-lived. Merge within 2 days.
- Never push directly to `main`.
- `main` must always run locally and pass CI, because a passing `main` can deploy itself.

## Issues

- Every change starts from an issue. Do not open a duplicate if one already exists.
- Assign yourself and add a label: `documentation` for docs, `enhancement` for features,
  `bug` for fixes.
- Set the milestone of the deliverable the issue belongs to, if there is one. Milestones go on
  issues only, not on pull requests, so progress is not counted twice. Each milestone
  description lists where its outputs live.
- Issues have no reviewer field. End the issue body with `Reviewer: @handle`, and request
  that person as reviewer when you open the pull request.
- GitHub Projects is not used.

## Pull requests

- A pull request is required for every change to `main`.
- Required approvals: 0. Reviews are recommended, not mandatory. If nobody reviews within
  24 hours, the author merges.
- `main` is protected: the `backend` and `frontend` checks must pass before merging, for
  admins too. Force pushes and deleting `main` are blocked.
- PR title follows the commit message format below (it becomes the squash commit message).
- The body comes from [.github/pull_request_template.md](.github/pull_request_template.md).
  Keep the Summary to one or two sentences, tick the checklist, and fill in `Closes #N`.

## Commit messages

Commits inside a branch are squashed on merge, so their messages are free-form.
The rules below apply to the PR title, which becomes the commit message on `main`.

Conventional Commits format:

```
<type>(<scope>): <summary>
```

- `type` is one of: `feat`, `fix`, `docs`, `refactor`, `style`, `test`, `chore`, `ci`
- `scope` is one of: `frontend`, `backend`, `deploy`, `spikes`. Omit it for root files,
  `docs/specs/`, `.github/` or changes touching several.
- `summary`: English, imperative verb, lowercase, no trailing period, 50 characters or fewer.
- Body is optional. Use it only to explain why.

Examples:

```
feat(frontend): add product list page
fix(backend): return 401 on expired refresh token
fix(deploy): make scripts executable
chore(spikes): update toss spike dependencies
ci: add backend and frontend jobs
docs: add tech stack doc
```

## CI and deploy

- `ci` ([ci.yml](.github/workflows/ci.yml)): on every pull request to `main` and every push to
  `main`. Job `backend` runs `black --check`, a missing-migration check and the Django tests
  (the concurrency test on a file database). Job `frontend` runs `prettier --check`,
  `npm run lint`, `npm test` and `npm run build`.
- `deploy` ([deploy.yml](.github/workflows/deploy.yml)): after `ci` passes on a push to `main`,
  it tags that commit `release-YYYYMMDD-N` and runs `deploy/deploy.sh` on the production
  server. It runs only while the repository variable `DEPLOY_ENABLED` is `true`; set it to
  anything else to pause deploys, for example during a demo. Details: `docs/specs/sip/`.
- `docs-sync` ([docs-sync.yml](.github/workflows/docs-sync.yml)): on a push to `main` that
  touches `docs/specs/`, `docs/images/` or `.github/google-docs.json`, see Documentation.

## Documentation

`docs/` is the source of truth. Documents are written and revised in `docs/` through issues
and pull requests, like code.

- `docs/` is Markdown first: documents as Markdown, with images and diagram sources next to
  them. Any other format needs a reason in the PR description.
- Stage documents live in `docs/specs/`, one folder per document and one file per numbered
  section: `spmp/` (project plan), `srs/` (requirements), `sdd/` (design), `stp/` (test plan),
  `sip/` (installation plan), `smp/` (maintenance plan). Start from `docs/specs/README.md`.
- Which change goes where: a requirement goes to `srs/`, a design or technical choice to `sdd/`
  (its reason to `sdd/12-rationale.md`), a requirement-level policy to `srs/7-decisions.md`,
  scope and schedule to `spmp/`.
- Requirements carry IDs (`DR-n`, `FR-n`, `NFR-n`, `UC-n`). One FR holds one function and one
  NFR one measurable condition. IDs are never renumbered or reused once merged; a dropped one
  stays with "(삭제, date, reason)". Test names and PR bodies cite the IDs.
- On every merge, `docs-sync` builds each stage document with
  [.github/scripts/build-docs.mjs](.github/scripts/build-docs.mjs) and overwrites its Google Doc
  (IDs in [.github/google-docs.json](.github/google-docs.json)). Never edit those Google Docs.
  Course submission copies are made separately and are not committed.

## Language

- Code, comments, commit messages, PR titles, issue titles and config files are in English.
- Course deliverable documents in `docs/` are in Korean, matching the submission.
  Identifiers such as table, column, class and method names and status values stay in English.
- Issue and PR bodies for course deliverables are in Korean. Other issue and PR bodies are
  in English.

## Notifications

A Discord webhook posts on push, pull request, pull request review and issues.

## Do not commit

- `.env` (commit `.env.example` instead). When you add a new environment variable, add its key to `.env.example` too.
- `db.sqlite3` or any other `*.sqlite3` database.
- Word or HWP files (`.doc`, `.docx`, `.hwp`, `.hwpx`). See Documentation above.
- Build output and dependencies: `dist/`, `node_modules/`, `.venv/`.
