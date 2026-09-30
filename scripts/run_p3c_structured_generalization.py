"""Prompt 3C S6 structured-payload generalization benchmark (development only)."""
from __future__ import annotations
import hashlib, json, math, sys
from collections import Counter
from pathlib import Path
import numpy as np
import torch
from safetensors import safe_open
from safetensors.torch import save_file
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.run_p3b_structured_payload import _development_sources, _json_bytes, _load_state, _sha256, _write
from src.p3_ml_dashboard.structured_stego import extract_features as _extract_structured_features
META=ROOT/'data/training/metadata'; OUTDIR=ROOT/'data/training/s6_structured_generalization'
MANIFEST=META/'s6_structured_generalization_manifest.json'; CACHE=META/'s6_structured_generalization_development.json'; EVAL=META/'s6_structured_generalization_evaluation.json'
STRENGTHS=(.005,.01,.02,.05); TARGETS=('layer3.1.conv2.weight','layer4.0.conv2.weight','layer4.1.conv2.weight')
FAMILIES=('ASCII','BINARY','FRAMED_RANDOM'); WINDOW=4096; STRIDE=2048
NAMES=('min_window_entropy','max_window_printable_fraction','max_window_byte_chi2','max_window_transition_deviation','max_window_repeat_fraction')
ASCII=b'GE_HEALTHCARE_SAFE_STEG_BENCHMARK_V1|NON_EXECUTABLE_PAYLOAD|MODEL_SECURITY_TEST|'
BINARY=bytes.fromhex('00 FF 55 AA 13 EC 7F 80 42 BD 24 DB 66 99 18 E7'); MARKER=bytes.fromhex('00 FF 00 FF 7E 81 3C C3')

def choose(source_id:str, choices:tuple[str,...])->str:
    return choices[int.from_bytes(hashlib.sha256(source_id.encode()).digest()[:8],'little')%len(choices)]

def payload(family:str, bit_count:int, source_id:str)->tuple[np.ndarray,str]:
    n=math.ceil(bit_count/8)
    if family=='ASCII': data=(ASCII*math.ceil(n/len(ASCII)))[:n]
    elif family=='BINARY': data=(BINARY*math.ceil(n/len(BINARY)))[:n]
    elif family=='FRAMED_RANDOM':
        rng=np.random.default_rng(int.from_bytes(hashlib.sha256(('S6|'+source_id).encode()).digest()[:8],'little'))
        chunks=[]
        while sum(map(len,chunks))<n:
            chunks.extend([rng.integers(0,256,256,dtype=np.uint8).tobytes(),MARKER])
        data=b''.join(chunks)[:n]
    else: raise ValueError(family)
    return np.unpackbits(np.frombuffer(data,dtype=np.uint8),bitorder='little')[:bit_count].astype(np.uint32),hashlib.sha256(data).hexdigest()

def embed(clean:Path,strength:float,source_id:str)->tuple[dict[str,torch.Tensor],dict]:
    state=_load_state(clean); total=sum(x.numel() for x in state.values() if x.dtype==torch.float32); selected=math.ceil(total*strength)
    family=choose(source_id,FAMILIES); target=choose(source_id,TARGETS)
    if target not in state or state[target].dtype!=torch.float32 or state[target].numel()<selected: raise ValueError(f'Assigned target unavailable/insufficient: {target}')
    bits,payload_sha=payload(family,selected,source_id); array=state[target].numpy().copy(order='C'); raw=array.view(np.uint32).reshape(-1); before=raw[:selected].copy()
    raw[:selected]=(raw[:selected]&np.uint32(0xFFFFFFFE))|bits; changed=int(np.count_nonzero(before!=raw[:selected]))
    if changed<=0: raise AssertionError('No target values changed')
    state[target]=torch.from_numpy(array)
    return state,{'attack_family':'S6_STRUCTURED_GENERALIZATION','attack_strength':strength,'payload_family':family,'target_tensor':target,'payload_sha256':payload_sha,'total_fp32_elements':int(total),'selected_element_count':int(selected),'actually_changed_element_count':changed,'bit_position':0,'bit_order':'little_endian_within_byte','embedding_operation':'u_new=(u&0xFFFFFFFE)|b'}

