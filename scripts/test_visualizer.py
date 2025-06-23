#!/usr/bin/env python3
"""
Test script for ResilientFlow Visualizer Integration
Demonstrates the workflow with mock Pub/Sub events for the visualizer
"""

import os
import sys
import asyncio
import json
from datetime import datetime

# Add the workspace to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Pub/Sub events for testing
MOCK_PUBSUB_EVENTS = []

class MockPubSubClient:
    """Mock Pub/Sub client that stores events for testing"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.topic_path = f'projects/{project_id}/topics/rf-visualizer-events'
    
    def publish_json_message(self, data: dict):
        """Mock publish that stores events"""
        MOCK_PUBSUB_EVENTS.append({
            "timestamp": datetime.now().isoformat(),
            "topic": self.topic_path,
            "data": data
        })
        print(f"📡 VISUALIZER EVENT: {data.get('event_type')} - {data.get('step_name')}")
        return "mock_message_id"

# Patch the orchestrator to use mock Pub/Sub
def patch_orchestrator_for_testing():
    """Patch the orchestrator to use mock Pub/Sub for testing"""
    # Import and patch the orchestrator module
    import orchestrator
    
    # Replace the SimplePubSubClient class with our mock
    orchestrator.SimplePubSubClient = MockPubSubClient
    
    # Also patch the PUBSUB_AVAILABLE flag
    orchestrator.PUBSUB_AVAILABLE = True
    
    print("✅ Patched orchestrator to use mock Pub/Sub for visualizer events")

async def test_workflow_with_visualizer():
    """Test the complete workflow with visualizer events"""
    
    print("🌪️ ResilientFlow Visualizer Integration Test")
    print("=" * 50)
    
    # Patch the orchestrator
    patch_orchestrator_for_testing()
    
    # Import after patching
    from orchestrator import DisasterResponseAgent, handle_disaster_event
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Hurricane Harvey",
            "event_data": {
                "event_type": "hurricane",
                "location": "Houston, TX",
                "severity": 85,
                "affected_population": 2300000,
                "satellite_image": "mock_hurricane_data.tiff"
            }
        },
        {
            "name": "Wildfire Camp Fire", 
            "event_data": {
                "event_type": "wildfire",
                "location": "Paradise, CA",
                "severity": 92,
                "affected_population": 26800,
                "satellite_image": "mock_wildfire_data.tiff"
            }
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🔥 Test Scenario {i}: {scenario['name']}")
        print("-" * 40)
        
        # Clear previous events
        MOCK_PUBSUB_EVENTS.clear()
        
        # Run workflow using the handle_disaster_event function
        start_time = datetime.now()
        try:
            result = await handle_disaster_event(scenario["event_data"])
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            print(f"\n✅ Workflow completed in {execution_time:.1f}s")
            print(f"📊 Severity: {result.get('impact_assessment', {}).get('overall_severity', 0)}")
            print(f"🚚 Resources: {result.get('allocation_plan', {}).get('total_resources', 0)}")
            print(f"📢 Alerts: {result.get('communications_result', {}).get('alerts_sent', 0)}")
            
            print(f"\n📡 Visualizer Events Generated: {len(MOCK_PUBSUB_EVENTS)}")
            for event in MOCK_PUBSUB_EVENTS:
                data = event["data"]
                print(f"  • {data.get('event_type')} - {data.get('step_name')}")
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            
        print("\n" + "=" * 50)

def print_visualizer_setup_instructions():
    """Print instructions for setting up the visualizer"""
    
    print("\n🎨 Visualizer Setup Instructions")
    print("=" * 50)
    print("1. Install visualizer dependencies:")
    print("   pip install streamlit networkx matplotlib google-cloud-pubsub")
    print()
    print("2. Start the visualizer:")
    print("   streamlit run visualizer/app.py")
    print()
    print("3. Configure in the sidebar:")
    print(f"   - GCP Project ID: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0768345181')}")
    print("   - Pub/Sub Subscription: rf-visualizer-events-sub")
    print()
    print("4. Run disaster scenarios to see real-time visualization!")
    print("   python scripts/quick_demo.py")
    print()
    print("🔗 The visualizer will show agent interactions in real-time")
    print("   as workflows execute.")

if __name__ == "__main__":
    print("🚀 Starting ResilientFlow Visualizer Integration Test")
    
    # Run the test
    asyncio.run(test_workflow_with_visualizer())
    
    # Print setup instructions
    print_visualizer_setup_instructions()
    
    print("\n✅ Visualizer integration test completed!")
    print("🎯 Ready for Hour 4-7: Live Communications integration") 