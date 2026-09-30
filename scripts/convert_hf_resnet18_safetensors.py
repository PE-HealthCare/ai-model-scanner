"""Safely normalize the known Hugging Face ResNet18 SafeTensors layout.

The converter reads only SafeTensors tensors, maps the documented
``transformers.ResNetForImageClassification`` parameter names to the
torchvision ResNet18 state-dict names, and rejects anything that is not an
exact canonical ResNet18 tensor contract.  It never imports remote code or
deserializes pickle data.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import save_file
from torchvision.models import resnet18


_STEM = "resnet.embedder.embedder."
_STAGE = re.compile(
    r"^resnet\.encoder\.stages\.(?P<stage>[0-3])\.layers\.(?P<block>[0-1])\.(?P<tail>.+)$"
)


def _map_name(source_name: str) -> str:
    """Map one known Transformers ResNet18 tensor name to torchvision."""
    if source_name == "classifier.1.weight":
        return "fc.weight"
    if source_name == "classifier.1.bias":
        return "fc.bias"
    if source_name.startswith(_STEM + "convolution."):
        return "conv1." + source_name.removeprefix(_STEM + "convolution.")
    if source_name.startswith(_STEM + "normalization."):
        return "bn1." + source_name.removeprefix(_STEM + "normalization.")

    match = _STAGE.fullmatch(source_name)
    if match is None:
        raise ValueError(f"Unsupported Hugging Face ResNet tensor name: {source_name}")
    prefix = f"layer{int(match['stage']) + 1}.{match['block']}."
    tail = match["tail"]
    for source_prefix, target_prefix in (
        ("layer.0.convolution.", "conv1."),
        ("layer.0.normalization.", "bn1."),
        ("layer.1.convolution.", "conv2."),
        ("layer.1.normalization.", "bn2."),
        ("shortcut.convolution.", "downsample.0."),
        ("shortcut.normalization.", "downsample.1."),
    ):
        if tail.startswith(source_prefix):
            return prefix + target_prefix + tail.removeprefix(source_prefix)
    raise ValueError(f"Unsupported Hugging Face ResNet tensor name: {source_name}")


def convert(source: Path, destination: Path) -> None:
    """Convert and strictly validate one known Transformers ResNet18 file."""
    with safe_open(source, framework="pt", device="cpu") as handle:
        mapped = [(_map_name(name), handle.get_tensor(name)) for name in handle.keys()]
    normalized = dict(mapped)

    if len(normalized) != 122:
        raise ValueError(f"Expected 122 canonical ResNet18 tensors, got {len(normalized)}")
    if len(normalized) != len(mapped):
        raise ValueError("Multiple source tensors mapped to the same canonical tensor")

    fc_weight = normalized.get("fc.weight")
    fc_bias = normalized.get("fc.bias")
    if (
        fc_weight is None
        or fc_bias is None
        or fc_weight.ndim != 2
        or fc_weight.shape[1] != 512
        or fc_weight.shape[0] <= 0
        or tuple(fc_bias.shape) != (fc_weight.shape[0],)
    ):
        raise ValueError(
            "Invalid ResNet18 classifier contract; expected fc.weight "
            "[classes, 512] and fc.bias [classes]"
        )
    trusted = resnet18(weights=None, num_classes=fc_weight.shape[0]).state_dict()
    if set(normalized) != set(trusted):
        missing = set(trusted) - set(normalized)
        unexpected = set(normalized) - set(trusted)
        raise ValueError(
            "Canonical ResNet18 contract mismatch after normalization: "
            f"missing={len(missing)}, unexpected={len(unexpected)}"
        )
    for name, tensor in normalized.items():
        if tuple(tensor.shape) != tuple(trusted[name].shape):
            raise ValueError(
                f"Shape mismatch after normalization for {name}: "
                f"expected {tuple(trusted[name].shape)}, got {tuple(tensor.shape)}"
            )
        if not tensor.is_floating_point() and tensor.dtype != torch.int64:
            raise ValueError(f"Non-floating tensor in FP32 corpus checkpoint: {name}")
        if tensor.is_floating_point() and not torch.isfinite(tensor).all():
            raise ValueError(f"Non-finite tensor in source checkpoint: {name}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    save_file(normalized, str(destination), metadata={
        "format": "canonical-torchvision-resnet18",
        "conversion": "hf-transformers-resnet18-safetensors-v1",
        "source_filename": source.name,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    convert(args.source, args.destination)
    print(args.destination)


if __name__ == "__main__":
    main()
