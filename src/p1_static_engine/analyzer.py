"""Phase 1 zero-trust intake and static feature producer owned by P1."""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
from safetensors import safe_open
from scipy import stats

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
MAX_HEADER_SIZE = 5 * 1024 * 1024
MAX_METADATA_SIZE = 1 * 1024 * 1024
MAX_TENSORS = 10000
MAX_RANK = 8
MAX_DIMENSION = 1000000

QUANTIZED_SAFE_TENSORS_DTYPES = {
    "I8", "U8", "F8_E5M2", "F8_E4M3", "F8_E4M3FN",
    "F8_E5M2FNUZ", "F8_E4M3FNUZ",
}
CONTROL_DTYPES = {"I64", "I32", "I16", "BOOL"}


def _is_quantized_torch_tensor(tensor: torch.Tensor) -> bool:
    quantized_dtypes = {torch.int8, torch.uint8}
    for name in (
        "float8_e5m2", "float8_e4m3", "float8_e4m3fn",
        "float8_e5m2fnuz", "float8_e4m3fnuz",
    ):
        dtype = getattr(torch, name, None)
        if dtype is not None:
            quantized_dtypes.add(dtype)
    return tensor.dtype in quantized_dtypes


@dataclass
class TrustedModelContext:
    # For FP32/FP16 this is the trusted canonical model.
    # For supported quantized input this is a scanner-controlled state-dict
    # representation preserving the submitted quantized tensor dtypes/values.
    model: Any
    architecture: str
    input_domain: str
    is_quantized: bool


def intake_model(path: Path, declared_architecture: str = None) -> Optional[TrustedModelContext]:
    """Validate a SafeTensors artifact at the zero-trust P1 boundary."""
    if declared_architecture is None:
        raise ValueError("Integrity violated: declared_architecture is required")
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")

    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"Limit violated: file size {file_size} exceeds {MAX_FILE_SIZE} bytes")
    if file_size < 8:
        raise ValueError("Integrity violated: file too small to contain a SafeTensors header")

    with path.open("rb") as f:
        header_len = struct.unpack("<Q", f.read(8))[0]
    if header_len > MAX_HEADER_SIZE:
        raise ValueError(f"Limit violated: header size {header_len} exceeds {MAX_HEADER_SIZE} bytes")

    if declared_architecture == "resnet18":
        input_domain = "VISION"
        try:
            from torchvision.models import resnet18
            trusted_model = resnet18(weights=None)
        except ImportError as exc:
            raise RuntimeError("Integrity violated: torchvision not available") from exc
    elif declared_architecture == "distilbert":
        input_domain = "NLP"
        try:
            from transformers import DistilBertConfig, DistilBertModel
            trusted_model = DistilBertModel(DistilBertConfig())
        except ImportError as exc:
            raise RuntimeError("Integrity violated: transformers not available") from exc
    else:
        raise ValueError(f"Integrity violated: Unknown architecture {declared_architecture}")

    try:
        with safe_open(path, framework="pt") as st:
            metadata = st.metadata() or {}
            if len(json.dumps(metadata).encode("utf-8")) > MAX_METADATA_SIZE:
                raise ValueError(f"Limit violated: metadata size exceeds {MAX_METADATA_SIZE} bytes")

            st_keys_list = st.keys()
            if len(st_keys_list) > MAX_TENSORS:
                raise ValueError(f"Limit violated: tensor count {len(st_keys_list)} exceeds {MAX_TENSORS}")

            trusted_state_dict = trusted_model.state_dict()
            trusted_keys = set(trusted_state_dict.keys())
            st_keys = set(st_keys_list)
            if trusted_keys != st_keys:
                missing = trusted_keys - st_keys
                unexpected = st_keys - trusted_keys
                raise ValueError(
                    "Integrity violated: architecture mismatch. "
                    f"Missing tensors: {len(missing)}, Unexpected tensors: {len(unexpected)}"
                )

            is_quantized = None
            for key in trusted_keys:
                trusted_shape = list(trusted_state_dict[key].shape)
                st_slice = st.get_slice(key)
                st_shape = list(st_slice.get_shape())
                if len(st_shape) > MAX_RANK:
                    raise ValueError(
                        f"Limit violated: tensor '{key}' rank {len(st_shape)} exceeds {MAX_RANK}"
                    )
                if any(dim > MAX_DIMENSION for dim in st_shape):
                    raise ValueError(f"Limit violated: tensor '{key}' dimension exceeds {MAX_DIMENSION}")
                if st_shape != trusted_shape:
                    raise ValueError(
                        f"Integrity violated: shape mismatch for tensor {key}. "
                        f"Expected {trusted_shape}, got {st_shape}"
                    )

                dtype_str = st_slice.get_dtype()
                if dtype_str in ("F32", "F16", "BF16", "F64"):
                    tensor_q = False
                elif dtype_str in QUANTIZED_SAFE_TENSORS_DTYPES:
                    tensor_q = True
                elif dtype_str in CONTROL_DTYPES:
                    tensor_q = None
                else:
                    raise ValueError(
                        f"Integrity violated: unknown or incompatible dtype {dtype_str} for tensor {key}"
                    )
                if tensor_q is not None:
                    if is_quantized is None:
                        is_quantized = tensor_q
                    elif is_quantized != tensor_q:
                        raise ValueError("Integrity violated: mixed/inconsistent dtype state")

            if is_quantized is None:
                is_quantized = False

            loaded_state_dict = {key: st.get_tensor(key) for key in trusted_keys}
            if is_quantized:
                # Do not assign quantized tensors into the floating-point trusted graph.
                # Preserve the validated quantized tensors in a scanner-controlled state dict.
                return TrustedModelContext(
                    model=loaded_state_dict,
                    architecture=declared_architecture,
                    input_domain=input_domain,
                    is_quantized=True,
                )

            trusted_model.requires_grad_(False)
            trusted_model.load_state_dict(loaded_state_dict, assign=True)
            return TrustedModelContext(
                model=trusted_model,
                architecture=declared_architecture,
                input_domain=input_domain,
                is_quantized=False,
            )

    except Exception as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("Limit violated:"):
            raise
        if isinstance(exc, ValueError) and str(exc).startswith("Integrity violated:"):
            raise
        raise ValueError(f"Integrity violated: malformed SafeTensors file ({exc})") from exc


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


