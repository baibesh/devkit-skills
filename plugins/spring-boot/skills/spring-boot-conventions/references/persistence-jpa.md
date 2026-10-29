# Persistence with Spring Data JPA

Boot 4 ships Hibernate ORM 7 and Jakarta Persistence 3.2. Everything is `jakarta.persistence.*`.

## Baseline settings

```yaml
spring:
  jpa:
    open-in-view: false          # no lazy loading from controllers / serializers
    hibernate:
      ddl-auto: validate         # Flyway owns the schema
    properties:
      hibernate:
        jdbc.time_zone: UTC
        default_batch_fetch_size: 50
  flyway:
    locations: classpath:db/migration
```

Dependencies: `spring-boot-starter-data-jpa`, `spring-boot-starter-flyway` (Boot 4 needs the starter, not just `flyway-core`), plus `flyway-database-postgresql` for Postgres.

## Entity design

```java
@Entity
@Table(name = "orders")
@EntityListeners(AuditingEntityListener.class)
public class Order {

    @Id
    private UUID id;

    @Column(nullable = false)
    private String customerId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private OrderStatus status;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderLine> lines = new ArrayList<>();

    @Column(nullable = false)
    private BigDecimal total = BigDecimal.ZERO;

    @Version
    private @Nullable Long version; // wrapper: null tells Spring Data the entity is new

    @CreatedDate
    private Instant createdAt;

    @LastModifiedDate
    private Instant updatedAt;

    protected Order() {} // for JPA

    public Order(String customerId) {
        this.id = UUID.randomUUID();
        this.customerId = customerId;
        this.status = OrderStatus.NEW;
    }

    public void addLine(String sku, int quantity, BigDecimal price) {
        lines.add(new OrderLine(this, sku, quantity, price));
        total = total.add(price.multiply(BigDecimal.valueOf(quantity)));
    }

    public void cancel() {
        if (status == OrderStatus.SHIPPED) {
            throw new BusinessRuleException("order-already-shipped", "Shipped orders cannot be cancelled");
        }
        status = OrderStatus.CANCELLED;
    }

    // getters only; no public setters for invariants
}
```

- Entities are classes, never records (JPA needs mutability and proxies). Records are for DTOs and projections.
- `protected` no-arg constructor; a public constructor that establishes invariants; behaviour methods instead of setters.
- `@Enumerated(EnumType.STRING)`, never ordinal.
- `@Version` for optimistic locking on aggregates that are edited concurrently.
- IDs: app-assigned `UUID` (shown above; keeps `equals` stable before persist) or a DB sequence (`@GeneratedValue(strategy = SEQUENCE)`). Avoid `IDENTITY` when you need JDBC batch inserts.
- With app-assigned IDs, Spring Data decides "new vs merge" from a wrapper-typed `@Version` (null = new). Without it, `save()` issues a pointless `select` before insert; implement `Persistable<UUID>` if there is no version field.
- `equals`/`hashCode`: base on the ID only if it is assigned at construction; otherwise use identity (do not override). Never include lazy associations. No Lombok `@Data` on entities.
- Associations: `@ManyToOne(fetch = FetchType.LAZY)` always (the JPA default is EAGER). Prefer unidirectional or `mappedBy` on the parent; avoid `@ManyToMany` (model the join table as an entity).
- Do not map associations across feature boundaries; store the other aggregate's ID.

## Repositories

```java
interface OrderRepository extends JpaRepository<Order, UUID> {

    @EntityGraph(attributePaths = "lines")
    Optional<Order> findWithLinesById(UUID id);

    Page<OrderSummary> findByStatus(OrderStatus status, Pageable pageable);

    @Query("""
           select new com.acme.orders.api.OrderTotals(o.customerId, count(o), sum(o.total))
           from Order o where o.createdAt >= :since group by o.customerId
           """)
    List<OrderTotals> totalsSince(Instant since);
}

public record OrderSummary(UUID id, OrderStatus status, Instant createdAt) {}
```

- Derived queries for simple filters; `@Query` (JPQL text block) when the name gets long.
- Return `Optional` for single lookups; throw a domain `NotFoundException` in the service (`orElseThrow`).
- Read paths return projections (records or interfaces), not entities. Records work as Spring Data DTO projections when the constructor parameters match property names.
- Modifying queries: `@Modifying(clearAutomatically = true)` and call them inside a service transaction.
- Dynamic filters: `Specification` or Querydsl; avoid string-concatenated JPQL.

## N+1 and fetching

- Symptom: one query for parents, then one per child. Detect with `spring.jpa.properties.hibernate.generate_statistics=true` locally or a query-count assertion in tests.
- Fixes, in order of preference:
  1. A projection that selects exactly the columns needed.
  2. `@EntityGraph(attributePaths = ...)` on the repository method for the use case.
  3. `join fetch` in JPQL (do not combine collection fetch joins with pagination; Hibernate paginates in memory).
  4. `hibernate.default_batch_fetch_size` as a safety net.
- With `open-in-view=false`, a `LazyInitializationException` means the service did not load what the response needs. Fix the query, not the setting.

## Transactions

- `@Transactional` on public service methods only. Class-level `@Transactional(readOnly = true)` plus method-level `@Transactional` for writes is a good default.
- Self-invocation bypasses the proxy: calling a `@Transactional` method from the same class does not start a transaction.
- Keep transactions short: no remote HTTP calls or message sends inside. Publish events and handle them with `@TransactionalEventListener(phase = AFTER_COMMIT)`.
- Checked exceptions do not roll back by default; domain exceptions should be unchecked.
- Dirty checking saves managed entities on commit; calling `save()` on an already-managed entity is unnecessary.

## Auditing

```java
@Configuration(proxyBeanMethods = false)
@EnableJpaAuditing
class JpaConfig {
    @Bean
    AuditorAware<String> auditorAware() {
        return () -> Optional.ofNullable(SecurityContextHolder.getContext().getAuthentication())
                .map(Authentication::getName);
    }
}
```

`@CreatedDate`, `@LastModifiedDate`, `@CreatedBy`, `@LastModifiedBy` plus `@EntityListeners(AuditingEntityListener.class)` on the entity (or a `@MappedSuperclass`).

## Flyway

- Location: `src/main/resources/db/migration`, names `V<version>__<description>.sql` (two underscores). Use sequential integers or timestamps (`V20261029_1200__add_status.sql`) consistently.
- Never edit an applied migration; add a new one. Repeatable `R__` scripts only for views/functions.
- Backward-compatible changes for zero-downtime deploys: add nullable column, deploy, backfill, then add constraint in a later migration.
- Create indexes for every foreign key and every column used in `where`/`order by` of hot queries. On Postgres, large-table indexes go `CREATE INDEX CONCURRENTLY` in a migration that disables the transaction (Flyway script config `executeInTransaction=false`).
- Hibernate validates against the migrated schema (`ddl-auto=validate`), so a mismatch fails startup, which is what you want.
