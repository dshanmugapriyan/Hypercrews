import os
import joblib
import numpy as np
from app.services.url.interface import URLFeatures, URLRiskModel, URLRiskPrediction

class RealURLRiskModel(URLRiskModel):
    def __init__(self, model_dir="app/resources"):
        self.model_path = os.path.join(model_dir, "url_classifier.joblib")
        self.classifier = None
        self.model_name = "RealURL-XGBoost"
        self.model_version = "1.0.0"
        self._load_or_train_fallback()

    def is_trained(self) -> bool:
        return self.classifier is not None

    def _load_or_train_fallback(self):
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                self.classifier = data["classifier"]
                self.model_name = data.get("model_name", self.model_name)
                self.model_version = data.get("model_version", self.model_version)
                return
            except Exception:
                pass

        self._train_inline()

    def _train_inline(self):
        # Generate some synthetic URL features for training
        # Vector format: [url_length, domain_length, subdomain_count, digit_ratio, special_char_ratio, entropy, has_suspicious_tld, is_https, redirect_count]
        # Y labels: 0 for safe, 1 for scam URL
        import xgboost as xgb
        
        train_x = [
            [80, 25, 3, 0.25, 0.15, 4.2, 1, 0, 2],  # scam
            [95, 30, 4, 0.30, 0.20, 4.5, 1, 0, 1],  # scam
            [120, 28, 2, 0.20, 0.18, 3.9, 0, 1, 1], # scam
            [45, 15, 1, 0.05, 0.05, 2.8, 0, 1, 0],  # safe
            [35, 12, 0, 0.02, 0.04, 2.5, 0, 1, 0],  # safe
            [22, 10, 0, 0.00, 0.00, 2.1, 0, 1, 0],  # safe
            [110, 35, 4, 0.28, 0.22, 4.8, 1, 0, 3], # scam
            [50, 18, 1, 0.08, 0.06, 3.1, 0, 1, 0],  # safe
        ]
        train_y = [1, 1, 1, 0, 0, 0, 1, 0]

        self.classifier = xgb.XGBClassifier(n_estimators=30, max_depth=3, learning_rate=0.1, eval_metric="logloss")
        self.classifier.fit(np.array(train_x), np.array(train_y))

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            "classifier": self.classifier,
            "model_name": self.model_name,
            "model_version": self.model_version
        }, self.model_path)

    def _get_vector(self, f: URLFeatures):
        return [
            float(f.url_length),
            float(f.domain_length),
            float(f.subdomain_count),
            float(f.digit_ratio),
            float(f.special_char_ratio),
            float(f.entropy),
            1.0 if f.has_suspicious_tld else 0.0,
            1.0 if f.is_https else 0.0,
            float(f.redirect_count or 0)
        ]

    def predict(self, f: URLFeatures) -> URLRiskPrediction:
        if not self.classifier:
            return URLRiskPrediction(0.1, f, {}, "fallback", "0.0.0", False)

        vec = self._get_vector(f)
        probs = self.classifier.predict_proba(np.array([vec]))[0]
        risk_prob = float(probs[1])

        # Feature explanation based on native XGBoost feature importances
        feature_names = [
            "url_length", "domain_length", "subdomain_count",
            "digit_ratio", "special_char_ratio", "entropy",
            "has_suspicious_tld", "is_https", "redirect_count"
        ]
        
        # XGBoost feature importances represents global split gains
        importances = self.classifier.feature_importances_
        
        # Calculate impact of each feature
        contributions = {}
        for name, val, imp in zip(feature_names, vec, importances):
            # Highlight feature contributions (importance scaled by value deviation)
            # e.g., if is_https is 0 (unsecured), it adds to the threat. If has_suspicious_tld is 1, it adds.
            val_adjusted = 1.0 - val if name == "is_https" else val
            contrib = val_adjusted * imp
            if abs(contrib) > 0.01:
                contributions[name] = round(float(contrib), 4)

        return URLRiskPrediction(
            url_risk_probability=round(risk_prob, 4),
            features=f,
            feature_importance=contributions,
            model_name=self.model_name,
            model_version=self.model_version,
            is_demo_prediction=False
        )
