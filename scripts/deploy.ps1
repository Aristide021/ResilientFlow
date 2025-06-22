# ResilientFlow Deployment Script (PowerShell)
# Simplified version without Unicode characters

param(
    [string]$ProjectId = $env:GOOGLE_CLOUD_PROJECT,
    [string]$Region = "us-central1"
)

if (-not $ProjectId) {
    Write-Host "ERROR: Please set GOOGLE_CLOUD_PROJECT environment variable" -ForegroundColor Red
    exit 1
}

Write-Host "ResilientFlow Deployment Starting..." -ForegroundColor Cyan
Write-Host "Project: $ProjectId" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host ""

# Set project
Write-Host "Step 1: Setting Google Cloud project..." -ForegroundColor Blue
gcloud config set project $ProjectId
if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Project setup" -ForegroundColor Red
    exit 1 
}

# Enable APIs  
Write-Host "Step 2: Enabling APIs..." -ForegroundColor Blue
gcloud services enable cloudbuild.googleapis.com run.googleapis.com bigquery.googleapis.com pubsub.googleapis.com firestore.googleapis.com storage.googleapis.com
if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: API enablement" -ForegroundColor Red
    exit 1 
}

# Create service account
Write-Host "Step 3: Creating service account..." -ForegroundColor Blue
gcloud iam service-accounts create resilientflow-agents --display-name="ResilientFlow Agents" 2>$null
$agentEmail = "resilientflow-agents@$ProjectId.iam.gserviceaccount.com"

# Assign roles
Write-Host "Step 4: Assigning IAM roles..." -ForegroundColor Blue
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$agentEmail" --role="roles/bigquery.dataEditor" | Out-Null
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$agentEmail" --role="roles/datastore.user" | Out-Null
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$agentEmail" --role="roles/pubsub.editor" | Out-Null
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$agentEmail" --role="roles/storage.objectAdmin" | Out-Null

# Create Firestore database
Write-Host "Step 5: Setting up Firestore..." -ForegroundColor Blue
gcloud firestore databases create --location="nam5" 2>$null

# Create BigQuery dataset
Write-Host "Step 6: Setting up BigQuery..." -ForegroundColor Blue
bq mk --dataset --location=US "$ProjectId`:resilientflow" 2>$null

# Create tables
bq mk --table "$ProjectId`:resilientflow.impact_assessments" assessment_id:STRING,latitude:FLOAT64,longitude:FLOAT64,severity_score:INT64,damage_type:STRING,assessed_timestamp:TIMESTAMP 2>$null
bq mk --table "$ProjectId`:resilientflow.impact_zones" zone_id:STRING,center_latitude:FLOAT64,center_longitude:FLOAT64,severity_score:FLOAT64,last_updated:TIMESTAMP 2>$null

# Create Pub/Sub topics
Write-Host "Step 7: Setting up Pub/Sub..." -ForegroundColor Blue
gcloud pubsub topics create rf-disaster-events 2>$null
gcloud pubsub topics create rf-impact-updates 2>$null
gcloud pubsub topics create rf-allocation-plans 2>$null
gcloud pubsub topics create rf-agent-events 2>$null

# Create subscriptions
gcloud pubsub subscriptions create rf-disaster-events-aggregator --topic=rf-disaster-events 2>$null
gcloud pubsub subscriptions create rf-impact-updates-allocator --topic=rf-impact-updates 2>$null
gcloud pubsub subscriptions create rf-all-events-reporter --topic=rf-agent-events 2>$null

# Create storage buckets
Write-Host "Step 8: Creating storage buckets..." -ForegroundColor Blue
gsutil mb -l US "gs://$ProjectId-situation-reports" 2>$null
gsutil mb -l US "gs://$ProjectId-model-artifacts" 2>$null

# Build and deploy first agent (data aggregator)
Write-Host "Step 9: Building and deploying data aggregator..." -ForegroundColor Blue
# Copy Dockerfile to root temporarily for Cloud Build context
Copy-Item "agents/aggregator/Dockerfile" "Dockerfile.aggregator"
gcloud builds submit --tag "gcr.io/$ProjectId/data-aggregator" --file "Dockerfile.aggregator" .
Remove-Item "Dockerfile.aggregator"

if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Data aggregator build" -ForegroundColor Red
    exit 1 
}

gcloud run deploy data-aggregator --image="gcr.io/$ProjectId/data-aggregator" --region=$Region --platform=managed --service-account="$agentEmail" --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId" --memory=2Gi --allow-unauthenticated --quiet
if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Data aggregator deployment" -ForegroundColor Red
    exit 1 
}

Write-Host "SUCCESS: Data aggregator deployed!" -ForegroundColor Green

# Build and deploy impact assessor
Write-Host "Step 10: Building and deploying impact assessor..." -ForegroundColor Blue
Copy-Item "agents/assessor/Dockerfile" "Dockerfile.assessor"
gcloud builds submit --tag "gcr.io/$ProjectId/impact-assessor" --file "Dockerfile.assessor" .
Remove-Item "Dockerfile.assessor"

