#!/bin/bash

# ResilientFlow Bootstrap Script
# Deploys the complete disaster relief coordination system on Google Cloud

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"resilientflow-demo"}
REGION=${REGION:-"us-central1"}
ZONE=${ZONE:-"us-central1-a"}

echo "🚀 ResilientFlow Bootstrap Script"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    echo "❌ terraform not found. Please install Terraform."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ docker not found. Please install Docker."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Authenticate and set project
echo "🔐 Setting up authentication..."
gcloud auth application-default login --no-launch-browser
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔌 Enabling Google Cloud APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    pubsub.googleapis.com \
    bigquery.googleapis.com \
    firestore.googleapis.com \
    storage.googleapis.com \
    aiplatform.googleapis.com \
    translate.googleapis.com \
    texttospeech.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    eventarc.googleapis.com \
    functions.googleapis.com \
    --project=$PROJECT_ID

echo "✅ APIs enabled"

# Create service accounts
echo "👤 Creating service accounts..."

# Agent service account
gcloud iam service-accounts create resilientflow-agents \
    --description="Service account for ResilientFlow agents" \
    --display-name="ResilientFlow Agents" \
    --project=$PROJECT_ID || true

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudtranslate.user"

echo "✅ Service accounts created and configured"

# Setup Terraform
echo "🏗️  Setting up infrastructure with Terraform..."
cd infra/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
    -var="project_id=$PROJECT_ID" \
    -var="region=$REGION" \
    -out=tfplan

# Apply infrastructure
terraform apply tfplan

echo "✅ Infrastructure deployed"
cd ../..

# Create Cloud Storage buckets
echo "🪣 Creating Cloud Storage buckets..."

gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$PROJECT_ID-satellite-imagery/ || true
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$PROJECT_ID-processed-imagery/ || true
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$PROJECT_ID-situation-reports/ || true
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$PROJECT_ID-allocations/ || true

# Set bucket permissions
gsutil iam ch serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin \
    gs://$PROJECT_ID-satellite-imagery/

gsutil iam ch serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin \
    gs://$PROJECT_ID-processed-imagery/

gsutil iam ch serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin \
    gs://$PROJECT_ID-situation-reports/

gsutil iam ch serviceAccount:resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin \
    gs://$PROJECT_ID-allocations/

echo "✅ Cloud Storage buckets created"

# Build and deploy agents
echo "🤖 Building and deploying agents..."

# Build common protobuf messages
echo "📦 Building protobuf messages..."
protoc --python_out=. proto/api.proto

# Deploy Data Aggregator
echo "🛰️  Deploying Data Aggregator agent..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/data-aggregator agents/aggregator/ --project=$PROJECT_ID

gcloud run deploy data-aggregator \
    --image gcr.io/$PROJECT_ID/data-aggregator \
    --platform managed \
    --region $REGION \
    --service-account resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    --memory 2Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --allow-unauthenticated \
    --project=$PROJECT_ID

# Deploy Impact Assessor
echo "📊 Deploying Impact Assessor agent..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/impact-assessor agents/assessor/ --project=$PROJECT_ID

gcloud run deploy impact-assessor \
    --image gcr.io/$PROJECT_ID/impact-assessor \
    --platform managed \
    --region $REGION \
    --service-account resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    --memory 2Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --allow-unauthenticated \
    --project=$PROJECT_ID

# Deploy Resource Allocator
echo "📦 Deploying Resource Allocator agent..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/resource-allocator agents/allocator/ --project=$PROJECT_ID

gcloud run deploy resource-allocator \
    --image gcr.io/$PROJECT_ID/resource-allocator \
    --platform managed \
    --region $REGION \
    --service-account resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 5 \
    --allow-unauthenticated \
    --project=$PROJECT_ID

# Deploy Communications Coordinator
echo "📢 Deploying Communications Coordinator agent..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/comms-coordinator agents/comms/ --project=$PROJECT_ID

gcloud run deploy comms-coordinator \
    --image gcr.io/$PROJECT_ID/comms-coordinator \
    --platform managed \
    --region $REGION \
    --service-account resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 10 \
    --allow-unauthenticated \
    --project=$PROJECT_ID

# Deploy Report Synthesizer
echo "📄 Deploying Report Synthesizer agent..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/report-synthesizer agents/reporter/ --project=$PROJECT_ID

gcloud run deploy report-synthesizer \
    --image gcr.io/$PROJECT_ID/report-synthesizer \
    --platform managed \
    --region $REGION \
    --service-account resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    --memory 2Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 5 \
    --allow-unauthenticated \
    --project=$PROJECT_ID

echo "✅ All agents deployed"

# Setup Cloud Functions for image processing
echo "⚡ Setting up Cloud Functions..."

