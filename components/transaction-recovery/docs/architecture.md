# Transaction & Recovery Architecture

```text
Synthetic Mutation Candidate
             |
             v
Canonical Incident Validator
             |
             v
Mutation Integrity Gate
             |
             v
Staged Generation
             |
             v
fsync(files + staging directory)
             |
             v
Rename Staging -> GEN-N
             |
             v
fsync(generations directory)
             |
             v
Write + fsync temporary CURRENT
             |
             v
Atomic CURRENT replacement
             |
             v
fsync(lab directory)
             |
             v
Published Incident Generation

Independent Recovery Decision Engine
             |
             v
Cooperative Shared Lock
             |
             v
Read-only Snapshot Inspection
             |
             v
ACCEPT_CURRENT / CONSISTENT
```

## Scope

This implementation has been demonstrated using isolated synthetic
fixtures. The recovery assessment was performed on a separate fixture
copied from the committed generation.

No concurrent shared-registry coordination or actual power-loss
recovery has been demonstrated.
