from abc import ABC,abstractmethod
from dataclasses import dataclass,field
@dataclass
class IdentityClaim:
    claimed_company:str|None=None; sender_name:str|None=None; sender_email:str|None=None; email_domain:str|None=None; website_domain:str|None=None; official_company_domain:str|None=None
@dataclass
class IdentityConsistencyResult:
    identity_consistency_score:float; mismatches:list[str]=field(default_factory=list); checks_performed:list[str]=field(default_factory=list); is_demo_prediction:bool=True
class IdentityConsistencyModel(ABC):
    @abstractmethod
    def evaluate(self,claim:IdentityClaim)->IdentityConsistencyResult: raise NotImplementedError
