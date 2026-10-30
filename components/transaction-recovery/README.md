# TITAN — Transaction & Recovery Engine

A synthetic-lab implementation of transactional incident-state
publication and read-only recovery assessment.

## Components

- Transaction Committer V3.2 — Bash
- Durable Publication Helper V2.2 — Python
- Recovery Decision Engine V3.2.3 — Python

## Architecture

1. Validate a proposed incident-state mutation.
2. Apply canonical and mutation-integrity checks.
3. Build a staged incident-state generation.
4. Synchronize generation files and directory.
5. Rename the staged generation into the published inventory.
6. Synchronize the generation inventory directory.
7. Write and synchronize a temporary CURRENT pointer.
8. Atomically replace CURRENT and synchronize its parent directory.
9. Evaluate published state with a read-only recovery engine.

## Demonstrated workflow

GEN2 -> ATTACH_EVIDENCE -> GEN3 -> ACCEPT_CURRENT / CONSISTENT

## Synthetic validation results

| Validation | Result |
|---|---|
| Mutation integrity | PASS |
| GEN2 to GEN3 transaction | PASS |
| Generation file integrity | PASS |
| Previous generation preserved | PASS |
| Independent recovery assessment | PASS |

## Requirements

- Linux environment with Bash and Python 3.
- jq for JSON processing and canonical validation.
- util-linux flock for cooperative transaction locking.
- A filesystem supporting the required rename and fsync operations.
- An isolated synthetic test directory.
- No operational incident registry connection.

The transaction and recovery components use bundled validation
modules. Synthetic fixtures are not included in this public package.

## Known limitations

- Power-loss durability has not been experimentally demonstrated.
- Protection against non-cooperative concurrent writers is incomplete.
- Failure-injection qualification for V3.2 is incomplete.
- Runtime paths are resolved relative to the package or through
  TITAN_TEST_ROOT for isolated synthetic fixtures.
- Canonical validation and mutation-integrity dependencies are
  bundled in the package.
- Recovery validation used an independent copy of published artifacts.
- Production use is not authorized.

## Safety

Run only in isolated synthetic laboratories.
Do not connect this candidate to an operational incident registry.
