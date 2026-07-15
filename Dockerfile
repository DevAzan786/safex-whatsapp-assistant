# Use official lightweight Python image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user

# Set working directory
WORKDIR /app

# Create a non-root user (Hugging Face Spaces runs as user ID 1000)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:${PATH}"

# Copy requirements and install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application files
COPY --chown=user . .

# Run the data ingestion script to build the local ChromaDB database inside the Docker image
RUN python scripts/ingest_data.py

# Expose port 7860 for Hugging Face Spaces routing
EXPOSE 7860

# Start FastAPI using uvicorn on port 7860
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
