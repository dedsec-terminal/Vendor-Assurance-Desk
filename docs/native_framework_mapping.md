# Native CISO Assistant framework references

The ten Vendor Assurance Desk (`VAD-TPRM-CONTROLS-1.0`) supplier-review questions are linked to one exact ISO/IEC 27001:2022 Annex A reference each in the local CISO Assistant v4.3.2 instance. These are *primary topical associations* that make the relevant native reference visible from each applied question. They do not establish that a supplier meets a control, demonstrate compliance, or claim equivalence.

## Why only one reference is linked

The installed ORM schema defines `core.AppliedControl.reference_control` as a single nullable foreign key to `core.ReferenceControl`. It cannot represent the multiple NIST and ISO references listed for several catalog questions. The chosen ISO reference is the primary topical association; the full NIST CSF 2.0 and additional ISO crosswalk IDs and caveats remain in [`../case-study/control_catalog.json`](../case-study/control_catalog.json). NIST CSF 2.0 ReferenceControl records were not available in this local database, so no NIST association was fabricated.

| VAD question | Native ISO/IEC 27001:2022 reference | Reason for the primary link |
| --- | --- | --- |
| TPRM-GOV-01 | A.5.19 | Supplier relationships is closest to pre-engagement supplier diligence. |
| TPRM-GOV-02 | A.5.19 | Supplier relationship governance is closest to lifecycle ownership. |
| TPRM-CON-01 | A.5.20 | Supplier agreements directly cover contractual security obligations. |
| TPRM-SUP-01 | A.5.21 | ICT supply-chain security directly covers downstream dependencies. |
| TPRM-IAM-01 | A.5.15 | Access control is the broad primary topic; identity, access-rights, and authentication references remain in the proposed crosswalk. |
| TPRM-CHG-01 | A.8.32 | Change management directly covers authorized and controlled service changes. |
| TPRM-OPS-01 | A.8.16 | Monitoring activities is closest to review of security-relevant activity. |
| TPRM-IR-01 | A.5.26 | Incident response directly covers coordinated response to incidents. |
| TPRM-RES-01 | A.8.13 | Information backup is closest to service backup and restore evidence. |
| TPRM-REV-01 | A.5.22 | Supplier service monitoring and review is closest to reassessment and follow-up. |

The standard record IDs were validated against CISO Assistant's exact bundled **International standard ISO/IEC 27001:2022**, version **19** library. The integration loads this library only when it is not already loaded, then sets only the ten `reference_control` foreign keys. The operation does not edit supplier findings, evidence records, decisions, assessment statuses, or control statuses. Proof uses canonical JSON SHA-256 (`canonical-json-v1`) so Windows and Linux line endings produce the same digest. A legacy raw-byte proof is accepted for migration only when its hash equals the exact current catalog bytes; successful verification rewrites the proof with the canonical hash.

## Reproduce and verify

Run from the repository root in PowerShell. The scripts execute through the local Docker backend. The staging step copies only the scripts and public control catalog; it does not use administrator credentials.

```powershell
$repo = (Resolve-Path .).Path
$linuxRepo = '/mnt/' + $repo.Substring(0, 1).ToLowerInvariant() + '/' + $repo.Substring(3).Replace('\', '/')
$stage = "docker run --rm --volumes-from backend:rw -v '$linuxRepo/scripts:/scripts:ro' -v '$linuxRepo/case-study:/case:ro' alpine:3.23 sh -c 'mkdir -p /code/db/vad_data && cp /scripts/docker_link_frameworks.py /scripts/docker_verify_framework_links.py /code/db/ && cp /case/control_catalog.json /code/db/vad_data/'"
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc $stage
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc 'docker exec backend python /code/db/docker_link_frameworks.py'
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc 'docker exec backend python /code/db/docker_link_frameworks.py --apply'
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc 'docker exec backend python /code/db/docker_verify_framework_links.py'
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc 'docker exec backend python /code/db/docker_link_frameworks.py --apply'
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc 'docker exec backend python /code/db/docker_verify_framework_links.py'
wsl.exe -d Ubuntu-24.04 -u root -- bash -lc "docker exec backend cat /code/db/framework_links.json > '$linuxRepo/output/framework_links.json'"
```

The first command is a no-write plan. `--apply` uses one database transaction for loading the bundled ISO reference library (if required) and linking the controls. It refuses unknown or ambiguous source IDs, duplicate catalog or applied-control IDs, an unexpected control set or folder, changed control statuses, or conflicting existing links. It checks FK targets again after the locked read and before transaction commit. Repeating it leaves correct links unchanged and refuses to replace manual drift. The verifier independently reads the native records, checks every FK points to exactly one reference in the selected library, and confirms all ten controls remain `to_do`, the supplier and findings assessments remain `in_review`, and the three findings remain identified. Run the existing [`docker_verify_sync.py`](../scripts/docker_verify_sync.py) too to verify finding, evidence and remediation integration remains intact.

## Limits

The mapping is a focused training crosswalk, not a comprehensive framework mapping exercise. A topical association is not proof that the supplier implemented a requirement. No supplier control is marked effective, no assessment is approved, and the HarborPay Demo onboarding decision remains on hold pending human review of authentic, in-scope evidence.
