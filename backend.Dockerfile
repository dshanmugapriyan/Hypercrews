FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
COPY requirements-ml.txt .

RUN pip install --no-cache-dir -r requirements.txt -r requirements-ml.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Ensure database and models directories exist
RUN mkdir -p app/resources/models app/resources/transformer_model

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