def validate(clean:Path,derivative:Path,details:dict)->None:
    a,b=_load_state(clean),_load_state(derivative)
    if tuple(sorted(a))!=tuple(sorted(b)): raise AssertionError('Tensor names changed')
    changed=0
    for name in sorted(a):
        x,y=a[name],b[name]
        if x.shape!=y.shape or x.dtype!=y.dtype: raise AssertionError(f'Schema changed: {name}')
        aa,bb=x.numpy(),y.numpy()
        if name!=details['target_tensor']:
            if not np.array_equal(aa,bb): raise AssertionError(f'Non-target changed: {name}')
        else:
            diff=np.bitwise_xor(aa.view(np.uint32),bb.view(np.uint32))
            if np.any(diff&np.uint32(0xFFFFFFFE)): raise AssertionError('Modified bit other than FP32 mantissa bit 0')
            changed=int(np.count_nonzero(diff))
    if changed<=0 or changed!=details['actually_changed_element_count']: raise AssertionError('Changed count mismatch')
    if details['selected_element_count']!=math.ceil(details['total_fp32_elements']*details['attack_strength']): raise AssertionError('Selected count mismatch')

def corpus()->dict:
    prior=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'artifacts':[]}; old={(x['source_model_id'],float(x['attack_strength'])):x for x in prior['artifacts']}; artifacts=[]
    for src in _development_sources():
        clean=ROOT/src['file']
        if _sha256(clean)!=src['file_sha256']: raise AssertionError('Clean source SHA mismatch')
        for strength in STRENGTHS:
            ident=hashlib.sha256(_json_bytes({'source_sha':src['file_sha256'],'strength':strength,'family':choose(src['source_model_id'],FAMILIES),'target':choose(src['source_model_id'],TARGETS),'version':'p3c-v1'})).hexdigest()[:24]
            path=OUTDIR/f'{ident}.safetensors'; existing=old.get((src['source_model_id'],strength)); reusable=existing and path.exists() and _sha256(path)==existing.get('derivative_sha256')
            if reusable:
                details={k:existing[k] for k in ('attack_family','attack_strength','payload_family','target_tensor','payload_sha256','total_fp32_elements','selected_element_count','actually_changed_element_count','bit_position','bit_order','embedding_operation')}; validate(clean,path,details)
            else:
                state,details=embed(clean,strength,src['source_model_id']); path.parent.mkdir(parents=True,exist_ok=True); save_file({k:v.contiguous() for k,v in state.items()},str(path)); validate(clean,path,details)
            artifacts.append({'artifact_id':ident,'file':str(path.relative_to(ROOT)).replace('\\','/'),'derivative_sha256':_sha256(path),'clean_parent_sha256':src['file_sha256'],'source_model_id':src['source_model_id'],'parent_lineage_id':src['parent_lineage_id'],'partition':'DEVELOPMENT',**details})
            _write(MANIFEST,{'version':'p3c-s6-v1','artifacts':artifacts,'complete':False})
    result={'version':'p3c-s6-v1','artifacts':artifacts,'complete':True};_write(MANIFEST,result);return result

def features(path:Path)->dict[str,float]:
    """Compatibility wrapper around the production frozen detector extractor."""
    return _extract_structured_features(path)

def targets(c:dict)->list[dict]:
    clean=[{'file':s['file'],'artifact_sha256':s['file_sha256'],'source_model_id':s['source_model_id'],'parent_lineage_id':s['parent_lineage_id'],'partition':'DEVELOPMENT','attack_family':'CLEAN','attack_strength':None,'label':0} for s in _development_sources()]
    s6=[{'file':x['file'],'artifact_sha256':x['derivative_sha256'],'source_model_id':x['source_model_id'],'parent_lineage_id':x['parent_lineage_id'],'partition':x['partition'],'attack_family':x['attack_family'],'attack_strength':x['attack_strength'],'payload_family':x['payload_family'],'target_tensor':x['target_tensor'],'label':1} for x in c['artifacts']]
    rows=clean+s6
    if len(rows)!=65 or any(x['partition']!='DEVELOPMENT' or x['attack_family']=='S4' for x in rows):raise AssertionError('Invalid development-only target set')
    return rows

def extract(c:dict)->list[dict]:
    prior=json.loads(CACHE.read_text()) if CACHE.exists() else {'records':[]}; old={x['artifact_sha256']:x for x in prior['records']};rows=[]
    for t in targets(c):
        previous=old.get(t['artifact_sha256']);valid=previous and _sha256(ROOT/t['file'])==t['artifact_sha256'] and tuple(previous.get('feature_names',[]))==NAMES and all(math.isfinite(float(previous['features'][n])) for n in NAMES)
        rows.append({**t,'feature_names':list(NAMES),'features':previous['features'] if valid else features(ROOT/t['file'])});_write(CACHE,{'version':'p3c-s6-byte-scanner-v1','feature_names':list(NAMES),'records':rows,'complete':False})
    _write(CACHE,{'version':'p3c-s6-byte-scanner-v1','feature_names':list(NAMES),'records':rows,'complete':True});return rows

