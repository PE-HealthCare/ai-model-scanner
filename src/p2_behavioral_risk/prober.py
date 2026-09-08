"""Phase 1 mock behavioral/risk producer owned by P2."""


def build_mock_risk_results(ml_results: dict, generation_commit: str) -> dict:
    if ml_results.get("producer") != "P3" or ml_results.get("mock_status") != "MOCK":
        raise ValueError("Phase 1 mock P2 requires a P3 MOCK ML artifact")
    if ml_results.get("generation_commit") != generation_commit:
        raise ValueError("Phase 1 P2 rejects stale P3 artifact generation")
    s_static, s_behavior = 0.10, 0.05
    p_tamper = float(ml_results["p_tamper"])
    mrs_score = min(100.0, 40 * s_static + 35 * p_tamper + 25 * s_behavior)
    verdict = "PASS" if mrs_score < 35 else "REVIEW" if mrs_score < 70 else "FAIL"
    return {
        "producer": "P2", "mock_status": "MOCK", "contract_version": "1.0", "generation_commit": generation_commit,
        "mrs_score": mrs_score, "verdict": verdict, "s_static": s_static, "p_tamper": p_tamper, "s_behavior": s_behavior,
    }
