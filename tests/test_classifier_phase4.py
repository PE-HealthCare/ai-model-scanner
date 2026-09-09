import tempfile
import unittest
from pathlib import Path
import lightgbm as lgb
import numpy as np
from src.p3_ml_dashboard.classifier import FEATURE_NAMES, build_ml_results

class TestPhase4Classifier(unittest.TestCase):
    def _model(self, path: Path):
        rng = np.random.default_rng(7)
        X = np.vstack([rng.normal(size=(30, 10)), rng.normal(loc=1, size=(30, 10))])
        y = np.r_[np.zeros(30), np.ones(30)]
        model = lgb.train({"objective":"binary","verbosity":-1,"seed":7,"feature_pre_filter":False}, lgb.Dataset(X,label=y,feature_name=list(FEATURE_NAMES)), num_boost_round=20)
        model.save_model(str(path))

    def _features(self):
        return {"producer":"P1","mock_status":"VERIFIED-REAL","contract_version":"1.0","generation_commit":"TEST","layer_count":1,"static_features":[{"layer_name":"layer1","entropy":1.0,"pov_chi2":1.0,"lsb_kl":0.1,"ks_stat":0.1,"mean":0.0,"std":1.0,"skewness":0.0,"kurtosis":3.0,"sparsity":0.1,"outlier_pct":1.0}]}

    def test_real_classifier_and_tree_shap_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"model.txt"; self._model(p); result=build_ml_results(self._features(),"TEST",model_path=p)
        self.assertEqual(result["producer"],"P3")
        self.assertEqual(result["mock_status"],"VERIFIED-REAL")
        self.assertTrue(0.0 <= result["p_tamper"] <= 1.0)
        self.assertEqual(list(result["shap_attributions"]),list(FEATURE_NAMES))

    def test_stale_generation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"model.txt"; self._model(p)
            with self.assertRaisesRegex(ValueError,"stale"): build_ml_results(self._features(),"OTHER",model_path=p)

    def test_nonfinite_feature_rejected_without_imputation(self):
        f=self._features(); f["static_features"][0]["entropy"]=float("nan")
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"model.txt"; self._model(p)
            with self.assertRaisesRegex(ValueError,"non-finite"): build_ml_results(f,"TEST",model_path=p)

    def test_multi_layer_aggregation_not_invented(self):
        f=self._features(); f["layer_count"]=2; f["static_features"].append(dict(f["static_features"][0],layer_name="layer2"))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"model.txt"; self._model(p)
            with self.assertRaisesRegex(RuntimeError,"DECISION REQUIRED"): build_ml_results(f,"TEST",model_path=p)
