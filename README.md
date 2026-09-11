# SampleApp — Self-Healing CI Pipeline Demo

A minimal Spring Boot app (Java 21 / Maven) wired to a GitHub Actions pipeline
that detects its own CI failures, classifies the root cause with an LLM
(Groq, `llama-3.3-70b-versatile`), and automatically opens a remediation PR
for the failure categories where that's safe.

## The app

- `GET /hello` — static greeting.
- `GET /add?a=&b=` — integer addition.

## The pipeline

On every push/PR to `main`, `self-healing-ci.yml` just runs the test suite
like normal CI. The self-healing behavior is demoed on demand via a
`workflow_dispatch` input, since a real repo can't be relied on to fail on
command:

1. **`prepare-demo`** — creates a throwaway `demo/<scenario>` branch off
   `main`, overlays a pre-built broken variant of a file from `scenarios/`,
   commits and pushes it. `main` itself is never touched.
2. **`build-and-test`** — runs `./mvnw test` on that branch, captures the
   full log to a `build-log` artifact regardless of outcome.
3. **`classify-failure`** — only runs if the previous job failed. Sends the
   tail of the log to Groq, which returns a structured classification:
   category (`deterministic_bug` / `flaky_test` / `dependency_issue` /
   `unknown`), root cause, and whether it's safe to auto-fix.
4. **`auto-remediate`** — only runs when the classification says
   `auto_fixable: true`. Restores the known-good file from `main`, re-runs
   the tests to confirm it's actually green, then opens a PR with the LLM's
   reasoning in the description.
5. **`flag-flaky`** — only runs for `flaky_test` classifications. Instead of
   "fixing" the code (there's nothing to fix — the test itself is
   nondeterministic), it retries the suite a few times and posts a job
   summary recommending quarantine. **No PR is opened for this category.**

### Failure scenarios

| Scenario | What breaks | Category | Outcome |
|---|---|---|---|
| `deterministic-bug` | `/add` returns `a + b + 1` | `deterministic_bug` | PR reverting the bug |
| `dependency-mismatch` | `spring-boot-starter-web` pinned to a nonexistent version | `dependency_issue` | PR reverting `pom.xml` |
| `flaky-test` | a timing-based test with a 5ms budget | `flaky_test` | Flagged in job summary, no PR |

Each broken variant lives under `scenarios/<name>/` and is copied over the
real file only on the demo branch by `scripts/inject_scenario.py` — it never
touches `main`.

## Running a demo

```bash
gh workflow run self-healing-ci.yml -f failure_scenario=deterministic-bug
gh run watch
```

Swap `deterministic-bug` for `dependency-mismatch` or `flaky-test` to see the
other two paths. Each run creates/reuses a `demo/<scenario>` branch — safe to
re-run repeatedly.

## One-time setup

1. **Groq API key**: `gh secret set GROQ_API_KEY` (free tier at
   [console.groq.com](https://console.groq.com)).
2. **Workflow permissions**: repo Settings → Actions → General → Workflow
   permissions → enable "Read and write permissions" and "Allow GitHub
   Actions to create and approve pull requests". Required for
   `auto-remediate` to push commits and open PRs.

## Design notes / trade-offs

- **Auto-fix is deliberately narrow.** Only `deterministic_bug` and
  `dependency_issue` are ever auto-fixable, and only when the model is
  confident the fix is a simple, obviously-correct revert. A real production
  version of this would want a stricter allowlist and human approval on the
  PR before merge (which this already gets, by design — it opens a PR, it
  doesn't merge one).
- **Flaky tests are quarantined, not patched.** Auto-"fixing" a flaky test by
  editing code would be guessing; the honest response is to flag it and
  retry, which is what `flag-flaky` does.
- **Demo failures live on throwaway branches, not `main`.** This keeps the
  repo's actual `main` always green while still giving the pipeline a real
  failure to diagnose and a real fix to verify.
