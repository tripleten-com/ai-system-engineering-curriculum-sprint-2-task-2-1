# Coldline Task 2.1 — Retrieval baseline

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/tripleten-com/ai-system-engineering-curriculum-sprint-2-task-2-1/tree/main)

## Step 1: Start the system and check readiness

Prerequisites are Python 3.12 and Docker with Compose v2. The supplied bootstrap supports macOS
arm64/x86-64, Windows x86-64, and Linux x86-64/aarch64, and installs pinned uv 0.11.8 under
`.tools/bin`. If your computer cannot run the stack locally, use the Codespaces button above.

On macOS and most Linux distributions the interpreter is `python3`; substitute it wherever these
commands say `python`.

```shell
python infra/scripts/bootstrap.py
./.tools/bin/uv sync --frozen
./.tools/bin/uv run --frozen poe preflight
./.tools/bin/uv run --frozen poe start
./.tools/bin/uv run --frozen poe ready
```

PowerShell and POSIX wrappers are available under `infra/scripts/`. After uv is on `PATH`, the
shorter `uv run --frozen poe <task>` form works.

| Service | Local URL | Purpose |
|---|---|---|
| API | `http://localhost:8000` | Submit exception workflows and retrieval queries |
| Grafana | `http://localhost:3000` | Use the focused diagnostics dashboard |
| Prometheus | `http://localhost:9090` | Query bounded metrics |
| Jaeger | `http://localhost:16686` | Inspect local traces |
| LocalStack S3 | `http://localhost:4566` | Inspect the emulated object-storage endpoint |

Each of these ports can be overridden by setting the matching `COLDLINE_API_HOST_PORT`,
`COLDLINE_GRAFANA_HOST_PORT`, `COLDLINE_PROMETHEUS_HOST_PORT`, `COLDLINE_JAEGER_HOST_PORT`, or
`COLDLINE_LOCALSTACK_HOST_PORT` environment variable in your shell environment or a local `.env`
file (copy `.env.example`) if a default collides with something already running on your machine.
Keep the override in place for every `poe` command.

If you change the API port, also set `COLDLINE_API_HOST_PORT` in the shell that runs
`poe load-test`: this command does not read `.env`. Use the same port for startup and load testing.
For example, to use port 8001, run the command for your shell before starting the system:

| Shell | Set the API host port |
|---|---|
| PowerShell | `$env:COLDLINE_API_HOST_PORT = "8001"` |
| macOS/Linux (POSIX) | `export COLDLINE_API_HOST_PORT=8001` |

PostgreSQL, Redis, worker metrics, and OTLP remain inside the Compose network. Codespaces uses the
same `compose.yaml` and keeps every forwarded port private.

## Step 2: Ingest and inspect the corpus

After Step 1 readiness checks pass, load the prepared documents and provenance through ObjectStore:

```shell
./.tools/bin/uv run --frozen poe ingest
```

