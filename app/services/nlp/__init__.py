def get_nlp_model(is_demo: bool = True):
    from app.core.config import settings
    if settings.FORCE_DEMO_MODE or is_demo:
        from app.services.nlp.demo import DemoNLPModel
        return DemoNLPModel()
    else:
        from app.services.nlp.transformer_model import TransformerNLPModel
        return TransformerNLPModel(settings.NLP_MODEL_PATH)
