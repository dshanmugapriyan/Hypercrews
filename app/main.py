import os
import uuid
import datetime
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, desc

from app.core.config import settings
from app.core.database import Base, engine, get_db, SessionLocal
from app.models import (
    Scan, Opportunity, Company, Domain, Entity, Evidence,
    ModelPrediction, RiskSignal, ScamFingerprint, VerificationCheck,
    Report, CommunityReport, User, ScamPattern
)
from app.models.base import ScanStatus, RiskLevel, VerificationCheckStatus
from app.schemas.scan import ScanCreateRequest, ScanAnalyzeResponse, ScanStatusResponse, RiskBreakdown, EvidenceItem, ScamFingerprintItem, VerificationStep
from app.schemas.report import TrustReportResponse, TrustReportHeader, TrustReportHero, OpportunityPassport
from app.schemas.copilot import CopilotChatRequest, CopilotChatResponse, CommunityReportRequest, CommunityReportResponse
from app.schemas.common import Verdict, InputType
from app.schemas.auth import LoginRequest, TokenResponse, GoogleLoginRequest
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

GOOGLE_CLIENT_ID = "84060840192-6mrkiancb1ngboqpssj07ke0b55emktm.apps.googleusercontent.com"
# Create database tables at startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pipeline Factories
from app.services.nlp import get_nlp_model
from app.services.url import get_url_model
from app.services.embeddings import get_scam_pattern_retriever
from app.services.fusion import get_fusion_model
from app.services.calibration import get_calibrator
from app.services.identity import get_identity_checker
from app.services.entities import get_entity_extractor
from app.services.url.features import extract_url_features
from app.services.identity.interface import IdentityClaim
from app.services.fusion.interface import FusionFeatureVector
from app.services.risk_scoring import assemble_risk_trust_output

