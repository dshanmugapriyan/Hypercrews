from abc import ABC,abstractmethod
from dataclasses import dataclass
@dataclass
class FusionFeatureVector:
    nlp_scam_probability:float; url_risk_probability:float|None; identity_consistency:float; semantic_similarity:float; payment_probability:float; social_engineering_probability:float; opportunity_risk:float; company_verification_signal:float; metadata_features:dict[str,float]
    def as_ordered_list(self):
        return [self.nlp_scam_probability,self.url_risk_probability if self.url_risk_probability is not None else 0.,self.identity_consistency,self.semantic_similarity,self.payment_probability,self.social_engineering_probability,self.opportunity_risk,self.company_verification_signal,*self.metadata_features.values()]
@dataclass
class FusionResult:
    final_scam_probability:float; feature_contributions:dict[str,float]; model_name:str; model_version:str; is_demo_prediction:bool
class FusionModel(ABC):
    @abstractmethod
    def fuse(self,features): raise NotImplementedError
    @abstractmethod
    def is_trained(self): raise NotImplementedError
