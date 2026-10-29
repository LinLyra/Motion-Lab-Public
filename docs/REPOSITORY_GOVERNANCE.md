# LYKON repository governance

## Canonical repositories

| Repository | Authority | Contains | Must not contain |
| --- | --- | --- | --- |
| `lykon-platform` | Product control plane | identity, consent, sessions, uploads, API contracts, operations UI | raw high-frequency samples, research notebooks, synthetic claims presented as real |
| `lykon-motion-lab-v2` | Research and processing engine | versioned data contracts, validation, synchronisation, quality checks, feature/event pipelines | production credentials, user authentication logic, public athlete dashboards |
| `lykon-demo` | Presentation-only surface | synthetic investor/partner walkthroughs | production database access, secrets, claims that placeholder metrics are validated |

Legacy clones and datasets inside another repository are local working material, not
canonical source.  They must remain ignored until their ownership and provenance are
reviewed explicitly.

## Branch protection baseline

When the company GitHub organisation is created:

1. Create private repositories first.
2. Require pull requests for the default branch.
3. Require at least one approval once a second maintainer joins.
4. Require passing type checks, tests, secret scanning, and dependency review.
5. Disable force pushes and branch deletion on the default branch.
6. Grant access through teams, not ad-hoc repository invitations.
7. Require hardware-backed MFA for organisation owners.
8. Keep at least two organisation owners when a trusted second administrator exists.

## Change ownership

- Data-contract changes require a schema version and migration/compatibility test.
- Raw-data parsers must accept only documented versions.
- Algorithm outputs record pipeline/model version and source asset identifiers.
- Research labels remain separate from immutable sensor captures.
- Demo fixtures are visibly marked synthetic and never copied into research results.

## Release path

```text
edge collector -> immutable session bundle -> platform upload
              -> motion-lab validation/processing worker
              -> versioned quality and analysis artifacts
              -> operations/research console
```

The first supported workflow is recorded-data replay.  Live capture reuses the same
session bundle and contract after the file-based path is reliable.
