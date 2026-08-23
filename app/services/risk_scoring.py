from dataclasses import dataclass
from app.models.base import RiskLevel
MIN_EVIDENCE_FOR_VERDICT=1
@dataclass
class RiskTrustOutput:
    risk_score:float; trust_score:float; confidence:float; risk_level:RiskLevel|None; verdict:str
def assemble_risk_trust_output(calibrated_probability,confidence_score,evidence_count):
    if evidence_count<MIN_EVIDENCE_FOR_VERDICT: return RiskTrustOutput(0.,0.,0.,None,"UNABLE_TO_VERIFY")
    risk_score=round(calibrated_probability*100,1); trust_score=round(100-risk_score,1); confidence=round(confidence_score*100,1)
    risk_level=RiskLevel.from_score(risk_score)
    verdict="LIKELY_SCAM" if risk_level in (RiskLevel.HIGH,RiskLevel.CRITICAL) else "SUSPICIOUS" if risk_level is RiskLevel.MODERATE else "LIKELY_SAFE"
    return RiskTrustOutput(risk_score,trust_score,confidence,risk_level,verdict)
