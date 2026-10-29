---
name: api-contract
description: "OpenAPI-first contract between a Spring Boot backend and TypeScript clients: generate the spec with springdoc-openapi 3.x, commit it as the source of truth, generate typed clients (openapi-typescript with openapi-fetch for React and Next.js, ng-openapi-gen or openapi-generator typescript-angular for Angular), enforce RFC 9457 Problem Details errors, pagination, naming, date-time and enum conventions, and contract checks in CI. Use when adding or changing a REST endpoint, DTO or error shape, generating or updating an API client, or reviewing a change that touches both backend and frontend."
license: MIT
metadata:
  author: baibesh/devkit-skills
---

# API Contract (OpenAPI-first)

Targets: Spring Boot 4 / Java 21-25 with springdoc-openapi 3.x; Angular 22, React 19, Next.js 16 TypeScript clients. First detect the project's real versions and adapt; never downgrade a project.

The committed OpenAPI document is the single source of truth between backend and frontend.
The backend produces it from code; clients are generated from it; CI proves the three agree.

## Use when / do not use

Use when:

- Adding, changing or removing a REST endpoint, request/response DTO, query parameter or error shape.
- Setting up or updating springdoc, the spec export, or a generated TypeScript client.
- Reviewing a pull request that touches a controller, a DTO and frontend API calls together.
- Wiring contract checks (drift, breaking changes) into CI.

Do not use:

- For GraphQL, gRPC or WebSocket/STOMP messaging contracts.
- For internal service code with no HTTP surface (use `spring-boot-conventions`).
- For general controller or test style questions (use `spring-boot-conventions`, `spring-boot-testing`).
- For component and state code that merely consumes an existing client (use `angular-developer` or `vercel-react-best-practices`).

## Workflow

1. **Detect the setup.** Read `pom.xml`/`build.gradle(.kts)` for the Spring Boot and springdoc versions, and `package.json` for the client generator. Locate the committed spec (convention: `api/openapi.json` at the repo root) and the generated client folder. If none exists, set them up per `references/springdoc-setup.md` and `references/ts-client-generation.md`.
2. **Change the backend contract first.** Edit DTOs (Java records), controllers and `@Schema`/`@Operation` annotations following `references/conventions-checklist.md`. Errors go through `ProblemDetail` per `references/error-format-rfc9457.md`.
3. **Export the spec.** Either the build-time `springdoc-openapi-maven-plugin` (`mvn verify`) or a Spring Boot test that fetches `/v3/api-docs` and writes `api/openapi.json`. Keep output deterministic (`springdoc.writer-with-order-by-keys=true`).
4. **Review the spec diff.** `git diff api/openapi.json` must show exactly the intended change. Run `oasdiff breaking` against the base branch; a breaking change needs an explicit decision (new version, deprecation window, or coordinated release).
5. **Regenerate the client.** Run the project's generate script (e.g. `npm run api:generate`). Commit generated output; never hand-edit it. Fix call sites until `tsc`/`ng build` passes.
6. **Test both sides.** Backend: a slice or integration test per endpoint including the error case. Frontend: test against the generated types (mock at the HTTP layer, not the client).
7. **Enforce in CI.** Re-export spec and regenerate client, then `git diff --exit-code` on both paths; run `oasdiff breaking --fail-on ERR` against the base branch.
8. **Document the change** in the PR: endpoint list, breaking or not, migration notes for consumers.

## Rules

- Do treat `api/openapi.json` as a reviewed, committed artifact; every API PR shows its diff.
- Do generate clients from the committed file, not from a running server URL.
- Do commit generated client code and mark it read-only by convention (header comment, lint ignore).
- Do expose only DTO records at the controller boundary; never JPA entities.
- Do return errors as `application/problem+json` (RFC 9457) with a stable `type` URI per error kind.
- Do use camelCase JSON properties, plural kebab-case resource paths, and nouns not verbs.
- Do send timestamps as ISO-8601 UTC strings (`Instant` / `OffsetDateTime`, `format: date-time`); dates as `LocalDate` (`format: date`).
- Do model enums as string values (`@Schema(enumAsRef = true)`), and make clients tolerate unknown values.
- Do use one pagination envelope across the API (see `references/conventions-checklist.md`).
- Do mark required fields explicitly (`@Schema(requiredMode = REQUIRED)` or `@NotNull`) so generated types are not all optional.
- Do give every operation a stable, unique `operationId`; generated function names depend on it.
- Do run `oasdiff breaking` on every PR that changes the spec.
- Don't edit generated client files, or wrap them in hand-written duplicate types.
- Don't return `Map<String, Object>`, `Object` or `JsonNode` from endpoints; untyped schemas generate `unknown`.
- Don't expose `Page<T>`/`PageImpl` directly; its JSON is not stable.
- Don't use epoch numbers or zone-less `LocalDateTime` for instants.
- Don't use ordinal or numeric enums, or rename enum constants without a deprecation cycle.
- Don't remove or rename fields, make optional fields required, or tighten validation without a breaking-change decision.
- Don't put secrets, internal hostnames or stack traces in the spec, examples or Problem Details.
- Don't let the frontend build call `/v3/api-docs` of a live environment.
- Don't serve Swagger UI or `/v3/api-docs` publicly in production unless intended; gate with a profile or security rule.

## References

| File | Read when |
|---|---|
| [references/springdoc-setup.md](references/springdoc-setup.md) | Adding springdoc, configuring it, or exporting the spec at build time or from a test |
| [references/ts-client-generation.md](references/ts-client-generation.md) | Generating or updating the React/Next.js or Angular client, and wiring CI drift checks |
| [references/error-format-rfc9457.md](references/error-format-rfc9457.md) | Designing error responses, validation errors, or handling them in the client |
| [references/conventions-checklist.md](references/conventions-checklist.md) | Designing or reviewing an endpoint: naming, dates, enums, pagination, idempotency, versioning, breaking changes |
