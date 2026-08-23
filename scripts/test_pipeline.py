import os
import sys
import uuid
import json

# Add current workspace to path
sys.path.append(".")

# Enforce SQLite testing DB
os.environ["DATABASE_URL"] = "sqlite:///./test_scamcheck.db"

from app.core.database import Base, engine, SessionLocal
from app.models import Scan, ModelPrediction, Opportunity, Report
from app.models.base import ScanStatus
from app.services.nlp import get_nlp_model
from app.services.url import get_url_model
from app.services.url.features import extract_url_features
from app.services.embeddings import get_scam_pattern_retriever
from app.services.fusion import get_fusion_model
from app.services.calibration import get_calibrator
from app.services.identity import get_identity_checker
from app.services.entities import get_entity_extractor

def run_tests():
    print("==================================================")
    # 1. Database schema generation
    print("Testing Database Schema Generation...")
    Base.metadata.drop_all(bind=engine) # clean slate
    Base.metadata.create_all(bind=engine)
    print("[OK] Schema initialized successfully.")
    
    # 2. Model Loading Tests
    print("\nTesting Model Loading & Registry Check...")
    nlp = get_nlp_model(is_demo=False)
    url = get_url_model(is_demo=False)
    fuse = get_fusion_model(is_demo=False)
    cal = get_calibrator(is_demo=False)
    
    print(f"NLP Model Name: {nlp.model_name} (Fine-tuned: {nlp.is_fine_tuned()})")
    print(f"URL Model Name: {url.model_name} (Trained: {url.is_trained()})")
    print(f"Fusion Model Name: {fuse.model_name} (Trained: {fuse.is_trained()})")
    
    assert nlp.model_name is not None
    assert url.model_name is not None
    assert fuse.model_name is not None
    print("[OK] Models resolved and loaded successfully.")

    # 3. NLP Inference & Long-Text safe chunking
    print("\nTesting NLP Inference & Long-Text safe chunking...")
    # Standard text
    pred_standard = nlp.predict("Urgent! Wire registration fee of 200 dollars immediately for your security deposit.")
    print(f"Standard Text scam probability: {pred_standard.scam_probability}")
    assert pred_standard.scam_probability > 0.4
    
    # Long text exceeding 512 tokens (safe chunking test)
    long_text = "This is a standard recruiting message. " * 300
    pred_long = nlp.predict(long_text)
    print(f"Long Text (Safe chunking) scam probability: {pred_long.scam_probability}")
    assert pred_long.scam_probability is not None
    print("[OK] NLP Inference and safe chunking passed.")

    # 4. URL Feature & Risk Tests
    print("\nTesting URL Feature extraction & XGBoost inference...")
    features = extract_url_features("http://stripe.verification.portal.pay.now.xyz/redirect-verify/checkout/3920")
    print(f"TLD check: {features.has_suspicious_tld}, Entropy: {features.entropy}")
    assert features.has_suspicious_tld is True
    
    url_pred = url.predict(features)
    print(f"XGBoost URL risk: {url_pred.url_risk_probability}")
    print(f"Feature contributions: {url_pred.feature_importance}")
    assert url_pred.url_risk_probability > 0.5
    print("[OK] URL features and XGBoost inference passed.")

    # 5. Embedding Retrieval & Fallback Check
    print("\nTesting Embedding Retrieval and Empty DB fallbacks...")
    retriever = get_scam_pattern_retriever(is_demo=False)
    
    # Manually empty the database to test the empty db behavior
    db_clean = SessionLocal()
    from sqlalchemy import text
    db_clean.execute(text("DELETE FROM scam_patterns"))
    db_clean.commit()
    db_clean.close()
    
    res = retriever.find_similar("Standard text query")
    print(f"Historical similar patterns found on empty DB: {len(res.similar_patterns)}")
    assert len(res.similar_patterns) == 0
    
    # Re-seed the patterns for subsequent end-to-end tests
    retriever._seed_default_patterns()
    print("[OK] Embeddings empty-database inconclusive response test passed.")

    # 6. Identity Checks
    print("\nTesting deterministic and probabilistic Identity Checks...")
    checker = get_identity_checker()
    from app.services.identity.interface import IdentityClaim
    claim = IdentityClaim(
        claimed_company="Stripe",
        sender_email="recruitment@gmail.com",
        email_domain="gmail.com",
        website_domain="stripe-verify.xyz",
        official_company_domain="stripe.com"
    )
    id_res = checker.evaluate(claim)
    print(f"Identity consistency score: {id_res.identity_consistency_score}")
    print(f"Mismatches detected: {id_res.mismatches}")
    assert id_res.identity_consistency_score < 0.5
    assert len(id_res.mismatches) > 0
    print("[OK] Identity evaluation checks passed.")

    # 7. Model Fusion & Calibration
    print("\nTesting Model Fusion and Calibrated scaling...")
    from app.services.fusion.interface import FusionFeatureVector
    vector = FusionFeatureVector(
        nlp_scam_probability=pred_standard.scam_probability,
        url_risk_probability=url_pred.url_risk_probability,
        identity_consistency=id_res.identity_consistency_score,
        semantic_similarity=0.0, # empty db
        payment_probability=pred_standard.payment_risk,
        social_engineering_probability=pred_standard.social_engineering_risk,
        opportunity_risk=pred_standard.opportunity_risk,
        company_verification_signal=0.0,
        metadata_features={}
    )
    
    fuse_res = fuse.fuse(vector)
    print(f"Fusion meta score: {fuse_res.final_scam_probability}")
    
    cal_res = cal.calibrate(fuse_res.final_scam_probability, 3) # 3 evidence items
    print(f"Calibrated probability: {cal_res.calibrated_probability}, Confidence: {cal_res.confidence_score}")
    assert cal_res.calibrated_probability is not None
    assert cal_res.confidence_score > 0.4
    print("[OK] Fusion and calibration pipeline passed.")

    # 8. End-to-End Scan & Database Persistence Tests
    print("\nTesting End-to-End Scan & Database Persistence...")
    db = SessionLocal()
    
    # Create opportunity
    opp = Opportunity(title="Test Job", source="email", raw_content="Urgent Stripe Job! Pay $150 registration fee now. Details at http://stripe-verify.xyz/login. Contact recruiter@gmail.com.")
    db.add(opp)
    db.commit()
    
    # Create Scan
    scan = Scan(opportunity_id=opp.id, status=ScanStatus.PENDING)
    db.add(scan)
    db.commit()
    scan_id = scan.id
    db.close() # close session to clear identity cache
    
    # Run the pipeline function in main.py
    from app.main import run_analysis_pipeline
    run_analysis_pipeline(scan_id, SessionLocal, is_demo=False)
    
    # Load completed scan and check database entries using a fresh session
    db = SessionLocal()
    scan_updated = db.query(Scan).filter(Scan.id == scan.id).first()
    print(f"Final scan status: {scan_updated.status}")
    print(f"Calibrated score: {scan_updated.risk_score}%, verdict: {scan_updated.verdict}")
    assert scan_updated.status == ScanStatus.COMPLETE
    
    # Check predictions storage
    preds = db.query(ModelPrediction).filter(ModelPrediction.scan_id == scan.id).all()
    print(f"Total model predictions persisted in DB: {len(preds)}")
    for p in preds:
        print(f" - Key: {p.output_key}, Value: {p.output_value}")
    
    assert len(preds) == 6 # All 6 predictions must be persisted: nlp, url, id, ret, fuse, cal
    
    # Check report
    report = db.query(Report).filter(Report.scan_id == scan.id).first()
    print(f"Report Summary: {report.narrative_summary}")
    print(f"Recommended actions: {report.recommended_actions}")
    assert report is not None
    assert len(report.recommended_actions) > 0
    
    db.close()
    print("[OK] End-to-End scan and database persistence passed successfully!")
    print("==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! 100% CORRECT PIPELINE INTEGRATION.")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
