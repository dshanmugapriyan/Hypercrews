from abc import ABC, abstractmethod
from dataclasses import dataclass
@dataclass
class URLFeatures:
    url:str; url_length:int; domain_length:int; subdomain_count:int; digit_ratio:float; special_char_ratio:float; entropy:float; has_suspicious_tld:bool; is_https:bool; redirect_count:int; domain_age_days:int|None; brand_similarity_score:float|None
@dataclass
class URLRiskPrediction:
    url_risk_probability:float; features:URLFeatures; feature_importance:dict[str,float]; model_name:str; model_version:str; is_demo_prediction:bool
class URLRiskModel(ABC):
    @abstractmethod
    def predict(self,features:URLFeatures)->URLRiskPrediction: raise NotImplementedError
    @abstractmethod
    def is_trained(self)->bool: raise NotImplementedError
