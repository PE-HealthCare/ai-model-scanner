"""P1 D2 trusted ResNet18 construction (recovered from a7cd019).

ResNet18-only side path beside the NumPy static-extraction path.
Historical source: a7cd019 analyzer.py TrustedModelContext/intake_model.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from safetensors import safe_open

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
MAX_HEADER_SIZE = 5 * 1024 * 1024
MAX_METADATA_SIZE = 1 * 1024 * 1024
def intake_model(path: Path, declared_architecture: str | None = None):
    if declared_architecture is None:
        raise ValueError("Integrity violated: declared_architecture is required")
    if declared_architecture != "resnet18":
        raise ValueError("Integrity violated: only resnet18 is supported in recovery")
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
    try:
        from torchvision.models import resnet18
        trusted_model = resnet18(weights=None)
    except ImportError as exc:
        raise RuntimeError("Integrity violated: torchvision not available") from exc
    try:
        with safe_open(path, framework="pt") as st:
            metadata = st.metadata() or {}
            if len(json.dumps(metadata).encode("utf-8")) > MAX_METADATA_SIZE:
                raise ValueError("Limit violated: metadata size exceeds limit")
            st_keys_list = st.keys()
            if len(st_keys_list) > MAX_TENSORS:
                raise ValueError("Limit violated: tensor count exceeds limit")
            trusted_state_dict = trusted_model.state_dict()
            trusted_keys = set(trusted_state_dict.keys())
            st_keys = set(st_keys_list)
            if trusted_keys != st_keys:
                missing = trusted_keys - st_keys
                unexpected = st_keys - trusted_keys
                raise ValueError(
                    f"Integrity violated: architecture mismatch. "
                    f"Missing tensors: {len(missing)}, Unexpected tensors: {len(unexpected)}"
                )
            is_quantized = None
            for key in trusted_keys:
                trusted_shape = list(trusted_state_dict[key].shape)
                st_slice = st.get_slice(key)
                st_shape = list(st_slice.get_shape())
                if len(st_shape) > MAX_RANK:
                    raise ValueError(f"Limit violated: tensor '{key}' rank exceeds limit")
                if any(dim > MAX_DIMENSION for dim in st_shape):
                    raise ValueError(f"Limit violated: tensor '{key}' dimension exceeds limit")
                if st_shape != trusted_shape:
                    raise ValueError(f"Integrity violated: shape mismatch for tensor {key}")
                dtype_str = st_slice.get_dtype()
                if dtype_str in ("F32", "F16", "BF16", "F64"):
                    tensor_q = False
                elif dtype_str in ("I8", "U8", "F8_E5M2", "F8_E4M3", "F8_E4M3FN", "F8_E5M2FNUZ", "F8_E4M3FNUZ"):
                    tensor_q = True
                elif dtype_str in ("I64", "I32", "I16", "BOOL"):
                    tensor_q = None
                else:
                    raise ValueError(f"Integrity violated: unknown dtype {dtype_str} for tensor {key}")
                if tensor_q is not None:
                    if is_quantized is None:
                        is_quantized = tensor_q
                    elif is_quantized != tensor_q:
                        raise ValueError("Integrity violated: mixed/inconsistent dtype state")
            if is_quantized is True:
                raise ValueError("Integrity violated: unsupported-quantized-graph")
            if is_quantized is None:
                is_quantized = False
            trusted_model.requires_grad_(False)
            loaded = {key: st.get_tensor(key) for key in trusted_keys}
            trusted_model.load_state_dict(loaded, assign=True)
            return TrustedModelContext(
                model=trusted_model, architecture="resnet18",
                input_domain="VISION", is_quantized=is_quantized,
            )
    except Exception as e:
        if isinstance(e, ValueError) and str(e).startswith("Limit violated:"):
            raise
        raise ValueError(f"Integrity violated: malformed SafeTensors file ({e})") from e

MAX_TENSORS = 10000
MAX_RANK = 8
MAX_DIMENSION = 1000000


@dataclass
class TrustedModelContext:
    model: Any
    architecture: str
    input_domain: str
    is_quantized: bool


def intake_resnet18(path: Path) -> TrustedModelContext:
    return intake_model(Path(path), declared_architecture="resnet18")
# ---------------------------------------------------------------------------
# D2 -> P2 bridge (the only addition needed for integration).
#
# P2 must never reload the model itself (handoff.py docstring). The recovered
# authoritative P2 path obtains the module exclusively through the handoff:
#     src/p2_behavioral_risk/analyzer.py  STEP 2  -> get_trusted_model()
#     src/p2_behavioral_risk/handoff.py           -> _TRUSTED_CONTEXT.model
# so the context produced by the D2 intake above must be stored in that handoff
# before P2 runs. Architecture stays explicitly declared as resnet18: no
# detection, no second architecture, no generic loader.
# ---------------------------------------------------------------------------
def load_resnet18_and_handoff(path: Path) -> TrustedModelContext:
    """Run the D2 resnet18 intake, then hand the trusted model to P2.

    Returns:
        The TrustedModelContext. After this call
        ``handoff.get_trusted_model()`` yields ``context.model``.
    """
    context = intake_resnet18(Path(path))

    # Imported lazily so this P1 module stays importable on its own, matching
    # the existing lazy-import style used for torchvision above.
    from src.p2_behavioral_risk.handoff import receive_trusted_model

    receive_trusted_model(context)
    return context
