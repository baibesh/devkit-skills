# Security review checklist

Mapped to OWASP Top 10 (2021 categories; check whether the team tracks a newer edition and map accordingly).
Any confirmed item here is normally a Blocker or Major finding.

## A01 Broken access control

- [ ] Every new endpoint, Server Action and Route Handler requires authentication unless explicitly public.
- [ ] Object-level authorization: lookups by ID check ownership/tenant (`findByIdAndOwnerId`, `@PreAuthorize("@orderAuth.canRead(#id, authentication)")`), not only "is logged in" (IDOR).
- [ ] Function-level authorization: admin operations check roles server-side; hidden buttons are not protection.
- [ ] Multi-tenant queries always filter by tenant; no tenant ID taken from the request body when it is in the token.
- [ ] Mass assignment: request DTOs exclude `id`, `ownerId`, `role`, `status` transitions the user must not control.
- [ ] CORS: no `allowedOrigins("*")` with credentials; origins listed per environment.
- [ ] CSRF: enabled for cookie-based sessions; disabled only for stateless bearer-token APIs.

## A02 Cryptographic failures

- [ ] Passwords hashed with `PasswordEncoder` (bcrypt/argon2 via `DelegatingPasswordEncoder`); never reversible encryption or plain hashes.
- [ ] No custom crypto; keys and salts not hard-coded.
- [ ] Sensitive data not in URLs, logs, error messages, analytics or client storage.
- [ ] TLS assumed for all external calls; no disabled certificate validation (`TrustAllStrategy`, `rejectUnauthorized: false`).
- [ ] Random tokens use `SecureRandom` / `crypto.getRandomValues`, not `Math.random` or `Random`.

## A03 Injection

- [ ] SQL/JPQL: parameters bound (`:name`, Spring Data derived queries, Criteria API); no string concatenation with user input, including `ORDER BY` and column names (whitelist sort fields).
- [ ] Native queries and `JdbcClient` calls use parameters.
- [ ] No user input in shell commands (`ProcessBuilder`), LDAP filters, XPath, or SpEL expressions evaluated at runtime.
- [ ] Log injection: user input with newlines not written raw into logs used for auditing.
- [ ] XSS: frontend renders user content as text; `innerHTML`, `dangerouslySetInnerHTML`, `bypassSecurityTrust*` only with sanitized content; Markdown renderers sanitize.
- [ ] Template engines (Thymeleaf, email templates) use escaped output (`th:text`, not `th:utext`) for user data.

## A04 Insecure design

- [ ] Business limits enforced server-side: quantities, amounts, rate of actions, state transitions.
- [ ] Sensitive flows (password reset, email change, payment) have rate limits, expiry and single-use tokens.
- [ ] Idempotency on payment-like operations to prevent double execution.

## A05 Security misconfiguration

- [ ] Actuator: only `health`/`info` exposed publicly; others behind auth or a management port.
- [ ] Swagger UI and `/v3/api-docs` not public in production unless intended.
- [ ] Error responses do not leak stack traces, SQL or framework versions.
- [ ] Security headers in place (CSP, `X-Content-Type-Options`, frame options) per project policy; Next.js `headers()` or reverse proxy.
- [ ] Debug flags, `ddl-auto=update/create`, H2 console and dev profiles not enabled in prod configs.
- [ ] XML parsers disable external entities (XXE).

## A06 Vulnerable and outdated components

- [ ] New dependencies are maintained, from the expected registry, version-pinned through the lockfile/BOM.
- [ ] No dependency added with known critical CVEs (`npm audit`, OWASP Dependency-Check, Dependabot/Renovate alerts).
- [ ] Lockfile changes match the `package.json`/`pom.xml` change; unexpected transitive churn questioned.

## A07 Identification and authentication failures

- [ ] JWT validation: signature, issuer, audience, expiry checked (Spring Security resource server config), `alg: none` rejected.
- [ ] Session cookies `HttpOnly`, `Secure`, `SameSite`; session fixation protection kept.
- [ ] Login and token endpoints rate-limited; generic error messages (no user enumeration).
- [ ] Logout invalidates server-side session/refresh token.

## A08 Software and data integrity failures

- [ ] No Java deserialization of untrusted data; Jackson default typing not enabled globally (`activateDefaultTyping`).
- [ ] Webhooks verify signatures and timestamps.
- [ ] CI changes: no secrets exposed to untrusted PR workflows (`pull_request_target` with checkout of PR code), actions pinned.

## A09 Security logging and monitoring failures

- [ ] Security-relevant events logged (login failure, permission denied, admin actions) without sensitive payloads.
- [ ] Audit trails for data changes where required by the domain.

## A10 Server-side request forgery

- [ ] Server-side fetches of user-supplied URLs (webhooks, image import, link previews, Next.js image remote patterns) restricted by allowlist; internal ranges and metadata endpoints blocked; redirects re-validated.

## Input validation (all layers)

- [ ] Bean Validation on every request DTO and parameter; size limits on strings, collections and uploads.
- [ ] File uploads: size limit (`spring.servlet.multipart.max-file-size`), content-type and magic-byte checks, generated storage names, no path from user input (path traversal), served with `Content-Disposition: attachment` when untrusted.
- [ ] Redirect targets after login/actions validated against an allowlist (open redirect).
- [ ] Regexes on user input checked for catastrophic backtracking (ReDoS).

## Secrets

- [ ] No credentials, tokens, private keys or connection strings with passwords in the diff, including tests, fixtures, `.env` files, Docker/CI configs and comments.
- [ ] `.env*` files with real values gitignored; examples use placeholders.
- [ ] If a secret was committed: report location (not value), require rotation; removing it in a later commit is not enough.
- [ ] Frontend env variables exposed to the browser (`NEXT_PUBLIC_*`, Angular `environment.ts`) contain only public values.
