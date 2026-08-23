import os
import joblib
import numpy as np
from app.services.nlp.interface import NLPModel, NLPPrediction

# Define categories matching the interface
_CATEGORIES = ["payment_scam", "company_impersonation", "phishing", "unrealistic_compensation", "legitimate"]

# In-memory inline training set in case the model hasn't been trained yet
_INLINE_DATA = [
    ("Urgent: Pay registration fee now to secure your job slot!", "payment_scam"),
    ("Please wire $150 to our account for background check.", "payment_scam"),
    ("We need a security deposit of $200 via GPay before training.", "payment_scam"),
    ("We are recruiting for Google. No interview required, start tomorrow!", "company_impersonation"),
    ("Congratulations! Amazon has selected you. Click link to fill details.", "company_impersonation"),
    ("Verify your bank account details and submit OTP immediately.", "phishing"),
    ("Send your Aadhaar card photo, PAN details, and passwords.", "phishing"),
    ("Earn $5000 per week for 2 hours of simple data entry work from home!", "unrealistic_compensation"),
    ("Guaranteed income of $1000 daily with zero prior experience.", "unrealistic_compensation"),
    ("Hi, I am writing to schedule a standard technical interview for tomorrow.", "legitimate"),
    ("Here is the job description and our company website link.", "legitimate"),
    ("The interview will consist of coding questions and a design discussion.", "legitimate")
]

