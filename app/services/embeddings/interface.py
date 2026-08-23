from abc import ABC,abstractmethod
from dataclasses import dataclass
@dataclass
class SimilarPattern:
    pattern_id:str; similarity_score:float; matching_evidence:str; is_demo_data:bool
@dataclass
class RetrievalResult:
    query_embedding_dim:int; similar_patterns:list[SimilarPattern]; is_demo_data:bool
class EmbeddingModel(ABC):
    @abstractmethod
    def embed(self,text:str)->list[float]: raise NotImplementedError
class ScamPatternRetriever(ABC):
    @abstractmethod
    def find_similar(self,text:str,top_k:int=5)->RetrievalResult: raise NotImplementedError
