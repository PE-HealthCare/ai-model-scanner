"""Prompt 3 bounded development-only normalized entropy-strip evaluation."""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
import sys
import numpy as np, torch
from sklearn.metrics import average_precision_score,roc_auc_score
from sklearn.model_selection import GroupKFold
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)) if str(ROOT) not in sys.path else None
from scripts.run_p2_static_model_level import _targets
from src.p1_static_engine.analyzer import intake_model
OUT=ROOT/'data/training/metadata/behavioral_development.json'; N=32; SEED=42
def probes():
 g=torch.Generator(device='cpu').manual_seed(SEED); x=torch.randn((N,3,224,224),generator=g,dtype=torch.float32)
 return x,hashlib.sha256(x.numpy().tobytes()).hexdigest()
def one(target,x,fingerprint):
 ctx=intake_model(ROOT/target['file'],'resnet18')
 if ctx.is_quantized or ctx.input_domain!='VISION': raise AssertionError('Non-quantized vision required')
 m=ctx.model.eval()
 with torch.inference_mode(): logits=m(x)
 if logits.shape[0]!=N or not torch.isfinite(logits).all(): raise ValueError('Invalid logits')
 p=torch.softmax(logits,dtype=torch.float64,dim=1)
 if not torch.isfinite(p).all() or not torch.allclose(p.sum(1),torch.ones(N,dtype=torch.float64),atol=1e-10): raise ValueError('Invalid probabilities')
 terms=torch.where(p>0,p*torch.log(p),torch.zeros_like(p));h=-terms.sum(1)/math.log(logits.shape[1])
 if not torch.isfinite(h).all() or torch.any(h< -1e-12) or torch.any(h>1+1e-12): raise ValueError('Invalid entropy')
 return {**target,'probe_count':N,'probe_seed':SEED,'probe_fingerprint':fingerprint,'output_class_count':int(logits.shape[1]),
         'H_STRIP':float(h.mean()),'entropy_std':float(h.std(unbiased=False)),'entropy_min':float(h.min()),'entropy_max':float(h.max())}
def write(records,complete=False):
 tmp=OUT.with_suffix('.json.tmp'); tmp.write_text(json.dumps({'version':'p3-entropy-strip-v1','records':records,'complete':complete},indent=2)+'\n');tmp.replace(OUT)
def extract():
 x,fp=probes(); prior=json.loads(OUT.read_text()) if OUT.exists() else {'records':[]}; old={r['artifact_sha256']:r for r in prior['records']}; records=[]
 for t in _targets():
  r=old.get(t['artifact_sha256'])
  valid=r and r.get('probe_fingerprint')==fp and r.get('probe_count')==N and all(math.isfinite(float(r[k])) for k in ('H_STRIP','entropy_std','entropy_min','entropy_max'))
  records.append(r if valid else one(t,x,fp));write(records)
 write(records,True);return records,x,fp
def roc(rows,scores):
 y=np.array([r['label'] for r in rows]);p=np.array([scores[r['artifact_sha256']] for r in rows]);return float(roc_auc_score(y,p))
def run():
 rows,x,fp=extract(); groups=np.array([r['parent_lineage_id'] for r in rows]); scores={}; folds=[];deg=[]
 for f,(tr,va) in enumerate(GroupKFold(n_splits=3).split(np.arange(len(rows)),groups=groups)):
  train=[rows[i] for i in tr];valid=[rows[i] for i in va]; tg={r['parent_lineage_id'] for r in train};vg={r['parent_lineage_id'] for r in valid}
  if tg&vg:raise AssertionError('lineage leakage')
  c=np.array([r['H_STRIP'] for r in train if r['label']==0]); med=float(np.median(c)); scale=float(1.4826*np.median(abs(c-med))); scale=float(np.std(c)) if scale<=1e-12 else scale
  if scale<=1e-12:deg.append(f);continue
  for r in valid:scores[r['artifact_sha256']]=(med-r['H_STRIP'])/scale
  folds.append((f,roc(valid,scores)))
 if deg: return {'baseline_degenerate_folds':deg,'records':rows}
 y=np.array([r['label'] for r in rows]);p=np.array([scores[r['artifact_sha256']] for r in rows]); clean=[r for r in rows if not r['label']]
 result={'records':rows,'probe_fingerprint':fp,'folds':folds,'pooled_behavior_ROC_AUC':float(roc_auc_score(y,p)),'pooled_behavior_PR_AUC':float(average_precision_score(y,p)),'PR_baseline':float(y.mean()),'baseline_degenerate_folds':[],'scores':scores}
 for fam in ('S1','S2','S3'):
  result[f'{fam}_ROC']=roc(clean+[r for r in rows if r['attack_family']==fam],scores)
  for st,label in ((.005,'.5'),(.01,'1'),(.02,'2'),(.05,'5')):result[f'{fam}_{label}_ROC']=roc(clean+[r for r in rows if r['attack_family']==fam and r['attack_strength']==st],scores)
 return result
if __name__=='__main__':
 r=run();(ROOT/'data/training/metadata/behavioral_development_evaluation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'records':len(r['records']),'degenerate':r['baseline_degenerate_folds']}))
