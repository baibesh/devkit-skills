# REST controllers

Contract decisions (resource naming, status codes, OpenAPI) belong to the `api-contract` skill. This file covers the Spring implementation.

## Controller shape

```java
@RestController
@RequestMapping("/api/orders")
class OrderController {

    private final OrderService orders;

    OrderController(OrderService orders) {
        this.orders = orders;
    }

    @GetMapping("/{id}")
    OrderResponse get(@PathVariable UUID id) {
        return orders.get(id); // throws OrderNotFoundException -> 404 problem
    }

    @PostMapping
    ResponseEntity<OrderResponse> create(@Valid @RequestBody CreateOrderRequest request,
                                         UriComponentsBuilder uri) {
        OrderResponse created = orders.create(request);
        URI location = uri.path("/api/orders/{id}").build(created.id());
        return ResponseEntity.created(location).body(created);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void cancel(@PathVariable UUID id) {
        orders.cancel(id);
    }
}
```

- Controllers are thin: bind, validate, delegate, map status. No repositories, no `@Transactional`, no business rules.
- Return the DTO directly for 200; use `ResponseEntity` only when headers or a non-default status matter.
- Use `UUID` or a typed ID record in paths, not raw database sequences, when IDs are public.

## DTO records and validation

```java
public record CreateOrderRequest(
        @NotBlank String customerId,
        @NotEmpty @Size(max = 100) List<@Valid LineItemRequest> items,
        @Nullable @Size(max = 500) String note) {}

public record LineItemRequest(@NotBlank String sku, @Positive int quantity) {}

public record OrderResponse(UUID id, String customerId, OrderStatus status,
                            BigDecimal total, Instant createdAt) {
    static OrderResponse from(Order order) {
        return new OrderResponse(order.getId(), order.getCustomerId(), order.getStatus(),
                order.getTotal(), order.getCreatedAt());
    }
}
```

- `@Valid` on `@RequestBody`; constraints on record components. Nested collections need `List<@Valid T>`.
- Path/query parameter constraints (`@Min` on `@RequestParam`) are validated by Spring MVC's built-in method validation since Framework 6.1; failures raise `HandlerMethodValidationException`.
- Cross-field rules: a custom class-level constraint, or validate in the service and throw a domain exception.
- Requires `spring-boot-starter-validation`.

## Problem Details (RFC 9457)

One global advice, extending `ResponseEntityExceptionHandler` so Spring's own exceptions (400 binding, 405, 415, 406 ...) already render as `application/problem+json`.

```java
@RestControllerAdvice
class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(NotFoundException.class)
    ProblemDetail handleNotFound(NotFoundException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        pd.setType(URI.create("https://errors.acme.com/not-found"));
        pd.setTitle("Resource not found");
        return pd;
    }

    @ExceptionHandler(BusinessRuleException.class)
    ProblemDetail handleRule(BusinessRuleException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_ENTITY, ex.getMessage());
        pd.setType(URI.create("https://errors.acme.com/" + ex.code()));
        pd.setProperty("code", ex.code());
        return pd;
    }

    @Override
    protected @Nullable ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers,
            HttpStatusCode status, WebRequest request) {
        ProblemDetail pd = ex.getBody();
        pd.setProperty("errors", ex.getBindingResult().getFieldErrors().stream()
                .map(fe -> Map.of("field", fe.getField(),
                        "message", String.valueOf(fe.getDefaultMessage())))
                .toList());
        return handleExceptionInternal(ex, pd, headers, status, request);
    }
}
```

Response shape:

```json
{
  "type": "https://errors.acme.com/not-found",
  "title": "Resource not found",
  "status": 404,
  "detail": "Order 3f2c... not found",
  "instance": "/api/orders/3f2c..."
}
```

- `type` is a stable URI per error kind (clients switch on it); `title` is constant per type; `detail` is human-readable and instance-specific.
- Extra fields via `setProperty` (`code`, `errors`, `traceId`). Never include stack traces or SQL.
- Domain exceptions can instead extend `ErrorResponseException` to carry their own `ProblemDetail`; pick one style per service.
- `spring.mvc.problemdetails.enabled=true` registers a default handler only when you have no advice of your own; with the advice above it is redundant but harmless.
- Unexpected exceptions: add an `@ExceptionHandler(Exception.class)` returning a generic 500 problem and log the exception with its stack trace once.

## Pagination

```java
@GetMapping
PageResponse<OrderSummary> list(@RequestParam(required = false) @Nullable OrderStatus status,
                                @PageableDefault(size = 20, sort = "createdAt",
                                        direction = Sort.Direction.DESC) Pageable pageable) {
    return PageResponse.from(orders.search(status, pageable));
}

public record PageResponse<T>(List<T> content, int page, int size, long totalElements, int totalPages) {
    public static <T> PageResponse<T> from(Page<T> p) {
        return new PageResponse<>(p.getContent(), p.getNumber(), p.getSize(),
                p.getTotalElements(), p.getTotalPages());
    }
}
```

- Never serialize `Page`/`PageImpl` directly; its JSON is not a stable contract. Use your own record (above) or Spring Data's `PagedModel` via `@EnableSpringDataWebSupport(pageSerializationMode = VIA_DTO)`.
- Cap page size: `spring.data.web.pageable.max-page-size=100`.
- Whitelist sortable properties; unknown sort fields otherwise surface as 500s from the persistence layer.
- For large or fast-moving tables prefer keyset pagination (Spring Data `ScrollPosition`/`Window`).

## Versioning

- Default: URI prefix (`/api/v1/...`) for breaking changes only; additive changes need no new version.
- Spring Framework 7 adds first-class API versioning: `@GetMapping(path = "/{id}", version = "2")` plus a resolution strategy configured with `spring.mvc.apiversion.*` properties (for example `spring.mvc.apiversion.use.header=API-Version`) or `WebMvcConfigurer#configureApiVersioning`. Use it when the team picks header or media-type versioning; check the exact property names in the Boot reference for your version.
- Do not mix both strategies in one service.

## Misc

- JSON naming: camelCase, ISO-8601 timestamps (Boot's default with Jackson 3 writes dates as ISO strings).
- Use `@JsonInclude(NON_NULL)` sparingly; explicit `null` is often clearer for clients.
- File uploads: `MultipartFile` with `spring.servlet.multipart.max-file-size` set explicitly.
- Long-running work: return 202 with a status resource rather than blocking a request thread.
