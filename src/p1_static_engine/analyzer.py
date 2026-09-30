"""Phase 1 zero-trust intake and static feature producer owned by P1."""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
import torch
from safetensors import safe_open
from scipy import stats

from src.common.feature_names import B0_FEATURE_NAMES, B1_ADDITIONAL_FEATURE_NAMES

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
MAX_HEADER_SIZE = 5 * 1024 * 1024
MAX_METADATA_SIZE = 1 * 1024 * 1024
MAX_TENSORS = 10000
MAX_RANK = 8
MAX_DIMENSION = 1000000
LOCAL_WINDOW_BYTES = 4096
MAX_LOCAL_WINDOWS = 8

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
            # Start from the canonical [2, 2, 2, 2] BasicBlock contract.  A
            # submitted ResNet18 may later select only its classifier output
            # count; every backbone key and shape remains exact below.
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

            st_keys = set(st_keys_list)
            trusted_state_dict = trusted_model.state_dict()
            trusted_keys = set(trusted_state_dict.keys())
            if trusted_keys != st_keys:
                missing = trusted_keys - st_keys
                unexpected = st_keys - trusted_keys
                raise ValueError(
                    "Integrity violated: architecture mismatch. "
                    f"Missing tensors: {len(missing)}, Unexpected tensors: {len(unexpected)}"
                )

            if declared_architecture == "resnet18":
                # This is the sole permitted ResNet18 variation: a genuine
                # classifier output count.  Its input width, its bias, every
                # key, and every non-head tensor remain validated exactly.
                fc_weight_shape = list(st.get_slice("fc.weight").get_shape())
                fc_bias_shape = list(st.get_slice("fc.bias").get_shape())
                if (
                    len(fc_weight_shape) != 2
                    or len(fc_bias_shape) != 1
                    or fc_weight_shape[1] != 512
                    or fc_weight_shape[0] <= 0
                    or fc_weight_shape[0] > MAX_DIMENSION
                    or fc_bias_shape != [fc_weight_shape[0]]
                ):
                    raise ValueError(
                        "Integrity violated: invalid ResNet18 classifier contract; "
                        "expected fc.weight [classes, 512] and fc.bias [classes]"
                    )
                trusted_model = resnet18(weights=None, num_classes=fc_weight_shape[0])
                trusted_state_dict = trusted_model.state_dict()

            is_quantized = None
            for key in st_keys_list:
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

            # Materialize every validated tensor, including control tensors,
            # while excluding them from quantized statistical evidence below.
            loaded_state_dict = {key: st.get_tensor(key) for key in st_keys_list}
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
        "is_quantized": False, "layer_count": 3,
        "static_features": [
            {"layer_name": "mock.layer1", "entropy": 0.98, "pov_chi2": 1.05, "lsb_kl": 0.02, "ks_stat": 0.12, "mean": 0.01, "std": 0.24, "skewness": -0.08, "kurtosis": 2.91, "sparsity": 0.08, "outlier_pct": 0.30},
            {"layer_name": "mock.layer2", "entropy": 0.95, "pov_chi2": 1.10, "lsb_kl": 0.03, "ks_stat": 0.15, "mean": -0.02, "std": 0.27, "skewness": 0.11, "kurtosis": 3.12, "sparsity": 0.10, "outlier_pct": 0.40},
            {"layer_name": "mock.layer3", "entropy": 0.97, "pov_chi2": 1.08, "lsb_kl": 0.025, "ks_stat": 0.13, "mean": 0.015, "std": 0.25, "skewness": 0.02, "kurtosis": 3.01, "sparsity": 0.09, "outlier_pct": 0.35},
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


def _ks_stat_against_global(layer_values: np.ndarray, global_sorted: np.ndarray) -> float:
    """Exact two-sample KS statistic for a layer versus all other layers.

    ``global_sorted`` is the sorted union of this layer and every eligible
    layer.  At each distinct layer value, the reference ECDF is reconstructed
    as ``(global_count - layer_count) / other_size``.  The ECDF difference can
    only attain a maximum immediately before or after a layer-value jump, so
    checking those two boundaries is equivalent to scipy's scan over the
    combined samples, including ties.
    """
    values, counts = np.unique(layer_values, return_counts=True)
    layer_size = layer_values.size
    other_size = global_sorted.size - layer_size
    if other_size <= 0:
        raise ValueError("Integrity violated: insufficient KS reference population")

    global_before = np.searchsorted(global_sorted, values, side="left")
    global_after = np.searchsorted(global_sorted, values, side="right")
    layer_after = np.cumsum(counts)
    layer_before = layer_after - counts

    before_difference = np.abs(
        layer_before / layer_size - (global_before - layer_before) / other_size
    )
    after_difference = np.abs(
        layer_after / layer_size - (global_after - layer_after) / other_size
    )
    return float(max(np.max(before_difference), np.max(after_difference)))


def _bit_layout(arr: np.ndarray) -> tuple[np.ndarray, int, int, int]:
    """Return raw IEEE bits and layout parameters for supported FP tensors."""
    if arr.dtype == np.float32:
        return arr.view(np.uint32), 31, 23, 8
    if arr.dtype == np.float16:
        return arr.view(np.uint16), 15, 10, 5
    raise ValueError(f"Integrity violated: unsupported FP dtype {arr.dtype} for bit analysis")


def _mean_lag1_autocorrelation(values: np.ndarray) -> float:
    """Finite lag-1 Pearson autocorrelation; constant sequences are fully persistent."""
    if values.size < 2 or np.all(values == values[0]):
        return 1.0
    left = values[:-1].astype(np.float64)
    right = values[1:].astype(np.float64)
    left -= left.mean()
    right -= right.mean()
    denominator = np.sqrt(np.dot(left, left) * np.dot(right, right))
    return 1.0 if denominator == 0 else float(np.dot(left, right) / denominator)


def _b1_features(arr: np.ndarray) -> dict[str, float]:
    """Bounded B1 evidence using deterministic byte/element chunks.

    At most eight contiguous chunks are used.  Small tensors are split at
    approximately 4096-byte boundaries; larger tensors use up to eight equal
    contiguous chunks, so memory remains bounded to one tensor view and the
    scan stays linear in that tensor's size.  Window KL compares each chunk's
    byte distribution with this same tensor's full byte distribution, then
    reports the mean chunk KL.
    """
    arr = np.ascontiguousarray(arr.reshape(-1))
    bits, sign_shift, mantissa_shift, exponent_width = _bit_layout(arr)
    # Distributional arithmetic uses FP64 working precision.  ``arr`` stays
    # untouched so all byte/bit evidence below retains the submitted FP16/32
    # representation.  This prevents finite FP32 values from overflowing in
    # intermediate moment/dispersion calculations.
    distribution_values = arr.astype(np.float64, copy=False)
    mean = float(np.mean(distribution_values))
    std = float(np.std(distribution_values, ddof=0))
    quantiles = np.percentile(distribution_values, [1, 5, 25, 50, 75, 95, 99])
    exponent = (bits >> mantissa_shift) & ((1 << exponent_width) - 1)
    lsbs = bits & 1
    bytes_view = arr.view(np.uint8)
    global_counts = np.bincount(bytes_view, minlength=256).astype(np.float64)
    global_distribution = global_counts / global_counts.sum()
    window_count = min(MAX_LOCAL_WINDOWS, max(1, int(np.ceil(bytes_view.size / LOCAL_WINDOW_BYTES))))
    byte_windows = np.array_split(bytes_view, window_count)
    bit_windows = np.array_split(lsbs, window_count)
    byte_entropies = []
    byte_kls = []
    byte_autocorrelations = []
    for window in byte_windows:
        counts = np.bincount(window, minlength=256).astype(np.float64)
        distribution = counts / counts.sum()
        present = distribution > 0
        byte_entropies.append(float(-np.sum(distribution[present] * np.log2(distribution[present]))))
        byte_kls.append(float(np.sum(
            distribution[present] * np.log(distribution[present] / global_distribution[present])
        )))
        byte_autocorrelations.append(_mean_lag1_autocorrelation(window))
    global_lsb_fraction = float(np.mean(lsbs))
    local_lsb_deviations = [abs(float(np.mean(window)) - global_lsb_fraction) for window in bit_windows]
    return {
        "q01": float(quantiles[0]), "q05": float(quantiles[1]),
        "q25": float(quantiles[2]), "q50": float(quantiles[3]),
        "q75": float(quantiles[4]), "q95": float(quantiles[5]),
        "q99": float(quantiles[6]), "iqr": float(quantiles[4] - quantiles[2]),
        # A bounded relative-dispersion CV definition: std / (abs(mean) + std).
        # It equals 0 for any constant finite tensor and 1 for a non-constant
        # exactly-zero-mean tensor, so finite near-zero means never create
        # invalid evidence or receive an arbitrary imputed training value.
        "coefficient_of_variation": 0.0 if std == 0.0 else std / (abs(mean) + std),
        "sign_bit_fraction": float(np.mean((bits >> sign_shift) & 1)),
        "exponent_mean": float(np.mean(exponent)),
        "exponent_std": float(np.std(exponent, ddof=0)),
        "mantissa_lsb_imbalance": float(abs(2.0 * global_lsb_fraction - 1.0)),
        "low_bit_transition_rate": float(np.mean(lsbs[1:] != lsbs[:-1])) if lsbs.size > 1 else 0.0,
        "window_byte_entropy_mean": float(np.mean(byte_entropies)),
        "local_byte_lag1_autocorrelation": float(np.mean(byte_autocorrelations)),
        "local_byte_kl_mean": float(np.mean(byte_kls)),
        "local_low_bit_deviation_mean": float(np.mean(local_lsb_deviations)),
    }


def extract_features(
    context: TrustedModelContext,
    generation_commit: str,
    *,
    layer_names: Sequence[str] | None = None,
    feature_set: str = "b0",
) -> dict:
    """Extract the authoritative format-adaptive P1 static feature contract.

    Optional CP4-scoped performance filter: when ``layer_names`` is given,
    only those layers get rows in ``static_features`` (and ``layer_count``
    reflects the selection). All zero-trust integrity checks still run over
    the full submitted model, all 10 feature definitions/formulas are
    unchanged, and each selected layer's KS reference pool still spans the
    full model. Existing callers omitting the filter see identical output.
    """
    if context is None or context.model is None:
        raise ValueError("Integrity violated: Valid TrustedModelContext required")
    if feature_set not in {"b0", "b1"}:
        raise ValueError(f"Integrity violated: unsupported feature_set {feature_set!r}")
    if feature_set == "b1" and context.is_quantized:
        raise ValueError("Integrity violated: B1 is supported only for FP32/FP16 tensors")

    state_dict = _state_dict_from_context(context)
    if context.is_quantized:
        feature_tensors = {
            name: tensor for name, tensor in state_dict.items()
            if _is_quantized_torch_tensor(tensor)
        }
        unsupported = [
            name for name, tensor in state_dict.items()
            if not _is_quantized_torch_tensor(tensor)
            and tensor.dtype not in {
                torch.int64, torch.int32, torch.int16, torch.bool,
            }
        ]
        if unsupported:
            raise ValueError(
                "Integrity violated: unsupported quantized tensor representation "
                f"for tensor {unsupported[0]!r}"
            )
    else:
        feature_tensors = {
            name: tensor for name, tensor in state_dict.items()
            if tensor.is_floating_point()
        }

    all_layer_names = list(feature_tensors.keys())
    if len(all_layer_names) < 3:
        raise ValueError("Integrity violated: insufficient-baseline condition (fewer than 3 layers)")

    tensors = {}
    for name in all_layer_names:
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

    if layer_names is not None:
        requested = list(layer_names)
        if not requested:
            raise ValueError("Integrity violated: layer_names filter must be non-empty")
        if len(requested) < 3:
            raise ValueError(
                "Integrity violated: layer_names filter must select at least 3 layers"
            )
        unknown = [name for name in requested if name not in tensors]
        if unknown:
            raise ValueError(f"Integrity violated: unknown layer requested: {unknown[0]!r}")
        selected_layer_names = requested
    else:
        selected_layer_names = list(all_layer_names)

    # The old per-layer scipy call sorted an almost-identical concatenation of
    # all other FP tensors for every layer.  Sort the one model-wide union once
    # and reconstruct each unchanged "all other layers" ECDF exactly below.
    global_sorted = None
    if not context.is_quantized:
        global_sorted = np.concatenate(list(tensors.values()))
        global_sorted.sort()

    static_features = []
    for layer_name in selected_layer_names:
        arr = tensors[layer_name]
        if context.is_quantized:
            pooled_other = np.concatenate([tensors[k] for k in all_layer_names if k != layer_name])
            ks_stat = float(stats.ks_2samp(arr, pooled_other).statistic)
        else:
            ks_stat = _ks_stat_against_global(arr, global_sorted)

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
            arr_uint, _, _, _ = _bit_layout(arr)

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

            # Use a temporary FP64 view for real-valued distributional
            # statistics only.  It preserves the existing SciPy definitions
            # while avoiding FP16/32 overflow in centered powers.  The raw
            # tensor remains the sole source for bit/byte forensic features.
            distribution_values = arr.astype(np.float64, copy=False)
            mean_val = float(np.mean(distribution_values))
            std_val = float(np.std(distribution_values, ddof=0))
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                skew_val = float(stats.skew(distribution_values, bias=True))
                kurt_val = float(stats.kurtosis(distribution_values, fisher=False, bias=True))

            sparsity = float(np.count_nonzero(arr == 0)) / arr.size
            q1, q3 = np.percentile(distribution_values, [25, 75])
            iqr = q3 - q1
            outliers = np.sum(
                (distribution_values < q1 - 1.5 * iqr)
                | (distribution_values > q3 + 1.5 * iqr)
            )
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
            if feature_set == "b1":
                feat_dict.update(_b1_features(arr))
            # Fail closed: every required FP statistical feature must be a
            # finite numeric value before this layer may be emitted.
            for _feature_name in B0_FEATURE_NAMES + (
                B1_ADDITIONAL_FEATURE_NAMES if feature_set == "b1" else ()
            ):
                if not np.isfinite(feat_dict[_feature_name]):
                    raise ValueError(
                        "Integrity violated: non-finite derived feature "
                        f"{_feature_name} in layer {layer_name}"
                    )
        static_features.append(feat_dict)

    result = {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": generation_commit,
        "input_domain": context.input_domain,
        "is_quantized": context.is_quantized,
        "layer_count": len(selected_layer_names),
        "static_features": static_features,
    }
    # Omit this optional marker for B0 so legacy serialized output remains
    # byte-for-byte shape-compatible; B1 must identify its wider contract.
    if feature_set == "b1":
        result["feature_set"] = "B1"
    return result
