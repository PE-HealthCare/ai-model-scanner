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

import numpy as np
from scipy import stats

def extract_features(context: TrustedModelContext, generation_commit: str) -> dict:
    """
    Phase 3: Real Static Feature Extractor.
    Extracts the 10-feature schema layer-by-layer from the trusted model context.
    """
    if context is None or context.model is None:
        raise ValueError("Integrity violated: Valid TrustedModelContext required")
        
    state_dict = context.model.state_dict()
    layer_names = list(state_dict.keys())
    
    if len(layer_names) < 3:
        raise ValueError("Integrity violated: insufficient-baseline condition (fewer than 3 layers)")
        
    tensors = {}
    for name in layer_names:
        tensor = state_dict[name]
        if tensor.numel() == 0:
            raise ValueError(f"Integrity violated: empty tensor {name}")
            
        # Extract numpy array
        arr = tensor.detach().cpu().numpy()
        
        # Check NaN/Inf
        if not np.isfinite(arr).all():
            raise ValueError(f"Integrity violated: NaN or Inf found in layer {name}")
            
        tensors[name] = arr.flatten()
        
    static_features = []
    
    for layer_name in layer_names:
        arr = tensors[layer_name]
        
        # KS Statistic (against pooled other layers)
        other_arrays = [tensors[k] for k in layer_names if k != layer_name]
        pooled_other = np.concatenate(other_arrays)
        ks_stat = float(stats.ks_2samp(arr, pooled_other).statistic)
        
        if context.is_quantized:
            # Quantized: whole-weight KS only
            # The schema requires 10 features, but for quantized, we only compute KS.
            # Schema states missing properties violate schema unless they are populated.
            # "Keep the output representation contract consistent with the existing project schema."
            # We will populate others with NaN or 0? 
            # Wait, the PLAN says "Quantized behavior retains the finalized format-adaptive rules" 
            # and schema has required fields. If they are required, we output NaN or None.
            # Python json.dumps serializes float('nan') as NaN.
            feat_dict = {
                "layer_name": layer_name,
                "entropy": float('nan'),
                "pov_chi2": float('nan'),
                "lsb_kl": float('nan'),
                "ks_stat": ks_stat,
                "mean": float('nan'),
                "std": float('nan'),
                "skewness": float('nan'),
                "kurtosis": float('nan'),
                "sparsity": float('nan'),
                "outlier_pct": float('nan')
            }
        else:
            # FP32/FP16 Features
            
            # Bit-level features
            if arr.dtype == np.float32:
                arr_uint = arr.view(np.uint32)
            elif arr.dtype == np.float16:
                arr_uint = arr.view(np.uint16)
            else:
                raise ValueError(f"Integrity violated: unsupported FP dtype {arr.dtype} for bit analysis")
                
            # 1. Entropy
            arr_bytes = arr.view(np.uint8)
            counts = np.bincount(arr_bytes, minlength=256)
            p = counts[counts > 0] / counts.sum()
            entropy = float(-np.sum(p * np.log2(p)))
            
            # 2. PoV chi2 & 3. LSB KL
            lsbs = arr_uint & 1
            count1 = np.count_nonzero(lsbs)
            count0 = lsbs.size - count1
            
            chi2_stat, _ = stats.chisquare([count0, count1], f_exp=[lsbs.size/2.0, lsbs.size/2.0])
            pov_chi2 = float(chi2_stat)
            
            p_lsb = [count0 / lsbs.size, count1 / lsbs.size]
            lsb_kl = float(stats.entropy(p_lsb, [0.5, 0.5]))
            
            # 5-8. Moments
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr, ddof=0))
            
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                skew_val = float(stats.skew(arr, bias=True))
                kurt_val = float(stats.kurtosis(arr, fisher=False, bias=True))
            
            # 9. Sparsity
            sparsity = float(np.count_nonzero(arr == 0)) / arr.size
            
            # 10. Outlier Percentage
            q1, q3 = np.percentile(arr, [25, 75])
            iqr = q3 - q1
            outliers = np.sum((arr < q1 - 1.5 * iqr) | (arr > q3 + 1.5 * iqr))
            outlier_pct = float(outliers) / arr.size * 100.0
            
            feat_dict = {
                "layer_name": layer_name,
                "entropy": entropy,
                "pov_chi2": pov_chi2,
                "lsb_kl": lsb_kl,
                "ks_stat": ks_stat,
                "mean": mean_val,
                "std": std_val,
                "skewness": skew_val,
                "kurtosis": kurt_val,
                "sparsity": sparsity,
                "outlier_pct": outlier_pct
            }
            
        static_features.append(feat_dict)
            
    return {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": generation_commit,
        "input_domain": context.input_domain,
        "is_quantized": context.is_quantized,
        "layer_count": len(layer_names),
        "static_features": static_features
    }
