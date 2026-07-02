# Base image matching user's Python runtime
FROM python:3.13-slim

# Install system dependencies required for OpenCV image matrix operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements list
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download ML models so they are baked into the image and never downloaded at runtime
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
RUN python -c "import easyocr; easyocr.Reader(['en', 'hi'])"
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY ./app ./app
COPY .env .env

# Create storage mounts
RUN mkdir -p /app/uploads /app/vector_store

# Expose API port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
