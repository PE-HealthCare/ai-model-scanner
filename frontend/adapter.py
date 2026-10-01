"""Session-local integration. All security decisions belong to the backend."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
LIMITATIONS = [
    'Authoritative scope: trusted FP32 ResNet18 SafeTensors and the tested structured-LSB payload patterns. Other precision paths have no final assessment from this detector.',
    'PASS means no statistical evidence exceeded this detector threshold within its tested scope; it does not guarantee safety.',
    'Structured-LSB is an anomaly statistic, not a calibrated probability of malware.',
    'Development threshold selection used grouped out-of-fold scores with fold-specific clean normalization. Runtime instead normalizes against all 13 development-clean reference vectors; OOF performance is not a measured runtime performance guarantee.',
    'External validation is not established: the acquisition manifest reports an insufficient external clean set (2 accepted; minimum 5).',
    'Historical MRS is an experimental diagnostic excluded from the final assessment. It produced 72.39 / FAIL on the known-clean torchvision reference.',
    'LightGBM and TreeSHAP are advisory only. P_tamper is not a calibrated malware probability and cannot override the statistical detector.',
    'Behavioral evidence is supporting only and cannot override the statistical detector.',
    'Behavior uses random-noise probes and a stored ResNet18 calibration. Comparability to other classifier heads is not established. No trigger verification executes.',
]


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def finalize(result: dict, filename: str, size: int, elapsed: float) -> dict:
    """Bind backend evidence to one upload and one immutable export snapshot."""
    snapshot = {
        'contract_version': 'sigtensor-ui-assessment-v3',
        'scan_id': str(uuid4()),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'upload': {'filename': filename, 'size_bytes': size},
        'duration_seconds': elapsed,
        'backend': deepcopy(result),
        'limitations': list(LIMITATIONS),
        'evidence': [
            {'id': f'STATIC-{i:02d}', 'source': f'backend.structured_stego.features.{name}',
             'category': 'STRUCTURED_LSB',
             'feature': name, 'value': value, 'diagnostic_only': name == 'max_window_repeat_fraction'}
            for i, (name, value) in enumerate(result.get('structured_stego', {}).get('features', {}).items(), 1)
        ],
    }
    snapshot['evidence_sha256'] = hashlib.sha256(canonical_bytes(snapshot)).hexdigest()
    return snapshot


def scan_upload(filename: str, content: bytes) -> dict:
    start = time.perf_counter()
    # User filenames are display-only; they never become filesystem paths.
    filename = filename.replace('\\', '/').rsplit('/', 1)[-1]
    try:
        from scan_model import run_pipeline, run_structured_scan
        if not filename.lower().endswith('.safetensors'):
            raise ValueError('Unsupported file extension. Select a .safetensors artifact.')
        if len(content) > 200 * 1024 * 1024:
            raise ValueError('Upload exceeds the UI memory policy of 200 MiB.')
        temp_root = ROOT / 'tmp' / 'uploads'
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='scan-', dir=temp_root) as directory:
            path = Path(directory) / 'artifact.safetensors'
            path.write_bytes(content)
            runtime = {}
            result = {'artifact': {'sha256': hashlib.sha256(content).hexdigest()},
                      'verdict': 'WITHHELD', 'intake': {'status': 'NOT_CONFIRMED'},
                      'execution_status': 'INCOMPLETE', 'canonical': runtime}
            try:
                run_pipeline(path, declared_architecture='resnet18', output_dir=Path(directory)/'outputs', evidence=runtime)
            except Exception as exc:
                result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
            if runtime.get('artifact'):
                result['artifact'].update(runtime['artifact'])
                result['intake']['status'] = 'PASS'
                structured_started = time.perf_counter()
                if runtime['artifact']['is_quantized']:
                    result['structured_status'] = {'status': 'not_applicable', 'reason': 'Structured-LSB requires FP32 weights.'}
                else:
                    try:
                        separate = run_structured_scan(path, declared_architecture='resnet18')
                        validate_backend_result(separate, content)
                        result['structured_stego'] = separate['structured_stego']
                        result['structured_status'] = {'status': 'complete'}
                    except Exception as exc:
                        result['structured_status'] = {'status': 'unavailable', 'reason': str(exc)}
                result['structured_status']['seconds'] = time.perf_counter() - structured_started
            else:
                result['structured_status'] = {'status': 'skipped', 'reason': 'Trusted intake did not complete.'}
            # Pass through the validated detector verdict, never recompute it.
            if 'structured_stego' in result:
                result['verdict'] = result['structured_stego']['verdict']
                result['execution_status'] = 'COMPLETE' if 'dashboard_results' in runtime else 'PARTIAL'
            result['decision_source'] = 'src.p3_ml_dashboard.structured_stego.scan'
            result['assessment_status'] = 'complete' if 'structured_stego' in result else 'withheld'
            result['roles'] = {'structured_stego': 'authoritative', 'ml': 'advisory',
                               'behavior': 'supporting', 'legacy_mrs': 'experimental_excluded'}
        result['artifact']['filename'] = filename
        canonical_bytes(result)  # Non-finite evidence must never reach a verdict screen.
        if result['artifact']['sha256'] != hashlib.sha256(content).hexdigest():
            raise ValueError('Current scan identity mismatch')
    except Exception as exc:
        result = {'artifact': {'filename': filename, 'sha256': hashlib.sha256(content).hexdigest()},
                  'verdict': 'WITHHELD', 'intake': {'status': 'NOT_CONFIRMED'},
                  'execution_status': 'FAILED',
                  'error': {'type': type(exc).__name__, 'message': str(exc)}}
    return finalize(result, filename, len(content), time.perf_counter() - start)


def validate_backend_result(result: dict, content: bytes) -> None:
    """Validate transport completeness/identity, without recomputing a decision."""
    from src.p3_ml_dashboard.structured_stego import FEATURE_NAMES
    artifact = result['artifact']
    detector = result['structured_stego']
    for key in ('architecture', 'input_domain', 'dtype', 'is_quantized', 'layer_count'):
        if key not in artifact:
            raise ValueError(f'Backend artifact is missing {key}')
    if artifact['sha256'] != hashlib.sha256(content).hexdigest():
        raise ValueError('Backend artifact identity does not match the upload')
    if result['intake']['status'] != 'PASS':
        raise ValueError('Backend did not confirm trusted intake')
    if result['verdict'] not in ('PASS', 'FAIL') or detector['verdict'] != result['verdict']:
        raise ValueError('Backend verdict fields are missing or inconsistent')
    if set(detector['features']) != set(FEATURE_NAMES):
        raise ValueError('Backend feature contract is incomplete')
    if set(detector['z_scores']) != {'entropy', 'printable', 'chi2', 'transition'}:
        raise ValueError('Backend normalized evidence is incomplete')
    for key in ('score', 'threshold', 'dominant_signal', 'reference_hash', 'detector_version'):
        if key not in detector:
            raise ValueError(f'Backend detector is missing {key}')
    required_numbers = [detector['score'], detector['threshold'],
                        *detector['features'].values(), *detector['z_scores'].values()]
    if any(type(number) not in (int, float) or not math.isfinite(number) for number in required_numbers):
        raise ValueError('Backend required evidence must contain finite numeric values')


def json_export(snapshot: dict) -> bytes:
    return json.dumps(snapshot, indent=2, ensure_ascii=True, allow_nan=False).encode()
