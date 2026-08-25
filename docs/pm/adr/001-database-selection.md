# ADR-001: Database Selection — DynamoDB over Aurora DSQL / Aurora PostgreSQL Serverless

## Status
Accepted

## Context
The project required a genuinely free, cloud-hosted database. Two relational options were attempted first, in this order:
1. **Aurora DSQL** — blocked by AWS at cluster creation, with an account-level restriction on new accounts.
2. **Aurora PostgreSQL Serverless** — also blocked; the console explicitly stated the account's Free Plan limits access to RDS/Aurora "Full configuration" options.

Both restrictions were confirmed as documented, deliberate AWS Free Plan guardrails, not bugs or misconfiguration.

## Decision
Use **Amazon DynamoDB**, AWS's Always Free NoSQL database, with a single-table design.

## Rationale
- DynamoDB is not subject to the same Free Plan gating seen on RDS/Aurora — it is designed to be usable immediately at small scale.
- It is genuinely free indefinitely (25GB storage, generous on-demand allowances), matching the project's zero-cost-risk requirement, rather than being funded by a time-limited signup credit.
- Serverless by nature — no capacity planning, no idle-cost risk.

## Consequences
- The clean relational schema (four normalized tables with foreign keys) had to be redesigned as a single-table NoSQL schema, modeled around access patterns rather than entity normalization (see ADR-002).
- Power BI has no native DynamoDB connector, requiring a scheduled export pattern instead of live BI queries (see ADR-003).
- The pivot cost implementation time but did not compromise the project's zero-cost guarantee, which was treated as a harder constraint than schema elegance.

## Alternatives Considered
- **Aurora DSQL**: rejected due to account-level restriction, not a technical shortcoming of the service itself.
- **Aurora PostgreSQL Serverless**: rejected for the same reason; also would have drawn from a time-limited signup credit rather than being unconditionally free.
- **Supabase / Neon (third-party managed Postgres)**: considered as a no-card, no-restriction alternative; not chosen because the project's owner elected to stay within the AWS ecosystem for skill-building purposes after already investing in AWS IAM/CLI setup.
