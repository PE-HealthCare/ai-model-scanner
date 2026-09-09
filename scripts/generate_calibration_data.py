# scripts/generate_calibration_data.py
import os
import sys

# Add the project root (parent of 'scripts/') to Python's import path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import torch
import torchvision.models as models
from transformers import DistilBertModel, DistilBertConfig
import json
import numpy as np
from datetime import datetime

# Now we can import from src
from src.p2_behavioral_risk.prober import generate_probes, run_bounded_inference, compute_h_strip


def calibrate_model(model, domain, model_name, repetitions=30, probe_count=32, seed=42):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model.eval()
    results = []
    print(f"Calibrating {model_name} ({domain}) with {repetitions} runs of {probe_count} probes each...")
    for i in range(repetitions):
        probes = generate_probes(domain, n=probe_count)
        with torch.no_grad():
            outputs = run_bounded_inference(model, probes, bound_n=probe_count)
        h_strip = compute_h_strip(outputs)
        results.append(h_strip)
        if (i + 1) % 5 == 0 or i == repetitions - 1:
            print(f"  Run {i+1}/{repetitions}: H_STRIP = {h_strip:.4f}")
    arr = np.array(results)
    return {
        "model_name": model_name,
        "domain": domain,
        "probe_count": probe_count,
        "repetitions": repetitions,
        "seed": seed,
        "timestamp": datetime.now().isoformat(),
        "h_strip_values": results,
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "percentiles": {
            "p5": float(np.percentile(arr, 5)),
            "p25": float(np.percentile(arr, 25)),
            "p50": float(np.percentile(arr, 50)),
            "p75": float(np.percentile(arr, 75)),
            "p95": float(np.percentile(arr, 95)),
        }
    }


def load_vision_model():
    return models.resnet18(pretrained=True)


def load_nlp_model():
    config = DistilBertConfig.from_pretrained("distilbert-base-uncased")
    base = DistilBertModel.from_pretrained("distilbert-base-uncased", config=config)

    class Wrapper(torch.nn.Module):
        def __init__(self, base_model):
            super().__init__()
            self.base = base_model
            self.fc = torch.nn.Linear(config.dim, 1000)

        def forward(self, input_ids):
            attention_mask = torch.ones_like(input_ids)
            outputs = self.base(input_ids=input_ids, attention_mask=attention_mask)
            cls_output = outputs.last_hidden_state[:, 0, :]
            return self.fc(cls_output)

    wrapped = Wrapper(base)
    wrapped.eval()
    return wrapped


def main():
    os.makedirs("data/calibration", exist_ok=True)
    calibration_data = {}

    print("\n" + "=" * 60)
    print("VISION CALIBRATION")
    print("=" * 60)
    vision_model = load_vision_model()
    calibration_data["VISION"] = calibrate_model(vision_model, "VISION", "ResNet18")

    print("\n" + "=" * 60)
    print("NLP CALIBRATION")
    print("=" * 60)
    nlp_model = load_nlp_model()
    calibration_data["NLP"] = calibrate_model(nlp_model, "NLP", "DistilBERT")

    output = {
        "calibration_data": calibration_data,
        "provenance": {
            "generated_by": "P2",
            "purpose": "D3/D4 calibration baseline",
            "methodology": "STRIP probing on clean reference models",
            "probe_count": 32,
            "repetitions": 30,
            "random_seed": 42,
            "note": "This is newly measured experimental data, not a pre-existing project decision."
        }
    }

    output_path = "data/calibration/calibration_data.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print("\n✅ Calibration data saved to", output_path)
    print("\nSummary:")
    for domain in ["VISION", "NLP"]:
        stats = calibration_data[domain]
        print(f"\n{domain}:")
        print(f"  mean = {stats['mean']:.4f}, std = {stats['std']:.4f}")
        print(f"  median = {stats['median']:.4f}, P5 = {stats['percentiles']['p5']:.4f}, P95 = {stats['percentiles']['p95']:.4f}")


if __name__ == "__main__":
    main()