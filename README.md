# devkit-skills

[![validate](https://github.com/baibesh/devkit-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/baibesh/devkit-skills/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Curated agent skills for fullstack teams building Angular, React and Next.js frontends on top of Java / Spring Boot backends.

Official framework skills are referenced straight from their upstream repositories, so they stay version-matched. What the frameworks do not cover (Spring Boot conventions, testing, the OpenAPI contract between backend and frontend, code review) is maintained here.

Works with Claude Code (plugin marketplace) and with any agent supported by [`npx skills`](https://github.com/vercel-labs/skills): Codex, Cursor, Copilot, Gemini CLI.

## What's inside

| Plugin | Skills | Source |
|---|---|---|
| `angular` | `angular-developer`, `angular-new-app` | [angular/skills](https://github.com/angular/skills) (official) |
| `react` | `vercel-react-best-practices`, `vercel-composition-patterns`, `vercel-react-view-transitions`, `web-design-guidelines` | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) (official) |
| `nextjs` | `next-cache-components-*`, `next-partial-prefetching-*`, `next-bundle-optimizer`, `next-dev-loop` (installs `react` too) | [vercel/next.js](https://github.com/vercel/next.js/tree/canary/skills) (official) |
| `spring-boot` | `spring-boot-conventions`, `spring-boot-testing` | this repo |
| `spring-boot-community` | `spring-boot-skill`, `java-code-review`, `jspecify-skill`, `spring-modulith-verifier` | [sivaprasadreddy/sivalabs-agent-skills](https://github.com/sivaprasadreddy/sivalabs-agent-skills) |
| `frontend` | `typescript-conventions`, `frontend-testing` | this repo |
| `fullstack` | `api-contract`, `review-checklist`, `fullstack-feature` | this repo |

Typical sets:

- Angular + Spring Boot: `angular`, `frontend`, `spring-boot`, `fullstack`
- Next.js + Spring Boot: `nextjs`, `frontend`, `spring-boot`, `fullstack`
- Backend only: `spring-boot`, `spring-boot-community`

## Install in Claude Code

```sh
claude plugin marketplace add baibesh/devkit-skills
claude plugin install spring-boot@devkit-skills
claude plugin install fullstack@devkit-skills
claude plugin install frontend@devkit-skills
claude plugin install angular@devkit-skills     # or react@devkit-skills / nextjs@devkit-skills
```

Inside a session the same works with `/plugin marketplace add baibesh/devkit-skills` and `/plugin`.

### Updates

Auto-update is off by default for third-party marketplaces. Turn it on in `/plugin` > Marketplaces > devkit-skills > Enable auto-update, or update manually:

```sh
claude plugin marketplace update devkit-skills
claude plugin update spring-boot@devkit-skills
```

### Share with the whole team

Register the marketplace in a project so everyone who opens it is offered the plugins:

```sh
claude plugin marketplace add baibesh/devkit-skills --scope project
```

Commit the resulting `.claude/settings.json`. Equivalent snippet:

```json
{
  "extraKnownMarketplaces": {
    "devkit-skills": {
      "source": { "source": "github", "repo": "baibesh/devkit-skills" },
      "autoUpdate": true
    }
  }
}
```

No SSH key for GitHub on the machine? Set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`.

## Install with `npx skills` (Codex, Cursor, Copilot, Gemini, Claude Code)

Own skills from this repo:

```sh
npx skills add baibesh/devkit-skills                              # pick interactively
npx skills add baibesh/devkit-skills --skill api-contract -a codex
```

Upstream skills directly:

```sh
npx skills add angular/skills
npx skills add vercel-labs/agent-skills --skill react-best-practices --skill composition-patterns
npx skills add vercel/next.js
npx skills add sivaprasadreddy/sivalabs-agent-skills --skill spring-boot
```

Keep them fresh with `npx skills check` and `npx skills update`.

Codex can also use the experimental plugin marketplace (own plugins only): `codex plugin marketplace add baibesh/devkit-skills`.

## Recommended companions

- **Angular CLI MCP server**: build, test and docs tools for the agent. Add to `.mcp.json`:

  ```json
  { "mcpServers": { "angular-cli": { "command": "npx", "args": ["-y", "@angular/cli", "mcp"] } } }
  ```

- **Next.js 16.3+** writes an `AGENTS.md` block on `next dev` that points the agent to docs bundled in `node_modules/next/dist/docs/`. A copy is in [templates/nextjs](templates/nextjs/). For Claude Code add a `CLAUDE.md` with the line `@AGENTS.md`.

## Version targets

| Stack | Target |
|---|---|
| Angular | 20+ (current 22.x) |
| React | 19 |
| Next.js | 16 |
| TypeScript | 6.0, strict (7 as an optional fast type-check) |
| Testing | Vitest 5, MSW 3, Playwright |
| Spring Boot | 4.x (Spring Framework 7) |
| Java | 21 or 25 LTS |
| springdoc-openapi | 3.x |

Every skill tells the agent to detect the project's real versions first and adapt.

## Credits and licenses

This repo is MIT. Referenced plugins are fetched from their upstream repositories at install time and keep their own licenses:

| Source | License |
|---|---|
| [angular/skills](https://github.com/angular/skills) | MIT (declared in skill frontmatter, © Google LLC) |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | MIT (declared in README and skill frontmatter) |
| [vercel/next.js](https://github.com/vercel/next.js) | MIT |
| [sivaprasadreddy/sivalabs-agent-skills](https://github.com/sivaprasadreddy/sivalabs-agent-skills) | MIT |

## See also

- [rrezartprebreza/spring-boot-skills](https://github.com/rrezartprebreza/spring-boot-skills): 30+ Spring Boot 3 and 4 skills
- [jdubois/dr-jskill](https://github.com/jdubois/dr-jskill): bootstrap Spring Boot 4 apps
- [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills): broad fullstack collection
- [skills.sh](https://skills.sh): skills directory

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).

## Быстрый старт (RU)

```sh
claude plugin marketplace add baibesh/devkit-skills
for p in spring-boot fullstack frontend angular; do   # angular → react / nextjs по стеку
  claude plugin install "$p@devkit-skills"
done
```

Чтобы получать обновления автоматически, включи auto-update: `/plugin` > Marketplaces > devkit-skills.
