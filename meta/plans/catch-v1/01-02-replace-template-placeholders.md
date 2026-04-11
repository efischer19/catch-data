# feat: Replace template placeholders with catch-data project values

## What do you want to build?

Replace all `{{PLACEHOLDER}}` tokens inherited from the blueprint-repo-blueprints
template with concrete values for the catch-data project. This includes project
names, author identifiers, AWS configuration placeholders, and documentation
references throughout the entire repository.

## Acceptance Criteria

- [ ] `{{PROJECT_NAME}}` is replaced with `catch-data` in all files
- [ ] `{{GITHUB_OWNER}}` is replaced with `efischer19` in all pyproject.toml and documentation files
- [ ] `{{PROJECT_URL}}` is replaced with the actual GitHub repository URL
- [ ] AWS placeholders (`{{AWS_ACCOUNT_ID}}`, `{{AWS_REGION}}`, `{{AWS_ROLE_ARN}}`, `{{TF_STATE_BUCKET}}`, `{{TF_LOCK_TABLE}}`, `{{S3_BUCKET_NAME}}`) are replaced with concrete values or clearly documented as environment-specific configuration
- [ ] `meta/DEVELOPMENT_PHILOSOPHY.md` and `meta/ROBOT_ETHICS.md` are updated to remove the "inherited from template" notice and reference catch-data specifically
- [ ] No `{{...}}` placeholder tokens remain in any tracked file (excluding cookiecutter templates in `templates/`)
- [ ] A `grep -r '{{' --include='*.md' --include='*.toml' --include='*.tf' --include='*.yml' --include='*.py'` returns zero results outside `templates/`

## Implementation Notes

Run a comprehensive search for `{{` across all file types to build the
replacement map. Some AWS placeholders may need to remain as environment
variables or Terraform variables rather than being hardcoded — use judgment:

- Project identity values (name, owner, URL): hardcode everywhere.
- AWS values (account ID, region, role ARN): keep as Terraform variables with
  sensible defaults, but remove the `{{...}}` syntax in favor of proper HCL
  variable references.

The `templates/` directory contains cookiecutter templates that legitimately use
`{{cookiecutter.*}}` syntax — leave those untouched.

Update `meta/DEVELOPMENT_PHILOSOPHY.md` to be catch-data specific rather than
generic template guidance. Update `meta/ROBOT_ETHICS.md` similarly, noting the
specific MLB Stats API data source.
