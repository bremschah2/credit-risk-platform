# ADR-005: Dependency Version Pinning for Lambda Deployment

## Status
Accepted

## Context
The trained model (`model.pkl`) was initially serialized using scikit-learn 1.9.0. When containerizing the scoring API for AWS Lambda, `pip install` inside the minimal Lambda base image attempted to compile numpy from source (no prebuilt wheel was available for scikit-learn 1.9.0 on that platform), which failed due to an outdated system compiler that could not be feasibly upgraded within the base image.

## Decision
Downgrade scikit-learn to **1.7.2** (a version with prebuilt wheels available for the target platform) in both the local training environment and the Lambda container, and **re-train and re-save the model** under this version rather than assuming the original pickle would remain valid or behaviorally identical.

## Rationale
- Forcing prebuilt-wheel-only installation (`--only-binary=:all:`) surfaced the real constraint clearly, rather than continuing to work around compiler issues that were a symptom, not the cause.
- A library version mismatch between the environment that trained a model and the environment serving it is a known source of subtle, hard-to-detect bugs. Re-training under the target version, rather than hoping the existing pickle would "probably still work," removed that risk entirely.

## Consequences
- Verified explicitly: after re-training under scikit-learn 1.7.2, the model produced identical ROC-AUC (0.6964), identical Brier score (0.1482), and identical portfolio expected-loss totals to the penny ($27,540,353.31) compared to the 1.9.0 version — confirming no behavioral drift resulted from the downgrade.
- `requirements.txt` for the API pins the exact version (`scikit-learn==1.7.2`) rather than leaving it unconstrained, preventing this issue from silently recurring on a future rebuild.

## Alternatives Considered
- **Install a newer compiler toolchain in the Docker image to allow compiling scikit-learn 1.9.0 from source**: attempted first; abandoned once the required GCC version proved infeasible to obtain cleanly within the base image.
- **Serve the model via a different runtime (e.g., ONNX export) to avoid the scikit-learn version dependency entirely**: considered out of scope — added complexity disproportionate to the actual problem, which had a simple, verifiable fix.
