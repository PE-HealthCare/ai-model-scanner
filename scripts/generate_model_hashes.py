# scripts/generate_model_hashes.py
import hashlib
import torch
import torchvision.models as models
from transformers import DistilBertModel
import tempfile
import os

def get_model_hash(model, model_name):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        torch.save(model.state_dict(), tmp.name)
        tmp_path = tmp.name
    hasher = hashlib.sha256()
    with open(tmp_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    os.unlink(tmp_path)
    return hasher.hexdigest()

# ResNet18
resnet = models.resnet18(pretrained=True)
resnet_hash = get_model_hash(resnet, "ResNet18")
print(f"ResNet18 hash: {resnet_hash}")

# DistilBERT
distilbert = DistilBertModel.from_pretrained("distilbert-base-uncased")
distilbert_hash = get_model_hash(distilbert, "DistilBERT")
print(f"DistilBERT hash: {distilbert_hash}")