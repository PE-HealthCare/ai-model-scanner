"""Phase 1 zero-trust intake and mock feature producer owned by P1."""

from __future__ import annotations

import json
import os
import struct
from pathlib import Path

from safetensors import safe_open


MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
MAX_HEADER_SIZE = 5 * 1024 * 1024     # 5 MB
MAX_METADATA_SIZE = 1 * 1024 * 1024     # 1 MB
MAX_TENSORS = 10000
MAX_RANK = 8
MAX_DIMENSION = 1000000


def intake_model(path: Path) -> None:
    """
    Phase 2: Zero-Trust SafeTensors Intake Boundary.
    Validates limits and fails closed on violation.
    Does not return the trusted graph yet (deferred).
    """
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")

    # 1. File size limit
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"Limit violated: file size {file_size} exceeds {MAX_FILE_SIZE} bytes")
    if file_size < 8:
        raise ValueError("Integrity violated: file too small to contain a SafeTensors header")

    # 2. Header size limit
    with path.open("rb") as f:
        header_len_bytes = f.read(8)
        header_len = struct.unpack("<Q", header_len_bytes)[0]
    
    if header_len > MAX_HEADER_SIZE:
        raise ValueError(f"Limit violated: header size {header_len} exceeds {MAX_HEADER_SIZE} bytes")

    # 3. Safe open and structural validation
    try:
        with safe_open(path, framework="pt") as st:
            # 4. Metadata size limit
            metadata = st.metadata() or {}
            metadata_str = json.dumps(metadata)
            if len(metadata_str.encode("utf-8")) > MAX_METADATA_SIZE:
                raise ValueError(f"Limit violated: metadata size exceeds {MAX_METADATA_SIZE} bytes")

            # 5. Tensor count limit
            keys = st.keys()
            if len(keys) > MAX_TENSORS:
                raise ValueError(f"Limit violated: tensor count {len(keys)} exceeds {MAX_TENSORS}")
            
            # 6. Rank and dimension limits
            for key in keys:
                shape = st.get_slice(key).get_shape()
                if len(shape) > MAX_RANK:
                    raise ValueError(f"Limit violated: tensor '{key}' rank {len(shape)} exceeds {MAX_RANK}")
                for dim in shape:
                    if dim > MAX_DIMENSION:
                        raise ValueError(f"Limit violated: tensor '{key}' dimension {dim} exceeds {MAX_DIMENSION}")
                        
    except Exception as e:
        if isinstance(e, ValueError) and str(e).startswith("Limit violated:"):
            raise
        raise ValueError(f"Integrity violated: malformed SafeTensors file ({e})") from e


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
