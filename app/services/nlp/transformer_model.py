import os
import torch
import numpy as np
from app.services.nlp.interface import NLPModel, NLPPrediction

class TransformerNLPModel(NLPModel):
    def __init__(self, model_path=None):
        self.model_path = model_path or "app/resources/transformer_model"
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "TransformerNLP-SequenceClassifier"
        self.model_version = "1.0.0"
        self.loaded_successfully = False
        self._load_model()

    def is_fine_tuned(self) -> bool:
        return self.loaded_successfully

    def _load_model(self):
        # Only attempt to load if the model directory exists
        if self.model_path and os.path.exists(self.model_path):
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
                self.model.to(self.device)
                self.model.eval()
                self.loaded_successfully = True
                print(f"Loaded Transformer NLP Model successfully from {self.model_path}")
            except Exception as e:
                print(f"Error loading Transformer NLP Model: {e}")
                self.loaded_successfully = False

    def predict(self, text: str) -> NLPPrediction:
        # If no checkpoint exists, fall back to the demo keyword model with is_demo_prediction = True
        if not self.loaded_successfully:
            from app.services.nlp.demo import DemoNLPModel
            demo = DemoNLPModel()
            pred = demo.predict(text)
            # Enforce that fallback predictions are marked as demo
            pred.is_demo_prediction = True
            return pred

        text = text or ""

        try:
            # Tokenize without truncation to chunk long texts safely
            inputs = self.tokenizer(text, truncation=False, return_tensors="pt")
            input_ids = inputs["input_ids"][0]
            
            # Split into chunks of 512 tokens maximum
            max_len = 512
            chunks = [input_ids[i:i + max_len] for i in range(0, len(input_ids), max_len)]
            
            all_probs = []
            for chunk in chunks:
                chunk_tensor = chunk.unsqueeze(0).to(self.device)
                attention_mask = torch.ones_like(chunk_tensor).to(self.device)
                with torch.no_grad():
                    outputs = self.model(chunk_tensor, attention_mask=attention_mask)
                    logits = outputs.logits[0].softmax(dim=-1).cpu().numpy()
                    all_probs.append(logits)
            
            # Average probabilities across chunks
            avg_probs = np.mean(all_probs, axis=0)
            
            # Map average probabilities
            # Assuming standard binary classification: index 1 is scam, index 0 is safe
            scam_prob = float(avg_probs[1]) if len(avg_probs) > 1 else float(avg_probs[0])
            
            # Zero-shot like category distributions based on scam probability
            cat_probs = {
                "payment_scam": scam_prob * 0.4,
                "company_impersonation": scam_prob * 0.2,
                "phishing": scam_prob * 0.2,
                "unrealistic_compensation": scam_prob * 0.2,
                "legitimate": 1.0 - scam_prob
            }

            # Saliency token attribution using occlusion
            words = text.split()
            token_attributions = []
            
            # Calculate word occlusion for up to 10 words to preserve speed
            for word in words[:10]:
                masked_text = " ".join([w for w in words if w != word])
                inputs_m = self.tokenizer(masked_text, truncation=True, max_length=512, return_tensors="pt").to(self.device)
                with torch.no_grad():
                    out_m = self.model(**inputs_m)
                    probs_m = out_m.logits[0].softmax(dim=-1).cpu().numpy()
                    m_scam = float(probs_m[1]) if len(probs_m) > 1 else float(probs_m[0])
                    diff = scam_prob - m_scam
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
            
        except Exception as e:
            # Fall back to demo keyword model on inference failure
            from app.services.nlp.demo import DemoNLPModel
            demo = DemoNLPModel()
            pred = demo.predict(text)
            pred.is_demo_prediction = True
            return pred
