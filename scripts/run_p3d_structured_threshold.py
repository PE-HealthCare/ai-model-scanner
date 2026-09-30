"""Prompt 3D: fixed development-only threshold over frozen Prompt 3C OOF scores."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'data/training/metadata/s6_structured_generalization_evaluation.json'
OUTPUT=ROOT/'data/training/metadata/s6_structured_generalization_threshold.json'

def write(value:dict)->None:
    temp=OUTPUT.with_suffix('.json.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(OUTPUT)

def classification(rows:list[dict],scores:dict[str,float],threshold:float)->dict:
    y=np.array([r['label'] for r in rows],dtype=int);p=np.array([scores[r['artifact_sha256']] for r in rows],float);fail=p>=threshold
    tn=int(np.sum((y==0)&~fail));fp=int(np.sum((y==0)&fail));fn=int(np.sum((y==1)&~fail));tp=int(np.sum((y==1)&fail))
    return {'threshold':float(threshold),'TN':tn,'FP':fp,'FN':fn,'TP':tp,'clean_specificity':tn/(tn+fp),'tampered_recall':tp/(tp+fn),'balanced_accuracy':.5*(tn/(tn+fp)+tp/(tp+fn)),'overall_accuracy':float(np.mean((fail.astype(int))==y))}

def run()->dict:
    data=json.loads(INPUT.read_text(encoding='utf-8'));rows=data['records'];scores=data['full']['scores']
    if len(rows)!=65 or sum(r['label']==0 for r in rows)!=13 or sum(r['label']==1 for r in rows)!=52:raise AssertionError('Expected 13 clean + 52 S6 records')
    if any(r['partition']!='DEVELOPMENT' or r['attack_family']!='CLEAN' and r['attack_family']!='S6_STRUCTURED_GENERALIZATION' for r in rows):raise AssertionError('Non-development/non-S6 record')
    if len(scores)!=65 or any(r['artifact_sha256'] not in scores for r in rows):raise AssertionError('Incomplete Prompt 3C FULL OOF scores')
    candidates=[classification(rows,scores,t) for t in sorted({float(x) for x in scores.values()})]
    valid=[x for x in candidates if x['FP']<=1]
    if not valid:raise AssertionError('No boundary satisfies FP <= 1')
    # Fixed lexicographic objective: recall, specificity, largest threshold.
    selected=max(valid,key=lambda x:(x['tampered_recall'],x['clean_specificity'],x['threshold']))
    result={'score_source':'PROMPT3C_FULL_OOF','threshold_selection_data':'DEVELOPMENT_ONLY','selected':selected,'records':rows,'scores':scores}
    for key,field in [('strength', 'attack_strength'),('family','payload_family'),('target','target_tensor')]:
        out={}
        values=sorted({r[field] for r in rows if r['label']==1})
        for value in values:
            subset=[r for r in rows if r['label']==1 and r[field]==value];fails=sum(scores[r['artifact_sha256']]>=selected['threshold'] for r in subset)
            out[str(value)]={'tampered_count':len(subset),'detected_fail':int(fails),'missed_pass':len(subset)-int(fails),'recall':fails/len(subset)}
        result[key]=out
    clean=[scores[r['artifact_sha256']] for r in rows if not r['label']];tampered=[scores[r['artifact_sha256']] for r in rows if r['label']]
    result['distribution']={'max_clean_score':float(max(clean)),'min_tampered_score':float(min(tampered)),'clean_score_median':float(np.median(clean)),'tampered_score_median':float(np.median(tampered)),'margin':float(min(tampered)-max(clean))}
    result['decision']='FREEZE_STRUCTURED_STEGO_THRESHOLD' if selected['FP']<=1 and selected['tampered_recall']>=.85 else 'THRESHOLD_NOT_GOOD_ENOUGH'
    write(result);return result

def report(r:dict)->None:
    s=r['selected'];strength=r['strength'];family=r['family'];target=r['target'];d=r['distribution']
    out={'PROMPT3D':'COMPLETE','score_source':r['score_source'],'threshold_selection_data':r['threshold_selection_data'],'selected_threshold':s['threshold'],'TN':s['TN'],'FP':s['FP'],'FN':s['FN'],'TP':s['TP'],'clean_total':13,'tampered_total':52,'clean_specificity':s['clean_specificity'],'clean_false_positive_rate':1-s['clean_specificity'],'tampered_recall':s['tampered_recall'],'tampered_false_negative_rate':1-s['tampered_recall'],'balanced_accuracy':s['balanced_accuracy'],'overall_accuracy':s['overall_accuracy'],'CLEAN_predicted_PASS':s['TN'],'CLEAN_predicted_FAIL':s['FP'],'S6_predicted_PASS':s['FN'],'S6_predicted_FAIL':s['TP'],'S6_0.5_recall':strength['0.005']['recall'],'S6_1_recall':strength['0.01']['recall'],'S6_2_recall':strength['0.02']['recall'],'S6_5_recall':strength['0.05']['recall'],'ASCII_recall':family['ASCII']['recall'],'BINARY_recall':family['BINARY']['recall'],'FRAMED_RANDOM_recall':family['FRAMED_RANDOM']['recall'],'layer3.1.conv2_recall':target['layer3.1.conv2.weight']['recall'],'layer4.0.conv2_recall':target['layer4.0.conv2.weight']['recall'],'layer4.1.conv2_recall':target['layer4.1.conv2.weight']['recall'],**d,'final_test_records':0,'s4_records':0,'lineage_leakage':False,'DECISION':r['decision']}
    for k,v in out.items():print(f'{k}={v}')
    print('FILES_CREATED_OR_MODIFIED:');print('scripts/run_p3d_structured_threshold.py');print('data/training/metadata/s6_structured_generalization_threshold.json')
if __name__=='__main__':report(run())
