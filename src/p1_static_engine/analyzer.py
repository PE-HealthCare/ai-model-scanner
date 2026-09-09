"""P1 static engine: real steganalysis feature extraction + Phase 1 mock.

Real path:
    build_features(model_path, generation_commit)
        -> zero-trust intake (intake.py) -> deterministic per-layer static
        features -> features.json payload (mock_status="VERIFIED-REAL").

Mock path (Phase 1, preserved for tests):
    build_mock_features(generation_commit)

All statistics are implemented with vectorized NumPy only (no scipy), and are
deterministic functions of the tensor bytes. The 10 feature names and their
order are fixed by the Master Graph and encoded in contracts/features.schema.json:

    entropy, pov_chi2, lsb_kl, ks_stat, mean, std, skewness, kurtosis,
    sparsity, outlier_pct

Feature definitions (documented for explainability):
- entropy:     Shannon entropy (bits) of the 256-bin value histogram,
               normalized by log2(256)=8 so it lies in [0, 1].
- pov_chi2:    Pearson chi-square statistic of the 256-bin observed histogram
               against counts expected under a fitted Gaussian, divided by
               degrees of freedom (255). ~1 means distribution-shaped like a
               normal; large values flag distributional anomalies.
- lsb_kl:      KL divergence (bits) of the empirical LSB distribution of the
               raw float bit pattern against a uniform 50/50 LSB. Natural
               weights have biased LSBs (KL > 0); LSB steganography drives
               the LSB toward uniform (KL -> 0).
- ks_stat:     Kolmogorov-Smirnov statistic (max ECDF deviation) of the values
               against a Gaussian fitted to their own mean/std.
- mean/std:    Arithmetic mean / population standard deviation.
- skewness:    m3 / m2^1.5 (population).
- kurtosis:    m4 / m2^2 (non-excess; Gaussian ~ 3).
- sparsity:    fraction of elements with |value| < 1e-6.
- outlier_pct: percentage of elements with |value - mean| > 3 * std.
"""

from __future__ import annotations

import numpy as np

from src.common.feature_names import FEATURE_NAMES
from src.p1_static_engine.intake import load_safetensors

__all__ = ["FEATURE_NAMES", 
           "build_features", "build_mock_features", 
           "extract_layer_features"]

_HISTOGRAM_BINS = 256
_SPARSITY_EPS = 1e-6
_OUTLIER_SIGMA = 3.0

_NLP_HINTS = ("embed", "token", "word", "wte", "wpe", "vocab", "position", "bert", "gpt")


def _erf(x: np.ndarray) -> np.ndarray:
    """Vectorized error function (Abramowitz & Stegun 7.1.26, |eps| < 1.5e-7)."""
    sign = np.sign(x)
    a = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * a)
    poly = t * (
        0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))
    )
    return sign * (1.0 - poly * np.exp(-(a * a)))


def _normal_cdf(x: np.ndarray, mean: float, std: float) -> np.ndarray:
    return 0.5 * (1.0 + _erf((x - mean) / (std * np.sqrt(2.0))))


def _uint_view(arr: np.ndarray) -> np.ndarray:
    if arr.dtype == np.float32:
        return arr.view(np.uint32)
    if arr.dtype == np.float64:
        return arr.view(np.uint64)
    if arr.dtype == np.float16:
        return arr.view(np.uint16)
    raise TypeError(f"unsupported dtype for LSB analysis: {arr.dtype}")


