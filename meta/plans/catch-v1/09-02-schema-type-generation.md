# feat: Configure JSON Schema to TypeScript type generation

## What do you want to build?

Set up the `json-schema-to-typescript` toolchain in catch-app that converts the
`schema.json` (synced from catch-data) into strict TypeScript interfaces. This
ensures the frontend's type system exactly matches the backend data contract
with zero manual type definitions.

## Acceptance Criteria

- [ ] `json-schema-to-typescript` is installed as a dev dependency
- [ ] A `generate-types` npm script converts `src/schema/schema.json` into `src/types/generated.ts`
- [ ] The generated TypeScript interfaces include: `GoldTeamSchedule`, `GoldUpcomingGames`, `GoldGameSummary`, `GoldTeamInfo`, `GoldBoxscoreSummary`
- [ ] The generated types are strict: no `any` types, all nullable fields use `| null` (not optional)
- [ ] A pre-build hook runs type generation automatically before each build
- [ ] The generated `generated.ts` file is `.gitignore`d (generated at build time, not committed)
- [ ] TypeScript compilation succeeds with `strict: true` in `tsconfig.json`
- [ ] A CI check verifies that type generation succeeds and the build compiles with the generated types
- [ ] A README section documents the schema-to-type workflow for developers

## Implementation Notes

**🔧 Data Pipeline Janitor notes:**

- The `schema.json` file IS committed to the repo (synced via PR from
  catch-data). The generated `generated.ts` is NOT committed — it's built
  from `schema.json` at build time. This prevents merge conflicts in
  generated code.
- If `json-schema-to-typescript` produces types that don't match developer
  expectations (e.g., enum handling, nullable vs. optional), the fix should
  be in the Pydantic model or schema post-processing in catch-data, not in
  the catch-app type generation.

**🧪 QA notes:**

- Write a smoke test that imports the generated types and constructs a sample
  object. This catches type generation failures at build time rather than
  runtime.
- Consider a "contract test" that fetches a Gold JSON file from the dev
  environment and validates it against the TypeScript types using a schema
  validator like `ajv`.

**⚡ PWA Performance Fanatic notes:**

- Generated types are compile-time only — they have zero runtime cost. No
  impact on bundle size.

**😴 Lazy Maintainer notes:**

- When catch-data updates its Gold models, the schema-sync PR (ticket 07-02)
  updates `schema.json`. When that PR is merged, the next build automatically
  picks up the new types. Zero manual intervention.
- If the schema change is backward-incompatible, TypeScript compilation will
  fail, pointing directly to the code that needs updating. This is a feature,
  not a bug.

This is a catch-app repository ticket.
