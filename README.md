# ScamCheck PRO - AI Recruitment Fraud Intelligence

ScamCheck PRO is a production-style fraud-intelligence SaaS application built to analyze internship and job postings to detect employment scams, phishing, and fake recruitment campaigns.

## Key Features
*   **Deep Learning NLP Transformer**: Fine-tuned on a real-world dataset to classify job descriptions as `legitimate`, `suspicious`, or `fraudulent`.
*   **Multi-Model Architecture**: Fuses predictions from URL risk models, NLP models, and semantic retrieval to produce a calibrated trust score.
*   **Modern React UI**: A responsive, beautifully designed Vite + React frontend with micro-animations and data visualizations.
*   **Secure Authentication**: Integrated with Google OAuth for real, secure user authentication.
*   **RESTful Backend**: A robust Python FastAPI backend managing the ML inference pipeline.

---

## 1. Machine Learning Performance Metrics

ScamCheck PRO uses a fine-tuned Transformer model (EMSCAD-trained) to evaluate textual signals (urgency, payment flags) alongside traditional models.

### NLP Transformer Classifier
*Evaluated on a held-out test split from the `internship_job_scam_dataset.csv` (900 balanced records).*

| Evaluation Metric | Score | Description |
| :--- | :--- | :--- |
| **Accuracy** | **89.44%** | Overall model classification accuracy |
| **F1 Score** | **85.27%** | Harmonic mean of precision and recall |
| **Recall** | **87.30%** | Ability to find all relevant cases |
| **Precision** | **83.33%** | Proportion of positive identifications that were actually correct |

---

## 2. Integrated Pipeline Architecture

Data flows sequentially through these core layers:
1.  **Extraction**: Identifies company claims, email/website domains, and salary info using named entity parses.
2.  **Transformer NLP Classifier**: Deep learning model evaluates text for scam patterns.
3.  **URL Risk Model (XGBoost)**: Predicts domain threat ratings from static string metrics (length, entropy, TLD check, HTTPS).
4.  **Identity Consistency**: Verifies if sender domains match official websites.
5.  **Semantic Retrieval**: Checks cosine similarity against the database threat patterns using pgvector / Python fallback.
6.  **Model Fusion**: Combines scores using a trained logistic meta-model.
7.  **Calibration**: Scales final scores using Isotonic Regression fit on validation thresholds.

---

## 3. How to Run Locally

### Requirements
*   Python 3.10+
*   Node.js 18+

### Setup the Backend (FastAPI + ML)
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt -r requirements-ml.txt
    ```
2.  Start the backend server:
    ```bash
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
    ```
    *The API will be available at http://localhost:8000*

### Setup the Frontend (React + Vite)
1.  Open a new terminal and navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the development server:
    ```bash
    npm run dev
    ```
    *The application will be available at http://localhost:5173*

### Authentication Note
You must configure a valid Google Client ID to use the frontend login. We have pre-configured a Client ID for demo purposes.

Alternatively, you can log in using the default local administrator credentials:
- **Email:** `admin@scamcheck.io`
- **Password:** `password123`

---

## 4. Deployment

### Render (Recommended for Free Tier)
This repository contains a `render.yaml` Blueprint file for seamless 1-click deployment to Render.com.
1. Create a new Blueprint on Render and link this repository.
2. Render will automatically detect and deploy both the FastAPI web service and the React static site.
3. Once deployed, update the `VITE_API_BASE` environment variable on the frontend service to point to your new backend URL.

### Docker
Production-ready `frontend.Dockerfile`, `backend.Dockerfile`, and `docker-compose.yml` are provided. 
```bash
docker-compose up --build
```
