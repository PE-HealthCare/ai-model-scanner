# src/p2_behavioral_risk/output_writer.py
import json
import math

def write_risk_results(data, filepath):
    """Step 9: Writes JSON, sanitizes NaNs/Infs."""
    def sanitize(v):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    cleaned = {k: sanitize(v) for k, v in data.items()}
    
    with open(filepath, 'w') as f:
        json.dump(cleaned, f, indent=2)