def score_eval(rows:list[dict], use_printable:bool)->dict:
    """Prompt 3C.1: repeat fraction is retained only as a raw diagnostic."""
    scored=('min_window_entropy','max_window_byte_chi2','max_window_transition_deviation')
    if use_printable: scored=('min_window_entropy','max_window_printable_fraction','max_window_byte_chi2','max_window_transition_deviation')
    groups=np.array([r['parent_lineage_id'] for r in rows]);scores={};folds=[];deg=[]
    winners={}
    for f,(tr,va) in enumerate(GroupKFold(n_splits=3).split(np.arange(len(rows)),groups=groups)):
        train=[rows[i] for i in tr];valid=[rows[i] for i in va]
        if {x['parent_lineage_id'] for x in train}&{x['parent_lineage_id'] for x in valid}:raise AssertionError('Lineage leakage')
        base={}; bad=False
        for n in scored:
            vals=np.array([x['features'][n] for x in train if not x['label']],float);med=float(np.median(vals));scale=float(1.4826*np.median(abs(vals-med)));scale=float(np.std(vals)) if scale<=1e-12 else scale;base[n]=(med,scale);bad|=scale<=1e-12
        if bad:deg.append(f);continue
        for r in valid:
            z={'entropy':(base['min_window_entropy'][0]-r['features']['min_window_entropy'])/base['min_window_entropy'][1],
               'chi2':(r['features']['max_window_byte_chi2']-base['max_window_byte_chi2'][0])/base['max_window_byte_chi2'][1],
               'transition':(r['features']['max_window_transition_deviation']-base['max_window_transition_deviation'][0])/base['max_window_transition_deviation'][1]}
            if use_printable: z['printable']=(r['features']['max_window_printable_fraction']-base['max_window_printable_fraction'][0])/base['max_window_printable_fraction'][1]
            scores[r['artifact_sha256']]=float(max(0,*z.values()))
            if use_printable: winners[r['artifact_sha256']]=max(z, key=z.get)
        folds.append({'fold':f,'roc_auc':float(roc_auc_score([x['label'] for x in valid],[scores[x['artifact_sha256']] for x in valid]))})
    if deg:return {'scores':scores,'folds':folds,'baseline_degenerate_folds':deg,'winners':winners}
    y=np.array([x['label'] for x in rows]);p=np.array([scores[x['artifact_sha256']] for x in rows]);return {'scores':scores,'folds':folds,'baseline_degenerate_folds':[],'winners':winners,'pooled_ROC_AUC':float(roc_auc_score(y,p)),'pooled_PR_AUC':float(average_precision_score(y,p)),'PR_baseline':float(y.mean())}

def roc(rows:list[dict],scores:dict[str,float])->float:return float(roc_auc_score([x['label'] for x in rows],[scores[x['artifact_sha256']] for x in rows]))
def run()->dict:
    # Prompt 3C.1 freezes the generated corpus and five-feature cache.
    cached=json.loads(CACHE.read_text(encoding='utf-8'))
    if not cached.get('complete') or tuple(cached.get('feature_names',()))!=NAMES:
        raise AssertionError('Missing or incompatible frozen S6 feature cache')
    rows=cached['records']
    if len(rows)!=65 or sum(not r['label'] for r in rows)!=13 or sum(r['label'] for r in rows)!=52:
        raise AssertionError('Frozen S6 cache counts are invalid')
    full=score_eval(rows,True);nop=score_eval(rows,False)
    if full['baseline_degenerate_folds'] or nop['baseline_degenerate_folds']:raise RuntimeError(f"BASELINE_DEGENERATE full={full['baseline_degenerate_folds']} no_printable={nop['baseline_degenerate_folds']}")
    clean=[x for x in rows if not x['label']];s6=[x for x in rows if x['label']]
    for family in FAMILIES:
        subset=clean+[x for x in s6 if x['payload_family']==family];full[f'{family}_ROC']=roc(subset,full['scores']);nop[f'{family}_ROC']=roc(subset,nop['scores'])
    for strength,label in zip(STRENGTHS,('0.5','1','2','5')):full[f'S6_{label}_ROC']=roc(clean+[x for x in s6 if x['attack_strength']==strength],full['scores'])
    for target in TARGETS:full[f'{target}_ROC']=roc(clean+[x for x in s6 if x['target_tensor']==target],full['scores'])
    result={'records':rows,'full':full,'no_printable':nop};_write(EVAL,result);return result

