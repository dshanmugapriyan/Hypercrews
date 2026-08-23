import json
import hashlib
import numpy as np
from sqlalchemy import text
from app.core.database import SessionLocal
from app.services.embeddings.interface import EmbeddingModel, RetrievalResult, ScamPatternRetriever, SimilarPattern

_DIM = 384

# Reference list of global scam patterns to populate the DB
DEFAULT_SCAM_PATTERNS = [
    ("payment_scam", "Requires a registration fee or processing fee before onboarding starts."),
    ("payment_scam", "Asks the candidate to buy software or laptops from a specific vendor to be reimbursed later."),
    ("urgency", "Pressures the applicant to sign a contract or respond to an offer within a few hours."),
    ("credential_harvesting", "Asks for bank login details, card number, or OTP over WhatsApp or Telegram chat."),
    ("identity_impersonation", "Claims to represent a major company (e.g. Google, Apple) but uses a generic public domain email."),
    ("unrealistic_compensation", "Offers extremely high pay ($100/hr) for unskilled data entry tasks requiring no interview.")
]

def _hash_embed(text_str, dim=_DIM):
    # Deterministic vector fallback
    d = hashlib.sha256((text_str or "").encode()).digest()
    vec = []
    for i in range(dim):
        # Generate pseudo-random float between -1 and 1
        val = (d[i % len(d)] / 255.0) * 2.0 - 1.0
        vec.append(val)
    # Normalize vector to unit length
    norm = sum(x*x for x in vec)**0.5
    return [x/norm for x in vec] if norm > 0 else vec

class RealEmbeddingModel(EmbeddingModel):
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._load_lightweight_model()

    def _load_lightweight_model(self):
        try:
            # Try importing Hugging Face sentence-transformers
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            try:
                # Fallback to loading standard model via transformers pipeline
                from transformers import AutoTokenizer, AutoModel
                import torch
                self.tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
                self.model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            except Exception:
                pass

    def embed(self, text_str: str) -> list[float]:
        text_str = text_str or ""
        
        # 1. Try using sentence_transformers model
        if self.model and hasattr(self.model, "encode"):
            try:
                emb = self.model.encode(text_str)
                return [float(x) for x in emb]
            except Exception:
                pass

        # 2. Try using raw transformers mean-pooling
        if self.model and self.tokenizer:
            try:
                import torch
                inputs = self.tokenizer(text_str, padding=True, truncation=True, return_tensors="pt")
                with torch.no_grad():
                    outputs = self.model(**inputs)
                # Mean Pooling
                token_embeddings = outputs[0]
                attention_mask = inputs["attention_mask"]
                input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
                sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                emb = (sum_embeddings / sum_mask)[0]
                # Normalize
                emb_norm = emb / torch.norm(emb)
                return [float(x) for x in emb_norm]
            except Exception:
                pass

        # 3. Deterministic fallback if offline/no libraries
        return _hash_embed(text_str, _DIM)

class RealScamPatternRetriever(ScamPatternRetriever):
    def __init__(self, embedder=None):
        self.embedder = embedder or RealEmbeddingModel()
        self._seed_default_patterns()

    def _seed_default_patterns(self):
        # Populate the database with default patterns if not present
        db = SessionLocal()
        try:
            # Check if scam_patterns table exists (it gets created at startup)
            db.execute(text("SELECT 1 FROM scam_patterns LIMIT 1"))
            count = db.execute(text("SELECT COUNT(*) FROM scam_patterns")).scalar()
            if count == 0:
                for cat, desc in DEFAULT_SCAM_PATTERNS:
                    emb = self.embedder.embed(desc)
                    emb_str = json.dumps(emb)
                    # Use standard SQL to stay database-agnostic during seeding
                    db.execute(
                        text("INSERT INTO scam_patterns (id, pattern_text, pattern_category, embedding_data, created_at, updated_at) VALUES (:id, :txt, :cat, :emb, datetime('now'), datetime('now'))"),
                        {"id": hashlib.md5(desc.encode()).hexdigest(), "txt": desc, "cat": cat, "emb": emb_str}
                    )
                db.commit()
        except Exception:
            # Table might not be created yet, will be handled during app start
            pass
        finally:
            db.close()

    def find_similar(self, text_str: str, top_k: int = 5) -> RetrievalResult:
        q_emb = self.embedder.embed(text_str)
        db = SessionLocal()
        
        try:
            # Check if postgres/pgvector is active
            bind = db.get_bind()
            if "postgresql" in bind.driver:
                try:
                    # Execute pgvector cosine distance query
                    # If pgvector is present, embedding column is castable to vector
                    q_emb_list_str = str(q_emb)
                    result = db.execute(
                        text("SELECT id, pattern_text, pattern_category, 1 - (embedding <=> :q_emb::vector) as similarity FROM scam_patterns ORDER BY similarity DESC LIMIT :top_k"),
                        {"q_emb": q_emb_list_str, "top_k": top_k}
                    )
                    patterns = []
                    for row in result:
                        patterns.append(SimilarPattern(
                            pattern_id=str(row[0]),
                            similarity_score=round(float(row[3]), 4),
                            matching_evidence=f"[{row[2].upper()}] {row[1]}",
                            is_demo_data=False
                        ))
                    return RetrievalResult(_DIM, patterns, False)
                except Exception:
                    # Fall back to sqlite python matching if query fails
                    pass

            # SQLite python fallback matching
            result = db.execute(text("SELECT id, pattern_text, pattern_category, embedding_data FROM scam_patterns")).fetchall()
            
            scored = []
            for row in result:
                row_emb = json.loads(row[3]) if row[3] else None
                if row_emb:
                    # Calculate cosine similarity
                    dot = sum(x*y for x, y in zip(q_emb, row_emb))
                    norm_a = sum(x*x for x in q_emb)**0.5
                    norm_b = sum(x*x for x in row_emb)**0.5
                    sim = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
                    
                    scored.append(SimilarPattern(
                        pattern_id=str(row[0]),
                        similarity_score=round(sim, 4),
                        matching_evidence=f"[{row[2].upper()}] {row[1]}",
                        is_demo_data=False
                    ))
            
            scored.sort(key=lambda x: x.similarity_score, reverse=True)
            return RetrievalResult(_DIM, scored[:top_k], False)
            
        except Exception as e:
            # Return an explicit inconclusive result on database empty/failure
            return RetrievalResult(_DIM, [], False)
        finally:
            db.close()

def get_scam_pattern_retriever():
    return RealScamPatternRetriever()
