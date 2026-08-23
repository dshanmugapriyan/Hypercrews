import os
import joblib
from app.services.fusion.interface import FusionFeatureVector, FusionModel, FusionResult

class RealFusionModel(FusionModel):
    def __init__(self, model_dir="app/resources"):
        self.model_path = os.path.join(model_dir, "fusion_model.joblib")
        self.classifier = None
        self.model_name = "RealFusion-LogisticRegression"
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
        from sklearn.linear_model import LogisticRegression
        
        # Features ordering in as_ordered_list:
        # [nlp_scam_probability, url_risk_probability, identity_consistency, semantic_similarity,
        #  payment_probability, social_engineering_probability, opportunity_risk, company_verification_signal]
        # Y labels: 0 for safe, 1 for scam
        train_x = [
            # High risk features
            [0.9, 0.8, 0.0, 0.8, 0.9, 0.8, 0.9, 0.0],  # scam
            [0.8, 0.7, 0.2, 0.75, 0.8, 0.7, 0.8, 0.2], # scam
            [0.95, 0.9, 0.0, 0.9, 0.95, 0.9, 0.95, 0.0],# scam
            # Low risk features
            [0.1, 0.1, 1.0, 0.1, 0.1, 0.1, 0.1, 1.0],  # safe
            [0.05, 0.05, 1.0, 0.05, 0.05, 0.05, 0.05, 1.0], # safe
            [0.15, 0.1, 0.8, 0.2, 0.15, 0.1, 0.2, 0.8], # safe
            # Mixed (mostly safe or suspicious)
            [0.4, 0.3, 0.6, 0.4, 0.3, 0.4, 0.4, 0.6],  # suspicious/borderline (trained as safe/moderate)
            [0.7, 0.2, 0.4, 0.6, 0.7, 0.5, 0.6, 0.4]   # scam
        ]
        train_y = [1, 1, 1, 0, 0, 0, 0, 1]

        self.classifier = LogisticRegression()
        self.classifier.fit(train_x, train_y)

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            "classifier": self.classifier,
            "model_name": self.model_name,
            "model_version": self.model_version
        }, self.model_path)

    def fuse(self, f: FusionFeatureVector) -> FusionResult:
        if not self.classifier:
            # Fallback inline weights if loading/training failed
            nlp_score = f.nlp_scam_probability
            url_score = f.url_risk_probability or 0.0
            identity_score = 1.0 - f.identity_consistency
            similarity = f.semantic_similarity
            raw_prob = (nlp_score * 0.35) + (url_score * 0.2) + (identity_score * 0.25) + (similarity * 0.2)
            contributions = {
                "nlp_scam_probability": round(nlp_score * 0.35, 4),
                "url_risk_probability": round(url_score * 0.2, 4),
                "identity_inconsistency": round(identity_score * 0.25, 4),
                "semantic_similarity": round(similarity * 0.2, 4)
            }
            return FusionResult(round(raw_prob, 4), contributions, "fallback-weights", "0.0.0", False)

        vec = f.as_ordered_list()
        
        # Ensure feature vector length matches the model's coefficients
        # Slice or pad with 0.0 to match self.classifier.coef_[0] length
        expected_len = len(self.classifier.coef_[0])
        if len(vec) < expected_len:
            vec += [0.0] * (expected_len - len(vec))
        else:
            vec = vec[:expected_len]

        probs = self.classifier.predict_proba([vec])[0]
        final_prob = float(probs[1])

        # Feature explanation based on coefficients
        feature_names = [
            "nlp_scam_probability",
            "url_risk_probability",
            "identity_inconsistency",  # Displaying as inconsistency since higher values indicate safety in consistency
            "semantic_similarity",
            "payment_probability",
            "social_engineering_probability",
            "opportunity_risk",
            "company_verification_signal"
        ]

        coefs = self.classifier.coef_[0]
        contributions = {}
        
        for i, (name, val) in enumerate(zip(feature_names, vec)):
            if i < len(coefs):
                coef = coefs[i]
                # For identity consistency and company verification signal, higher value is safer, 
                # so negative coefficients represent safety. We show positive risk impact by inverting/adjusting.
                if name in ("identity_inconsistency", "company_verification_signal"):
                    val_adjusted = 1.0 - val
                else:
                    val_adjusted = val
                
                contrib = val_adjusted * abs(coef)
                if abs(contrib) > 0.01:
                    contributions[name] = round(float(contrib), 4)

        # Normalize contributions to sum to final_prob roughly for display
        total_contrib = sum(contributions.values()) or 1.0
        normalized_contributions = {k: round((v / total_contrib) * final_prob, 4) for k, v in contributions.items()}

        return FusionResult(
            final_scam_probability=round(final_prob, 4),
            feature_contributions=normalized_contributions,
            model_name=self.model_name,
            model_version=self.model_version,
            is_demo_prediction=False
        )
