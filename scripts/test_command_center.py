#!/usr/bin/env python3
"""
Test script for ResilientFlow Streamlit Command Center
Demonstrates the web-based dashboard functionality
"""

import os
import sys
import subprocess
import time
import webbrowser
from datetime import datetime

# Add the workspace to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add visualizer to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "visualizer"))

def test_command_center_startup():
    """Test that the command center can start up"""
    
    print("🌪️ ResilientFlow Command Center Test")
    print("=" * 50)
    
    # Test imports
    try:
        import streamlit
        print("✅ Streamlit installed and ready")
    except ImportError:
        print("❌ Streamlit not installed")
        return False
    
    try:
        import plotly
        print("✅ Plotly installed for visualizations")
    except ImportError:
        print("❌ Plotly not installed")
        return False
    
    try:
        import streamlit_app
        print("✅ Command Center application imports successfully")
    except ImportError as e:
        print(f"❌ Command Center import failed: {e}")
        return False
    
    try:
        from orchestrator import handle_disaster_event
        print("✅ Orchestrator integration available")
    except ImportError:
        print("⚠️  Orchestrator not available - will run in demo mode")
    
    return True

def print_command_center_instructions():
    """Print instructions for running the command center"""
    
    print("\n🎛️ Command Center Startup Instructions")
    print("=" * 50)
    
    print("\n1. Start the Command Center:")
    print("   streamlit run visualizer/streamlit_app.py")
    print()
    print("2. Open your browser to:")
    print("   http://localhost:8501")
    print()
    print("3. Use the dashboard features:")
    print("   • Create emergency incidents")
    print("   • Monitor real-time workflows")
    print("   • View analytics and charts")
    print("   • Toggle mock/live modes")
    print("   • Test emergency alerts")
    print()
    print("4. Key Features:")
    print("   📊 Real-time metrics dashboard")
    print("   🆘 Emergency incident creator")
    print("   📈 Analytics and visualizations")
    print("   🎛️ Live communications controls")
    print("   📋 Workflow history tracking")
    print()
    print("5. Demo Scenarios:")
    print("   • Hurricane (severity 85)")
    print("   • Wildfire (severity 92)")
    print("   • Earthquake (severity 78)")
    print("   • Flood (severity 65)")
    print("   • Tornado (severity 73)")

def demo_command_center_features():
    """Demonstrate key command center features"""
    
    print("\n🎯 Command Center Features Demo")
    print("=" * 50)
    
    features = [
        {
            "name": "System Status Dashboard",
            "description": "Real-time status of all 5 agents (Aggregator, Assessor, Allocator, Comms, Reporter)",
            "icon": "🟢"
        },
        {
            "name": "Emergency Incident Creator", 
            "description": "Interactive form to create and trigger disaster response workflows",
            "icon": "🆘"
        },
        {
            "name": "Live Metrics Tracking",
            "description": "Real-time metrics: workflows, incidents, response time, resources deployed",
            "icon": "📊"
        },
        {
            "name": "Interactive Visualizations",
            "description": "Plotly charts showing incident distribution, response analysis, timelines",
            "icon": "📈"
        },
        {
            "name": "Communications Control Panel",
            "description": "Toggle between mock/live modes, configure Slack/Twilio integration",
            "icon": "📱"
        },
        {
            "name": "Workflow History Table",
            "description": "Complete history of executed workflows with filtering and search",
            "icon": "📋"
        },
        {
            "name": "Quick Action Buttons",
            "description": "Test alerts, system health checks, dashboard reset controls",
            "icon": "⚡"
        }
    ]
    
    for i, feature in enumerate(features, 1):
        print(f"{i}. {feature['icon']} **{feature['name']}**")
        print(f"   {feature['description']}")
        print()

def create_demo_data_script():
    """Create a script to populate the dashboard with demo data"""
    
    demo_script = """
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def populate_demo_data():
    '''Populate the command center with demo workflow data'''
    from orchestrator import handle_disaster_event
    
    demo_incidents = [
        {
            "event_type": "hurricane",
            "severity": 85,
            "location": "Miami, FL",
            "latitude": 25.7617,
            "longitude": -80.1918,
            "affected_population": 450000
        },
        {
            "event_type": "wildfire", 
            "severity": 92,
            "location": "Los Angeles, CA",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "affected_population": 75000
        },
        {
            "event_type": "earthquake",
            "severity": 78,
            "location": "San Francisco, CA", 
            "latitude": 37.7749,
            "longitude": -122.4194,
            "affected_population": 125000
        }
    ]
    
    print("Populating Command Center with demo data...")
    
    for i, incident in enumerate(demo_incidents, 1):
        print(f"Processing incident {i}/3: {incident['event_type']} in {incident['location']}")
        
        incident["event_id"] = f"demo_{incident['event_type']}_{i}"
        incident["timestamp"] = datetime.now().isoformat()
        incident["satellite_image"] = f"mock_{incident['event_type']}_data.tiff"
        
        try:
            result = await handle_disaster_event(incident)
            print(f"Completed: {result.get('resources_allocated', 0)} resources, {result.get('alerts_sent', 0)} alerts")
        except Exception as e:
            print(f"Failed: {e}")
    
    print("Demo data population complete!")

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(populate_demo_data())
"""
    
    with open("scripts/populate_demo_data.py", "w", encoding="utf-8") as f:
        f.write(demo_script)
    
    print("✅ Created demo data population script: scripts/populate_demo_data.py")

def main():
    """Main test function"""
    
    print("🚀 ResilientFlow Command Center Integration Test")
    print("=" * 60)
    
    # Test startup
    if not test_command_center_startup():
        print("❌ Command Center startup test failed")
        return
    
    # Demo features
    demo_command_center_features()
    
    # Create demo script
    create_demo_data_script()
    
    # Print instructions
    print_command_center_instructions()
    
    print("\n✅ Command Center integration test completed!")
    print("🎯 Ready for Hour 9-10: End-to-end smoke testing")
    
    # Offer to start the command center
    print("\n🚀 To start the Command Center now:")
    print("   streamlit run visualizer/streamlit_app.py")

if __name__ == "__main__":
    main() 