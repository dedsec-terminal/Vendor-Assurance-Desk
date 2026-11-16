# Native CISO Assistant finding and evidence integration

## What it adds

The synthetic HarborPay supplier case now has a native **Findings Assessment** in CISO Assistant, with three native **Finding** records, their proposed remediation text, links to the applicable seeded **Applied Controls**, and links to synthetic **Evidence** inventory records. The existing supplier **Entity Assessment** remains `in_review`; the product model has no direct EntityAssessment-to-FindingsAssessment relation, so the records are related by matching supplier context and provenance rather than claiming a native foreign-key association. Each of the ten scoped supplier controls stays `to_do`. Findings remain identified, severity is undefined, and the evidence objects are explicitly `missing` because no authentic vendor artifacts were supplied. The recommendation remains **hold onboarding** and human approval remains pending.

These object types follow the product's native model instead of representing issues as completed controls or risk acceptances. This is a local, synthetic workflow demonstration. It does not establish enterprise GRC platform implementation experience, a production deployment, an actual supplier decision, or an audit opinion.

## Provenance and safety

The sync consumes only `output/assessment.json` and `output/control_review.json`, mounted read-only into the backend. It hashes parsed JSON using canonical JSON serialization (`canonical-json-v1`) so Windows and Linux line endings produce the same digest, then records those hashes in each managed finding's observation and the Findings Assessment description. Each attached Evidence item says it is a synthetic inventory placeholder and is created in `missing` state without an attachment. The deterministic `VAD-SYN-` references make repeated syncs idempotent.

The integration fails closed if the case stops being fictional, its recommendation changes, the scoped records are absent, or an existing managed record's fields or relations no longer match the integration's expected state. It does not update existing findings in place, overwrite manual edits, mark a control effective, close a finding, approve evidence, or accept risk. If the source or a managed record changes, investigate and reconcile deliberately rather than rerunning blindly.

## Run against the local Docker stack

From the repository root in PowerShell:

```powershell
$repo = (Resolve-Path .).Path
$linuxRepo = '/mnt/' + $repo.Substring(0, 1).ToLowerInvariant() + '/' + $repo.Substring(3).Replace('\', '/')
$stage = "docker run --rm --volumes-from backend:rw -v '$linuxRepo/scripts:/scripts:ro' -v '$linuxRepo/output:/input:ro' alpine:3.23 sh -c 'mkdir -p /code/db/vad_data && cp /scripts/docker_sync_assessment.py /scripts/docker_verify_sync.py /scripts/docker_test_sync_safety.py /code/db/ && cp /input/assessment.json /input/control_review.json /code/db/vad_data/'"
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc $stage
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc 'docker exec backend python /code/db/docker_sync_assessment.py'
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc 'docker exec backend python /code/db/docker_verify_sync.py'
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc 'docker exec backend python /code/db/docker_test_sync_safety.py'
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc 'docker exec backend python /code/db/docker_verify_sync.py >/dev/null 2>&1'
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc "docker exec backend cat /tmp/platform_sync.json > '$linuxRepo/output/platform_sync.json'"
```

Run the sync command again, then the verification command again. The second sync should report zero created and three unchanged findings. `docker_test_sync_safety.py` checks that a changed supplier identity is rejected, a same-count wrong evidence link fails exact-link verification, and a manual finding status edit is preserved while sync refuses to overwrite it; test mutations run inside rolled-back database transactions. The verifier emits a canonical record snapshot digest; it should be identical across readbacks when records have not changed. It exits nonzero on detected drift. The repo's ignored private Docker credentials are not read or printed by these commands.

## Native object mapping

| Training case item | CISO Assistant object | Treatment |
| --- | --- | --- |
| Vendor due-diligence review | Existing `EntityAssessment` | Preserved in review; no direct FK to findings register in upstream model |
| Findings register | `FindingsAssessment` | Stable ref `VAD-SYN-FINDINGS-HPD-2026-001`, in review; linked by case/supplier context |
| Expired assurance metadata | `Finding` | Identified, undefined severity; maps to `TPRM-REV-01` |
| Assurance scope mismatch | `Finding` | Identified, undefined severity; maps to `TPRM-REV-01` and `TPRM-SUP-01` |
| Customer-operated MFA condition | `Finding` | Identified, undefined severity; maps to `TPRM-IAM-01`; not attributed to vendor controls |
| Synthetic baseline/retest evidence references | `Evidence` | `missing`, synthetic inventory only, no attachment; linked to finding |
| Proposed next steps | Finding recommendation | Human action required; no automatic closure |

The `TPRM-*` questions retain their complete proposed NIST CSF 2.0 and ISO/IEC 27001:2022 crosswalk as scoping aids. The [native reference configuration](native_framework_mapping.md) adds one primary ISO/IEC 27001:2022 association per question through the product's single reference-control field. The additional ISO and NIST references remain proposed in the source catalog. These associations do not establish control effectiveness or compliance equivalence.

## Verification limits

The verifier checks counts, states, link targets, input hashes, and a stable digest of the read-back records. A repeat run tests idempotence and supports detection of manual drift; it is not a concurrency lock against another writer changing the database between separate command runs. All supplier data and evidence are fictional. A hiring résumé may describe this as a local CISO Assistant integration prototype with native findings, remediation, evidence-state and control relationships—not as client GRC implementation or verified vendor assurance.
