# Vendor ITGC review and framework references

The vendor risk assessment now includes three defined IT control tests. A due-diligence review should examine both supplier-operated controls and the customer responsibilities that shape the residual risk. These rows model sample vendor evidence; they do not establish a vendor's overall security posture.

| Control | Vendor due diligence question | Related NIST CSF 2.0 reference | Related ISO/IEC 27001:2022 Annex A references |
|---|---|---|---|
| ITGC-ACCESS | Does the supplier remove workforce and privileged access at termination, and can the timing be evidenced? | PR.AA-05 | A.5.18, A.8.2 |
| ITGC-CHANGE | Are supplier changes to the assessed service approved before production deployment, including a controlled emergency path? | PR.PS-01 | A.8.32 |
| ITGC-BACKUP | Are backups successful and is there dated restore-test evidence for the relevant service/data scope? | PR.DS-11, RC.RP-03 | A.8.13, A.8.14 |

These are proposed related mappings. A reference indicates a useful review lens; it does not mean that a single CSV result demonstrates or certifies conformity with NIST or ISO. The assessor must compare control design, operating evidence, applicability, exceptions and the supplier service boundary. The exact control wording and scope must be checked against the named framework edition before use in any real engagement.

## How this relates to LedgerCast

The tests reuse the learning pattern of Swaraj's existing LedgerCast control-testing project: a defined control objective, population, test conditions and exceptions register. LedgerCast's source files informed the review logic for terminated-user access, production approval sequence and backup evidence:

- `D:\LedgerCast\ledgercast\test_access_management.py`
- `D:\LedgerCast\ledgercast\test_change_management.py`
- `D:\LedgerCast\ledgercast\test_backup_recovery.py`

The vendor dataset, revision scenario, filenames and integrated control-review function in this project are new fictional training material. Reuse of a test method does not turn this into real supplier due diligence.

## Results scope

The baseline contains one seeded failure and one clean row for each of the three controls. The retest resolves the access and backup sample exceptions. The historical production change remains open because the approval was recorded after deployment; changing that date retroactively would falsify the evidence. Results are deterministic fixture measurements, not a judgment about an actual supplier.
