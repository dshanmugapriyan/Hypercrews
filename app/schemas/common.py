from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict
class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
class InputType(str, Enum):
    TEXT="TEXT"; SCREENSHOT="SCREENSHOT"; PDF="PDF"; URL="URL"
class RiskLevel(str, Enum):
    LOW="LOW"; MODERATE="MODERATE"; HIGH="HIGH"; CRITICAL="CRITICAL"
    
    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        if score < 25.0:
            return cls.LOW
        elif score < 60.0:
            return cls.MODERATE
        elif score < 85.0:
            return cls.HIGH
        else:
            return cls.CRITICAL
class ScanStatus(str, Enum):
    PENDING="PENDING"; EXTRACTING="EXTRACTING"; ANALYZING="ANALYZING"; VERIFYING="VERIFYING"; SCORING="SCORING"; COMPLETE="COMPLETE"; FAILED="FAILED"; UNABLE_TO_VERIFY="UNABLE_TO_VERIFY"
class Verdict(str, Enum):
    LIKELY_SAFE="LIKELY_SAFE"; SUSPICIOUS="SUSPICIOUS"; LIKELY_SCAM="LIKELY_SCAM"; UNABLE_TO_VERIFY="UNABLE_TO_VERIFY"
class TimestampedSchema(ORMBase):
    id: str
    created_at: datetime
    updated_at: datetime
