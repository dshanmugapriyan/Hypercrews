from app.services.fusion.interface import FusionFeatureVector,FusionModel,FusionResult
_WEIGHTS={"nlp_scam_probability":.30,"url_risk_probability":.15,"identity_inconsistency":.20,"semantic_similarity":.10,"payment_probability":.15,"social_engineering_probability":.10}
class DemoFusionModel(FusionModel):
    def is_trained(self): return False
    def fuse(self,f):
        c={"nlp_scam_probability":.30*f.nlp_scam_probability,"url_risk_probability":.15*(f.url_risk_probability or 0.),"identity_inconsistency":.20*(1-f.identity_consistency),"semantic_similarity":.10*f.semantic_similarity,"payment_probability":.15*f.payment_probability,"social_engineering_probability":.10*f.social_engineering_probability}
        return FusionResult(round(min(.99,sum(c.values())),4),{k:round(v,4) for k,v in c.items()},"demo-linear-fusion","0.1.0-demo",True)
def get_fusion_model():
    from app.core.config import settings
    if settings.FUSION_MODEL_PATH: pass
    return DemoFusionModel()
