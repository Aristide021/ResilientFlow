# ResilientFlow Scripts Directory

## 🎯 Demo Scripts (Essential)

### Core Demo & Testing
- **`quick_demo.py`** - 3-minute demo script for judges ⭐
- **`system_health_check.py`** - Comprehensive system validation ⭐  
- **`smoke_test_e2e.py`** - End-to-end testing suite ⭐

### Data & Setup
- **`load_inventory.py`** - Load demo facilities and resources
- **`populate_demo_data.py`** - Populate Command Center with demo workflows
- **`publish_mocks.py`** - Generate mock disaster events for testing

### Status & Validation
- **`pubsub_status_check.py`** - Validate Pub/Sub integration
- **`test_command_center.py`** - Test Command Center functionality
- **`test_live_comms.py`** - Test live Slack/Twilio communications

## 🚀 Deployment Scripts

### Quick Deploy (For Demo)
- **`deploy.ps1`** - PowerShell deployment script for Windows

### Full Infrastructure (For Production)  
- **`bootstrap.sh`** - Bash deployment with Terraform
- **`bootstrap.ps1`** - PowerShell deployment with Terraform

## 🔧 Development Utilities

- **`protobuf_compile.sh`** - Compile protocol buffer definitions
- **`vertex_ai_setup.py`** - Setup AI models (future enhancement)

## 📋 Quick Start Guide

### For Judges/Demo:
```bash
# 1. Run comprehensive health check
python scripts/system_health_check.py

# 2. Start 3-minute demo
python scripts/quick_demo.py

# 3. Start Command Center
streamlit run visualizer/streamlit_app.py
```

### For Testing:
```bash
# Full system test
python scripts/smoke_test_e2e.py

# Communications test
python scripts/test_live_comms.py

# Load demo data
python scripts/load_inventory.py
```

### For Development:
```bash
# Deploy to cloud (Windows)
scripts/deploy.ps1

# Compile protobuf
scripts/protobuf_compile.sh

# Check Pub/Sub status  
python scripts/pubsub_status_check.py
```

## 🎮 Demo Scenarios

The scripts support these disaster scenarios:
- **Hurricane** (severity 85) - NYC area
- **Wildfire** (severity 92) - Los Angeles  
- **Earthquake** (severity 78) - San Francisco
- **Flood** (severity 65) - Various locations
- **Tornado** (severity 73) - Midwest

## 🏆 Judge Testing Workflow

1. **Health Check**: `python scripts/system_health_check.py`
2. **Quick Demo**: `python scripts/quick_demo.py` 
3. **Command Center**: `streamlit run visualizer/streamlit_app.py`
4. **Create Incident**: Use dashboard incident creator
5. **Watch Workflow**: See real-time trace visualization

## 📊 Performance Expectations

- **System Health Check**: ~30-60 seconds
- **Quick Demo**: ~2-3 minutes per scenario
- **Workflow Response**: ~7-8 seconds average
- **Command Center Startup**: ~10-15 seconds

All scripts are optimized for the 12-hour demo deadline! 🌪️ 