def extract_layer_features(arr: np.ndarray) -> dict[str, float]:
    """Compute the 10 contractual static features for one tensor."""
    if arr.size < 16:
        raise ValueError(f"tensor too small for statistical analysis ({arr.size} elements)")
    x = np.ascontiguousarray(arr).astype(np.float64).ravel()
    n = x.size

    mean = float(x.mean())
    std = float(x.std())

    # --- entropy over 256 equal-width bins spanning [min, max] -------------
    counts, _ = np.histogram(x, bins=_HISTOGRAM_BINS)
    p = counts.astype(np.float64) / n
    p = p[p > 0.0]
    entropy = float(-(p * np.log2(p)).sum() / np.log2(_HISTOGRAM_BINS))

    # --- pov_chi2: observed vs fitted-Gaussian expected counts -------------
    lo, hi = float(x.min()), float(x.max())
    if hi <= lo:  # degenerate constant tensor
        pov_chi2 = 0.0
    else:
        edges = np.linspace(lo, hi, _HISTOGRAM_BINS + 1)
        edges[0] = np.nextafter(lo, -np.inf)
        edges[-1] = np.nextafter(hi, np.inf)
        expected = np.diff(_normal_cdf(edges, mean, std)) * n
        mask = expected > 1e-12
        chi2 = float((((counts[mask] - expected[mask]) ** 2) / expected[mask]).sum())
        pov_chi2 = chi2 / (_HISTOGRAM_BINS - 1)

    # --- lsb_kl: LSB distribution vs uniform --------------------------------
    lsb = (_uint_view(np.ascontiguousarray(arr)).ravel() & 1).astype(np.float64)
    p1 = float(lsb.mean())
    p1 = min(max(p1, 1e-12), 1.0 - 1e-12)
    lsb_kl = float(p1 * np.log2(p1 / 0.5) + (1.0 - p1) * np.log2((1.0 - p1) / 0.5))

    # --- ks_stat vs fitted Gaussian -----------------------------------------
    xs = np.sort(x)
    fitted = _normal_cdf(xs, mean, std)
    ecdf_hi = np.arange(1, n + 1, dtype=np.float64) / n
    ecdf_lo = np.arange(0, n, dtype=np.float64) / n
    ks_stat = float(max(np.abs(ecdf_hi - fitted).max(), np.abs(ecdf_lo - fitted).max()))

    # --- moments -------------------------------------------------------------
    centered = x - mean
    m2 = float((centered**2).mean())
    if m2 > 0.0:
        skewness = float((centered**3).mean() / m2**1.5)
        kurtosis = float((centered**4).mean() / (m2 * m2))
    else:
        skewness, kurtosis = 0.0, 0.0

    sparsity = float((np.abs(x) < _SPARSITY_EPS).mean())
    outlier_pct = (
        float((np.abs(centered) > _OUTLIER_SIGMA * std).mean() * 100.0) if std > 0.0 else 0.0
    )

    values = {
        "entropy": entropy,
        "pov_chi2": pov_chi2,
        "lsb_kl": lsb_kl,
        "ks_stat": ks_stat,
        "mean": mean,
        "std": std,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "sparsity": sparsity,
        "outlier_pct": outlier_pct,
    }
    return {name: float(values[name]) for name in FEATURE_NAMES}


def _infer_input_domain(layer_names: list[str]) -> str:
    joined = " ".join(layer_names).lower()
    return "NLP" if any(hint in joined for hint in _NLP_HINTS) else "VISION"


def build_features(model_path, generation_commit: str) -> dict:
    """Zero-trust analysis of a SafeTensors artifact -> features payload."""
    tensors = load_safetensors(model_path)
    static_features = [
        {"layer_name": name, **extract_layer_features(tensors[name])}
        for name in sorted(tensors)
    ]
    return {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": generation_commit,
        "input_domain": _infer_input_domain([f["layer_name"] for f in static_features]),
        "is_quantized": False,  # intake whitelist only accepts float dtypes
        "layer_count": len(static_features),
        "static_features": static_features,
    }


def build_mock_features(generation_commit: str) -> dict:
    return {
        "producer": "P1", "mock_status": "MOCK", "contract_version": "1.0",
        "generation_commit": generation_commit, "input_domain": "VISION",
        "is_quantized": False, "layer_count": 2,
        "static_features": [
            {"layer_name": "mock.layer1", "entropy": 0.98, "pov_chi2": 1.05, "lsb_kl": 0.02, "ks_stat": 0.12, "mean": 0.01, "std": 0.24, "skewness": -0.08, "kurtosis": 2.91, "sparsity": 0.08, "outlier_pct": 0.30},
            {"layer_name": "mock.layer2", "entropy": 0.95, "pov_chi2": 1.10, "lsb_kl": 0.03, "ks_stat": 0.15, "mean": -0.02, "std": 0.27, "skewness": 0.11, "kurtosis": 3.12, "sparsity": 0.10, "outlier_pct": 0.40},
        ],
    }