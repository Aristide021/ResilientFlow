# ResilientFlow Infrastructure
# Terraform configuration for Google Cloud resources
#
# PRODUCTION-READY INFRASTRUCTURE-AS-CODE
# ========================================
# This configuration provides complete infrastructure management for ResilientFlow.
# 
# CURRENT STATUS: Not used for demo deployment (manual deployment working)
# FUTURE USE: Production environment with full infrastructure management
#
# For demo/development, use: scripts/deploy.ps1 or manual Cloud Run deployment
# For production, use: terraform apply (this file)

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Google Cloud Zone"
  type        = string
  default     = "us-central1-a"
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Data sources
data "google_client_config" "current" {}

# BigQuery Dataset
resource "google_bigquery_dataset" "resilientflow" {
  dataset_id                  = "resilientflow"
  friendly_name              = "ResilientFlow Dataset"
  description                = "Dataset for disaster relief coordination data"
  location                   = "US"
  default_table_expiration_ms = 2592000000 # 30 days

  labels = {
    env     = "production"
    project = "resilientflow"
  }

  access {
    role          = "OWNER"
    user_by_email = data.google_client_config.current.access_token != "" ? "resilientflow-agents@${var.project_id}.iam.gserviceaccount.com" : null
  }

  access {
    role           = "READER"
    special_group  = "projectReaders"
  }

  access {
    role           = "WRITER"
    special_group  = "projectWriters"
  }
}

# BigQuery Tables
resource "google_bigquery_table" "impact_assessments" {
  dataset_id = google_bigquery_dataset.resilientflow.dataset_id
  table_id   = "impact_assessments"

  labels = {
    env = "production"
  }

  schema = jsonencode([
    {
      name = "assessment_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "latitude"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "longitude"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "grid_cell_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "severity_score"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "damage_type"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "confidence_scores"
      type = "JSON"
      mode = "NULLABLE"
    },
    {
      name = "assessed_timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "assessed_ms"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "source_agent"
      type = "STRING"
      mode = "REQUIRED"
    }
  ])
}

resource "google_bigquery_table" "impact_zones" {
  dataset_id = google_bigquery_dataset.resilientflow.dataset_id
  table_id   = "impact_zones"

  labels = {
    env = "production"
  }

  schema = jsonencode([
    {
      name = "zone_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "center_latitude"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "center_longitude"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "severity_score"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "affected_area_km2"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "damage_types"
      type = "STRING"
      mode = "REPEATED"
    },
    {
      name = "assessment_count"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "confidence"
      type = "FLOAT"
      mode = "REQUIRED"
    },
    {
      name = "last_updated"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "geojson_polygon"
      type = "STRING"
      mode = "NULLABLE"
    }
  ])
}

resource "google_bigquery_table" "heat_map_tiles" {
  dataset_id = google_bigquery_dataset.resilientflow.dataset_id
  table_id   = "heat_map_tiles"

  labels = {
    env = "production"
  }

  schema = jsonencode([
    {
      name = "tile_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "zoom_level"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "tile_x"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "tile_y"
      type = "INTEGER"
      mode = "REQUIRED"
    },
    {
      name = "severity_grid"
      type = "JSON"
      mode = "REQUIRED"
    },
    {
      name = "generated_timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "data_sources"
      type = "STRING"
      mode = "REPEATED"
    }
  ])
}

# Pub/Sub Topics
resource "google_pubsub_topic" "rf_agent_events" {
  name = "rf-agent-events"

  labels = {
    env     = "production"
    project = "resilientflow"
  }

  message_retention_duration = "604800s" # 7 days
}

resource "google_pubsub_topic" "rf_disaster_events" {
  name = "rf-disaster-events"

  labels = {
    env     = "production"
    project = "resilientflow"
  }

  message_retention_duration = "604800s"
}

resource "google_pubsub_topic" "rf_impact_updates" {
  name = "rf-impact-updates"

  labels = {
    env     = "production"
    project = "resilientflow"
  }

  message_retention_duration = "604800s"
}

resource "google_pubsub_topic" "rf_allocation_plans" {
  name = "rf-allocation-plans"

  labels = {
    env     = "production"
    project = "resilientflow"
  }

  message_retention_duration = "604800s"
}

resource "google_pubsub_topic" "rf_alert_broadcasts" {
  name = "rf-alert-broadcasts"

  labels = {
    env     = "production"
    project = "resilientflow"
  }

  message_retention_duration = "604800s"
}

# Pub/Sub Subscriptions for each agent
resource "google_pubsub_subscription" "data_aggregator_disaster_events" {
  name  = "rf-data_aggregator-disaster_events"
  topic = google_pubsub_topic.rf_disaster_events.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.rf_agent_events.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_subscription" "impact_assessor_disaster_events" {
  name  = "rf-impact_assessor-disaster_events"
  topic = google_pubsub_topic.rf_disaster_events.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60
}

