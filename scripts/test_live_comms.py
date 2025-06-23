#!/usr/bin/env python3
"""
Test script for ResilientFlow Live Communications Integration
Demonstrates both mock and live Slack/Twilio emergency alerts
"""

import os
import sys
import asyncio
from datetime import datetime

# Add the workspace to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_communications_mock_mode():
    """Test communications in mock mode (default)"""
    
    print("📢 Testing Communications - MOCK MODE")
    print("=" * 50)
    
    # Import after setting up path
    from agents.comms_tool import coordinate_communications
    
    # Mock allocation plan
    test_allocation = {
        "total_resources": 25,
        "disaster_type": "hurricane",
        "severity": "high",
        "allocations": [
            {"location": "Houston", "resources": 10},
            {"location": "Galveston", "resources": 8},
            {"location": "Beaumont", "resources": 7}
        ]
    }
    
    start_time = datetime.now()
    
    try:
        result = await coordinate_communications(
            allocation_plan=test_allocation,
            project_id="gen-lang-client-0768345181"
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Communications completed in {execution_time:.1f}s")
        print(f"📧 Emergency Message: {result['emergency_message']}")
        print(f"🌍 Languages: {len(result['multilingual_alerts'])}")
        print(f"📡 Total Alerts: {result['alerts_sent']:,}")
        print(f"📱 Channels: {result['channels_used']}")
        print(f"🔄 Live Mode: {result['live_mode']}")
        print(f"📞 Live Communications: {len(result['live_communications'])}")
        
        return result
        
    except Exception as e:
        print(f"❌ Communications test failed: {e}")
        return None

async def test_communications_live_mode():
    """Test communications in live mode (requires credentials)"""
    
    print("\n📢 Testing Communications - LIVE MODE")
    print("=" * 50)
    
    # Check if live credentials are available
    slack_webhook = os.environ.get('SLACK_WEBHOOK_URL')
    twilio_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    twilio_token = os.environ.get('TWILIO_AUTH_TOKEN')
    
    if not slack_webhook and not (twilio_sid and twilio_token):
        print("⚠️  No live credentials configured - skipping live test")
        print("To test live mode, set environment variables:")
        print("  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...")
        print("  TWILIO_ACCOUNT_SID=your_account_sid")
        print("  TWILIO_AUTH_TOKEN=your_auth_token")
        return None
    
    # Set live mode
    os.environ['USE_MOCK'] = '0'
    
    print(f"🔗 Slack Webhook: {'✅ Configured' if slack_webhook else '❌ Missing'}")
    print(f"📱 Twilio SMS: {'✅ Configured' if (twilio_sid and twilio_token) else '❌ Missing'}")
    
    # Import after setting environment
    from agents.comms_tool import coordinate_communications
    
    # Test allocation plan for live alerts
    test_allocation = {
        "total_resources": 15,
        "disaster_type": "wildfire",
        "severity": "critical",
        "allocations": [
            {"location": "Paradise", "resources": 8},
            {"location": "Chico", "resources": 7}
        ]
    }
    
    start_time = datetime.now()
    
    try:
        result = await coordinate_communications(
            allocation_plan=test_allocation,
            project_id="gen-lang-client-0768345181"
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Live communications completed in {execution_time:.1f}s")
        print(f"📧 Emergency Message: {result['emergency_message']}")
        print(f"🔄 Live Mode: {result['live_mode']}")
        print(f"📞 Live Communications Sent: {len(result['live_communications'])}")
        
        # Show live communication results
        for comm in result['live_communications']:
            platform = comm['platform']
            status = comm['status']
            if status == 'success':
                print(f"  ✅ {platform.upper()}: Message sent successfully")
            else:
                print(f"  ❌ {platform.upper()}: {comm.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Live communications test failed: {e}")
        return None
    
    finally:
        # Reset to mock mode
        os.environ['USE_MOCK'] = '1'

def print_setup_instructions():
    """Print instructions for setting up live communications"""
    
    print("\n🔧 Live Communications Setup Instructions")
    print("=" * 50)
    
    print("\n1. Slack Integration:")
    print("   • Create a Slack app at https://api.slack.com/apps")
    print("   • Add 'Incoming Webhooks' feature")
    print("   • Create webhook for your channel")
    print("   • Set environment variable:")
    print("     export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/....'")
    
    print("\n2. Twilio SMS Integration:")
    print("   • Sign up at https://www.twilio.com/")
    print("   • Get Account SID and Auth Token from Console")
    print("   • Set environment variables:")
    print("     export TWILIO_ACCOUNT_SID='your_account_sid'")
    print("     export TWILIO_AUTH_TOKEN='your_auth_token'")
    print("     export TWILIO_FROM_NUMBER='+1234567890'")
    
    print("\n3. Test Live Mode:")
    print("   • Set USE_MOCK=0 to enable live communications")
    print("   • Run: python scripts/test_live_comms.py")
    
    print("\n4. Integration with Orchestrator:")
    print("   • Live communications automatically trigger when USE_MOCK=0")
    print("   • Orchestrator will send both mock alerts AND live alerts")
    print("   • Perfect for demo scenarios with real notifications!")

async def main():
    """Main test function"""
    
    print("🚀 ResilientFlow Live Communications Integration Test")
    print("=" * 60)
    
    # Test mock mode first
    mock_result = await test_communications_mock_mode()
    
    # Test live mode if credentials available
    live_result = await test_communications_live_mode()
    
    # Print setup instructions
    print_setup_instructions()
    
    print(f"\n✅ Live Communications integration test completed!")
    print("🎯 Ready for Hour 7-9: Streamlit Command Center")

if __name__ == "__main__":
    asyncio.run(main()) 