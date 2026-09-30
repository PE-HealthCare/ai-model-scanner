"""Build Gate-2A provenance and compatibility evidence for downloaded sources.

Only registered public SafeTensors sources are eligible.  The script never
loads pickle checkpoints or executes repository-supplied code; every candidate
passes the current P1 zero-trust ResNet18 intake before it is fingerprinted.
Raw download serializations are deliberately excluded when a validated,
canonical SafeTensors normalization is registered for the same source.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from safetensors import safe_open

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.p1_static_engine.analyzer import intake_model
from src.common.utils import ROOT


SOURCES_DIR = ROOT / "data" / "training" / "sources"
OUTPUT_PATH = ROOT / "data" / "training" / "metadata" / "source_manifest.json"
MISSING_OUTPUT_PATH = ROOT / "data" / "training" / "metadata" / "missing_sources_manifest.json"

# Provenance is deliberately explicit rather than inferred from a filename.
REGISTERED_SOURCES = {
    "timm_resnet18_a1_in1k.safetensors": {
        "source_model_id": "timm-resnet18-a1-in1k",
        "provider": "timm / Hugging Face",
        "identifier": "timm/resnet18.a1_in1k",
        "source_url": "https://huggingface.co/timm/resnet18.a1_in1k/resolve/main/model.safetensors",
        "license": "apache-2.0",
        "lineage": "ResNet Strikes Back A1; ImageNet-1k",
    },
    "timm_resnet18_a2_in1k.safetensors": {
        "source_model_id": "timm-resnet18-a2-in1k",
        "provider": "timm / Hugging Face",
        "identifier": "timm/resnet18.a2_in1k",
        "source_url": "https://huggingface.co/timm/resnet18.a2_in1k/resolve/main/model.safetensors",
        "license": "apache-2.0",
        "lineage": "ResNet Strikes Back A2; ImageNet-1k",
    },
    "timm_resnet18_a3_in1k.safetensors": {
        "source_model_id": "timm-resnet18-a3-in1k",
        "provider": "timm / Hugging Face",
        "identifier": "timm/resnet18.a3_in1k",
        "source_url": "https://huggingface.co/timm/resnet18.a3_in1k/resolve/main/model.safetensors",
        "license": "apache-2.0",
        "lineage": "ResNet Strikes Back A3; ImageNet-1k",
    },
    "timm_resnet18_fb_ssl_yfcc100m_ft_in1k.safetensors": {
        "source_model_id": "timm-resnet18-fb-ssl-yfcc100m-ft-in1k",
        "provider": "timm / Hugging Face",
        "identifier": "timm/resnet18.fb_ssl_yfcc100m_ft_in1k",
        "source_url": "https://huggingface.co/timm/resnet18.fb_ssl_yfcc100m_ft_in1k/resolve/main/model.safetensors",
        "license": "cc-by-nc-4.0",
        "lineage": "Facebook self-supervised YFCC100M, fine-tuned ImageNet-1k",
    },
    "timm_resnet18_fb_swsl_ig1b_ft_in1k.safetensors": {
        "source_model_id": "timm-resnet18-fb-swsl-ig1b-ft-in1k",
        "provider": "timm / Hugging Face",
        "identifier": "timm/resnet18.fb_swsl_ig1b_ft_in1k",
        "source_url": "https://huggingface.co/timm/resnet18.fb_swsl_ig1b_ft_in1k/resolve/main/model.safetensors",
        "license": "cc-by-nc-4.0",
        "lineage": "Facebook semi-weakly supervised IG-1B, fine-tuned ImageNet-1k",
    },
    "timm_resnet18_gluon_in1k.safetensors": {
        "source_model_id": "timm-resnet18-gluon-in1k",
        "provider": "timm / Hugging Face",
        "identifier": "timm/resnet18.gluon_in1k",
        "source_url": "https://huggingface.co/timm/resnet18.gluon_in1k/resolve/main/model.safetensors",
        "license": "apache-2.0",
        "lineage": "Apache Gluon Bag-of-Tricks; ImageNet-1k",
    },
    "stomoya_resnet18_st_safebooru_1k.safetensors": {
        "source_model_id": "stomoya-resnet18-st-safebooru-1k",
        "provider": "STomoya / Hugging Face",
        "identifier": "STomoya/resnet18.st_safebooru_1k",
        "source_url": "https://huggingface.co/STomoya/resnet18.st_safebooru_1k/resolve/main/model.safetensors",
        "license": "apache-2.0",
        "lineage": "timm ResNet18 trained for SafeBooru-1k",
    },
    "timm_resnet18_tv_in1k.safetensors": {
        "source_model_id": "timm-resnet18-tv-in1k",
        "provider": "timm / Hugging Face",
        "identifier": "timm/resnet18.tv_in1k",
        "source_url": "https://huggingface.co/timm/resnet18.tv_in1k/resolve/main/model.safetensors",
        "license": "bsd-3-clause",
        "lineage": "torchvision ResNet18 ImageNet-1k",
    },
    "microsoft_resnet18_imagenet1k_canonical.safetensors": {
        "source_model_id": "microsoft-resnet-18-imagenet1k",
        "parent_lineage_id": "torchvision-resnet18-imagenet1k-v1",
        "relationship_to_parent": "same underlying weights after safe key normalization",
        "provider": "Microsoft / Hugging Face",
        "identifier": "microsoft/resnet-18",
        "source_url": "https://huggingface.co/microsoft/resnet-18/resolve/main/model.safetensors",
        "license": "mit",
        "dataset": "ImageNet-1k",
        "lineage": "Microsoft serialization of torchvision ResNet18 ImageNet-1k",
        "original_format": "safetensors",
        "converted_format": "canonical-torchvision-safetensors",
    },
    "iust1n2_resnet18_wikiart_canonical.safetensors": {
        "source_model_id": "iust1n2-resnet18-wikiart",
        "parent_lineage_id": "microsoft-resnet-18",
        "relationship_to_parent": "full-weight fine-tune",
        "provider": "Iust1n2 / Hugging Face",
        "identifier": "Iust1n2/resnet-18-finetuned-wikiart",
        "source_url": "https://huggingface.co/Iust1n2/resnet-18-finetuned-wikiart/resolve/main/model.safetensors",
        "license": "apache-2.0", "dataset": "WikiArt", "lineage": "microsoft/resnet-18 fine-tune",
        "original_format": "safetensors", "converted_format": "canonical-torchvision-safetensors",
    },
    "gaborcselle_font_identifier_canonical.safetensors": {
        "source_model_id": "gaborcselle-font-identifier", "parent_lineage_id": "microsoft-resnet-18",
        "relationship_to_parent": "full-weight fine-tune", "provider": "gaborcselle / Hugging Face",
        "identifier": "gaborcselle/font-identifier", "source_url": "https://huggingface.co/gaborcselle/font-identifier/resolve/main/model.safetensors",
        "license": "mit", "dataset": "gaborcselle/font-examples", "lineage": "microsoft/resnet-18 fine-tune",
        "original_format": "safetensors", "converted_format": "canonical-torchvision-safetensors",
    },
    "robertz2011_resnet18_birb_canonical.safetensors": {
        "source_model_id": "robertz2011-resnet18-birb", "parent_lineage_id": "microsoft-resnet-18",
        "relationship_to_parent": "full-weight fine-tune", "provider": "RobertZ2011 / Hugging Face",
        "identifier": "RobertZ2011/resnet-18-birb", "source_url": "https://huggingface.co/RobertZ2011/resnet-18-birb/resolve/main/model.safetensors",
        "license": "unspecified", "dataset": "Caltech-UCSD Birds-200-2011", "lineage": "microsoft/resnet-18 fine-tune",
        "original_format": "safetensors", "converted_format": "canonical-torchvision-safetensors",
    },
    "man1103_resnet18_petimages.safetensors": {
        "source_model_id": "man1103-resnet18-petimages", "parent_lineage_id": "microsoft-resnet-18",
        "relationship_to_parent": "full-weight fine-tune", "provider": "Man1103 / Hugging Face",
        "identifier": "Man1103/ResNet18-FT-PetImages-11.7M", "source_url": "https://huggingface.co/Man1103/ResNet18-FT-PetImages-11.7M/resolve/main/model.safetensors",
        "license": "bsd-3-clause", "dataset": "Man1103/PetImages", "lineage": "microsoft/resnet-18 fine-tune",
    },
    "behradg_resnet18_mri_brain_canonical.safetensors": {
        "source_model_id": "behradg-resnet18-mri-brain", "parent_lineage_id": "unverified-behradg-resnet18-mri-brain",
        "relationship_to_parent": "training lineage not declared by provider", "provider": "BehradG / Hugging Face",
        "identifier": "BehradG/resnet-18-finetuned-MRI-Brain", "source_url": "https://huggingface.co/BehradG/resnet-18-finetuned-MRI-Brain/resolve/main/model.safetensors",
        "license": "unspecified", "dataset": "MRI Brain", "lineage": "public full checkpoint; parent unverified",
        "original_format": "safetensors", "converted_format": "canonical-torchvision-safetensors",
    },
    "wcosmas_resnet18_papsmear_canonical.safetensors": {
        "source_model_id": "wcosmas-resnet18-papsmear", "parent_lineage_id": "microsoft-resnet-18",
        "relationship_to_parent": "full-weight fine-tune", "provider": "wcosmas / Hugging Face",
        "identifier": "wcosmas/resnet-18-finetuned-papsmear", "source_url": "https://huggingface.co/wcosmas/resnet-18-finetuned-papsmear/resolve/main/model.safetensors",
        "license": "apache-2.0", "dataset": "imagefolder (Pap smear)", "lineage": "microsoft/resnet-18 fine-tune",
        "original_format": "safetensors", "converted_format": "canonical-torchvision-safetensors",
    },
    "kgoli_resnet18_fraud_canonical.safetensors": {
        "source_model_id": "kgoli-resnet18-fraud", "parent_lineage_id": "microsoft-resnet-18",
        "relationship_to_parent": "full-weight fine-tune", "provider": "kgoli / Hugging Face",
        "identifier": "kgoli/resnet-18-finetuned-fraud", "source_url": "https://huggingface.co/kgoli/resnet-18-finetuned-fraud/resolve/main/model.safetensors",
        "license": "apache-2.0", "dataset": "imagefolder (provider-declared fraud dataset)", "lineage": "microsoft/resnet-18 fine-tune",
        "original_format": "safetensors", "converted_format": "canonical-torchvision-safetensors",
    },
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tensor_fingerprint(path: Path) -> tuple[str, list[dict]]:
    """Hash canonical names, shapes, dtypes, and tensor bytes in name order."""
    digest = hashlib.sha256()
    tensor_summary: list[dict] = []
    with safe_open(path, framework="pt") as handle:
        for name in sorted(handle.keys()):
            tensor = handle.get_tensor(name).detach().cpu().contiguous()
            digest.update(name.encode("utf-8"))
            digest.update(str(tuple(tensor.shape)).encode("ascii"))
            digest.update(str(tensor.dtype).encode("ascii"))
            digest.update(tensor.numpy().tobytes())
            tensor_summary.append({
                "name": name,
                "shape": list(tensor.shape),
                "dtype": str(tensor.dtype),
            })
    return digest.hexdigest(), tensor_summary


def build_manifest() -> dict:
    records: list[dict] = []
    fingerprints: dict[str, str] = {}
    for filename in sorted(REGISTERED_SOURCES):
        path = SOURCES_DIR / filename
        if not path.exists():
            continue
        record = {
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "file_sha256": _sha256_file(path),
            "declared_architecture": "resnet18",
            "original_format": "safetensors",
            "converted_format": None,
        }
        provenance = REGISTERED_SOURCES.get(path.name)
        if provenance is None:
            record.update({"accepted": False, "rejection_reason": "unregistered provenance"})
            records.append(record)
            continue
        record.update(provenance)
        record.setdefault("parent_lineage_id", record["source_model_id"])
        record.setdefault("relationship_to_parent", "independent public training lineage")
        record.setdefault("dataset", "ImageNet-1k")
        try:
            context = intake_model(path, "resnet18")
            fingerprint, tensors = _tensor_fingerprint(path)
            record.update({
                "p1_intake": "accepted",
                "tensor_content_fingerprint": fingerprint,
                "tensor_count": len(tensors),
                "dtype": "FP32" if not context.is_quantized else "quantized",
                "classifier_output_dim": int(context.model.fc.out_features) if not context.is_quantized else None,
                "tensor_schema": tensors,
                "accepted": fingerprint not in fingerprints,
                "rejection_reason": None if fingerprint not in fingerprints else (
                    f"exact tensor-content duplicate of {fingerprints[fingerprint]}"
                ),
            })
            fingerprints.setdefault(fingerprint, record["source_model_id"])
        except Exception as exc:
            record.update({"accepted": False, "p1_intake": "rejected", "rejection_reason": str(exc)})
        records.append(record)

    accepted = [record for record in records if record["accepted"]]
    parent_lineages = sorted({record["parent_lineage_id"] for record in accepted})
    payload = {
        "manifest_version": "prompt2-gate2a-v1",
        "corpus_size_policy": "adaptive-15-18-21",
        "candidate_files_found": len(records),
        "independent_parent_lineage_count": sum(
            record["relationship_to_parent"] == "independent public training lineage" for record in accepted
        ),
        "distinct_clean_weight_population_count": len(accepted),
        "accepted_parent_lineage_ids": parent_lineages,
        "accepted_source_model_ids": [record["source_model_id"] for record in accepted],
        "records": records,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    missing = {
        "manifest_version": "prompt2-gate2a-v1",
        "status": "INITIAL_ADAPTIVE_CHECKPOINT_REACHED",
        "next_action": "development-only grouped learning curve decides 15 vs 18 vs 21",
        "independent_parent_lineage_count": payload["independent_parent_lineage_count"],
        "distinct_clean_weight_population_count": len(accepted),
        "required_contract": {
            "architecture": "torchvision-compatible resnet18",
            "format": "SafeTensors",
            "dtypes": ["FP32", "FP16"],
            "constraint": "must pass canonical ResNet18 P1 intake and have a distinct tensor-content fingerprint",
        },
        "known_catalog_checked": "https://huggingface.co/api/models?author=timm&search=resnet18&limit=100",
        "known_compatible_identifiers": [record["identifier"] for record in accepted],
        "resume_destination": "data/training/sources/",
        "resume_command": "& .\\venv\\Scripts\\python.exe scripts\\build_p2_source_manifest.py",
    }
    MISSING_OUTPUT_PATH.write_text(json.dumps(missing, indent=2) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = build_manifest()
    print(json.dumps({
        "candidate_files_found": result["candidate_files_found"],
        "distinct_clean_weight_population_count": result["distinct_clean_weight_population_count"],
        "manifest": str(OUTPUT_PATH.relative_to(ROOT)),
    }))
