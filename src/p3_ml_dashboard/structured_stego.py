"""Frozen Prompt-3C/D structured-LSB scanner used by experiment and CLI."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import torch
from safetensors import safe_open

FEATURE_NAMES=("min_window_entropy","max_window_printable_fraction","max_window_byte_chi2","max_window_transition_deviation","max_window_repeat_fraction")
SCORED_FEATURE_NAMES=FEATURE_NAMES[:4]
WINDOW_SIZE_BYTES=4096
STRIDE_BYTES=2048
FROZEN_THRESHOLD=3.180525532491262
ROOT=Path(__file__).resolve().parents[2]
REFERENCE_CACHE=ROOT/'data/training/metadata/s6_structured_generalization_development.json'

def extract_features(path:Path)->dict[str,float]:
    """Exact Prompt-3C LSB-byte stream representation; no metadata is read."""
    bits=[]
    with safe_open(path,framework='pt',device='cpu') as handle:
        for name in sorted(handle.keys()):
            tensor=handle.get_tensor(name).detach().cpu().contiguous()
            if tensor.dtype==torch.float32:
                bits.append((tensor.numpy().view(np.uint32).reshape(-1)&1).astype(np.uint8))
    if not bits: raise ValueError('Structured detector requires at least one FP32 tensor')
    stream=np.packbits(np.concatenate(bits),bitorder='little')
    if stream.size<WINDOW_SIZE_BYTES: raise ValueError('LSB byte stream shorter than frozen 4096-byte window')
    entropy=[]; printable=[]; chi2=[]; transition=[]; repeat=[]
    for start in range(0,stream.size-WINDOW_SIZE_BYTES+1,STRIDE_BYTES):
        window=stream[start:start+WINDOW_SIZE_BYTES]; counts=np.bincount(window,minlength=256).astype(float); p=counts[counts>0]/WINDOW_SIZE_BYTES
        entropy.append(float(-(p*np.log2(p)).sum()/8)); printable.append(float(np.count_nonzero((window>=32)&(window<=126))/WINDOW_SIZE_BYTES)); chi2.append(float(np.square(counts-WINDOW_SIZE_BYTES/256).sum()/(WINDOW_SIZE_BYTES/256)))
        wb=np.unpackbits(window,bitorder='little'); transition.append(float(abs(np.count_nonzero(wb[1:]!=wb[:-1])/(wb.size-1)-.5)))
        blocks=window.reshape(-1,16);repeat.append(float(1-np.unique(blocks,axis=0).shape[0]/blocks.shape[0]))
    return dict(zip(FEATURE_NAMES,(min(entropy),max(printable),max(chi2),max(transition),max(repeat))))

def deployment_reference()->dict[str,dict[str,float]]:
    """Freeze a single reference using the cached 13 development-clean vectors."""
    cached=json.loads(REFERENCE_CACHE.read_text(encoding='utf-8'))
    rows=[x for x in cached['records'] if x['label']==0]
    if len(rows)!=13 or tuple(cached.get('feature_names',()))!=FEATURE_NAMES: raise ValueError('Invalid frozen development clean reference cache')
    output={}
    for name in SCORED_FEATURE_NAMES:
        values=np.asarray([x['features'][name] for x in rows],dtype=float);median=float(np.median(values));scale=float(1.4826*np.median(abs(values-median)))
        if scale<=1e-12: scale=float(np.std(values))
        if not math.isfinite(scale) or scale<=1e-12: raise ValueError(f'DEPLOYMENT_BASELINE_DEGENERATE={name}')
        output[name]={'median':median,'scale':scale}
    return output

def reference_hash(reference:dict[str,dict[str,float]])->str:
    return hashlib.sha256(json.dumps(reference,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def score(feature_values:dict[str,float],reference:dict[str,dict[str,float]])->tuple[float,str,dict[str,float]]:
    z={'entropy':(reference['min_window_entropy']['median']-feature_values['min_window_entropy'])/reference['min_window_entropy']['scale'],
       'printable':(feature_values['max_window_printable_fraction']-reference['max_window_printable_fraction']['median'])/reference['max_window_printable_fraction']['scale'],
       'chi2':(feature_values['max_window_byte_chi2']-reference['max_window_byte_chi2']['median'])/reference['max_window_byte_chi2']['scale'],
       'transition':(feature_values['max_window_transition_deviation']-reference['max_window_transition_deviation']['median'])/reference['max_window_transition_deviation']['scale']}
    dominant=max(z,key=z.get);return float(max(0,*z.values())),dominant,{k:float(v) for k,v in z.items()}

def scan(path:Path)->dict:
    features=extract_features(path);reference=deployment_reference();value,dominant,z=score(features,reference)
    return {'score':value,'threshold':FROZEN_THRESHOLD,'verdict':'FAIL' if value>=FROZEN_THRESHOLD else 'PASS','dominant_signal':dominant,'features':features,'z_scores':z,'reference_hash':reference_hash(reference),'detector_version':'p3c-d-frozen-structured-lsb-v1'}
