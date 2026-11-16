# Expected vendor ITGC fixture outcomes

**All data is synthetic.** The independent key is `itgc_expected.json`; the engine does not read it during control evaluation.

| Control | Baseline | Revised population | Reviewer follow-up |
|---|---|---|---|
| ITGC-ACCESS | One terminated account remains enabled after termination. One separate row meets this selected check. | The original post-termination login remains in the retest. Access is disabled and removed on 2026-11-16, so current exposure is marked resolved while the historical control gap stays open. | Review actual evidence before any real closure. |
| ITGC-CHANGE | One production deployment predates approval. One separate row is approved on time. | The historical sequence remains unchanged. | Obtain a corrected future change record; never backdate approval. Keep the historical exception for review. |
| ITGC-BACKUP | Job BKP-301 failed and has no completed restore test. One separate row passes both selected checks. | The baseline record BKP-301 remains unchanged. A distinct 2026-11-16 job BKP-303 is the retest observation and has a passed mock restore test; the prior failure remains in baseline history. | Review the actual restore scope, evidence and exceptions before closing a real finding. |

The lab's baseline gate is 3/3 expected seeded controls with a detected exception, with no finding on the selected clean rows. The retest has two historical exceptions (ITGC-ACCESS and ITGC-CHANGE); current access exposure is resolved, and the new backup job passes while the original failed job remains part of the baseline history. These are fixture acceptance conditions; do not advertise them as enterprise detection rates.
