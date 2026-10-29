# Error format: RFC 9457 Problem Details

Every non-2xx response body is `application/problem+json` (RFC 9457, which obsoletes RFC 7807).
Spring Framework provides `ProblemDetail`, `ErrorResponse` and `ErrorResponseException`.

## Shape

```json
{
  "type": "https://api.example.com/problems/order-not-found",
  "title": "Order not found",
  "status": 404,
  "detail": "Order 42 does not exist",
  "instance": "/orders/42",
  "code": "ORDER_NOT_FOUND",
  "traceId": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

- `type`: stable URI per error kind; the client branches on `type` (or `code`), never on `detail` text. `about:blank` only for plain HTTP errors.
- `title`: short, human-readable, same for every occurrence of the type.
- `status`: mirrors the HTTP status.
- `detail`: occurrence-specific, safe to show to users; no stack traces, SQL, class names or internal IDs.
- Extension members (`code`, `traceId`, `errors`) are allowed; document them in the spec.

## Enabling in Spring Boot

```yaml
spring:
  mvc:
    problemdetails:
      enabled: true   # Spring MVC built-in exceptions render as ProblemDetail
```

Central handler extending `ResponseEntityExceptionHandler` so framework exceptions (400, 405, 415, 406) stay consistent:

```java
@RestControllerAdvice
class ApiExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(OrderNotFoundException.class)
    ProblemDetail notFound(OrderNotFoundException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        pd.setType(URI.create("https://api.example.com/problems/order-not-found"));
        pd.setTitle("Order not found");
        pd.setProperty("code", "ORDER_NOT_FOUND");
        return pd;
    }

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        ProblemDetail pd = ex.getBody();
        pd.setType(URI.create("https://api.example.com/problems/validation"));
        pd.setProperty("errors", ex.getFieldErrors().stream()
            .map(e -> new FieldViolation(e.getField(), e.getCode(), e.getDefaultMessage()))
            .toList());
        return handleExceptionInternal(ex, pd, headers, status, request);
    }

    @ExceptionHandler(Exception.class)
    ProblemDetail unexpected(Exception ex) {
        log.error("Unhandled error", ex);   // full detail in logs only
        return ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, "Unexpected error");
    }
}

record FieldViolation(String field, String code, String message) {}
```

Alternatively, domain exceptions extend `ErrorResponseException` and carry their own `ProblemDetail`.
Pick one approach per project; detect what exists before adding a second.

## Status code guide

| Situation | Status | type suffix |
| --- | --- | --- |
| Malformed JSON, wrong types, failed Bean Validation | 400 | `validation` / `malformed-request` |
| Missing or invalid credentials | 401 | `unauthenticated` |
| Authenticated but not allowed | 403 | `forbidden` |
| Resource missing, or hidden for authorization reasons | 404 | `<resource>-not-found` |
| Version conflict (optimistic lock, stale `If-Match`), duplicate unique key | 409 / 412 | `conflict` / `precondition-failed` |
| Business rule violation on valid input | 422 | `<rule-name>` |
| Rate limit | 429 (+ `Retry-After`) | `rate-limited` |
| Unexpected failure | 500 | `about:blank` or `internal` |

Choose 400 or 422 for business rules once, write it down, and apply it consistently.

## Documenting in OpenAPI

- Register a `ProblemDetail` schema (springdoc does for `ProblemDetail` return types) and the extension fields.
- Every operation lists its error responses with content type `application/problem+json`. An `OperationCustomizer` can add the common ones (400, 401, 403, 500) to all operations.
- Generated clients then type `error` correctly (openapi-fetch) or allow typed parsing of `HttpErrorResponse.error` (Angular).

## Client handling

React/Next.js (openapi-fetch):

```ts
const { data, error, response } = await api.POST("/orders", { body });
if (error) {
  if (error.type?.endsWith("/validation")) return mapFieldErrors(error.errors);
  throw new ApiError(response.status, error);
}
```

Angular: one functional interceptor maps `HttpErrorResponse` with `application/problem+json` to an app-level `ApiProblem` and leaves field-level mapping to the form.

Rules for both:

- Map `errors[].field` back to form controls; show `detail` for non-field problems.
- Treat unknown `type` values as generic errors; never crash on a new type.
- Log `traceId` and show it in support-facing error UI.
- Do not retry 4xx except 408/429 (respect `Retry-After`); retry idempotent requests on 502/503/504 with backoff.

## Security notes

- Same 404 for "does not exist" and "not yours" when existence itself is sensitive.
- No echoing of raw input into `detail` without encoding; clients must render it as text, not HTML.
- `server.error.include-stacktrace` and `include-message` stay at their safe defaults in production.
