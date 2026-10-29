# Angular testing with the Vitest builder

Angular 21 made Vitest (through `@angular/build:unit-test`) the default runner for `ng new` and generates zoneless apps by default; Angular 22 keeps both. Karma remains supported via `runner: "karma"`. For component, signal, and DI API details, defer to the `angular-developer` skill; this file covers test setup and patterns.

## Builder config

```jsonc
// angular.json -> projects.<app>.architect.test
{
  "builder": "@angular/build:unit-test",
  "options": {
    "tsConfig": "tsconfig.spec.json",
    "runner": "vitest",                       // default; "karma" for legacy suites
    "include": ["**/*.spec.ts"],
    "setupFiles": ["src/test-setup.ts"],
    "providersFile": "src/test-providers.ts",
    "coverageInclude": ["src/app/**/*.ts"],
    "coverageExclude": ["**/*.spec.ts", "**/*.routes.ts", "src/environments/**"],
    "coverageThresholds": { "statements": 80, "branches": 75, "functions": 80, "lines": 80 },
    "coverageReporters": ["text-summary", "html", "lcov"]
  },
  "configurations": {
    "ci": { "watch": false, "coverage": true, "reporters": ["default", "junit"] },
    "browser": { "browsers": ["chromiumHeadless"] }
  }
}
```

- `ng test` watches in a TTY and runs once when `CI=true`. Locally: `ng test --no-watch`. Coverage: `ng test --coverage`.
- Default environment is Node + jsdom (`jsdom` installed by `ng new`). For real-browser runs set `browsers` (`chromium`, `firefox`, `webkit`, with `Headless` suffix) and install `@vitest/browser-playwright` + `playwright`.
- `providersFile` default-exports an array of providers applied to every TestBed (e.g. `provideHttpClient()`, `provideHttpClientTesting()`, `provideZonelessChangeDetection()` if needed). Keep it minimal; prefer per-test providers.
- `runnerConfig: true` (or a path) loads `vitest-base.config.*` for advanced Vitest options; generate it with `ng generate config vitest`. The Angular team does not support third-party plugins there, so add only what you need.
- Setup files must also be listed in `tsconfig.spec.json` `files`/`include`.
- Test tsconfig types: `"types": ["vitest/globals"]` if the project uses globals (generated projects do); otherwise import from `vitest`.

## Migrating from Karma/Jasmine

1. `ng generate refactor-jasmine-vitest` (Angular CLI schematic, present in v22) rewrites common Jasmine APIs; review the diff.
2. Change the test builder to `@angular/build:unit-test`, remove `karma.conf.js`, `src/test.ts`, and Karma/Jasmine packages.
3. Replace `jasmine.createSpyObj` with `vi.fn()` objects, `spyOn(x, 'm').and.returnValue(v)` with `vi.spyOn(x, 'm').mockReturnValue(v)`, `jasmine.clock()` with `vi.useFakeTimers()`.
4. Replace `fakeAsync`/`tick`/`flush` (Zone.js based) with fake timers + `await fixture.whenStable()`; remove `waitForAsync`.
5. Run the suite, fix tests that relied on Zone-triggered change detection by awaiting stability or setting signals/inputs explicitly.

## Component test pattern (zoneless)

```ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestbedHarnessEnvironment } from '@angular/cdk/testing/testbed';
import { MatButtonHarness } from '@angular/material/button/testing';
import { InvoiceList } from './invoice-list';

describe('InvoiceList', () => {
  let fixture: ComponentFixture<InvoiceList>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InvoiceList],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(InvoiceList);
    fixture.componentRef.setInput('status', 'open');   // signal or @Input
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('renders loaded invoices', async () => {
    fixture.detectChanges();
    http.expectOne('/api/invoices?status=open').flush([{ id: '1', number: 'INV-1' }]);
    await fixture.whenStable();

    expect(fixture.nativeElement.textContent).toContain('INV-1');
  });

  it('reloads on refresh click', async () => {
    const loader = TestbedHarnessEnvironment.loader(fixture);
    const refresh = await loader.getHarness(MatButtonHarness.with({ text: 'Refresh' }));
    await refresh.click();                               // harness awaits stability
    http.expectOne((r) => r.url === '/api/invoices');
  });
});
```

- Use `fixture.componentRef.setInput()` for inputs (works with signal `input()`), never assign component fields directly.
- After changing state, `await fixture.whenStable()` (zoneless) instead of relying on `detectChanges` alone. `fixture.autoDetectChanges()` is fine for interaction-heavy tests.
- `TestBed.tick()` flushes pending effects and change detection synchronously when you need it.
- Prefer querying the DOM by role/text. `@testing-library/angular` works with Vitest too if the team prefers Testing Library queries (`render`, `screen`, `userEvent`).

## Component harnesses

- Use the CDK/Material harnesses (`MatInputHarness`, `MatSelectHarness`, `MatDialogHarness` via `TestbedHarnessEnvironment.documentRootLoader(fixture)` for overlays).
- Write a harness for your own reusable components (`ComponentHarness` subclass with `static hostSelector`) so tests and E2E-like integration tests don't depend on internal DOM.
- Harness methods are async and wait for stability; `await` each call.

```ts
export class InvoiceRowHarness extends ComponentHarness {
  static hostSelector = 'app-invoice-row';
  private number = this.locatorFor('.number');
  async getNumber() { return (await this.number()).text(); }
}
```

## Services, signals, resources

- Services: `TestBed.inject(MyService)` with `provideHttpClientTesting()`; test public methods and emitted values.
- Signals/computed: set inputs, read the signal value; no change detection needed for pure signal logic.
- `effect()`: trigger with `TestBed.tick()` or `await fixture.whenStable()`.
- `httpResource`/`resource`: flush the request through `HttpTestingController` (or MSW), then `await fixture.whenStable()` and assert on `value()`, `isLoading()`, `error()`.
- RxJS: use `firstValueFrom` / `lastValueFrom` with `await`; marble tests only for complex operators.
- Router: `provideRouter(routes)` + `RouterTestingHarness.create()` then `await harness.navigateByUrl('/x', ComponentType)`.

## HTTP mocking choice

- `HttpTestingController`: precise request assertions for a single service or component; default for Angular unit tests.
- MSW (`msw/node` in jsdom mode, `msw/browser` in browser mode): when tests should not know about `HttpClient` internals or you share handlers with Storybook/dev. Use `provideHttpClient()` (not the testing backend) so real requests reach MSW; `msw/node` intercepts both XHR and `fetch` (`withFetch()`). Don't combine both in one test.

## Timers and async

- Use `vi.useFakeTimers()` + `await vi.advanceTimersByTimeAsync(ms)` for debounce/polling; then `await fixture.whenStable()`.
- `fakeAsync` requires Zone.js; zoneless Vitest projects cannot use it. Zone-based legacy projects that keep `zone.js` should plan to remove these utilities.

## CI

```sh
ng test --configuration ci            # single run, coverage, junit
```

- Thresholds in `coverageThresholds` fail the build; keep them per project in angular.json.
- Upload `coverage/<project>/lcov.info` and the JUnit file. Check the report path in the builder output; reporter defaults may differ from plain Vitest.