# End-to-end Analysis Pipeline Worker
def run_analysis_pipeline(scan_id: uuid.UUID, db_session_maker, is_demo: bool):
    db = db_session_maker()
    try:
        # Load Scan
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return
        
        opportunity = db.query(Opportunity).filter(Opportunity.id == scan.opportunity_id).first()
        if not opportunity:
            scan.status = ScanStatus.FAILED
            scan.failure_reason = "Opportunity record missing"
            db.commit()
            return

        text_content = opportunity.raw_content or ""
        
        # 1. Parsing Input
        scan.status = ScanStatus.EXTRACTING
        db.commit()
        
        v_parse = VerificationCheck(
            scan_id=scan.id, step_name="Input parsed", step_order=1,
            status=VerificationCheckStatus.PASSED, detail="Successfully loaded input data."
        )
        db.add(v_parse)
        db.commit()

        # Handle file mock text extraction
        if opportunity.source in ("screenshot", "pdf") and not text_content:
            # Fake OCR / PDF Text Parsing fallback for demo files
            text_content = "URGENT OPPORTUNITY: Stripe HR is hiring a remote data entry clerk. Pay is $85/hr. Pay registration fee of $150 at stripe-jobs-portal.xyz/pay to start. Wire transfer, UPI or GPay accepted. Send bank credentials and OTP immediately to secure the slot."
            opportunity.raw_content = text_content
            db.commit()

        # 2. Entity Extraction
        extractor = get_entity_extractor()
        ext_res = extractor.extract(text_content)
        
        for ent in ext_res.entities:
            db_ent = Entity(
                opportunity_id=opportunity.id,
                entity_type=ent.entity_type,
                value=ent.value,
                confidence=ent.confidence,
                extraction_source=ent.source
            )
            db.add(db_ent)
        db.commit()

        # Check if claimed company found
        claimed_company_name = ext_res.first_value("claimed_company")
        company_id = None
        if claimed_company_name:
            # Check or create Company record
            comp = db.query(Company).filter(Company.name.ilike(claimed_company_name)).first()
            if not comp:
                comp = Company(
                    name=claimed_company_name,
                    domain=ext_res.first_value("website_domain") or ext_res.first_value("email_domain"),
                    is_verified=claimed_company_name.lower() in ("stripe", "google", "amazon", "microsoft", "netflix"),
                    trust_score=85.0 if claimed_company_name.lower() in ("stripe", "google", "amazon", "microsoft", "netflix") else 35.0,
                    description=f"Automated intelligence profile for {claimed_company_name}."
                )
                db.add(comp)
                db.commit()
            
            opportunity.company_id = comp.id
            company_id = comp.id
            db.commit()
            
            v_comp = VerificationCheck(
                scan_id=scan.id, step_name="Company identified", step_order=2,
                status=VerificationCheckStatus.PASSED if comp.is_verified else VerificationCheckStatus.WARNING,
                detail=f"Identified claimed company: {comp.name} (Verified: {comp.is_verified})."
            )
        else:
            v_comp = VerificationCheck(
                scan_id=scan.id, step_name="Company identified", step_order=2,
                status=VerificationCheckStatus.FAILED,
                detail="Could not find any clear company claiming this opportunity."
            )
        db.add(v_comp)
        db.commit()

        # 3. Domain Analysis & URL Risk Model
        scan.status = ScanStatus.ANALYZING
        db.commit()

        website_domain = ext_res.first_value("website_domain")
        email_domain = ext_res.first_value("email_domain")
        
        url_pred_score = 0.0
        url_features_obj = None
        url_importance = {}
        
        # Analyze website or email domain
        target_domain = website_domain or email_domain
        if target_domain:
            # Check domain records
            dom_rec = db.query(Domain).filter(Domain.domain_name == target_domain).first()
            if not dom_rec:
                is_official = False
                if claimed_company_name:
                    is_official = target_domain.endswith(f"{claimed_company_name.lower()}.com")
                
                dom_rec = Domain(
                    company_id=company_id if company_id else uuid.UUID(int=0), # mock/temp link
                    domain_name=target_domain,
                    is_official=is_official,
                    domain_age_days=15 if is_official else 1250,
                    registrar="GoDaddy Inc." if is_official else "SuspiciousRegistrar LLC",
                    risk_score=95.0 if not is_official and claimed_company_name else 10.0
                )
                if company_id:
                    dom_rec.company_id = company_id
                db.add(dom_rec)
                db.commit()

            # Predict URL Risk
            url_features_obj = extract_url_features(target_domain)
            url_model = get_url_model(is_demo)
            url_pred = url_model.predict(url_features_obj)
            url_pred_score = url_pred.url_risk_probability
            url_importance = url_pred.feature_importance

            db_model_url = ModelPrediction(
                scan_id=scan.id, model_name=url_pred.model_name,
                model_version=url_pred.model_version, output_key="url_xgboost",
                output_value=url_pred_score, is_demo_prediction=is_demo
            )
            db.add(db_model_url)
            db.commit()

            v_domain = VerificationCheck(
                scan_id=scan.id, step_name="Domain checked", step_order=3,
                status=VerificationCheckStatus.PASSED if url_pred_score < 0.3 else VerificationCheckStatus.FAILED,
                detail=f"Analyzed domain: {target_domain}. Risk probability: {round(url_pred_score*100, 1)}%."
            )
        else:
            v_domain = VerificationCheck(
                scan_id=scan.id, step_name="Domain checked", step_order=3,
                status=VerificationCheckStatus.WARNING, detail="No domain names found in opportunity for URL risk analysis."
            )
        db.add(v_domain)
        db.commit()

        # 4. Identity Consistency
        claim = IdentityClaim(
            claimed_company=claimed_company_name,
            sender_name=ext_res.first_value("recruiter_name"),
            sender_email=ext_res.first_value("email"),
            email_domain=email_domain,
            website_domain=website_domain,
            official_company_domain=f"{claimed_company_name.lower()}.com" if claimed_company_name else None
        )
        
        checker = get_identity_checker()
        identity_res = checker.evaluate(claim)
        
        v_identity = VerificationCheck(
            scan_id=scan.id, step_name="Identity compared", step_order=4,
            status=VerificationCheckStatus.PASSED if identity_res.identity_consistency_score >= 0.75 else VerificationCheckStatus.FAILED,
            detail=f"Identity matches: {round(identity_res.identity_consistency_score*100, 1)}%. Mismatches found: {len(identity_res.mismatches)}."
        )
        db.add(v_identity)
        db.commit()

        db_model_id = ModelPrediction(
            scan_id=scan.id, model_name="IdentityConsistencyModel",
            model_version="1.0.0", output_key="identity_consistency",
            output_value=identity_res.identity_consistency_score, is_demo_prediction=is_demo
        )
        db.add(db_model_id)
        db.commit()

        # 5. NLP Model Analysis
        nlp_model = get_nlp_model(is_demo)
        nlp_pred = nlp_model.predict(text_content)
        
        db_model_nlp = ModelPrediction(
            scan_id=scan.id, model_name=nlp_pred.model_name,
            model_version=nlp_pred.model_version, output_key="nlp_transformer",
            output_value=nlp_pred.scam_probability, is_demo_prediction=is_demo
        )
        db.add(db_model_nlp)
        db.commit()

        v_opp = VerificationCheck(
            scan_id=scan.id, step_name="Opportunity verification attempted", step_order=5,
            status=VerificationCheckStatus.PASSED if nlp_pred.scam_probability < 0.3 else VerificationCheckStatus.FAILED,
            detail=f"Processed text through classifier. Risk estimation: {round(nlp_pred.scam_probability*100, 1)}%."
        )
        db.add(v_opp)
        db.commit()

        # 6. Semantic Pattern Matching
        retriever = get_scam_pattern_retriever(is_demo)
        ret_res = retriever.find_similar(text_content, top_k=3)
        
        # Save fingerprints
        max_sim_score = 0.0
        for pat in ret_res.similar_patterns:
            max_sim_score = max(max_sim_score, pat.similarity_score)
            fingerprint = ScamFingerprint(
                scan_id=scan.id,
                pattern_type=pat.matching_evidence,
                confidence=pat.similarity_score,
                embedding_id=pat.pattern_id
            )
            db.add(fingerprint)
        db.commit()

        v_pattern = VerificationCheck(
            scan_id=scan.id, step_name="Pattern matching performed", step_order=6,
            status=VerificationCheckStatus.PASSED if max_sim_score < 0.6 else VerificationCheckStatus.FAILED,
            detail=f"Compared embeddings against threat database. Highest match similarity: {round(max_sim_score*100, 1)}%."
        )
        db.add(v_pattern)
        db.commit()

        db_model_ret = ModelPrediction(
            scan_id=scan.id, model_name="SemanticScamRetriever",
            model_version="1.0.0", output_key="semantic_retrieval",
            output_value=max_sim_score, is_demo_prediction=is_demo
        )
        db.add(db_model_ret)
        db.commit()

        # 7. Model Fusion
        scan.status = ScanStatus.SCORING
        db.commit()
        
        # Prepare vector
        fusion_vector = FusionFeatureVector(
            nlp_scam_probability=nlp_pred.scam_probability,
            url_risk_probability=url_pred_score,
            identity_consistency=identity_res.identity_consistency_score,
            semantic_similarity=max_sim_score,
            payment_probability=nlp_pred.payment_risk,
            social_engineering_probability=nlp_pred.social_engineering_risk,
            opportunity_risk=nlp_pred.opportunity_risk,
            company_verification_signal=1.0 if (claimed_company_name and claimed_company_name.lower() in ("stripe", "google", "amazon")) else 0.0,
            metadata_features={}
        )
        
        fusion_model = get_fusion_model(is_demo)
        fusion_res = fusion_model.fuse(fusion_vector)
        
        db_model_fuse = ModelPrediction(
            scan_id=scan.id, model_name=fusion_res.model_name,
            model_version=fusion_res.model_version, output_key="fusion_meta",
            output_value=fusion_res.final_scam_probability, is_demo_prediction=is_demo
        )
        db.add(db_model_fuse)
        db.commit()

        # 8. Calibration
        calibrator = get_calibrator(is_demo)
        
        # Determine evidence list
        evidence_items = []
        
        # Add NLP word attributions as evidence
        for word, weight in nlp_pred.token_attributions[:4]:
            if weight > 0.1:
                evidence_items.append(Evidence(
                    scan_id=scan.id, category="Communication Pattern",
                    excerpt=f"Extracted high-risk keyword token: '{word}' (impact weight: {round(weight, 2)})",
                    attribution_score=weight, source_model=nlp_pred.model_name
                ))

        # Add Identity mismatches as evidence
        for mismatch in identity_res.mismatches:
            evidence_items.append(Evidence(
                scan_id=scan.id, category="Identity Claim",
                excerpt=mismatch, attribution_score=0.85, source_model="IdentityConsistencyChecker"
            ))

        # Add suspicious URL features as evidence
        if url_features_obj:
            if url_features_obj.has_suspicious_tld:
                evidence_items.append(Evidence(
                    scan_id=scan.id, category="Domain Authenticity",
                    excerpt=f"Uses highly suspicious/non-standard top-level domain: TLD '{target_domain.split('.')[-1]}'",
                    attribution_score=0.90, source_model="URLFeatureExtractor"
                ))
            if not url_features_obj.is_https:
                evidence_items.append(Evidence(
                    scan_id=scan.id, category="Channel Security",
                    excerpt="Unencrypted communication channel: Website domain does not support HTTPS/SSL.",
                    attribution_score=0.60, source_model="URLFeatureExtractor"
                ))
            if url_features_obj.entropy > 4.2:
                evidence_items.append(Evidence(
                    scan_id=scan.id, category="Domain Authenticity",
                    excerpt=f"Entropy score of domain '{target_domain}' is abnormally high ({url_features_obj.entropy}), indicating potential generated phishing domain.",
                    attribution_score=0.75, source_model="URLFeatureExtractor"
                ))

        # Add semantic patterns as evidence
        for pat in ret_res.similar_patterns[:2]:
            if pat.similarity_score > 0.65:
                evidence_items.append(Evidence(
                    scan_id=scan.id, category="Threat Database Match",
                    excerpt=f"Close semantic alignment to reported scam fingerprint: {pat.matching_evidence} (Similarity: {round(pat.similarity_score*100, 1)}%)",
                    attribution_score=pat.similarity_score, source_model="SemanticScamRetriever"
                ))

        for ev in evidence_items:
            db.add(ev)
        db.commit()

        # Calibrate
        cal_res = calibrator.calibrate(fusion_res.final_scam_probability, len(evidence_items))
        
        db_model_cal = ModelPrediction(
            scan_id=scan.id, model_name="ProbabilityCalibrator",
            model_version="1.0.0", output_key="calibration",
            output_value=cal_res.calibrated_probability, is_demo_prediction=is_demo
        )
        db.add(db_model_cal)
        db.commit()
        
        # Risk output assembly
        final_scores = assemble_risk_trust_output(cal_res.calibrated_probability, cal_res.confidence_score, len(evidence_items))

        # Save scores to scan
        scan.risk_score = final_scores.risk_score
        scan.trust_score = final_scores.trust_score
        scan.confidence_score = final_scores.confidence
        scan.risk_level = final_scores.risk_level
        scan.verdict = final_scores.verdict
        
        # Detailed risk dimensions
        scan.identity_risk = round((1.0 - identity_res.identity_consistency_score) * 100, 1)
        scan.payment_risk = round(nlp_pred.payment_risk * 100, 1)
        scan.domain_risk = round(url_pred_score * 100, 1)
        scan.communication_risk = round(nlp_pred.social_engineering_risk * 100, 1)
        scan.opportunity_risk = round(nlp_pred.opportunity_risk * 100, 1)
        scan.company_trust = round((85.0 if (claimed_company_name and claimed_company_name.lower() in ("stripe", "google", "amazon")) else 25.0), 1)

        # 9. Verification Final Check
        v_final = VerificationCheck(
            scan_id=scan.id, step_name="Final assessment generated", step_order=7,
            status=VerificationCheckStatus.PASSED if final_scores.risk_score < 40 else VerificationCheckStatus.WARNING if final_scores.risk_score < 75 else VerificationCheckStatus.FAILED,
            detail=f"Completed multi-model fusion. Confidence: {final_scores.confidence}%. Verdict: {final_scores.verdict}."
        )
        db.add(v_final)
        db.commit()

        # 10. Save Trust Report Narrative summary & recommended actions
        nar_sum = f"Opportunity analyzed under Scan ID {scan.id}. "
        if final_scores.verdict == "LIKELY_SCAM":
            nar_sum += f"WARNING: This opportunity exhibits multiple high-risk factors characteristic of employment fraud, specifically mimicking {claimed_company_name or 'a company'} with inconsistent domains and requesting upfront payments."
        elif final_scores.verdict == "SUSPICIOUS":
            nar_sum += f"ATTENTION: A few suspicious signals were detected, including unverified domains or slight grammatical urgency. Exercise caution before proceeding."
        else:
            nar_sum += f"SAFE: No malicious indicators detected. Stated identity matches known domains and channels."

        rec_actions = []
        if final_scores.risk_score > 70:
            rec_actions = [
                "DO NOT send any money, registration fees, or security deposits.",
                "DO NOT provide passwords, bank login details, or OTP codes.",
                "Verify the recruiter via the company's official website or direct LinkedIn profile.",
                "Report this recruiting message to your email provider and community intelligence dashboard."
            ]
        elif final_scores.risk_score > 40:
            rec_actions = [
                "Proceed with caution. Request a direct video interview before disclosing documents.",
                "Validate if the email sender's address domain matches the company's official domain.",
                "Do not install any software downloads or share sensitive identity cards."
            ]
        else:
            rec_actions = [
                "Standard safe behaviors. Confirm contract details.",
                "Proceed with scheduled interview steps."
            ]

        report = Report(
            scan_id=scan.id,
            report_type="TRUST_REPORT",
            is_shared=False,
            share_slug=str(uuid.uuid4())[:8],
            narrative_summary=nar_sum,
            recommended_actions=rec_actions
        )
        db.add(report)
        
        # Set Complete
        scan.status = ScanStatus.COMPLETE
        db.commit()

    except Exception as e:
        scan.status = ScanStatus.FAILED
        scan.failure_reason = str(e)
        db.commit()
    finally:
        db.close()