def _state_dict_from_context(context: TrustedModelContext) -> dict:
    if isinstance(context.model, dict):
        return context.model
    return context.model.state_dict()


def _quantized_feature_array(tensor: torch.Tensor) -> np.ndarray:
    """Create a temporary numerical view for KS without altering the trusted tensor."""
    if not _is_quantized_torch_tensor(tensor):
        raise ValueError("Integrity violated: unsupported quantized tensor representation")
    # The trusted representation remains quantized; this temporary FP64 view is used
    # only to evaluate the explicitly authorized whole-weight KS statistic.
    try:
        arr = tensor.detach().cpu().to(torch.float64).numpy().reshape(-1)
    except Exception as exc:
        raise ValueError("Integrity violated: quantized values cannot be safely represented for KS") from exc
    if not np.isfinite(arr).all():
        raise ValueError("Integrity violated: NaN or Inf found in quantized layer")
    return arr


def extract_features(context: TrustedModelContext, generation_commit: str) -> dict:
    """Extract the authoritative format-adaptive P1 static feature contract."""
    if context is None or context.model is None:
        raise ValueError("Integrity violated: Valid TrustedModelContext required")

    state_dict = _state_dict_from_context(context)
    if context.is_quantized:
        feature_tensors = {
            name: tensor for name, tensor in state_dict.items()
            if _is_quantized_torch_tensor(tensor)
        }
    else:
        feature_tensors = {
            name: tensor for name, tensor in state_dict.items()
            if tensor.is_floating_point()
        }

    layer_names = list(feature_tensors.keys())
    if len(layer_names) < 3:
        raise ValueError("Integrity violated: insufficient-baseline condition (fewer than 3 layers)")

    tensors = {}
    for name in layer_names:
        tensor = feature_tensors[name]
        if tensor.numel() == 0:
            raise ValueError(f"Integrity violated: empty tensor {name}")
        if context.is_quantized:
            tensors[name] = _quantized_feature_array(tensor)
        else:
            arr = tensor.detach().cpu().numpy()
            if not np.isfinite(arr).all():
                raise ValueError(f"Integrity violated: NaN or Inf found in layer {name}")
            tensors[name] = arr.reshape(-1)

    static_features = []
    for layer_name in layer_names:
        arr = tensors[layer_name]
        pooled_other = np.concatenate([tensors[k] for k in layer_names if k != layer_name])
        ks_stat = float(stats.ks_2samp(arr, pooled_other).statistic)

        if context.is_quantized:
            feat_dict = {
                "layer_name": layer_name,
                "entropy": None,
                "pov_chi2": None,
                "lsb_kl": None,
                "ks_stat": ks_stat,
                "mean": None,
                "std": None,
                "skewness": None,
                "kurtosis": None,
                "sparsity": None,
                "outlier_pct": None,
            }
        else:
            if arr.dtype == np.float32:
                arr_uint = arr.view(np.uint32)
            elif arr.dtype == np.float16:
                arr_uint = arr.view(np.uint16)
            else:
                raise ValueError(f"Integrity violated: unsupported FP dtype {arr.dtype} for bit analysis")

            arr_bytes = arr.view(np.uint8)
            counts = np.bincount(arr_bytes, minlength=256)
            p = counts[counts > 0] / counts.sum()
            entropy = float(-np.sum(p * np.log2(p)))

            lsbs = arr_uint & 1
            count1 = np.count_nonzero(lsbs)
            count0 = lsbs.size - count1
            chi2_stat, _ = stats.chisquare(
                [count0, count1], f_exp=[lsbs.size / 2.0, lsbs.size / 2.0]
            )
            pov_chi2 = float(chi2_stat)
            p_lsb = [count0 / lsbs.size, count1 / lsbs.size]
            lsb_kl = float(stats.entropy(p_lsb, [0.5, 0.5]))

            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr, ddof=0))
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                skew_val = float(stats.skew(arr, bias=True))
                kurt_val = float(stats.kurtosis(arr, fisher=False, bias=True))

            sparsity = float(np.count_nonzero(arr == 0)) / arr.size
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
                "outlier_pct": outlier_pct,
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
        "static_features": static_features,
    }