if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Impact assessor build" -ForegroundColor Red
    exit 1 
}

gcloud run deploy impact-assessor --image="gcr.io/$ProjectId/impact-assessor" --region=$Region --platform=managed --service-account="$agentEmail" --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId" --memory=2Gi --allow-unauthenticated --quiet
if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Impact assessor deployment" -ForegroundColor Red
    exit 1 
}

Write-Host "SUCCESS: Impact assessor deployed!" -ForegroundColor Green

# Build and deploy resource allocator
Write-Host "Step 11: Building and deploying resource allocator..." -ForegroundColor Blue
Copy-Item "agents/allocator/Dockerfile" "Dockerfile.allocator"
gcloud builds submit --tag "gcr.io/$ProjectId/resource-allocator" --file "Dockerfile.allocator" .
Remove-Item "Dockerfile.allocator"

if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Resource allocator build" -ForegroundColor Red
    exit 1 
}

gcloud run deploy resource-allocator --image="gcr.io/$ProjectId/resource-allocator" --region=$Region --platform=managed --service-account="$agentEmail" --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId" --memory=2Gi --allow-unauthenticated --quiet
if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Resource allocator deployment" -ForegroundColor Red
    exit 1 
}

Write-Host "SUCCESS: Resource allocator deployed!" -ForegroundColor Green

# Build and deploy communications coordinator
Write-Host "Step 12: Building and deploying communications coordinator..." -ForegroundColor Blue
Copy-Item "agents/comms/Dockerfile" "Dockerfile.comms"
gcloud builds submit --tag "gcr.io/$ProjectId/comms-coordinator" --file "Dockerfile.comms" .
Remove-Item "Dockerfile.comms"

if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Comms coordinator build" -ForegroundColor Red
    exit 1 
}

gcloud run deploy comms-coordinator --image="gcr.io/$ProjectId/comms-coordinator" --region=$Region --platform=managed --service-account="$agentEmail" --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId" --memory=1Gi --allow-unauthenticated --quiet
if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Comms coordinator deployment" -ForegroundColor Red
    exit 1 
}

Write-Host "SUCCESS: Communications coordinator deployed!" -ForegroundColor Green

# Build and deploy report synthesizer
Write-Host "Step 13: Building and deploying report synthesizer..." -ForegroundColor Blue
Copy-Item "agents/reporter/Dockerfile" "Dockerfile.reporter"
gcloud builds submit --tag "gcr.io/$ProjectId/report-synthesizer" --file "Dockerfile.reporter" .
Remove-Item "Dockerfile.reporter"

if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Report synthesizer build" -ForegroundColor Red
    exit 1 
}

gcloud run deploy report-synthesizer --image="gcr.io/$ProjectId/report-synthesizer" --region=$Region --platform=managed --service-account="$agentEmail" --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId" --memory=2Gi --allow-unauthenticated --quiet
if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Report synthesizer deployment" -ForegroundColor Red
    exit 1 
}

Write-Host "SUCCESS: Report synthesizer deployed!" -ForegroundColor Green

# Deploy visualizer
Write-Host "Step 14: Building and deploying visualizer..." -ForegroundColor Blue
Set-Location visualizer
gcloud builds submit --tag "gcr.io/$ProjectId/resilientflow-visualizer" .
Set-Location ..
if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Visualizer build" -ForegroundColor Red
    exit 1 
}

gcloud run deploy resilientflow-visualizer --image="gcr.io/$ProjectId/resilientflow-visualizer" --region=$Region --platform=managed --allow-unauthenticated --port=8501 --memory=1Gi --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId" --quiet
if ($LASTEXITCODE -ne 0) { 
    Write-Host "FAILED: Visualizer deployment" -ForegroundColor Red
    exit 1 
}

Write-Host "SUCCESS: Visualizer deployed!" -ForegroundColor Green

# Load sample data
Write-Host "Step 15: Loading sample inventory data..." -ForegroundColor Blue
python scripts/load_inventory.py --project-id $ProjectId
if ($LASTEXITCODE -ne 0) { 
    Write-Host "WARNING: Inventory loading failed (optional)" -ForegroundColor Yellow
}

# Get deployment URLs
Write-Host ""
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green

$visualizerUrl = gcloud run services describe "resilientflow-visualizer" --region=$Region --format="value(status.url)" 2>$null
if ($visualizerUrl) {
    Write-Host "Visualizer URL: $visualizerUrl" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Open visualizer: $visualizerUrl"
Write-Host "2. Test system: python scripts/quick_demo.py $ProjectId"
Write-Host "3. Monitor: https://console.cloud.google.com/run?project=$ProjectId"
Write-Host ""
Write-Host "Ready for your demo!" -ForegroundColor Green 