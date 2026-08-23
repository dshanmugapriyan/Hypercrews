from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import RiskLevel, Verdict
from app.schemas.scan import EvidenceItem, RiskBreakdown, ScamFingerprintItem, VerificationStep
class TrustReportHeader(BaseModel):
    opportunity_title: str|None=None; company_name: str|None=None; source: str; scan_id: str; timestamp: datetime
class TrustReportHero(BaseModel):
    risk_score: float|None; trust_score: float|None; confidence: float|None; risk_level: RiskLevel|None; verdict: Verdict
class TrustReportResponse(BaseModel):
    header: TrustReportHeader; hero: TrustReportHero; risk_breakdown: RiskBreakdown; evidence: list[EvidenceItem]; verification_journey: list[VerificationStep]; scam_fingerprint: list[ScamFingerprintItem]; recommended_actions: list[str]; is_demo_data: bool
class OpportunityPassport(BaseModel):
    opportunity_title: str|None; company_name: str|None; risk_score: float|None; trust_score: float|None; confidence: float|None; verification_checks: list[VerificationStep]; status: str; scan_id: str; timestamp: datetime; share_url: str