# Startup Database Seeding to avoid empty histories
@app.on_event("startup")
def seed_database_samples():
    db = SessionLocal()
    try:
        count = db.query(Scan).count()
        if count == 0:
            print("Seeding database with default analysis history...")
            
            # Create an admin user for login
            admin_id = uuid.uuid4()
            admin = User(id=admin_id, email="admin@scamcheck.io", hashed_password="password123", is_active=True)
            db.add(admin)

            # Create a mock user
            u_id = uuid.uuid4()
            user = User(id=u_id, email="guest@scamcheck.io", hashed_password="mock", is_active=True)
            db.add(user)
            db.commit()

            # Seed 1: Scam opportunity
            opp1 = Opportunity(
                id=uuid.uuid4(),
                title="Remote Data Entry Clerk - Stripe Partner",
                source="email",
                raw_content="Stripe HR is recruiting remote workers. Earn $85/hr for copying files. You must pay a $150 registration fee to get your work laptop. Send bank details and OTP immediately."
            )
            db.add(opp1)
            db.commit()

            scan1 = Scan(
                id=uuid.uuid4(),
                opportunity_id=opp1.id,
                user_id=user.id,
                status=ScanStatus.PENDING
            )
            db.add(scan1)
            db.commit()

            # Seed 2: Safe opportunity
            opp2 = Opportunity(
                id=uuid.uuid4(),
                title="Senior Frontend Engineer",
                source="linkedin",
                raw_content="Hi John, I am a recruiter at Google. We have an opening for a Senior Frontend Engineer on our Cloud team. Please visit google.com/careers or let me know if you would like to schedule a 30 min chat."
            )
            db.add(opp2)
            db.commit()

            scan2 = Scan(
                id=uuid.uuid4(),
                opportunity_id=opp2.id,
                user_id=user.id,
                status=ScanStatus.PENDING
            )
            db.add(scan2)
            db.commit()

            # Run pipeline synchronously for seeding
            run_analysis_pipeline(scan1.id, SessionLocal, is_demo=False)
            run_analysis_pipeline(scan2.id, SessionLocal, is_demo=False)
            print("Database seeding completed.")
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()

