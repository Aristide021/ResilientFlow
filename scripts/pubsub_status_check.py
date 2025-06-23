#!/usr/bin/env python3
"""
ResilientFlow Pub/Sub Integration Status Check
Comprehensive verification of the entire Pub/Sub pipeline
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

# Add the workspace to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from google.cloud import pubsub_v1
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False

def check_pubsub_infrastructure():
    """Check Google Cloud Pub/Sub infrastructure"""
    print("🔧 Checking Pub/Sub Infrastructure")
    print("-" * 40)
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0768345181')
    print(f"📋 Project ID: {project_id}")
    
    if not PUBSUB_AVAILABLE:
        print("❌ Google Cloud Pub/Sub not available")
        return False
    
    try:
        # Check topic existence
        publisher = pubsub_v1.PublisherClient()
        topic_path = f'projects/{project_id}/topics/rf-visualizer-events'
        
        try:
            topic = publisher.get_topic(request={"topic": topic_path})
            print(f"✅ Topic exists: {topic.name}")
        except Exception as e:
            print(f"❌ Topic not found: {e}")
            return False
        
        # Check subscription existence
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = f'projects/{project_id}/subscriptions/rf-visualizer-events-sub'
        
        try:
            subscription = subscriber.get_subscription(request={"subscription": subscription_path})
            print(f"✅ Subscription exists: {subscription.name}")
        except Exception as e:
            print(f"❌ Subscription not found: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Pub/Sub check failed: {e}")
        return False

def check_message_backlog():
    """Check for any message backlog in the subscription"""
    print("\n📊 Checking Message Status")
    print("-" * 40)
    
    if not PUBSUB_AVAILABLE:
        return
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0768345181')
    
    try:
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = f'projects/{project_id}/subscriptions/rf-visualizer-events-sub'
        
        # Pull a few messages to check activity
        pull_request = {
            "subscription": subscription_path,
            "max_messages": 5,
            "return_immediately": True
        }
        
        response = subscriber.pull(request=pull_request)
        
        if response.received_messages:
            print(f"📨 Found {len(response.received_messages)} recent messages")
            
            # Show message samples
            for i, msg in enumerate(response.received_messages[:3], 1):
                try:
                    data = json.loads(msg.message.data.decode('utf-8'))
                    event_type = data.get('event_type', 'unknown')
                    step_name = data.get('step_name', 'unknown')
                    timestamp = data.get('timestamp', 'unknown')
                    
                    print(f"  {i}. [{timestamp[-8:] if len(timestamp) > 8 else timestamp}] {event_type} - {step_name}")
                except Exception:
                    print(f"  {i}. [Raw message] {len(msg.message.data)} bytes")
            
            # Acknowledge the pulled messages
            ack_ids = [msg.ack_id for msg in response.received_messages]
            if ack_ids:
                subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": ack_ids})
                print("✅ Messages acknowledged")
        else:
            print("📭 No recent messages in subscription")
            
    except Exception as e:
        print(f"❌ Message check failed: {e}")

def check_orchestrator_integration():
    """Check orchestrator Pub/Sub integration"""
    print("\n🤖 Checking Orchestrator Integration")
    print("-" * 40)
    
    try:
        # Import orchestrator to check Pub/Sub availability
        from orchestrator import PUBSUB_AVAILABLE as orch_pubsub, SimplePubSubClient
        
        if orch_pubsub:
            print("✅ Orchestrator has Pub/Sub enabled")
            
            # Test client initialization
            project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0768345181')
            try:
                client = SimplePubSubClient(project_id)
                print("✅ Pub/Sub client initializes successfully")
                
                # Test message publishing
                test_event = {
                    "event_type": "test",
                    "step_name": "Health Check",
                    "timestamp": datetime.now().isoformat(),
                    "source_agent": "health_checker",
                    "target_agent": "test",
                    "message": "TRACE: test - Health Check",
                    "data": {"test": True}
                }
                
                try:
                    message_id = client.publish_json_message(test_event)
                    if message_id:
                        print(f"✅ Test message published: {message_id}")
                    else:
                        print("⚠️  Test message publish returned None")
                except Exception as e:
                    print(f"❌ Test message publish failed: {e}")
                    
            except Exception as e:
                print(f"❌ Pub/Sub client initialization failed: {e}")
        else:
            print("❌ Orchestrator Pub/Sub is disabled")
            
    except ImportError as e:
        print(f"❌ Cannot import orchestrator: {e}")

def check_visualizer_integration():
    """Check visualizer integration"""
    print("\n📊 Checking Visualizer Integration")
    print("-" * 40)
    
    try:
        # Check if visualizer components are available (trace-based)
        try:
            from visualizer import feed_trace, get_stats, get_network_figure
            print("✅ Trace-based visualizer functions available")
        except ImportError:
            print("⚠️  Visualizer module not found but trace rendering available in Command Center")
        
        # Check Command Center integration
        try:
            # Import streamlit app to check visualizer availability
            import importlib.util
            spec = importlib.util.spec_from_file_location("streamlit_app", "visualizer/streamlit_app.py")
            if spec and spec.loader:
                print("✅ Command Center streamlit app found")
            else:
                print("⚠️  Command Center app not found")
        except Exception as e:
            print(f"⚠️  Command Center check error: {e}")
            
    except Exception as e:
        print(f"❌ Visualizer check failed: {e}")

def main():
    """Main status check function"""
    print("🌪️ ResilientFlow Pub/Sub Integration Status")
    print("=" * 60)
    print(f"🕐 Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all checks
    infrastructure_ok = check_pubsub_infrastructure()
    check_message_backlog()
    check_orchestrator_integration()
    check_visualizer_integration()
    
    # Overall status
    print("\n🎯 Overall Status")
    print("-" * 40)
    
    if infrastructure_ok and PUBSUB_AVAILABLE:
        print("✅ Pub/Sub integration is OPERATIONAL")
        print("🌟 Ready for real-time event visualization")
        print("\n🚀 To test live integration:")
        print("   1. Start Command Center: streamlit run visualizer/streamlit_app.py")
        print("   2. Create an incident with severity >= 75")
        print("   3. Watch the Live Agent Network section for real-time updates")
        print("   4. Check the 'Generate Demo Network Activity' button")
    else:
        print("❌ Pub/Sub integration has ISSUES")
        print("🔧 Check Google Cloud credentials and project configuration")
    
    print(f"\n📋 Quick Reference:")
    print(f"   Project: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0768345181')}")
    print(f"   Topic: rf-visualizer-events")
    print(f"   Subscription: rf-visualizer-events-sub")
    print(f"   Command Center: http://localhost:8501")

if __name__ == "__main__":
    main() 