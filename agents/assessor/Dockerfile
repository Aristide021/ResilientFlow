FROM python:3.11-slim

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY agents/assessor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy common utilities
COPY common/ ./common/
COPY proto/ ./proto/

# Copy agent code
COPY agents/assessor/ ./agents/assessor/

# Set environment variables
ENV PYTHONPATH=/workspace
ENV GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}

# Expose port for Cloud Run
EXPOSE 8080

# Set entrypoint
CMD ["python", "agents/assessor/main.py"] 