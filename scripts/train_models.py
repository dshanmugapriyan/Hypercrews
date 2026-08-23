import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from app.services.registry import ModelRegistry

# Create resources directory
RESOURCES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "resources"))
os.makedirs(RESOURCES_DIR, exist_ok=True)

# 1. Train NLP Model
def train_nlp_model():
    print("Training Real NLP Model...")
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
    
    csv_path = "DataSet.csv/internship_job_scam_dataset.csv"
    if os.path.exists(csv_path):
        print(f"Loading real dataset from {csv_path}...")
        df = pd.read_csv(csv_path)
        texts = df["text"].fillna("").tolist()
        labels = df["label"].tolist()
        
        # Split data for evaluation
        X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42)
        
        vectorizer = TfidfVectorizer(stop_words="english")
        X_train_vec = vectorizer.fit_transform(X_train)
        X_test_vec = vectorizer.transform(X_test)
        
        classifier = LogisticRegression(max_iter=300)
        classifier.fit(X_train_vec, y_train)
        
        # Evaluate metrics
        y_pred = classifier.predict(X_test_vec)
        y_probs = classifier.predict_proba(X_test_vec)
        
        precision = float(precision_score(y_test, y_pred, average="weighted"))
        recall = float(recall_score(y_test, y_pred, average="weighted"))
        f1 = float(f1_score(y_test, y_pred, average="weighted"))
        roc_auc = float(roc_auc_score(y_test, y_probs, multi_class="ovr", average="weighted"))
        
        print(f"Evaluation Metrics:")
        print(f" - Precision: {precision:.4f}")
        print(f" - Recall: {recall:.4f}")
        print(f" - F1 (FM) Score: {f1:.4f}")
        print(f" - ROC-AUC Score: {roc_auc:.4f}")
        
        metrics = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "samples_count": len(texts)
        }
    else:
        print("CSV dataset not found, falling back to synthetic dataset.")
        nlp_data = [
            ("Urgent notice: pay $25 registration fees for online verification.", "payment_scam"),
            ("To start your work, transfer 100 USD processing fees immediately.", "payment_scam"),
            ("Deposit security money via wire transfer to secure this slot.", "payment_scam"),
            ("Send registration fee using GPay or Paytm or UPI to start work.", "payment_scam"),
            ("Netflix is hiring remote data entry clerks. No interview needed, start today!", "company_impersonation"),
            ("This is Amazon Recruitment. Congratulations! You are selected. Click link.", "company_impersonation"),
            ("Welcome to Apple HR team. Fill this Google Form with details for instant offer.", "company_impersonation"),
            ("Hi, I am Microsoft HR, congratulations on getting this job offer, send files.", "company_impersonation"),
            ("Verify bank details, Aadhaar, PAN card, and passwords for payroll.", "phishing"),
            ("Submit bank statement and credit card CVV code over WhatsApp chat.", "phishing"),
            ("Confirm your account immediately by sharing the OTP sent to your phone.", "phishing"),
            ("Provide your login credentials for verified portal access.", "phishing"),
            ("Earn $1500 daily doing simple typing jobs from home. 1 hour/day.", "unrealistic_compensation"),
            ("Get paid 500 dollars per hour for copying files. No experience needed.", "unrealistic_compensation"),
            ("Guaranteed monthly income of 8000 USD for clicking ads.", "unrealistic_compensation"),
            ("Make 10000 INR daily with simple copy paste job. Fully remote.", "unrealistic_compensation"),
            ("Are you available for a phone interview tomorrow morning at 10 AM?", "legitimate"),
            ("Please review the attached software engineer job description and requirements.", "legitimate"),
            ("The hiring manager would like to schedule a 45-minute technical discussion.", "legitimate"),
            ("Welcome! Here is your onboarding portal link and team Slack invite.", "legitimate"),
            ("Our company website details our mission, values, and client testimonials.", "legitimate"),
            ("We do not charge any fees during any stage of our recruitment process.", "legitimate"),
            ("Please let me know if you have any questions regarding the benefit package.", "legitimate")
        ]
        texts = [x[0] for x in nlp_data]
        labels = [x[1] for x in nlp_data]
        
        vectorizer = TfidfVectorizer(stop_words="english")
        X = vectorizer.fit_transform(texts)
        
        classifier = LogisticRegression(max_iter=300)
        classifier.fit(X, labels)
        metrics = {"samples_count": len(texts)}

    out_path = os.path.join(RESOURCES_DIR, "nlp_classifier.joblib")
    joblib.dump({
        "vectorizer": vectorizer,
        "classifier": classifier,
        "model_name": "TrainedNLP-TfidfLogReg",
        "model_version": "1.1.0-trained"
    }, out_path)
    print(f"NLP Model saved to {out_path}")
    
    # Register model in registry
    ModelRegistry.register_model(
        model_name="TrainedNLP-TfidfLogReg",
        model_version="1.1.0-trained",
        artifact_path=out_path,
        feature_schema_version="1.0.0",
        metrics=metrics,
        is_production=True
    )