resource "google_pubsub_subscription" "impact_assessor_impact_updates" {
  name  = "rf-impact_assessor-impact_updates"
  topic = google_pubsub_topic.rf_impact_updates.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60
}

resource "google_pubsub_subscription" "resource_allocator_impact_updates" {
  name  = "rf-resource_allocator-impact_updates"
  topic = google_pubsub_topic.rf_impact_updates.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60
}

resource "google_pubsub_subscription" "resource_allocator_disaster_events" {
  name  = "rf-resource_allocator-disaster_events"
  topic = google_pubsub_topic.rf_disaster_events.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60
}

resource "google_pubsub_subscription" "comms_coordinator_disaster_events" {
  name  = "rf-comms_coordinator-disaster_events"
  topic = google_pubsub_topic.rf_disaster_events.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60
}

resource "google_pubsub_subscription" "comms_coordinator_impact_updates" {
  name  = "rf-comms_coordinator-impact_updates"
  topic = google_pubsub_topic.rf_impact_updates.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60
}

resource "google_pubsub_subscription" "comms_coordinator_allocation_plans" {
  name  = "rf-comms_coordinator-allocation_plans"
  topic = google_pubsub_topic.rf_allocation_plans.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60
}

resource "google_pubsub_subscription" "report_synthesizer_allocation_plans" {
  name  = "rf-report_synthesizer-allocation_plans"
  topic = google_pubsub_topic.rf_allocation_plans.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60
}

resource "google_pubsub_subscription" "report_synthesizer_impact_updates" {
  name  = "rf-report_synthesizer-impact_updates"
  topic = google_pubsub_topic.rf_impact_updates.name

  message_retention_duration = "604800s"
  retain_acked_messages      = false
  ack_deadline_seconds       = 60
}

# Firestore Database
resource "google_firestore_database" "resilientflow" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [
    google_project_service.firestore
  ]
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "bigquery.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
    "translate.googleapis.com",
    "texttospeech.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "eventarc.googleapis.com",
    "functions.googleapis.com"
  ])

  project = var.project_id
  service = each.value

  disable_dependent_services = false
  disable_on_destroy        = false
}

# Separate resource for Firestore API
resource "google_project_service" "firestore" {
  project = var.project_id
  service = "firestore.googleapis.com"

  disable_dependent_services = false
  disable_on_destroy        = false
}

# VPC Network (optional - using default for simplicity)
resource "google_compute_network" "resilientflow_vpc" {
  name                    = "resilientflow-vpc"
  auto_create_subnetworks = true
  mtu                     = 1460

  depends_on = [
    google_project_service.required_apis
  ]
}

# Cloud Scheduler Jobs for periodic reports
resource "google_cloud_scheduler_job" "generate_reports" {
  name             = "generate-situation-reports"
  description      = "Generate periodic situation reports"
  schedule         = "0 */6 * * *" # Every 6 hours
  time_zone        = "UTC"
  attempt_deadline = "320s"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://report-synthesizer-${random_id.suffix.hex}-uc.a.run.app/generate-report"
    
    headers = {
      "Content-Type" = "application/json"
    }
    
    body = base64encode(jsonencode({
      "scheduled": true,
      "report_type": "periodic"
    }))
  }

  depends_on = [
    google_project_service.required_apis
  ]
}

# Random suffix for unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# Monitoring notification channel (email)
resource "google_monitoring_notification_channel" "email" {
  display_name = "ResilientFlow Email Alerts"
  type         = "email"
  
  labels = {
    email_address = "alerts@resilientflow.example.com" # Change this
  }
  
  force_delete = false
}

# Alert policy for agent errors
resource "google_monitoring_alert_policy" "agent_errors" {
  display_name = "ResilientFlow Agent Errors"
  combiner     = "OR"
  
  conditions {
    display_name = "Agent error rate too high"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/severity\" AND metric.label.severity=\"ERROR\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.name
  ]
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Outputs
output "project_id" {
  description = "Google Cloud Project ID"
  value       = var.project_id
}

output "region" {
  description = "Google Cloud Region"
  value       = var.region
}

output "bigquery_dataset" {
  description = "BigQuery dataset for ResilientFlow"
  value       = google_bigquery_dataset.resilientflow.dataset_id
}

output "pubsub_topics" {
  description = "Pub/Sub topics created"
  value = {
    agent_events      = google_pubsub_topic.rf_agent_events.name
    disaster_events   = google_pubsub_topic.rf_disaster_events.name
    impact_updates    = google_pubsub_topic.rf_impact_updates.name
    allocation_plans  = google_pubsub_topic.rf_allocation_plans.name
    alert_broadcasts  = google_pubsub_topic.rf_alert_broadcasts.name
  }
} 