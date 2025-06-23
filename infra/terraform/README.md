# ResilientFlow Terraform Infrastructure

## Overview

This Terraform configuration provides production-ready infrastructure-as-code for the complete ResilientFlow disaster response system on Google Cloud Platform.

## What It Creates

### Core Infrastructure
- **BigQuery Dataset**: `resilientflow` with specialized tables
  - `impact_assessments` - Individual damage assessments  
  - `impact_zones` - Aggregated severity zones
  - `heat_map_tiles` - Visualization data
- **Firestore Database**: Real-time data storage
- **Pub/Sub System**: 5 topics + 9 agent-specific subscriptions
- **Cloud Storage**: Buckets for reports and artifacts
- **VPC Network**: Dedicated networking (optional)

### Services & Monitoring  
- **API Enablement**: 13 required Google Cloud APIs
- **IAM**: Service accounts with least-privilege access
- **Cloud Scheduler**: Periodic report generation
- **Monitoring**: Error alerts and log-based metrics
- **Dead Letter Queues**: Message retry handling

## When to Use

### Use Terraform When:
✅ **Production deployment** - Full infrastructure management  
✅ **Team environments** - Consistent multi-developer setup  
✅ **Infrastructure changes** - Modify/version infrastructure  
✅ **Compliance requirements** - Auditable infrastructure  

### Use Manual Deployment When:
🚀 **Demo/prototype** - Quick deployment for testing  
🚀 **Time constraints** - Need working system immediately  
🚀 **Simple setup** - Single developer, temporary use  

## Quick Start

```bash
# Set your project
export TF_VAR_project_id="your-project-id"

# Initialize Terraform
cd infra/terraform
terraform init

# Plan deployment
terraform plan

# Deploy infrastructure
terraform apply
```

## Current Demo Status

For the current demo submission, the system is deployed using:
- ✅ **Manual Cloud Run deployment** - Working services  
- ✅ **Basic Pub/Sub setup** - Essential messaging
- ✅ **Streamlit Command Center** - Interactive dashboard

The Terraform config is **ready for production** when you need full infrastructure management.

## Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `project_id` | Google Cloud Project ID | Required |
| `region` | Deployment region | `us-central1` |
| `zone` | Deployment zone | `us-central1-a` |

## Outputs

After deployment, Terraform provides:
- **BigQuery dataset ID**
- **Pub/Sub topic names** 
- **Service URLs**
- **Monitoring endpoints**

## Cost Estimation

Production deployment costs:
- **Cloud Run**: ~$20-50/month (based on usage)
- **BigQuery**: ~$5-20/month (1GB storage + queries)
- **Pub/Sub**: ~$1-5/month (messaging)
- **Firestore**: ~$1-10/month (documents + operations)
- **Monitoring**: ~$0-5/month (basic alerts)

**Total**: ~$30-90/month for moderate production usage

## Next Steps

1. **Demo Complete** ✅ - Manual deployment working
2. **Production Migration** - Use this Terraform config
3. **CI/CD Integration** - Automate infrastructure updates
4. **Multi-environment** - Dev/staging/prod environments 