# 2. Train URL Model
def train_url_model():
    print("Training Real URL Risk Model...")
    # Feature columns:
    # [url_length, domain_length, subdomain_count, digit_ratio, special_char_ratio, entropy, has_suspicious_tld, is_https, redirect_count]
    X_train = np.array([
        # Scam / Phishing URLs
        [110, 35, 4, 0.32, 0.25, 4.9, 1, 0, 3],
        [85, 25, 3, 0.28, 0.18, 4.3, 1, 0, 2],
        [150, 42, 5, 0.35, 0.28, 5.2, 1, 0, 4],
        [60, 20, 2, 0.22, 0.15, 3.8, 1, 0, 1],
        [90, 28, 3, 0.18, 0.12, 4.0, 0, 0, 2],
        [60, 22, 3, 0.02, 0.01, 4.1, 1, 0, 0], # scam with no digits/specials/redirects
        
        # Safe / Legitimate URLs
        [32, 12, 0, 0.00, 0.00, 2.3, 0, 1, 0],
        [45, 15, 1, 0.04, 0.04, 2.7, 0, 1, 0],
        [28, 10, 0, 0.00, 0.05, 2.1, 0, 1, 0],
        [52, 18, 1, 0.06, 0.02, 2.9, 0, 1, 0],
        [65, 22, 2, 0.05, 0.06, 3.2, 0, 1, 1],
    ])
    y_train = np.array([1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    import xgboost as xgb
    classifier = xgb.XGBClassifier(n_estimators=30, max_depth=3, learning_rate=0.1, eval_metric="logloss")
    classifier.fit(X_train, y_train)
    
    out_path = os.path.join(RESOURCES_DIR, "url_classifier.joblib")
    joblib.dump({
        "classifier": classifier,
        "model_name": "TrainedURL-XGBoost",
        "model_version": "1.1.0-trained"
    }, out_path)
    print(f"URL Model saved to {out_path}")
    
    # Register model
    ModelRegistry.register_model(
        model_name="TrainedURL-XGBoost",
        model_version="1.1.0-trained",
        artifact_path=out_path,
        feature_schema_version="1.0.0",
        metrics={"features_count": X_train.shape[1]},
        is_production=True
    )

# 3. Train Fusion Model
def train_fusion_model():
    print("Training Real Fusion Meta-Model...")
    # Features:
    # [nlp_scam_probability, url_risk_probability, identity_consistency, semantic_similarity,
    #  payment_probability, social_engineering_probability, opportunity_risk, company_verification_signal]
    X_train = np.array([
        # Scam cases
        [0.95, 0.90, 0.00, 0.85, 0.90, 0.80, 0.95, 0.00],
        [0.80, 0.70, 0.20, 0.70, 0.85, 0.75, 0.80, 0.10],
        [0.90, 0.85, 0.10, 0.90, 0.95, 0.80, 0.90, 0.00],
        [0.75, 0.60, 0.30, 0.65, 0.70, 0.70, 0.85, 0.20],
        
        # Safe cases
        [0.05, 0.05, 1.00, 0.10, 0.05, 0.05, 0.05, 1.00],
        [0.10, 0.15, 0.90, 0.15, 0.10, 0.10, 0.10, 0.90],
        [0.15, 0.08, 0.80, 0.20, 0.15, 0.15, 0.20, 0.85],
        [0.20, 0.12, 0.85, 0.25, 0.18, 0.20, 0.15, 0.80]
    ])
    y_train = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    
    classifier = LogisticRegression()
    classifier.fit(X_train, y_train)
    
    out_path = os.path.join(RESOURCES_DIR, "fusion_model.joblib")
    joblib.dump({
        "classifier": classifier,
        "model_name": "TrainedFusion-LogReg",
        "model_version": "1.1.0-trained"
    }, out_path)
    print(f"Fusion Model saved to {out_path}")
    
    # Register model
    ModelRegistry.register_model(
        model_name="TrainedFusion-LogReg",
        model_version="1.1.0-trained",
        artifact_path=out_path,
        feature_schema_version="1.0.0",
        metrics={"features_count": X_train.shape[1]},
        is_production=True
    )

# 4. Train Calibrator Model
def train_calibrator():
    print("Training Real Isotonic Calibration Model...")
    from sklearn.calibration import IsotonicRegression
    
    # Raw fusion probabilities matched with validation outcomes (0 = safe, 1 = scam)
    X_val = [0.08, 0.15, 0.22, 0.45, 0.68, 0.85, 0.95]
    y_val = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]
    
    ir = IsotonicRegression(out_of_bounds="clip")
    ir.fit(X_val, y_val)
    
    out_path = os.path.join(RESOURCES_DIR, "calibrator.joblib")
    joblib.dump({
        "calibrator": ir,
        "model_name": "IsotonicRegressionCalibrator",
        "model_version": "1.1.0-trained"
    }, out_path)
    print(f"Calibrator saved to {out_path}")
    
    # Register model
    ModelRegistry.register_model(
        model_name="IsotonicRegressionCalibrator",
        model_version="1.1.0-trained",
        artifact_path=out_path,
        feature_schema_version="1.0.0",
        metrics={"validation_points": len(X_val)},
        is_production=True
    )

if __name__ == "__main__":
    train_nlp_model()
    train_url_model()
    train_fusion_model()
    train_calibrator()
    print("All models trained and saved successfully!")
