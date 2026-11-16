# Synthetic outcome scorecard

**Case:** `HPD-2026-001`<br>
**Assessment input SHA-256:** `b54cc937f485ee5b0324fb436a34519e191865c1686565cefeb859c92a0172b4`

> Training fixture only: one fictional vendor, four selected metadata checks and three small ITGC tests. No overall maturity score is calculated.

## Assurance metadata retest

Selected checks with a gap: **3/4 baseline → 1/4 retest** (net gap delta **-2**). This is a change in fixture check results, not a risk reduction claim.

| Check | Baseline | Retest | Evidence (baseline → retest) |
|---|---|---|---|
| CERT-EXPIRY | gap | gap | `E01` → `E01` |
| ASSURANCE-SCOPE | gap | pass | `E02` → `E02-v2` |
| CUSTOMER-MFA | gap | pass | `E03` → `E03-v2` |
| POLICY-CHECK | pass | pass | `E04` → `E04` |

## Finding follow-up fields

Owner present: **3/3** · due date present: **3/3** · baseline and retest evidence hashes present: **3/3**.

## ITGC exception retest

Exceptions: **3 baseline → 2 retest** (delta **-1**). Current exposure remains unresolved in **1/3** selected control(s); **2** historical exception record(s) remain in the retest history.

| Control | Baseline exceptions | Retest exceptions | Current exposure resolved | Historical exception IDs |
|---|---:|---:|---|---|
| ITGC-ACCESS | 1 | 1 | True | ACC-101 |
| ITGC-CHANGE | 1 | 1 | False | CHG-201 |
| ITGC-BACKUP | 1 | 0 | True | — |

## GRC platform record links

Status: **verified** — Identity and input hash match; platform worker verified the linked records.

| Platform measure | Count |
|---|---:|
| Vendor records | 1 |
| Service records | 1 |
| Assessment records | 1 |
| Finding-to-control link relationships (not unique controls) | 4 |
| Linked finding records | 3 |
| Linked evidence records | 5 |
| Distinct configured control records represented by those links | 3 |
| Total supplier-scope control records configured for the assessment | 10 |

Finding-to-control link count is separate from distinct configured controls and total supplier-scope controls.

## Human review

Peer feedback: **Pending peer review** · reviewer closures: **0** · final onboarding decision: **Pending**.

## Scope and limits

- All records are fictional training data.
- One vendor, four selected metadata checks, and three small ITGC tests only.
- Passing a selected retest is not authentication, assurance, operating-effectiveness evidence, or approval.
- Counts describe this fixture only; no time savings, risk reduction, or business outcome is inferred.
