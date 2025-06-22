# ResilientFlow Bootstrap Deployment Script (PowerShell)
# Deploys complete ResilientFlow system to Google Cloud

param(
    [string]$ProjectId = $env:GOOGLE_CLOUD_PROJECT,
    [string]$Region = "us-central1"
)

if (-not $ProjectId) {
    Write-Host "❌ Please set GOOGLE_CLOUD_PROJECT environment variable or provide -ProjectId parameter" -ForegroundColor Red
    exit 1
}

Write-Host "ResilientFlow Bootstrap Deployment" -ForegroundColor Cyan
Write-Host "=" * 50
Write-Host "Project: $ProjectId" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host ""

# Function to check command success
function Test-LastCommand {
    param([string]$Description)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Description" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "SUCCESS: $Description" -ForegroundColor Green
    }
}

# Step 1: Set project
Write-Host "Setting up Google Cloud project..." -ForegroundColor Blue
gcloud config set project $ProjectId
Test-LastCommand "Project configuration"

# Step 2: Enable APIs
Write-Host "🔌 Enabling required APIs..." -ForegroundColor Blue
$apis = @(
    "cloudbuild.googleapis.com",
    "run.googleapis.com", 
    "bigquery.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
    "translate.googleapis.com",
    "cloudscheduler.googleapis.com"
)

foreach ($api in $apis) {
    Write-Host "  • Enabling $api..."
    gcloud services enable $api
}
Test-LastCommand "API enablement"

# Step 3: Create service accounts
Write-Host "👤 Creating service accounts..." -ForegroundColor Blue

Write-Host "  • Creating resilientflow-agents service account..."
gcloud iam service-accounts create resilientflow-agents --display-name="ResilientFlow Agents" --description="Service account for ResilientFlow agent containers" 2>$null

Write-Host "  • Creating resilientflow-terraform service account..."
gcloud iam service-accounts create resilientflow-terraform --display-name="ResilientFlow Terraform" --description="Service account for Terraform infrastructure management" 2>$null

Test-LastCommand "Service account creation"

# Step 4: Assign IAM roles
Write-Host "🔐 Assigning IAM roles..." -ForegroundColor Blue

$agentEmail = "resilientflow-agents@$ProjectId.iam.gserviceaccount.com"
$roles = @(
    "roles/bigquery.dataEditor",
    "roles/datastore.user", 
    "roles/pubsub.editor",
    "roles/storage.objectAdmin",
    "roles/aiplatform.user",
    "roles/cloudtranslate.user",
    "roles/logging.logWriter"
)

foreach ($role in $roles) {
    Write-Host "  • Assigning $role to agents..."
    gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$agentEmail" --role="$role" | Out-Null
}
Test-LastCommand "IAM role assignment"

# Step 5: Create Firestore database
Write-Host "🗄️ Setting up Firestore..." -ForegroundColor Blue
try {
    gcloud firestore databases create --location="nam5" 2>$null
    Write-Host "✅ Firestore database created"
} catch {
    Write-Host "✅ Firestore database already exists"
}

# Step 6: Create BigQuery dataset
Write-Host "📊 Setting up BigQuery..." -ForegroundColor Blue
try {
    bq mk --dataset --location=US "$ProjectId`:resilientflow"
    Write-Host "✅ BigQuery dataset created"
} catch {
    Write-Host "✅ BigQuery dataset already exists"
}

# Create BigQuery tables
Write-Host "  • Creating BigQuery tables..."

$impactAssessmentsSchema = @"
assessment_id:STRING,latitude:FLOAT64,longitude:FLOAT64,grid_cell_id:STRING,severity_score:INT64,damage_type:STRING,confidence_scores:JSON,assessed_timestamp:TIMESTAMP,source_agent:STRING
"@

$impactZonesSchema = @"
zone_id:STRING,center_latitude:FLOAT64,center_longitude:FLOAT64,severity_score:FLOAT64,affected_area_km2:FLOAT64,damage_types:STRING,assessment_count:INT64,confidence:FLOAT64,last_updated:TIMESTAMP,geojson_polygon:STRING
"@

bq mk --table --time_partitioning_field=assessed_timestamp --clustering_fields=grid_cell_id,damage_type "$ProjectId`:resilientflow.impact_assessments" $impactAssessmentsSchema 2>$null

bq mk --table --time_partitioning_field=last_updated --clustering_fields=severity_score "$ProjectId`:resilientflow.impact_zones" $impactZonesSchema 2>$null

Test-LastCommand "BigQuery setup"

# Step 7: Create Pub/Sub topics and subscriptions
Write-Host "📡 Setting up Pub/Sub..." -ForegroundColor Blue

$topics = @(
    "rf-disaster-events",
    "rf-impact-updates", 
    "rf-allocation-plans",
    "rf-alert-broadcasts",
    "rf-agent-events"
)

foreach ($topic in $topics) {
    Write-Host "  • Creating topic: $topic"
    gcloud pubsub topics create $topic 2>$null
}

