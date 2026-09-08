"""Phase 1 zero-trust intake and mock feature producer owned by P1."""

from __future__ import annotations

import json
import os
import struct
from pathlib import Path

from safetensors import safe_open


from dataclasses import dataclass
from typing import Any, Optional

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
MAX_HEADER_SIZE = 5 * 1024 * 1024     # 5 MB
MAX_METADATA_SIZE = 1 * 1024 * 1024     # 1 MB
MAX_TENSORS = 10000
MAX_RANK = 8
MAX_DIMENSION = 1000000

@dataclass
class TrustedModelContext:
    model: Any
    architecture: str
    input_domain: str
    is_quantized: bool

def intake_model(path: Path, declared_architecture: str = None) -> Optional[TrustedModelContext]:
    """
    Phase 2: Zero-Trust SafeTensors Intake Boundary.
    Validates limits, architecture, and returns the trusted model context.
    """
    if declared_architecture is None:
        raise ValueError("Integrity violated: declared_architecture is required")

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

    # 3. Architecture Registry and Trusted Canonical Model
    if declared_architecture == "resnet18":
        input_domain = "VISION"
        try:
            from torchvision.models import resnet18
            trusted_model = resnet18(weights=None)
        except ImportError:
            raise RuntimeError("Integrity violated: torchvision not available")
    elif declared_architecture == "distilbert":
        input_domain = "NLP"
        try:
            from transformers import DistilBertConfig, DistilBertModel
            config = DistilBertConfig()
            trusted_model = DistilBertModel(config)
        except ImportError:
            raise RuntimeError("Integrity violated: transformers not available")
    else:
        raise ValueError(f"Integrity violated: Unknown architecture {declared_architecture}")

    # 4. Safe open and structural validation
    try:
        with safe_open(path, framework="pt") as st:
            # 5. Metadata size limit
            metadata = st.metadata() or {}
            metadata_str = json.dumps(metadata)
            if len(metadata_str.encode("utf-8")) > MAX_METADATA_SIZE:
                raise ValueError(f"Limit violated: metadata size exceeds {MAX_METADATA_SIZE} bytes")

            # 6. Tensor count limit
            st_keys_list = st.keys()
            if len(st_keys_list) > MAX_TENSORS:
                raise ValueError(f"Limit violated: tensor count {len(st_keys_list)} exceeds {MAX_TENSORS}")

            # 7. Trusted Architecture Validation
            trusted_state_dict = trusted_model.state_dict()
            trusted_keys = set(trusted_state_dict.keys())
            st_keys = set(st_keys_list)

            if trusted_keys != st_keys:
                missing = trusted_keys - st_keys
                unexpected = st_keys - trusted_keys
                raise ValueError(f"Integrity violated: architecture mismatch. Missing tensors: {len(missing)}, Unexpected tensors: {len(unexpected)}")

            is_quantized = None
            
            for key in trusted_keys:
                trusted_tensor = trusted_state_dict[key]
                trusted_shape = list(trusted_tensor.shape)
                
                st_slice = st.get_slice(key)
                st_shape = list(st_slice.get_shape())
                
                # Rank and Dimension limits
                if len(st_shape) > MAX_RANK:
                    raise ValueError(f"Limit violated: tensor '{key}' rank {len(st_shape)} exceeds {MAX_RANK}")
                if any(dim > MAX_DIMENSION for dim in st_shape):
                    raise ValueError(f"Limit violated: tensor '{key}' dimension exceeds {MAX_DIMENSION}")
                
                # Shape equality
                if st_shape != trusted_shape:
                    raise ValueError(f"Integrity violated: shape mismatch for tensor {key}. Expected {trusted_shape}, got {st_shape}")
                    
                # Dtype and Quantization checking
                dtype_str = st_slice.get_dtype()
                
                if dtype_str in ("F32", "F16", "BF16", "F64"):
                    tensor_q = False
                elif dtype_str in ("I8", "U8", "F8_E5M2", "F8_E4M3", "F8_E4M3FN", "F8_E5M2FNUZ", "F8_E4M3FNUZ"):
                    tensor_q = True
                elif dtype_str in ("I64", "I32", "I16", "BOOL"):
                    tensor_q = None # Control tensor, ignore for quantization tracking
                else:
                    raise ValueError(f"Integrity violated: unknown or incompatible dtype {dtype_str} for tensor {key}")
                    
                if tensor_q is not None:
                    if is_quantized is None:
                        is_quantized = tensor_q
                    elif is_quantized != tensor_q:
                        raise ValueError("Integrity violated: mixed/inconsistent dtype state")
                        
            if is_quantized is True:
                raise ValueError("Integrity violated: unsupported-quantized-graph (cannot safely load INT8/FP8 artifact into trusted graph without unapproved conversion)")
                
            if is_quantized is None:
                is_quantized = False

            return TrustedModelContext(
                model=trusted_model,
                architecture=declared_architecture,
                input_domain=input_domain,
                is_quantized=is_quantized
            )
                        
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