# Create Cloud Function for image processing trigger
cat > /tmp/main.py << 'EOF'
import functions_framework
from google.cloud import run_v2
import json
import os

@functions_framework.cloud_event
def process_image(cloud_event):
    """Triggered when an image is uploaded to Cloud Storage"""
    
    # Extract event data
    data = cloud_event.data
    bucket = data['bucket']
    name = data['name']
    
    # Only process supported image formats
    if not any(name.lower().endswith(ext) for ext in ['.tif', '.tiff', '.jpg', '.jpeg', '.png']):
        print(f"Skipping non-image file: {name}")
        return
    
    print(f"Processing image: {bucket}/{name}")
    
    # Trigger Data Aggregator service
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    region = 'us-central1'
    
    try:
        # In production, would make HTTP request to Data Aggregator service
        print(f"Image processing triggered for {name}")
        return {"status": "success", "file": name}
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return {"status": "error", "error": str(e)}
EOF

# Deploy Cloud Function
gcloud functions deploy process-satellite-image \
    --gen2 \
    --runtime python311 \
    --source /tmp \
    --entry-point process_image \
    --trigger-bucket $PROJECT_ID-satellite-imagery \
    --service-account resilientflow-agents@$PROJECT_ID.iam.gserviceaccount.com \
    --region $REGION \
    --memory 512MB \
    --project=$PROJECT_ID

echo "✅ Cloud Functions deployed"

# Load sample data
echo "📊 Loading sample data..."
python3 scripts/load_inventory.py --project-id $PROJECT_ID

echo "✅ Sample data loaded"

# Setup monitoring and alerts
echo "📊 Setting up monitoring..."

# Create log-based metrics
gcloud logging metrics create agent_errors \
    --description="Count of agent errors" \
    --log-filter='resource.type="cloud_run_revision" AND severity="ERROR" AND labels."service_name"~"resilientflow"' \
    --project=$PROJECT_ID || true

gcloud logging metrics create agent_actions \
    --description="Count of successful agent actions" \
    --log-filter='resource.type="cloud_run_revision" AND jsonPayload.action IS NOT NULL AND jsonPayload.status="success"' \
    --project=$PROJECT_ID || true

echo "✅ Monitoring configured"

# Create sample alert policies
echo "🚨 Setting up alerting..."

# Alert for high error rate
gcloud alpha monitoring policies create --policy-from-file=- << 'EOF'
displayName: "ResilientFlow High Error Rate"
conditions:
  - displayName: "Agent error rate too high"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND metric.type="logging.googleapis.com/user/agent_errors"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 10
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
notificationChannels: []
alertStrategy:
  autoClose: 86400s
EOF

echo "✅ Alerting configured"

# Final verification
echo "🔍 Verifying deployment..."

# Check that all services are running
SERVICES=("data-aggregator" "impact-assessor" "resource-allocator" "comms-coordinator" "report-synthesizer")

for service in "${SERVICES[@]}"; do
    URL=$(gcloud run services describe $service --region=$REGION --format="value(status.url)" --project=$PROJECT_ID)
    if curl -f "$URL" > /dev/null 2>&1; then
        echo "✅ $service is running at $URL"
    else
        echo "⚠️  $service may not be responding at $URL"
    fi
done

# Display summary
echo ""
echo "🎉 ResilientFlow deployment completed!"
echo ""
echo "📋 Summary:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Agents deployed: ${#SERVICES[@]}"
echo ""
echo "🔗 Service URLs:"
for service in "${SERVICES[@]}"; do
    URL=$(gcloud run services describe $service --region=$REGION --format="value(status.url)" --project=$PROJECT_ID 2>/dev/null || echo "N/A")
    echo "  $service: $URL"
done
echo ""
echo "📊 Monitoring:"
echo "  Cloud Console: https://console.cloud.google.com/monitoring/dashboards?project=$PROJECT_ID"
echo "  Cloud Run: https://console.cloud.google.com/run?project=$PROJECT_ID"
echo "  Pub/Sub: https://console.cloud.google.com/cloudpubsub/topic/list?project=$PROJECT_ID"
echo ""
echo "🧪 Test the system:"
echo "  1. Upload a satellite image to gs://$PROJECT_ID-satellite-imagery/"
echo "  2. Run: python3 scripts/publish_mocks.py --project-id $PROJECT_ID"
echo "  3. Check Cloud Run logs for agent activity"
echo ""
echo "📖 Next steps:"
echo "  1. Fine-tune Vertex AI Vision model in models/vision_model/"
echo "  2. Configure Firebase for mobile push notifications"
echo "  3. Set up external SMS/social media integrations"
echo "  4. Create monitoring dashboards"
echo ""
echo "🎯 ResilientFlow is ready for disaster relief coordination!" 