# API Router Endpoints

@app.post("/api/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or user.hashed_password != request.password:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    return TokenResponse(
        access_token=f"mock_token_for_{user.id}",
        user_id=str(user.id),
        email=user.email
    )

@app.post("/api/login/google", response_model=TokenResponse)
def login_google(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(
            request.token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        email = idinfo.get('email')
        
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="Invalid Google token payload.")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Auto-register new Google user
            user = User(id=uuid.uuid4(), email=email, hashed_password="google_oauth", is_active=True)
            db.add(user)
            db.commit()
        
        return TokenResponse(
            access_token=f"mock_token_for_{user.id}",
            user_id=str(user.id),
            email=user.email
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google authentication token.")


@app.post("/api/scan", response_model=ScanAnalyzeResponse)
def create_scan(request: ScanCreateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Enforce database mock user ID or guest session
    guest_user = db.query(User).first()
    guest_id = guest_user.id if guest_user else None

    # Handle input type matching
    content = ""
    source = "pasted_text"
    if request.input_type == InputType.TEXT:
        content = request.text
        source = "text"
    elif request.input_type == InputType.URL:
        content = str(request.url)
        source = "url"
    elif request.input_type == InputType.SCREENSHOT:
        content = "" # Extracted via OCR in background
        source = "screenshot"
    elif request.input_type == InputType.PDF:
        content = "" # Extracted in background
        source = "pdf"

    # Create Opportunity
    opp = Opportunity(
        title=request.text[:40] + "..." if request.text else f"Analysis of {request.input_type}",
        source=source,
        raw_content=content
    )
    db.add(opp)
    db.commit()

    # Create Scan
    scan = Scan(
        opportunity_id=opp.id,
        user_id=guest_id,
        status=ScanStatus.PENDING
    )
    db.add(scan)
    db.commit()

    # Dispatch analysis pipeline to background worker
    # We pass the SessionLocal class so it can instantiate its own session safely in thread
    # Toggling is_demo based on request settings or global flags
    is_demo = settings.FORCE_DEMO_MODE

    background_tasks.add_task(run_analysis_pipeline, scan.id, SessionLocal, is_demo)

    return ScanAnalyzeResponse(
        id=str(scan.id),
        status=scan.status,
        message="Analysis started in background."
    )

@app.get("/api/scan/{scan_id}", response_model=ScanStatusResponse)
def get_scan_status(scan_id: str, db: Session = Depends(get_db)):
    try:
        s_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Scan ID format")

    scan = db.query(Scan).filter(Scan.id == s_uuid).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanStatusResponse(
        id=str(scan.id),
        status=scan.status,
        risk_score=scan.risk_score,
        trust_score=scan.trust_score,
        confidence_score=scan.confidence_score,
        risk_level=scan.risk_level,
        verdict=scan.verdict,
        failure_reason=scan.failure_reason
    )

@app.get("/api/report/{scan_id}", response_model=TrustReportResponse)
def get_trust_report(scan_id: str, db: Session = Depends(get_db)):
    try:
        s_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Scan ID format")

    scan = db.query(Scan).filter(Scan.id == s_uuid).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan.status != ScanStatus.COMPLETE:
        raise HTTPException(status_code=400, detail=f"Report not ready. Current scan status is {scan.status}")

    opp = db.query(Opportunity).filter(Opportunity.id == scan.opportunity_id).first()
    comp = db.query(Company).filter(Company.id == opp.company_id).first() if opp else None
    report = db.query(Report).filter(Report.scan_id == scan.id).first()
    
    evidences = db.query(Evidence).filter(Evidence.scan_id == scan.id).all()
    checks = db.query(VerificationCheck).filter(VerificationCheck.scan_id == scan.id).order_by(VerificationCheck.step_order).all()
    fingerprints = db.query(ScamFingerprint).filter(ScamFingerprint.scan_id == scan.id).all()

    # Determine if demo based on predictions
    preds = db.query(ModelPrediction).filter(ModelPrediction.scan_id == scan.id).all()
    is_demo_data = any(p.is_demo_prediction for p in preds) if preds else True

    # Assemble response schemas
    header = TrustReportHeader(
        opportunity_title=opp.title if opp else "Unknown Opportunity",
        company_name=comp.name if comp else "Unknown Claimed Company",
        source=opp.source if opp else "unknown",
        scan_id=str(scan.id),
        timestamp=scan.created_at
    )

    hero = TrustReportHero(
        risk_score=scan.risk_score,
        trust_score=scan.trust_score,
        confidence=scan.confidence_score,
        risk_level=scan.risk_level,
        verdict=scan.verdict
    )

    breakdown = RiskBreakdown(
        identity=scan.identity_risk,
        payment=scan.payment_risk,
        domain=scan.domain_risk,
        communication=scan.communication_risk,
        opportunity=scan.opportunity_risk,
        company_trust=scan.company_trust
    )

    evidence_items = [
        EvidenceItem(
            category=e.category,
            excerpt=e.excerpt,
            attribution_score=e.attribution_score,
            source_model=e.source_model
        ) for e in evidences
    ]

    journey = [
        VerificationStep(
            step_name=c.step_name,
            step_order=c.step_order,
            status=c.status,
            detail=c.detail
        ) for c in checks
    ]

    scam_fingerprints = [
        ScamFingerprintItem(
            pattern_type=f.pattern_type,
            confidence=f.confidence
        ) for f in fingerprints
    ]

    return TrustReportResponse(
        header=header,
        hero=hero,
        risk_breakdown=breakdown,
        evidence=evidence_items,
        verification_journey=journey,
        scam_fingerprint=scam_fingerprints,
        recommended_actions=report.recommended_actions if report else [],
        is_demo_data=is_demo_data
    )

@app.get("/api/passport/{scan_id}", response_model=OpportunityPassport)
def get_opportunity_passport(scan_id: str, db: Session = Depends(get_db)):
    try:
        s_uuid = uuid.UUID(scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Scan ID format")

    scan = db.query(Scan).filter(Scan.id == s_uuid).first()
    if not scan or scan.status != ScanStatus.COMPLETE:
        raise HTTPException(status_code=404, detail="Scan not found or not complete")

    opp = db.query(Opportunity).filter(Opportunity.id == scan.opportunity_id).first()
    comp = db.query(Company).filter(Company.id == opp.company_id).first() if opp else None
    checks = db.query(VerificationCheck).filter(VerificationCheck.scan_id == scan.id).order_by(VerificationCheck.step_order).all()
    report = db.query(Report).filter(Report.scan_id == scan.id).first()

    journey = [
        VerificationStep(
            step_name=c.step_name,
            step_order=c.step_order,
            status=c.status,
            detail=c.detail
        ) for c in checks
    ]

    return OpportunityPassport(
        opportunity_title=opp.title if opp else None,
        company_name=comp.name if comp else None,
        risk_score=scan.risk_score,
        trust_score=scan.trust_score,
        confidence=scan.confidence_score,
        verification_checks=journey,
        status="VERIFIED_SAFE" if scan.risk_score < 40 else "WARNING" if scan.risk_score < 75 else "BLOCKED_SCAM",
        scan_id=str(scan.id),
        timestamp=scan.created_at,
        share_url=f"/share/passport/{report.share_slug}" if report else f"/share/passport/{scan.id}"
    )

@app.get("/api/history")
def get_analysis_history(db: Session = Depends(get_db)):
    scans = db.query(Scan).order_by(desc(Scan.created_at)).limit(20).all()
    
    out = []
    for s in scans:
        opp = db.query(Opportunity).filter(Opportunity.id == s.opportunity_id).first()
        comp = db.query(Company).filter(Company.id == opp.company_id).first() if opp else None
        out.append({
            "id": str(s.id),
            "opportunity_title": opp.title if opp else "Analysis",
            "company_name": comp.name if comp else "Unknown Company",
            "source": opp.source if opp else "unknown",
            "status": s.status,
            "risk_score": s.risk_score,
            "verdict": s.verdict,
            "timestamp": s.created_at
        })
    return out

@app.post("/api/copilot", response_model=CopilotChatResponse)
def copilot_chat(request: CopilotChatRequest, db: Session = Depends(get_db)):
    try:
        s_uuid = uuid.UUID(request.scan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Scan ID format")

    scan = db.query(Scan).filter(Scan.id == s_uuid).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    evidences = db.query(Evidence).filter(Evidence.scan_id == scan.id).all()
    
    # Ground the reply in database evidence
    m_lower = request.message.lower()
    
    reply = ""
    grounded_ids = []
    
    if len(evidences) == 0:
        reply = "I analyzed this opportunity, but found no notable positive or negative evidence triggers in my checks. The details seem standard. Do you have any specific concerns about it?"
    else:
        intro = f"Based on the analysis of this opportunity (Verdict: **{scan.verdict}**, Risk Score: **{scan.risk_score}%**), here is what I found:\n\n"
        details = []
        for e in evidences:
            details.append(f"- **{e.category}**: {e.excerpt}")
            grounded_ids.append(str(e.id))
        
        reply = intro + "\n".join(details) + "\n\n"
        
        if "pay" in m_lower or "fee" in m_lower or "money" in m_lower:
            reply += "Critical Advice: Legitimate companies *never* require employees to pay registration, processing, or laptop setup fees upfront. If they ask for payment, it is a 100% confirmed scam."
        elif "email" in m_lower or "domain" in m_lower:
            reply += "Security Notice: Check the domain of the email sender carefully. Scammers often use free domains like gmail.com or slightly misspelled domains (e.g. stripe-jobs.xyz instead of stripe.com) to impersonate recruiters."
        else:
            reply += "What specific warning flag would you like me to explain in more detail?"

    return CopilotChatResponse(
        scan_id=str(scan.id),
        reply=reply,
        grounded_in_evidence_ids=grounded_ids,
        is_demo_provider=False
    )

@app.post("/api/community-report", response_model=CommunityReportResponse)
def submit_community_report(request: CommunityReportRequest, db: Session = Depends(get_db)):
    scan_uuid = None
    if request.scan_id:
        try:
            scan_uuid = uuid.UUID(request.scan_id)
        except ValueError:
            pass

    report = CommunityReport(
        scan_id=scan_uuid,
        description=request.description,
        is_reviewed=False
    )
    db.add(report)
    db.commit()

    return CommunityReportResponse(
        id=str(report.id),
        status="RECEIVED"
    )

@app.post("/api/settings/toggle-demo")
def toggle_demo_mode(is_demo: bool, db: Session = Depends(get_db)):
    settings.FORCE_DEMO_MODE = is_demo
    return {"message": f"Demo Mode toggled to {is_demo}"}

@app.post("/api/train")
def run_retraining(background_tasks: BackgroundTasks):
    from scripts.train_models import train_nlp_model, train_url_model, train_fusion_model
    
    def retrain_job():
        try:
            train_nlp_model()
            train_url_model()
            train_fusion_model()
            print("Retraining completed successfully.")
        except Exception as e:
            print(f"Error in retraining worker: {e}")
            
    background_tasks.add_task(retrain_job)
    return {"status": "TRAINING_STARTED", "message": "Model retraining initiated in background."}

@app.get("/api/settings/registry")
def get_model_registry():
    try:
        from app.services.registry import ModelRegistry
        return ModelRegistry.get_registered_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

