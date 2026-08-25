# ADR-002: Application-Layer Referential Integrity (No Foreign Keys)

## Status
Accepted

## Context
DynamoDB, chosen in ADR-001, does not support foreign key constraints, joins, or database-enforced referential integrity. The original relational schema assumed foreign keys would enforce, for example, that every loan references a real borrower.

## Decision
Design a **single-table NoSQL schema** using composite partition/sort keys (`PK`, `SK`) to model relationships logically, and enforce referential integrity in application code (Python) at write time rather than at the database layer.

## Rationale
- This is the standard, intentional pattern for DynamoDB usage — not a workaround. Single-table design is built around access patterns, not entity normalization.
- The specific access patterns needed by this project (get a borrower and all their loans; get a loan's full payment/risk history) map cleanly onto a well-chosen `PK`/`SK` structure without ever needing a join.

## Consequences
- Referential integrity checks (e.g., "does this borrower_id actually exist") must be handled explicitly in the ETL/loading code, since the database will not reject an orphaned record.
- Schema design shifted from "model the entities, query however needed later" to "decide the access patterns first, shape the keys to match" — a genuinely different design discipline, documented and understood, not an accidental limitation.

## Alternatives Considered
- **Enforce integrity via a secondary validation pass**: considered unnecessary overhead given the controlled, single-writer nature of this project's ETL pipeline.
- **Switch back to a relational database**: rejected, as it would have reintroduced the account-restriction problem documented in ADR-001.
