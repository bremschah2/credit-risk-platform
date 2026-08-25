# Project Charter
## Credit Risk & Collections Prioritization Platform

### Business Case
Lenders lose money in two directions on every loan: misjudging default risk causes losses through bad approvals, and inefficient collections effort wastes resources chasing low-recovery accounts instead of prioritizing high-value, high-risk ones. This project builds a platform that quantifies both risk and dollar-value exposure at the loan level, so a lender could prioritize collections effort where it actually matters.

### Objectives
1. Ingest and model real loan-level data in a genuinely free, cloud-hosted environment (zero cost risk, indefinitely).
2. Predict probability of default with a calibrated model — not just a ranking model, but one whose probability outputs are trustworthy enough to drive a dollar-value calculation.
3. Compute expected loss per loan (`P(default) × Exposure × (1 − Recovery Rate)`) and surface it in a decision-oriented dashboard.
4. Demonstrate real competency across four professional tracks — Data Analyst, Data Scientist, Data Engineer, IT Project Manager — on one coherent system, not four disconnected exercises.

### Scope
**In scope:** cloud database provisioning and administration; scheduled ETL; model training, calibration, and evaluation; a deployed real-time scoring API; a batch scoring job; a BI dashboard; documented architecture decisions.

**Out of scope:** production-scale traffic handling; automated credit approval/denial decisions (explicitly excluded — see ADR-004 and Phase 3 retrospective for why); write-back workflow tooling for collections agents; regulatory/compliance certification (fair lending, adverse action notices) that would be required for any real approval-decision use.

### Stakeholders
- **Project owner / sole contributor:** Shah Brahim — owns architecture, implementation, and delivery across all tracks.
- **Intended audience:** technical reviewers, hiring managers, and peers evaluating the project as a portfolio artifact.
- **Hypothetical business stakeholder (for framing purposes):** a collections/risk team lead who would use the Priority List dashboard page day to day.

### Success Criteria
- A working, live, publicly reachable scoring endpoint.
- A calibrated model with an honestly reported, defensible performance ceiling (not an inflated metric).
- A documented, coherent architecture with real trade-off decisions captured as ADRs.
- A dashboard that supports an actual prioritization decision, not just a data display.
- Zero cloud cost incurred throughout the build.

### Constraints
- Genuinely free cloud infrastructure only — no paid tiers, no relying on trial credits as a long-term foundation.
- Single contributor, part-time effort.
- Public dataset (Lending Club) — no proprietary or PII-sensitive data.

### Timeline (as executed, phase-based rather than date-based)
Phase 0 (cloud setup) → Phase 1 (schema + data) → Phase 2 (ETL pipeline) → Phase 3 (model + calibration) → Phase 4 (deployment) → Phase 5 (dashboard) → Phase 6 (this document) → Phase 7 (packaging).
