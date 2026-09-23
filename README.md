# AI Model Scanner

Detection of Steganographic Malware Hidden in AI Model Weights.

## Development

Implementation follows the phased plan in `.planning/phases/` and the ownership rules in `docs/contribution-rules.md`.
## Checkpoint Status

### CP4 — ML Classification: PASS

CP4 has been verified on `recovery-mainline` at commit `e5d1ab5`.

- LightGBM classifier trained from verified-real P1 feature extraction
- 96 training rows: 48 clean and 48 tampered
- Model artifact: `artifacts/lightgbm_model.txt`
- Provenance: `artifacts/lightgbm_model.provenance.json`
- `ml_results.json`: `VERIFIED-REAL`
- `P_tamper`: `0.9900758624030114`
- TreeSHAP: 10 canonical feature attributions
- Classifier regression suite: **27/27 tests passed**
- P1 generation commit recorded in ML output: `594c9a91df08a211ee1270de566c70d61205af26`

This verifies the CP4 ML pipeline and its regression evidence. It does **not** establish real-world classifier accuracy or generalization performance.
