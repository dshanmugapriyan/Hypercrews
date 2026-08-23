# ScamCheck — Existing Intelligence Layer Snapshot

This archive captures the files supplied by the project owner as the current continuation point.

## Important architecture constraint
The current interfaces intentionally separate:
- Transformer NLP classifier
- URL risk model
- Embedding + semantic retrieval
- Identity consistency
- Multimodel fusion
- Probability calibration
- Risk/trust output assembly
- Entity extraction
- Trust Report / Copilot contracts

The Demo implementations are explicitly marked as demo/mock and must be replaced by trained artifacts for production ML claims.

## Next implementation target
Implement the real Transformer NLP model behind `NLPModel` without changing the public interface or downstream contracts. Then proceed to real URL model, semantic retrieval, fusion/meta-model, and calibration.

## Safety constraint
Submitted URLs must not be automatically executed/fetched by the analysis pipeline. Network enrichment should remain explicit and isolated.