Inspect the report's object keys and corpus details, then follow
[Inspect database and object-store evidence](#inspect-database-and-object-store-evidence).
Check the records and access labels before running the baseline evaluation.

## Step 3: Run and inspect the baseline

```shell
./.tools/bin/uv run --frozen poe baseline
```

Read the per-query and per-stage evidence using the published outcome rules. Complete your
answer sheet from the observed results, then run the complete public command:

```shell
./.tools/bin/uv run --frozen poe verify
```

## Command reference

| Command | Use |
|---|---|
| `poe ingest` | Run the supplied baseline corpus ingestion inside the API container |
| `poe baseline` | Run every published query and print the baseline evaluation report |
| `poe unit` | Run fast isolated behavior tests |
| `poe contract` | Check interfaces, boundaries, submissions, and repository structure |
| `poe smoke` | Check the initialized running platform |
| `poe e2e` | Run the external API-to-worker workflow |
| `poe verify` | Run the public student verification path |
| `poe scenario` | Run the supplied exception-workflow walkthrough |
| `poe load-test` | Run this repository's supplied traffic profile |
| `poe reset-baseline` | Clear exception and Redis data, then restart the worker between load runs |
| `poe restart` | Restart the existing API and worker containers **without rebuilding**; run `poe start` instead after editing source |
| `poe stop` | Remove containers and the network, keeping named volumes |
| `poe reset` | Remove containers, the network, and local named volumes |

`poe ingest` is idempotent: running it twice produces the same rows, the same counts, and the same
corpus digest. `poe reset` removes the database volume, so run `poe ingest` again after a reset.

For Task 2.1, `poe verify` runs readiness, smoke tests, the end-to-end exception workflow, the
answer-sheet checks, and the two baseline answer checks. The baseline answer checks **rerun the
two queries you recorded** against your own running stack and compare the outcome against the
published criteria, so they need the stack started and the corpus ingested.

## Folder map

```text
repository root/
├── docs/                Student guidance, public contracts, and fidelity notes
│   ├── contracts/       Machine-readable public contracts
│   ├── fidelity/        Local-runtime boundary notes
│   └── retrieval/       Supplied retrieval pipeline reference
├── infra/               Local setup and runtime configuration
│   ├── corpus/          Supplied synthetic corpus, custody record, and query set
│   └── postgres/        Database initialization
├── loadtest/            Supplied traffic profile and provider-latency harness
├── src/
│   ├── api/             HTTP application code and the retrieval workflow
│   ├── worker/          Background application code
│   ├── domain/          Shared domain code, data contracts, embedding, chunking, fusion
│   ├── ports/           Application interfaces
│   └── adapters/        Technology-specific implementations
└── tests/
    ├── unit/            Isolated behavior checks
    ├── contract/        Interface, retrieval, and repository checks
    ├── smoke/           Running-platform checks
    └── e2e/             Supplied workflow tools and checks
```

## Overview

Use the Task 2.1 lesson to decide what evidence to collect. This README covers local setup and
repository orientation; investigate the supplied system from your own run.

1. `README.md` — local setup, commands, and permitted changes.
2. `compose.yaml` — the supplied local services and startup order.
3. [`docs/retrieval/pipeline.md`](docs/retrieval/pipeline.md) — the supplied stages and where each
   part lives.
4. [`infra/corpus/README.md`](infra/corpus/README.md) — what the corpus is, where it came from, and
   how its relevance labels are derived.
5. `src/domain/contracts.py` and `src/ports/__init__.py` — shared data and application interfaces.
6. `src/api/retrieval_workflow.py` — the coupled retrieval and context-assembly path.
7. `src/adapters/` — technology-specific implementations.

The application source lives in five flat packages:

| Package | Responsibility |
|---|---|
| `api` | HTTP delivery, API use cases, the retrieval workflow, configuration, and composition |
| `worker` | Background processing, retries, configuration, and composition |
| `domain` | Provider-neutral contracts, state rules, identity, redaction, embedding, chunking, fusion, access constraints |
| `ports` | Exactly five visible application interfaces |
| `adapters` | PostgreSQL, pgvector retrieval, Redis Streams, S3-compatible object storage, deterministic model, logs, traces |

`src/api/bootstrap.py` and `src/worker/bootstrap.py` compose each process from its settings and
adapters. Process settings live in `src/api/config.py` and `src/worker/config.py`; other modules
receive settings or collaborators through function and constructor arguments.

## Inspect database and object-store evidence

For database inspection after `poe ingest`, use the supplied PostgreSQL client:

```shell
docker compose exec -T postgres psql -U coldline -d coldline -c "\d documents"
docker compose exec -T postgres psql -U coldline -d coldline -c "\d chunks"
docker compose exec -T postgres psql -U coldline -d coldline -c "SELECT chunk_id, document_id, chunk_index, vector_dims(embedding), search_document, tenant_id, access_tier FROM chunks ORDER BY chunk_id;"
```

Compare these observations with `infra/postgres/002_retrieval_corpus.sql` and the corpus
fixtures. For object-store reads, inspect `docker compose logs localstack` alongside the
`/api/v1/corpus/objects` endpoint listed in this README. The initializer provisions resources;
`poe ingest` loads the searchable corpus. Retrieval outcome rules are under
[Published outcome criteria](#published-outcome-criteria); their draft qualification status still applies.

## The five ports

Find the available interfaces in `src/ports/`. A port describes an application capability; an
adapter provides it using a concrete technology. Determine which ports are active from your own
runtime evidence rather than from this guide.

| Port | General responsibility |
|---|---|
| `ModelProvider` | Call an AI model service |
| `Retriever` | Look up relevant context or documents |
| `ObjectStore` | Store large binary objects or files |
| `JobQueue` | Publish and consume background work |
| `SecretProvider` | Read API keys and credentials |

## Retrieval API

Two endpoints are new in this Sprint. Both are supplied and are not student work.

```text
POST /api/v1/retrieval/search
  {"query_id": "...", "text": "...",
   "authorization": {"tenant_id": "...", "clearance": "standard"},
   "explain": false}
  -> ranked results, per-stage evidence, prompt context, citations

GET  /api/v1/corpus/objects?prefix=corpus/
  -> the object keys visible through the published ObjectStore port
```

Set `"explain": true` to add the authorization stage's readable pool to the evidence. That costs
one extra query, so ordinary requests leave it off.

## Test levels

| Level | Requires Compose | Main question |
|---|---:|---|
| Unit | No | Does one responsibility behave correctly, including failures? |
| Contract | Some | Do interfaces, schemas, paths, and dependency rules stay compatible? |
| Smoke | Yes | Did the complete local platform initialize and become observable? |
| E2E | Yes | Can an external client complete the supplied workflow? |

Contract checks marked `runtime` need the running stack. `poe contract` skips them; `poe verify`
and `poe runtime-contract` run them.

## Submission checks

Run `poe verify` locally before opening your student pull request. Public GitHub CI repeats
the student checks. The course platform (CMS) runs the required protected grading separately
and associates its results with your submission commit. A green template-export check, or a
skipped student check on an `export/` branch, is not a passing grade. You do not configure
GitHub grading secrets. Follow the Task lesson's instructor-review and progression policy.

## Task boundary

Task 2.1 is an investigation. You run the supplied system, read its evidence, and record two direct
observations. You do not change application code or retrieval algorithms.

Only this path is student-editable:

- `submission.yaml`

The public verifier (`poe verify`) checks answer structure and completeness, checks that only this
path changed, and reruns the two queries you recorded against your running stack. It stores no
expected answer: it recomputes the outcome from your own system, so there is nothing to look up
and nothing to guess.

The supplied defaults are `top_k = 3` and `dense_weight = 0.5`. Each arm returns a fixed
candidate pool of 12 rows before fusion, so the two parameters change what fusion selects without
changing what the arms see.

### Published outcome criteria

| Criterion | Definition |
|---|---|
| success | the query's target document appears in the final ranked results |
| miss | the query's target document appears nowhere in the final ranked results |

`poe baseline` prints one row per published query with the outcome, the target document, and the
documents actually returned. Record one query meeting each criterion.

An empty index is **not** a miss. If every query returns no candidates, the corpus is not ingested;
run `poe ingest`. The answer checks reject that state explicitly rather than accepting it as a
miss.

### Student walkthrough

See **Task 2.1: Retrieval baseline** in your course platform for the full walkthrough. In outline:
start the stack, confirm readiness, confirm that the corpus and its custody record are reachable
through the `ObjectStore` port, ingest the corpus, inspect the dense and sparse representations,
run `poe baseline`, read the per-stage evidence for a miss without yet attributing a cause, record
both query identifiers, run `poe verify`, and open your pull request.

## Operational limits

This local system does not authenticate users, terminate TLS, or manage production secrets.
A retrieval request states its own tenancy and clearance, so that context is an asserted
identity rather than a verified one. The Compose PostgreSQL password and the LocalStack access keys
are local-only non-secret credentials. Never place real credentials, personal data, or production
records in this repository, including in `infra/corpus/`.

Named volumes preserve local PostgreSQL, Redis, Prometheus, Grafana, and Jaeger state across
`poe stop`. LocalStack object contents are deliberately not persisted; the initializer re-uploads
the supplied corpus artifacts on every start. The `poe reset` command deletes the named volumes.
This topology makes no backup, replication, high-availability, disaster-recovery, capacity,
latency-SLO, or availability claim.

See [JobQueue fidelity](docs/fidelity/JobQueue.md),
[ModelProvider fidelity](docs/fidelity/ModelProvider.md),
[ObjectStore fidelity](docs/fidelity/ObjectStore.md), and
[Retriever fidelity](docs/fidelity/Retriever.md) for the active adapter boundaries. The
[local runtime evidence](docs/fidelity/local-runtime.md) records the current measurement and its
qualification limits.