# Create subscriptions
Write-Host "  • Creating subscriptions..."
gcloud pubsub subscriptions create rf-disaster-events-aggregator --topic=rf-disaster-events 2>$null
gcloud pubsub subscriptions create rf-disaster-events-assessor --topic=rf-disaster-events 2>$null
gcloud pubsub subscriptions create rf-impact-updates-allocator --topic=rf-impact-updates 2>$null
gcloud pubsub subscriptions create rf-multi-coordinator --topic=rf-allocation-plans 2>$null
gcloud pubsub subscriptions create rf-all-events-reporter --topic=rf-agent-events 2>$null

Test-LastCommand "Pub/Sub setup"

# Step 8: Create Cloud Storage buckets
Write-Host "🪣 Creating Cloud Storage buckets..." -ForegroundColor Blue

$buckets = @(
    "$ProjectId-situation-reports",
    "$ProjectId-model-artifacts", 
    "$ProjectId-build-artifacts"
)

foreach ($bucket in $buckets) {
    Write-Host "  • Creating bucket: gs://$bucket"
    gsutil mb -l US "gs://$bucket" 2>$null
}
Test-LastCommand "Cloud Storage setup"

# Step 9: Build and deploy agents
Write-Host "🏗️ Building and deploying agents..." -ForegroundColor Blue

$agents = @(
    @{name="data-aggregator"; path="agents/aggregator"},
    @{name="impact-assessor"; path="agents/assessor"}, 
    @{name="resource-allocator"; path="agents/allocator"},
    @{name="comms-coordinator"; path="agents/comms"},
    @{name="report-synthesizer"; path="agents/reporter"}
)

foreach ($agent in $agents) {
    Write-Host "  🚀 Deploying $($agent.name)..." -ForegroundColor Cyan
    
    # Build container
    Write-Host "    • Building container image..."
    gcloud builds submit --tag "gcr.io/$ProjectId/$($agent.name)" -f "$($agent.path)/Dockerfile" .
    Test-LastCommand "Container build for $($agent.name)"
    
    # Deploy to Cloud Run
    Write-Host "    • Deploying to Cloud Run..."
    gcloud run deploy $agent.name `
        --image="gcr.io/$ProjectId/$($agent.name)" `
        --region=$Region `
        --platform=managed `
        --service-account="$agentEmail" `
        --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId" `
        --memory=2Gi `
        --cpu=1 `
        --min-instances=0 `
        --max-instances=10 `
        --allow-unauthenticated `
        --quiet
    Test-LastCommand "Cloud Run deployment for $($agent.name)"
}

# Step 10: Load inventory data
Write-Host "📦 Loading sample inventory data..." -ForegroundColor Blue
python scripts/load_inventory.py --project-id $ProjectId
Test-LastCommand "Inventory data loading"

# Step 11: Deploy visualizer
Write-Host "🎨 Deploying agent visualizer..." -ForegroundColor Blue

# Build visualizer container
gcloud builds submit --tag "gcr.io/$ProjectId/resilientflow-visualizer" visualizer/
Test-LastCommand "Visualizer container build"

# Deploy visualizer
gcloud run deploy resilientflow-visualizer `
    --image="gcr.io/$ProjectId/resilientflow-visualizer" `
    --region=$Region `
    --platform=managed `
    --allow-unauthenticated `
    --port=8501 `
    --memory=1Gi `
    --cpu=1 `
    --min-instances=0 `
    --max-instances=2 `
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId" `
    --quiet
Test-LastCommand "Visualizer deployment"

# Final verification
Write-Host "🧪 Running deployment verification..." -ForegroundColor Blue

Write-Host "  • Checking Cloud Run services..."
$services = gcloud run services list --region=$Region --format="value(metadata.name)" | Where-Object {$_ -like "*resilientflow*" -or $_ -like "*data-*" -or $_ -like "*impact-*" -or $_ -like "*resource-*" -or $_ -like "*comms-*" -or $_ -like "*report-*"}

if ($services.Count -ge 5) {
    Write-Host "✅ All agents deployed successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️ Some agents may not have deployed correctly" -ForegroundColor Yellow
}

# Get service URLs
Write-Host ""
Write-Host "🎉 ResilientFlow Deployment Complete!" -ForegroundColor Green
Write-Host "=" * 50

Write-Host "📋 Deployed Services:" -ForegroundColor Yellow
foreach ($service in $services) {
    $url = gcloud run services describe $service --region=$Region --format="value(status.url)" 2>$null
    if ($url) {
        Write-Host "  • $service`: $url" -ForegroundColor Cyan
    }
}

# Get visualizer URL
$visualizerUrl = gcloud run services describe "resilientflow-visualizer" --region=$Region --format="value(status.url)" 2>$null
if ($visualizerUrl) {
    Write-Host ""
    Write-Host "🎨 Visualizer: $visualizerUrl" -ForegroundColor Magenta
}

Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Test the system: python scripts/quick_demo.py $ProjectId"
Write-Host "  2. Open visualizer: $visualizerUrl"
Write-Host "  3. Run mock scenarios: python scripts/publish_mocks.py --project-id $ProjectId --scenario hurricane"
Write-Host ""
Write-Host "📊 Monitor at: https://console.cloud.google.com/run?project=$ProjectId" -ForegroundColor Blue
Write-Host ""

Write-Host "⚡ Ready for your 3-minute demo!" -ForegroundColor Green 