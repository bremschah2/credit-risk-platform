# ADR-003: Scheduled Export Refresh over Live BI Connection

## Status
Accepted

## Context
Power BI has native live-query connectors for SQL databases, but no native connector for DynamoDB — a direct consequence of the database choice in ADR-001.

## Decision
Build a Python export script that scans DynamoDB, joins borrower/loan/payment/risk-score records into a single flat CSV, and have Power BI read and refresh from that file on a scheduled basis, rather than querying the database live.

## Rationale
- This is a standard, widely-used pattern for BI over non-SQL sources — "live" in most real BI deployments already means "refreshes on a schedule," not "queries the source on every click."
- Avoids introducing a second database or a paid intermediary service purely to satisfy a live-connector requirement, which would have violated the project's zero-cost constraint.

## Consequences
- The dashboard is explicitly not real-time; it reflects the data as of the last export run. This is stated directly on the dashboard itself ("Data as of: [date]") rather than left ambiguous.
- A stronger version of this pattern (Power BI Service with scheduled cloud refresh, matching the Phase 2/4 GitHub Actions automation pattern) is a documented, feasible future extension, not yet built.

## Alternatives Considered
- **Migrate to a SQL-native database purely for BI purposes**: rejected — would have undone the zero-cost-risk decision in ADR-001 for a reporting convenience.
- **DynamoDB Streams + a real-time pipeline into a BI-friendly store**: considered out of scope for this project's size and goals; noted as a legitimate larger-scale alternative if this were a production system.