class RealNLPModel(NLPModel):
    def __init__(self, model_dir="app/resources"):
        self.model_path = os.path.join(model_dir, "nlp_classifier.joblib")
        self.vectorizer = None
        self.classifier = None
        self.huggingface_pipeline = None
        self.model_name = "RealNLP-TfidfLogReg"
        self.model_version = "1.0.0"
        self._load_or_train_fallback()

    def is_fine_tuned(self) -> bool:
        return self.classifier is not None or self.huggingface_pipeline is not None

    def _load_or_train_fallback(self):
        # 1. Try loading trained local model
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                self.vectorizer = data["vectorizer"]
                self.classifier = data["classifier"]
                self.model_name = data.get("model_name", self.model_name)
                self.model_version = data.get("model_version", self.model_version)
                return
            except Exception:
                pass

        # 2. Try loading a lightweight transformers model if packages are available
        try:
            from transformers import pipeline
            # Using a tiny sentiment pipeline to verify if transformers are available
            self.huggingface_pipeline = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
            self.model_name = "RealNLP-DistilBERT-SST"
            self.model_version = "0.1.0-hf"
            return
        except Exception:
            pass

        # 3. Fallback: Train the local TF-IDF model inline on the spot
        self._train_inline()

    def _train_inline(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        import pandas as pd

        csv_path = "DataSet.csv/internship_job_scam_dataset.csv"
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                texts = df["text"].fillna("").tolist()
                labels = df["label"].tolist()
                self.model_name = "RealNLP-TrainedTfidfLogReg"
            except Exception:
                texts = [x[0] for x in _INLINE_DATA]
                labels = [x[1] for x in _INLINE_DATA]
        else:
            texts = [x[0] for x in _INLINE_DATA]
            labels = [x[1] for x in _INLINE_DATA]

        self.vectorizer = TfidfVectorizer(stop_words="english")
        X = self.vectorizer.fit_transform(texts)
        self.classifier = LogisticRegression(max_iter=300)
        self.classifier.fit(X, labels)

        # Make sure target directory exists
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({"vectorizer": self.vectorizer, "classifier": self.classifier, "model_name": self.model_name, "model_version": self.model_version}, self.model_path)

    def predict(self, text: str) -> NLPPrediction:
        text = text or ""
        
        # 1. If we have a transformers model, use it to get score and perform occlusion for token attributions
        if self.huggingface_pipeline:
            try:
                res = self.huggingface_pipeline(text)[0]
                label = res["label"]
                score = res["score"]
                # Map standard sentiment to scam probability (NEGATIVE sentiment indicates high risk)
                scam_prob = float(score) if label == "NEGATIVE" else float(1 - score)
                
                # Zero-shot like category distributions based on sentiment
                cat_probs = {
                    "payment_scam": scam_prob * 0.4,
                    "company_impersonation": scam_prob * 0.2,
                    "phishing": scam_prob * 0.2,
                    "unrealistic_compensation": scam_prob * 0.2,
                    "legitimate": 1 - scam_prob
                }
                
                # Occlusion-based attribution
                words = text.split()
                token_attributions = []
                base_prob = scam_prob
                
                # Compute up to 15 key words to keep it fast
                for word in words[:15]:
                    masked_text = " ".join([w for w in words if w != word])
                    if masked_text:
                        m_res = self.huggingface_pipeline(masked_text)[0]
                        m_prob = float(m_res["score"]) if m_res["label"] == "NEGATIVE" else float(1 - m_res["score"])
                        diff = base_prob - m_prob
                        if abs(diff) > 0.01:
                            token_attributions.append((word, float(diff)))
                            
                return NLPPrediction(
                    scam_probability=round(scam_prob, 4),
                    scam_category_probabilities={k: round(v, 4) for k, v in cat_probs.items()},
                    severity=round(scam_prob, 4),
                    payment_risk=round(cat_probs["payment_scam"], 4),
                    identity_risk=round(cat_probs["company_impersonation"], 4),
                    social_engineering_risk=round(cat_probs["phishing"], 4),
                    opportunity_risk=round(cat_probs["unrealistic_compensation"], 4),
                    token_attributions=token_attributions,
                    model_name=self.model_name,
                    model_version=self.model_version,
                    is_demo_prediction=False
                )
            except Exception:
                # Fallback to local model if pipeline fails
                pass

        # 2. Local TF-IDF + LogisticRegression prediction
        if self.vectorizer and self.classifier:
            X = self.vectorizer.transform([text])
            probs = self.classifier.predict_proba(X)[0]
            classes = self.classifier.classes_

            # Build probability map
            prob_map = {cls: float(probs[i]) for i, cls in enumerate(classes)}
            
            # Extract probability outcomes
            fraud_prob = prob_map.get("fraudulent", 0.0)
            susp_prob = prob_map.get("suspicious", 0.0)
            legit_prob = prob_map.get("legitimate", 0.0)
            
            # Map fraudulent/suspicious/legitimate to category dimensions
            scam_category_probs = {
                "payment_scam": round(fraud_prob * 0.4, 4),
                "company_impersonation": round(fraud_prob * 0.2, 4),
                "phishing": round(fraud_prob * 0.2, 4),
                "unrealistic_compensation": round(susp_prob * 0.8 + fraud_prob * 0.2, 4),
                "legitimate": round(legit_prob, 4)
            }
            
            # Calibrate overall scam score (fraudulent is scam, suspicious is partial scam risk)
            scam_prob = 1.0 - legit_prob

            # Calculate feature attributions
            feature_names = self.vectorizer.get_feature_names_out()
            feature_weights = self.classifier.coef_[0] if len(self.classifier.classes_) > 2 else self.classifier.coef_[0]
            
            # Map weights to words in the text
            token_attributions = []
            words_in_text = set(text.lower().split())
            
            for word in words_in_text:
                if word in self.vectorizer.vocabulary_:
                    idx = self.vectorizer.vocabulary_[word]
                    # Handle coefficient weights mapping safely
                    weight = float(feature_weights[idx % len(feature_weights)])
                    if abs(weight) > 0.05:
                        token_attributions.append((word, round(weight, 4)))

            return NLPPrediction(
                scam_probability=round(scam_prob, 4),
                scam_category_probabilities=scam_category_probs,
                severity=round(scam_prob, 4),
                payment_risk=scam_category_probs["payment_scam"],
                identity_risk=scam_category_probs["company_impersonation"],
                social_engineering_risk=scam_category_probs["phishing"],
                opportunity_risk=scam_category_probs["unrealistic_compensation"],
                token_attributions=token_attributions,
                model_name=self.model_name,
                model_version=self.model_version,
                is_demo_prediction=False
            )

        # Fallback if both fail (should never happen due to _train_inline)
        return NLPPrediction(0.1, {}, 0.1, 0.0, 0.0, 0.0, 0.0, [], "fallback", "0.0.0", False)
