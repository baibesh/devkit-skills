# Observability

Starters: `spring-boot-starter-actuator`; metrics backend such as `io.micrometer:micrometer-registry-prometheus`; tracing via `spring-boot-starter-opentelemetry` (Boot 4's OpenTelemetry starter, exporting OTLP).

## Actuator exposure

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus
  endpoint:
    health:
      probes:
        enabled: true          # /actuator/health/liveness and /readiness
      show-details: when-authorized
  info:
    git:
      mode: simple
```

- Expose the minimum. Never expose `env`, `configprops`, `heapdump`, `threaddump`, `loggers` or `shutdown` publicly; if ops needs them, put management on its own port (`management.server.port`) reachable only internally.
- Liveness must not depend on external systems (a DB outage should not restart pods). Readiness may include the DB: `management.endpoint.health.group.readiness.include=readinessState,db`.
- Add build/git info with the `spring-boot-maven-plugin` `build-info` goal and the git-commit-id plugin so `/actuator/info` shows the version.

## Custom health indicators

```java
@Component
class PaymentGatewayHealthIndicator implements HealthIndicator {
    private final PaymentClient client;
    PaymentGatewayHealthIndicator(PaymentClient client) { this.client = client; }

    @Override
    public Health health() {
        return client.ping() ? Health.up().build() : Health.down().withDetail("gateway", "unreachable").build();
    }
}
```

Keep health checks cheap and time-bounded. Add a health indicator for each new hard dependency. Package locations of health types moved in Boot 4's modularization; let the IDE resolve the import.

## Metrics with Micrometer

- HTTP server/client, JVM, Hikari, Tomcat and Spring Data repository metrics come for free.
- Business metrics: inject `MeterRegistry` and register counters/timers once (constructor), or use `@Observed`/`@Timed`/`@Counted` annotations.

```java
@Service
public class OrderService {
    private final Counter ordersPlaced;

    public OrderService(MeterRegistry registry /*, ... */) {
        this.ordersPlaced = Counter.builder("orders.placed")
                .description("Orders successfully placed")
                .register(registry);
    }
}
```

- Name metrics in dot.case (`orders.placed`); the Prometheus registry converts to `orders_placed_total`.
- Tags must be low-cardinality (status, region). Never tag with user IDs, order IDs, emails or raw URLs.
- Common tags for all metrics: `management.metrics.tags.application=${spring.application.name}`.
- Histograms/percentiles only where needed: `management.metrics.distribution.percentiles-histogram.http.server.requests=true`.

## Observation API and tracing

- Spring instruments MVC, `RestClient`, JDBC (via datasource observation if configured), messaging with the Micrometer Observation API; one observation produces both a metric and a span.
- Custom operations: `@Observed(name = "orders.checkout")` on a bean method (requires the observation aspect, which Boot auto-configures when `spring-boot-starter-aspectj` / AspectJ is present; verify for your version), or programmatically:

```java
Observation.createNotStarted("orders.checkout", observationRegistry)
        .lowCardinalityKeyValue("payment.method", method.name())
        .observe(() -> checkout(order));
```

- Sampling: `management.tracing.sampling.probability=0.1` in production (default 0.1); 1.0 locally.
- The OTLP exporter endpoint property was reorganized in Boot 4; look up the current `management.*otlp*` keys in the Boot reference instead of copying Boot 3 snippets.
- Propagation: W3C `traceparent` by default. Outbound calls are traced only if the client was built from the auto-configured `RestClient.Builder`/`WebClient.Builder`.

## Structured logging

```yaml
logging:
  structured:
    format:
      console: ecs        # or logstash / gelf
  level:
    root: INFO
    com.acme: INFO
```

- Use structured JSON outside local dev; keep plain text locally (enable via profile or env var `LOGGING_STRUCTURED_FORMAT_CONSOLE=ecs`).
- Trace and span IDs are added to the MDC automatically when tracing is on, so logs correlate with traces.
- Add context with MDC or SLF4J 2 fluent API: `log.atInfo().addKeyValue("orderId", id).log("Order placed")`.
- Log once per failure, at the boundary that handles it, with the exception as the last argument.
- Levels: ERROR = needs a human; WARN = degraded but handled; INFO = business events and lifecycle; DEBUG = diagnostics, off in production.
- Never log secrets, tokens, passwords, full card numbers or whole request/response bodies.
