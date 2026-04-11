Title: feat: GitHub Action for cross-repo schema PR to catch-app

## What do you want to build?

Create a GitHub Actions workflow that automatically opens a Pull Request in the
`catch-app` repository whenever the `schema.json` in catch-data is updated.
This implements the cross-repo schema synchronization described in Section 5 of
the PRD, ensuring the frontend TypeScript types always match the backend Python
data models.

## Acceptance Criteria

- [ ] A workflow `.github/workflows/schema-sync.yml` triggers when `libs/catch-models/schema.json` is updated on `main` (or is called by the schema-generate workflow)
- [ ] The workflow clones the `catch-app` repository using a cross-repo token or GitHub App
- [ ] The workflow copies the updated `schema.json` into the `catch-app` repository at a well-known path (e.g., `src/schema/schema.json`)
- [ ] The workflow creates a new branch in `catch-app` (e.g., `schema-sync/{sha-short}`)
- [ ] The workflow opens a Pull Request in `catch-app` with a descriptive title and body referencing the catch-data commit
- [ ] If an open schema-sync PR already exists, the workflow updates it instead of creating a duplicate
- [ ] The PR body includes a link to the catch-data commit that triggered the sync
- [ ] The workflow handles the case where `catch-app` does not exist yet (exits gracefully)
- [ ] The cross-repo authentication uses a GitHub App or fine-grained PAT — never a classic PAT with broad permissions

## Implementation Notes

**📝 ADR Consideration:**

- Propose an ADR documenting the cross-repo automation strategy. Key decisions:
  which authentication method (GitHub App vs. fine-grained PAT), what
  permissions are needed, and how to handle the catch-app repo not existing yet.
- GitHub Apps are preferred for cross-repo automation because they have
  granular, repo-scoped permissions and don't consume a user's seat.

**😴 Lazy Maintainer notes:**

- The PR in catch-app should trigger that repo's CI, which will run
  `json-schema-to-typescript` to generate TypeScript types and validate they
  compile. If the schema change is backward-compatible, the PR should be
  green and mergeable.
- The PR title should follow a convention like:
  `chore(schema): sync schema.json from catch-data@{sha-short}`
- If the schema change is breaking (removed fields, type changes), the PR
  will fail CI in catch-app. This is intentional — it forces a conscious
  frontend update rather than silent breakage.

**🔧 Data Pipeline Janitor notes:**

- The workflow should be triggered by the schema-generate workflow (07-01)
  rather than by a `paths` filter on `main` push. This ensures the sync only
  happens after a successful schema generation, not on any random file change.
- Use `workflow_run` trigger or `workflow_call` to chain the workflows.

**🤑 FinOps Miser notes:**

- GitHub Actions for cross-repo operations: minimal compute, runs only when
  the schema changes. Expected: a few times per month during active
  development, then rarely.
- GitHub Apps are free to create and use for automation within personal/org
  repos.

**Security notes:**

- The cross-repo token MUST have only `contents: write` and `pull-requests:
  write` permissions on the catch-app repo. No other repositories.
- Store the token/App credentials as GitHub Actions secrets.

Reference ADR-014 (CI/CD Strategy), ADR-017 (GitHub OIDC for inspiration on
minimal-permission patterns).
