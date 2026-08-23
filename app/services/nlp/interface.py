from abc import ABC, abstractmethod
from dataclasses import dataclass
@dataclass
class NLPPrediction:
    scam_probability: float
    scam_category_probabilities: dict[str,float]
    severity: float
    payment_risk: float
    identity_risk: float
    social_engineering_risk: float
    opportunity_risk: float
    token_attributions: list[tuple[str,float]]
    model_name: str
    model_version: str
    is_demo_prediction: bool
class NLPModel(ABC):
    @abstractmethod
    def predict(self,text:str)->NLPPrediction: raise NotImplementedError
    @abstractmethod
    def is_fine_tuned(self)->bool: raise NotImplementedError
