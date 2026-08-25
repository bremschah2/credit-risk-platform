# RAID Log
## Credit Risk & Collections Prioritization Platform

RAID = Risks, Assumptions, Issues, Dependencies. Entries below are drawn from what actually occurred during the build, not hypothetical placeholders.

---

## Risks (things that could have gone wrong, and how they were managed)

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Cloud costs exceeding zero-cost target | Medium | Medium | $1 AWS Budgets alert configured in Phase 0, before any resources were provisioned |
| R2 | New AWS account service restrictions blocking build progress | Medium (realized) | High | Diversified deployment plan; pivoted to DynamoDB when Aurora DSQL and RDS were both gated (see ADR-001) |
| R3 | Model probability outputs being misleading despite good ranking (AUC) | Medium (realized) | High | Explicit calibration check added in Phase 3; isotonic calibration applied after discovering 34-point overconfidence |
| R4 | Credentials exposed via screenshots during setup walkthroughs | Low (realized) | Medium | IAM access key rotated immediately after exposure in Phase 0 |
| R5 | Library version mismatch between training and serving environments | Medium (realized) | High | scikit-learn pinned to 1.7.2 in both environments; model re-trained and re-verified bit-for-bit against original metrics after the version change |

## Assumptions

| ID | Assumption | Status |
|---|---|---|
| A1 | Recovery rate for defaulted unsecured personal loans ≈ 35% (industry-typical figure; no recovery data present in source dataset) | Documented explicitly in Phase 3; made interactively adjustable in the Phase 5 dashboard |
| A2 | A stratified ~10,000–40,000 row sample is representative enough for portfolio-scale modeling, vs. loading the full 1.3M-row historical dataset | Validated: sample default rate (20.98%–20.01%) closely tracked the full population |
| A3 | Public Lending Club data contains no PII requiring special handling | Confirmed — dataset is a standard, widely-used public research/portfolio dataset |

## Issues (things that actually went wrong, and how they were resolved)

| ID | Issue | Resolution |
|---|---|---|
| I1 | `.gitignore` unanchored `data/` rule blocked `etl/data/` batch files from being committed | Anchored rule to `/data/` |
| I2 | Aurora DSQL cluster creation blocked on new AWS account | Diagnosed as account-level restriction; pivoted to DynamoDB (see ADR-001) |
| I3 | Aurora PostgreSQL Serverless "Full configuration" also blocked on Free Plan | Confirmed as the same restriction pattern; reinforced the DynamoDB decision |
| I4 | Model's raw probability outputs overconfident by up to 34 percentage points | Root-caused to `class_weight="balanced"` distorting probability calibration; fixed with isotonic calibration |
| I5 | `sub_grade` missing from initial live DynamoDB schema, forcing an approximation in expected-loss scoring | Schema and both ETL loaders updated; table wiped and reloaded from source with `batch_writer` (also fixed a 1-hour → <1-minute performance issue in the process) |
| I6 | Docker build failed compiling numpy from source (GCC version too old on Lambda base image) | Root-caused to scikit-learn 1.9.0 lacking a prebuilt wheel for the target platform; resolved by pinning to 1.7.2 |
| I7 | Lambda rejected the pushed container image ("manifest not supported") | Root-caused to Docker's default attestation/provenance metadata; rebuilt with `--provenance=false --sbom=false` |
| I8 | Lambda function timed out at default 128MB/3s settings | Increased to the account-capped maximum (512MB / 60s); confirmed the true cause was AWS's fixed 10-second init-phase cap interacting with cold-start library loading, not a real failure |
| I9 | Power BI has no native DynamoDB connector | Resolved via a scheduled flat-file export pattern (see ADR-003) |

## Dependencies

| ID | Dependency | Notes |
|---|---|---|
| D1 | AWS account approval/verification | Blocked initial timeline briefly; workaround was proceeding with account-compatible services rather than waiting |
| D2 | Public Lending Club dataset availability (Kaggle) | External, stable, well-established dataset; low risk |
| D3 | GitHub Actions for scheduled automation (ETL and batch scoring) | Free tier sufficient for this project's schedule frequency |
| D4 | AWS Lambda's fixed platform constraints (memory cap, init-phase timeout) | Account-level and platform-level constraints outside project control; designed around rather than fought |