def report(r:dict)->None:
    rows=r['records'];clean=[x for x in rows if not x['label']];s6=[x for x in rows if x['label']];full=r['full'];nop=r['no_printable'];counts=Counter(str(x['attack_strength']) for x in s6);fc=Counter(x['payload_family'] for x in s6);folds=[x['roc_auc'] for x in full['folds']]
    dec='KEEP_GENERALIZED_STRUCTURED_STEGO_DETECTOR' if full['pooled_ROC_AUC']>=.85 and all(x>=.75 for x in folds) and all(full[f'{x}_ROC']>=.75 for x in FAMILIES) else ('GENERALIZATION_SIGNAL_PRESENT_BUT_INSUFFICIENT' if full['pooled_ROC_AUC']>=.70 else 'STOP_GENERALIZED_STRUCTURED_STEGO_DETECTOR')
    winners=Counter(full['winners'][x['artifact_sha256']] for x in s6)
    family_winners={family:Counter(full['winners'][x['artifact_sha256']] for x in s6 if x['payload_family']==family) for family in FAMILIES}
    repeat=lambda subset: [float(np.min([x['features']['max_window_repeat_fraction'] for x in subset])),float(np.median([x['features']['max_window_repeat_fraction'] for x in subset])),float(np.max([x['features']['max_window_repeat_fraction'] for x in subset]))]
    cr,sr=repeat(clean),repeat(s6)
    out={'PROMPT3C':'COMPLETE','corpus_reused':True,'s6_regenerated':False,'features_reextracted':False,'clean_artifacts':len(clean),'s6_artifacts':len(s6),'lineage_count':len({x['parent_lineage_id'] for x in rows}),'scored_features_full':4,'scored_features_no_printable':3,'repeat_feature_status':'DIAGNOSTIC_ONLY_DEGENERATE_CLEAN_BASELINE','FULL_pooled_ROC':full['pooled_ROC_AUC'],'FULL_pooled_PR_AUC':full['pooled_PR_AUC'],'PR_baseline':full['PR_baseline'],'FULL_fold_0_ROC':folds[0],'FULL_fold_1_ROC':folds[1],'FULL_fold_2_ROC':folds[2],'S6_ASCII_FULL_ROC':full['ASCII_ROC'],'S6_BINARY_FULL_ROC':full['BINARY_ROC'],'S6_FRAMED_RANDOM_FULL_ROC':full['FRAMED_RANDOM_ROC'],'S6_ASCII_NO_PRINTABLE_ROC':nop['ASCII_ROC'],'S6_BINARY_NO_PRINTABLE_ROC':nop['BINARY_ROC'],'S6_FRAMED_RANDOM_NO_PRINTABLE_ROC':nop['FRAMED_RANDOM_ROC'],'NO_PRINTABLE_pooled_ROC':nop['pooled_ROC_AUC'],'S6_0.5_ROC':full['S6_0.5_ROC'],'S6_1_ROC':full['S6_1_ROC'],'S6_2_ROC':full['S6_2_ROC'],'S6_5_ROC':full['S6_5_ROC'],'layer3.1.conv2_ROC':full['layer3.1.conv2.weight_ROC'],'layer4.0.conv2_ROC':full['layer4.0.conv2.weight_ROC'],'layer4.1.conv2_ROC':full['layer4.1.conv2.weight_ROC'],'winner_entropy':winners['entropy'],'winner_printable':winners['printable'],'winner_chi2':winners['chi2'],'winner_transition':winners['transition'],'ASCII_winners':dict(family_winners['ASCII']),'BINARY_winners':dict(family_winners['BINARY']),'FRAMED_RANDOM_winners':dict(family_winners['FRAMED_RANDOM']),'clean_repeat_min':cr[0],'clean_repeat_median':cr[1],'clean_repeat_max':cr[2],'s6_repeat_min':sr[0],'s6_repeat_median':sr[1],'s6_repeat_max':sr[2],'ASCII_repeat_median':repeat([x for x in s6 if x['payload_family']=='ASCII'])[1],'BINARY_repeat_median':repeat([x for x in s6 if x['payload_family']=='BINARY'])[1],'FRAMED_RANDOM_repeat_median':repeat([x for x in s6 if x['payload_family']=='FRAMED_RANDOM'])[1],'exact_repeat_structure_observed':cr[0]==0 and cr[2]==0 and sr[2]>0,'baseline_degenerate_scored_features':full['baseline_degenerate_folds'],'lineage_leakage':False,'final_test_records':0,'s4_records':0,'DECISION':dec}
    for k,v in out.items():print(f'{k}={v}')
    print('FILES_CREATED_OR_MODIFIED:');print('scripts/run_p3c_structured_generalization.py');print('data/training/s6_structured_generalization/');print('data/training/metadata/s6_structured_generalization_manifest.json');print('data/training/metadata/s6_structured_generalization_development.json');print('data/training/metadata/s6_structured_generalization_evaluation.json')
if __name__=='__main__':report(run())
