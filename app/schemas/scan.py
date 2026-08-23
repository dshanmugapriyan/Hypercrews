from pydantic import BaseModel, Field, HttpUrl, model_validator
from app.schemas.common import InputType, ORMBase, RiskLevel, ScanStatus, Verdict
class ScanCreateRequest(BaseModel):
    input_type: InputType
    text: str|None=Field(default=None,max_length=20000)
    url: HttpUrl|None=None
    file_ref: str|None=Field(default=None,description="Reference returned by upload endpoint")
    @model_validator(mode="after")
    def validate_payload_matches_type(self):
        if self.input_type==InputType.TEXT and not self.text: raise ValueError("`text` is required when input_type is TEXT")
        if self.input_type==InputType.URL and not self.url: raise ValueError("`url` is required when input_type is URL")
        if self.input_type in (InputType.SCREENSHOT,InputType.PDF) and not self.file_ref: raise ValueError("`file_ref` is required when input_type is SCREENSHOT or PDF")
        return self
class ScanCreateResponse(ORMBase):
    id: str; status: ScanStatus
class RiskBreakdown(BaseModel):
    identity: float|None=None; payment: float|None=None; domain: float|None=None; communication: float|None=None; opportunity: float|None=None; company_trust: float|None=None
class ScanStatusResponse(ORMBase):
    id: str; status: ScanStatus; risk_score: float|None=None; trust_score: float|None=None; confidence_score: float|None=None; risk_level: RiskLevel|None=None; verdict: Verdict|None=None; failure_reason: str|None=None
class EvidenceItem(BaseModel):
    category: str; excerpt: str|None=None; attribution_score: float|None=None; source_model: str|None=None
class ScamFingerprintItem(BaseModel):
    pattern_type: str; confidence: float
class VerificationStep(BaseModel):
    step_name: str; step_order: int; status: str; detail: str|None=None
class ScanAnalyzeResponse(BaseModel):
    id: str; status: ScanStatus; message: str
