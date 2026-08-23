def get_scam_pattern_retriever(is_demo: bool = True):
    from app.core.config import settings
    if settings.FORCE_DEMO_MODE or is_demo:
        from app.services.embeddings.demo import DemoScamPatternRetriever
        return DemoScamPatternRetriever()
    else:
        from app.services.embeddings.real import RealScamPatternRetriever
        return RealScamPatternRetriever()
