import hashlib
from app.services.embeddings.interface import EmbeddingModel,RetrievalResult,ScamPatternRetriever,SimilarPattern
_DIM=32
_PATTERNS=[("demo-pattern-payment-1","Requests a registration fee before onboarding starts"),("demo-pattern-urgency-1","Pressures the applicant to respond within a few hours"),("demo-pattern-credential-1","Asks for bank details or an OTP over chat")]
def _hash_embed(text,dim=_DIM):
    d=hashlib.sha256((text or "").encode()).digest()
    return [d[i%len(d)]/255. for i in range(dim)]
def _cosine(a,b):
    da=sum(x*x for x in a)**.5; db=sum(y*y for y in b)**.5
    return sum(x*y for x,y in zip(a,b))/(da*db) if da and db else 0.
class DemoEmbeddingModel(EmbeddingModel):
    def embed(self,text): return _hash_embed(text)
class DemoScamPatternRetriever(ScamPatternRetriever):
    def __init__(self,embedder=None): self._embedder=embedder or DemoEmbeddingModel()
    def find_similar(self,text,top_k=5):
        q=self._embedder.embed(text); scored=[SimilarPattern(pid,round(_cosine(q,_hash_embed(desc)),4),desc,True) for pid,desc in _PATTERNS]
        scored.sort(key=lambda x:x.similarity_score,reverse=True)
        return RetrievalResult(len(q),scored[:top_k],True)
def get_scam_pattern_retriever(): return DemoScamPatternRetriever()
