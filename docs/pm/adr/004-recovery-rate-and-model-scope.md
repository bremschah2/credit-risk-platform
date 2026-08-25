# ADR-004: Recovery Rate Assumption and Model Usage Boundaries

## Status
Accepted

## Context
The expected-loss calculation (`P(default) × Exposure × (1 − Recovery Rate)`) requires a recovery rate. The source dataset contains no recovery-amount field, so no rate could be fitted from data. Separately, the trained model's ROC-AUC (0.6964) is meaningfully below what production bureau-based credit scorecards typically achieve, primarily due to the absence of a credit score field in this dataset.

## Decision
1. Use a documented, industry-typical **35% recovery rate assumption** (commonly cited for unsecured personal loans), explicitly labeled as an assumption rather than a fitted value, and exposed as an adjustable parameter in the dashboard (see Phase 5).
2. Scope the model's intended use explicitly to **relative risk ranking for collections prioritization and portfolio monitoring**, and explicitly **exclude** standalone credit approval/denial decisions from the model's intended use.

## Rationale
- Presenting an unlabeled, precise-looking recovery rate would overstate the certainty of the expected-loss dollar figures.
- Automated credit approval/denial carries real regulatory obligations (fair lending compliance, adverse action notice requirements) that a model of this accuracy, trained on public data, is not positioned to responsibly support.
- Collections prioritization is a lower-stakes application where relative ranking, not absolute precision, is what matters — a good match for the model's actual demonstrated capability.

## Consequences
- All dollar-value expected-loss figures in this project should be understood as directional/illustrative given the assumption, not precise financial commitments.
- The dashboard's what-if parameter allows the assumption's sensitivity to be explored interactively rather than hidden.
- Any future extension toward approval/denial decisioning would require a materially stronger model (ideally with bureau data) and a compliance review, both explicitly out of this project's scope.

## Alternatives Considered
- **Omit the recovery rate assumption or bury it in code comments**: rejected as less transparent than surfacing it as a labeled, adjustable dashboard parameter.
- **Attempt to fit a recovery rate from proxy fields**: rejected — no reliable proxy existed in the available columns; a fabricated derivation would have been less honest than a clearly labeled industry-typical assumption.
