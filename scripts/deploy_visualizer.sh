#!/bin/bash

# Deploy ResilientFlow Visualizer to Cloud Run
# Quick deployment script for the Streamlit agent visualizer

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ Please set GOOGLE_CLOUD_PROJECT environment variable"
    exit 1
fi

REGION="${REGION:-us-central1}"
SERVICE_NAME="resilientflow-visualizer"

echo "🚀 Deploying ResilientFlow Visualizer to Cloud Run..."
echo "📋 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"

# Create Dockerfile for visualizer
cat > visualizer/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app.py .

# Expose Streamlit port
EXPOSE 8501

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run Streamlit app
CMD ["streamlit", "run", "app.py"]
EOF

# Navigate to visualizer directory
cd visualizer

# Build and deploy
echo "🔨 Building container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME .

echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8501 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 2 \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --format "value(status.url)")

echo ""
echo "✅ Visualizer deployed successfully!"
echo "🌐 URL: $SERVICE_URL"
echo ""
echo "💡 To test locally:"
echo "   cd visualizer"
echo "   pip install -r requirements.txt"
echo "   streamlit run app.py"
echo ""
echo "🎮 To generate demo data:"
echo "   python3 ../scripts/publish_mocks.py --project-id $PROJECT_ID --single-event"
echo "" 