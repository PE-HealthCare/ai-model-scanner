# src/p2_behavioral_risk/stub_models.py
import torch.nn as nn
from .config import VISION_NUM_CLASSES, VISION_IMAGE_SIZE, NLP_VOCAB_SIZE, NLP_SEQ_LEN, NLP_NUM_CLASSES

class StubVisionModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.flatten = nn.Flatten()
        self.fc = nn.Linear(3 * VISION_IMAGE_SIZE * VISION_IMAGE_SIZE, VISION_NUM_CLASSES)
    def forward(self, x):
        return self.fc(self.flatten(x))

class StubNLPModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed = nn.Embedding(NLP_VOCAB_SIZE, 128)
        self.fc = nn.Linear(128 * NLP_SEQ_LEN, NLP_NUM_CLASSES)  # 1000 classes for demo
    def forward(self, x):
        x = self.embed(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)