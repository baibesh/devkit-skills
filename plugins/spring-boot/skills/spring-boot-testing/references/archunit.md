# Architecture tests with ArchUnit

Encode the `spring-boot-conventions` layout as fast unit tests so violations fail the build instead of a review.

Dependency (test scope): `com.tngtech.archunit:archunit-junit5` (not managed by the Boot BOM; pin a current 1.x version).

## Base setup

```java
@AnalyzeClasses(packages = "com.acme", importOptions = ImportOption.DoNotIncludeTests.class)
class ArchitectureTest {

    @ArchTest
    static final ArchRule featuresAreFreeOfCycles =
            slices().matching("com.acme.(*)..").should().beFreeOfCycles();

    @ArchTest
    static final ArchRule noFieldInjection =
            noFields().should().beAnnotatedWith(Autowired.class)
                    .because("use constructor injection");

    @ArchTest
    static final ArchRule controllersDoNotUseRepositories =
            noClasses().that().resideInAPackage("..api..")
                    .should().dependOnClassesThat().areAssignableTo(Repository.class)
                    .because("controllers go through the feature service");

    @ArchTest
    static final ArchRule noTransactionalControllers =
            noClasses().that().resideInAPackage("..api..")
                    .should().beAnnotatedWith(Transactional.class);

    @ArchTest
    static final ArchRule noTransactionalControllerMethods =
            noMethods().that().areDeclaredInClassesThat().resideInAPackage("..api..")
                    .should().beAnnotatedWith(Transactional.class);
}
```

Imports: `com.tngtech.archunit.junit.*`, `com.tngtech.archunit.lang.ArchRule`, `com.tngtech.archunit.core.importer.ImportOption`, and static `com.tngtech.archunit.lang.syntax.ArchRuleDefinition.*`, `com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices`. `Repository` is `org.springframework.data.repository.Repository`.

`GeneralCodingRules.NO_CLASSES_SHOULD_USE_FIELD_INJECTION` is a ready-made alternative to the `noFieldInjection` rule.

## Feature-internal layering

```java
@ArchTest
static final ArchRule layering = layeredArchitecture()
        .consideringOnlyDependenciesInLayers()
        .layer("Api").definedBy("..api..")
        .layer("Domain").definedBy("..domain..")
        .layer("Infra").definedBy("..infra..")
        .whereLayer("Api").mayNotBeAccessedByAnyLayer()
        .whereLayer("Infra").mayOnlyBeAccessedByLayers("Domain", "Api")
        .whereLayer("Domain").mayOnlyBeAccessedByLayers("Api", "Infra");
```

(`layeredArchitecture` from `com.tngtech.archunit.library.Architectures`.) Adjust to the project's actual split; the feature service in the feature root is outside these layers.

## Cross-feature boundaries

Features may only use each other's public entry points (service, DTO/event records), never internals:

```java
@ArchTest
static final ArchRule featuresDoNotReachIntoEachOthersInternals =
        noClasses().that().resideInAPackage("com.acme.orders..")
                .should().dependOnClassesThat().resideInAnyPackage(
                        "com.acme.customers.infra..", "com.acme.customers.domain..");
```

For more than a few features, generate the rule per feature, or switch to Spring Modulith.

## Coding rules worth enforcing

```java
@ArchTest
static final ArchRule noJavaUtilLogging = GeneralCodingRules.NO_CLASSES_SHOULD_USE_JAVA_UTIL_LOGGING;

@ArchTest
static final ArchRule noStdStreams = GeneralCodingRules.NO_CLASSES_SHOULD_ACCESS_STANDARD_STREAMS;

@ArchTest
static final ArchRule noGenericExceptions = GeneralCodingRules.NO_CLASSES_SHOULD_THROW_GENERIC_EXCEPTIONS;

@ArchTest
static final ArchRule entitiesStayInDomain =
        classes().that().areAnnotatedWith(Entity.class)
                .should().resideInAPackage("..domain..");
```

- `jakarta.persistence.Entity`, not `javax`.
- Keep rules few and meaningful. Each one should map to a convention a reviewer would otherwise flag.

## Adopting on an existing codebase

- Freeze current violations so only new ones fail: `FreezingArchRule.freeze(rule)`, with the violation store committed (configure `archunit.properties`: `freeze.store.default.path=src/test/resources/archunit_store`, `freeze.store.default.allowStoreCreation=true` on first run only).
- Shrink the frozen store over time; never add to it by hand.

## Spring Modulith alternative

If the project uses Spring Modulith (direct subpackages of the root package are modules):

```java
class ModularityTest {
    static final ApplicationModules modules = ApplicationModules.of(Application.class);

    @Test
    void shouldRespectModuleBoundaries() {
        modules.verify();
    }

    @Test
    void writeDocumentation() {
        new Documenter(modules).writeDocumentation(); // optional: C4/PlantUML diagrams
    }
}
```

- `verify()` fails on cycles between modules and on access to another module's internal packages.
- Can be combined with ArchUnit for intra-module and coding rules.
- Requires `spring-modulith-starter-test`; use the Modulith 2.x line for Boot 4.
