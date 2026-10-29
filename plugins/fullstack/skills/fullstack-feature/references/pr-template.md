# Pull request template (fullstack feature)

Use the repository's own `.github/pull_request_template.md` if it exists; fill its sections with the content below.
Keep it short: reviewers read the summary and contract section first.

## Title

Conventional Commits style when the repo uses it: `feat(orders): allow cancelling an open order`.
Include the ticket key if the team links PRs by title: `feat(orders): allow cancelling an open order (SHOP-123)`.

## Body

```markdown
## Summary

<One to three sentences: what the user can do now and why.>

Ticket: <link>

## Acceptance criteria

- [x] <criterion 1> (covered by `OrderControllerTest#cancelOpenOrder`)
- [x] <criterion 2> (covered by `order-detail.spec.ts`)

## API contract

| Method | Path | Change |
| --- | --- | --- |
| POST | `/orders/{orderId}/cancel` | new |
| GET | `/orders/{orderId}` | adds `cancelledAt` (optional) |

- Breaking: no (`oasdiff breaking` clean) | yes: <what, and the migration plan>
- New error types: `https://api.example.com/problems/order-not-cancellable` (409)
- Authorization: order owner or `ROLE_SUPPORT`

## Backend

- <Migration `V42__add_cancelled_at.sql`: adds nullable column, no backfill>
- <Service/transaction notes, events published, external calls>

## Frontend

- <Routes/components added or changed>
- <State/data-fetching approach, feature flag>

Screenshots / recording:

| Before | After |
| --- | --- |
| <img> | <img> |

## Tests

- Backend: <slices and integration tests added>; `./mvnw verify` passes
- Frontend: <unit/component tests>; lint, type-check, build pass
- E2E: <spec or "not applicable">
- Manual: <steps tried, browsers, roles>

## Rollout

- Deploy order: <backend first; UI behind flag `orders.cancel`>
- Migration safety: <compatible with currently deployed version>
- Config/secrets: <new properties and where they are set, or "none">
- Rollback: <revert is safe / requires ...>

## Notes for reviewers

- <Trade-offs, things deliberately left out, follow-up tickets>
- Generated files: `api/openapi.json`, `<client folder>` (review the spec diff; skip the client diff)
```

## Pre-merge checklist (author)

- [ ] Acceptance criteria each map to a test.
- [ ] `api/openapi.json` regenerated and reviewed; client regenerated; CI drift check green.
- [ ] `oasdiff breaking` clean, or the breaking change is documented with a migration plan.
- [ ] Authorization tested with an allowed and a denied case.
- [ ] Error responses are Problem Details and the UI shows them sensibly.
- [ ] Loading, empty, error and permission-denied states implemented.
- [ ] Accessibility: labels, keyboard path, focus after actions.
- [ ] Migration backward compatible; no edits to applied migrations.
- [ ] No secrets, debug code, `console.log`, commented-out code or unrelated changes.
- [ ] `review-checklist` self-review done; blockers and majors fixed.
- [ ] Commits are logical units (contract + backend, client, UI) with conventional messages.

## Splitting into several PRs

When one PR is too large, link them and state order in each description:

```markdown
Part 1 of 2: contract + backend. UI follows in #<n>.
The endpoint is unused by the frontend until part 2 merges.
```
