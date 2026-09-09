"""Zero-trust SafeTensors intake for P1.

DESIGN (security-first):
- The artifact is treated as untrusted bytes. We NEVER import, pickle-load,
  or execute anything related to the model.
- The SafeTensors container is parsed manually:
      [u64 little-endian header length][JSON header][raw tensor bytes]
  This gives full control over validation before tensor bytes are
  interpreted as numbers.
- Fail closed: any malformed, inconsistent, or unsupported input raises an
  exception. No partial analysis is produced.

Supported dtypes (whitelist): F16, F32, F64. Non-floating tensors are
rejected because the contractual static steganalysis features are defined
over floating-point weight distributions.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MAX_HEADER_BYTES = 64 * 1024 * 1024  # 64 MiB safety cap on header size
MAX_FILE_BYTES = 8 * 1024 * 1024 * 1024  # 8 GiB artifact cap

_DTYPE_MAP = {
    "F16": np.dtype("<f2"),
    "F32": np.dtype("<f4"),
    "F64": np.dtype("<f8"),
}


class ArtifactRejected(Exception):
    """Raised when an untrusted artifact fails zero-trust validation."""


def _encode_float_array(arr: np.ndarray) -> tuple[np.ndarray, str]:
    if arr.dtype == np.float64:
        return arr.astype("<f8"), "F64"
    if arr.dtype == np.float32:
        return arr.astype("<f4"), "F32"
    if arr.dtype == np.float16:
        return arr.astype("<f2"), "F16"
    raise ValueError(f"only float arrays are supported, got {arr.dtype}")


def write_safetensors(path: Path, tensors: dict[str, np.ndarray]) -> Path:
    """Serialize float tensors into the SafeTensors container format.

    Used only for trusted, locally generated fixtures and demo models; it is
    not part of the untrusted-input path.
    """
    header: dict[str, object] = {}
    blobs: list[bytes] = []
    offset = 0
    for name in sorted(tensors):
        arr, dtype_name = _encode_float_array(np.ascontiguousarray(tensors[name]))
        n_bytes = arr.nbytes
        header[name] = {
            "dtype": dtype_name,
            "shape": list(arr.shape),
            "data_offsets": [offset, offset + n_bytes],
        }
        blobs.append(arr.tobytes())
        offset += n_bytes
    header_bytes = json.dumps(header).encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(len(header_bytes).to_bytes(8, "little"))
        fh.write(header_bytes)
        for blob in blobs:
            fh.write(blob)
    return path


def _parse_header(raw_header: bytes) -> dict:
    try:
        header = json.loads(raw_header.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactRejected(f"header is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(header, dict):
        raise ArtifactRejected("header must be a JSON object")
    return header


def _validate_entry(name: str, entry: object, data_len: int) -> tuple[str, list, int, int]:
    if not isinstance(entry, dict):
        raise ArtifactRejected(f"tensor entry {name!r} is not an object")
    dtype = entry.get("dtype")
    if dtype not in _DTYPE_MAP:
        raise ArtifactRejected(
            f"tensor {name!r} has unsupported dtype {dtype!r}; allowed: {sorted(_DTYPE_MAP)}"
        )
    shape = entry.get("shape")
    if not isinstance(shape, list) or not all(isinstance(d, int) and d >= 0 for d in shape):
        raise ArtifactRejected(f"tensor {name!r} has invalid shape {shape!r}")
    offsets = entry.get("data_offsets")
    if (
        not isinstance(offsets, list)
        or len(offsets) != 2
        or not all(isinstance(o, int) and o >= 0 for o in offsets)
        or offsets[0] > offsets[1]
        or offsets[1] > data_len
    ):
        raise ArtifactRejected(f"tensor {name!r} has invalid data_offsets {offsets!r}")
    itemsize = _DTYPE_MAP[dtype].itemsize
    n_elems = 1
    for d in shape:
        n_elems *= d
    span = offsets[1] - offsets[0]
    if span != n_elems * itemsize:
        raise ArtifactRejected(
            f"tensor {name!r}: byte span {span} does not match shape/dtype ({n_elems} x {itemsize})"
        )
    return dtype, shape, offsets[0], offsets[1]


def load_safetensors(path: Path) -> dict[str, np.ndarray]:
    """Zero-trust load of a SafeTensors file into in-memory numpy arrays.

    Returns ``{tensor_name: ndarray}`` with tensors ordered by sorted name
    (deterministic downstream ordering). Raises ArtifactRejected (or
    FileNotFoundError) on any validation failure. Never executes model code
    and never mutates the artifact on disk.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"artifact not found: {path}")
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ArtifactRejected(f"artifact too large ({size} bytes)")
    if size < 8:
        raise ArtifactRejected("artifact too small to contain a SafeTensors header")
    with path.open("rb") as fh:
        header_len = int.from_bytes(fh.read(8), "little", signed=False)
        if header_len <= 0 or header_len > MAX_HEADER_BYTES:
            raise ArtifactRejected(f"invalid header length {header_len}")
        if 8 + header_len > size:
            raise ArtifactRejected("header length exceeds file size")
        raw_header = fh.read(header_len)
        data = fh.read()
    header = _parse_header(raw_header)
    tensors: dict[str, np.ndarray] = {}
    for name in sorted(header):
        if name == "__metadata__":
            continue  # untrusted metadata is parsed but ignored
        dtype, shape, start, end = _validate_entry(name, header[name], len(data))
        arr = np.frombuffer(data[start:end], dtype=_DTYPE_MAP[dtype]).reshape(shape).copy()
        tensors[name] = arr
    if not any(np.issubdtype(t.dtype, np.floating) for t in tensors.values()):
        raise ArtifactRejected("artifact contains no floating-point tensors to analyze")
    return tensors