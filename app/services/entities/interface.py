from abc import ABC,abstractmethod
from dataclasses import dataclass,field
@dataclass
class ExtractedEntity:
    entity_type:str; value:str; confidence:float; source:str
@dataclass
class ExtractionResult:
    entities:list[ExtractedEntity]=field(default_factory=list)
    def by_type(self,entity_type): return [e for e in self.entities if e.entity_type==entity_type]
    def first_value(self,entity_type):
        matches=self.by_type(entity_type); return matches[0].value if matches else None
class EntityExtractor(ABC):
    @abstractmethod
    def extract(self,text:str)->ExtractionResult: raise NotImplementedError
