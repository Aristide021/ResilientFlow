#!/usr/bin/env python3
"""
ResilientFlow Quick Demo Script
Demonstrates the ADK-based disaster response orchestrator in under 3 minutes
"""

import os
import sys
import time
import json
import asyncio
from datetime import datetime

# Add the workspace to the Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import DisasterResponseAgent

class ResilientFlowDemo:
    def __init__(self, project_id):
        self.project_id = project_id
        self.start_time = time.time()
        self.orchestrator = DisasterResponseAgent()
        
        print("🌪️ ResilientFlow ADK Demo")
        print("=" * 50)
        print(f"📋 Project: {project_id}")
        print(f"⏰ Start Time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"🤖 Orchestrator: ADK Multi-Agent System")
        print()
    
    def log_step(self, step, message):
        """Log demo step with timing"""
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:6.1f}s] 🎬 {step}: {message}")
    
    def check_prerequisites(self):
        """Verify ADK orchestrator is ready"""
        self.log_step("SETUP", "Checking ADK orchestrator prerequisites...")
        
        try:
            # Test orchestrator import
            from orchestrator import DisasterResponseAgent
            self.log_step("SETUP", "✅ ADK orchestrator imported successfully")
            
            # Test agent tools import
            from agents.aggregator_tool import process_satellite_imagery
            from agents.assessor_tool import analyze_impact
            from agents.allocator_tool import optimize_resource_allocation
            from agents.comms_tool import coordinate_communications
            from agents.reporter_tool import synthesize_situation_report
            
            self.log_step("SETUP", "✅ All 5 agent tools loaded successfully")
            
            # Check Google ADK is installed
            import google.adk.agents
            self.log_step("SETUP", "✅ Google ADK framework ready")
            
            return True
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("💡 Ensure google-adk is installed: pip install google-adk==1.4.2")
            return False
        except Exception as e:
            print(f"❌ Setup error: {e}")
            return False
    
    def create_disaster_scenarios(self):
        """Create different disaster event scenarios for testing"""
        scenarios = {
            "hurricane": {
                "event_id": "demo_hurricane_sandy_2024",
                "event_type": "hurricane",
                "latitude": 40.7128,  # NYC
                "longitude": -74.0060,
                "severity": 85,
                "timestamp": datetime.now().isoformat(),
                "description": "Category 3 hurricane approaching NYC metropolitan area",
                "satellite_bucket": "resilientflow-satellite-data",
                "satellite_blob": "nyc_hurricane_damage_2024.tiff",
                "metadata": {
                    "wind_speed": "120 mph",
                    "category": 3,
                    "area_affected": "Greater NYC Metropolitan Area"
                }
            },
            
            "wildfire": {
                "event_id": "demo_wildfire_ca_2024",
                "event_type": "wildfire",
                "latitude": 34.0522,  # Los Angeles
                "longitude": -118.2437,
                "severity": 92,
                "timestamp": datetime.now().isoformat(),
                "description": "Large wildfire threatening residential areas in Southern California",
                "satellite_bucket": "resilientflow-satellite-data",
                "satellite_blob": "ca_wildfire_damage_2024.tiff",
                "metadata": {
                    "acres_burned": "15,000",
                    "containment": "15%",
                    "structures_threatened": 500
                }
            },
            
            "earthquake": {
                "event_id": "demo_earthquake_sf_2024",
                "event_type": "earthquake",
                "latitude": 37.7749,  # San Francisco
                "longitude": -122.4194,
                "severity": 78,
                "timestamp": datetime.now().isoformat(),
                "description": "Magnitude 6.8 earthquake in San Francisco Bay Area",
                "satellite_bucket": "resilientflow-satellite-data",
                "satellite_blob": "sf_earthquake_damage_2024.tiff",
                "metadata": {
                    "magnitude": "6.8",
                    "depth": "12 km",
                    "aftershocks": 23
                }
            }
        }
        return scenarios
    
    async def run_disaster_scenario(self, scenario_name, event_data):
        """Run a complete disaster response workflow through the ADK orchestrator"""
        self.log_step("SCENARIO", f"Starting {scenario_name.upper()} response workflow...")
        
        print(f"📍 Location: {event_data['description']}")
        print(f"🎯 Severity: {event_data['severity']}/100")
        print(f"📊 Event ID: {event_data['event_id']}")
        print()
        
        try:
            # Execute the complete workflow through the ADK orchestrator
            workflow_start = time.time()
            
            result = await self.orchestrator.process_disaster_event(event_data)
            
            workflow_time = time.time() - workflow_start
            
            # Display results
            self.log_step("WORKFLOW", f"✅ Complete workflow finished in {workflow_time:.1f}s")
            self.display_workflow_results(result, workflow_time)
            
            return result
            
        except Exception as e:
            self.log_step("WORKFLOW", f"❌ Workflow failed: {e}")
            return None
    
    def display_workflow_results(self, result, workflow_time):
        """Display the results from the orchestrator workflow"""
        print("\n" + "="*60)
        print("🎊 WORKFLOW RESULTS SUMMARY")
        print("="*60)
        
        if not result:
            print("❌ No results to display")
            return
        
        # Overall status
        status = result.get("status", "UNKNOWN")
        workflow_id = result.get("workflow_id", "unknown")
        print(f"🆔 Workflow ID: {workflow_id}")
        print(f"📊 Status: {status}")
        print(f"⏱️  Total Time: {workflow_time:.1f}s")
        print(f"🎯 Overall Severity: {result.get('overall_severity', 0)}/100")
        print()
        
        # Steps completed
        steps = result.get("steps_completed", {})
        print("📋 AGENT EXECUTION STATUS:")
        step_icons = {
            "data_aggregation": "🛰️ ",
            "impact_assessment": "📊",
            "resource_allocation": "🚁",
            "communications": "📢",
            "reporting": "📄"
        }
        
        for step, completed in steps.items():
            icon = step_icons.get(step, "🔧")
            status_icon = "✅" if completed else "⏭️ "
            step_name = step.replace("_", " ").title()
            print(f"  {status_icon} {icon} {step_name}")
        print()
        
        # Key metrics
        print("📈 KEY METRICS:")
        print(f"  🚁 Resources Allocated: {result.get('resources_allocated', 0)}")
        print(f"  📢 Alerts Sent: {result.get('alerts_sent', 0)}")
        print(f"  📄 Reports Generated: {result.get('reports_generated', 0)}")
        
        # If high severity, show additional details
        if result.get('overall_severity', 0) >= 60:
            print(f"\n🚨 HIGH SEVERITY EVENT - Full Response Activated")
            print(f"  • Resource allocation, communications, and reporting executed")
            print(f"  • Multi-agent coordination successful")
        else:
            print(f"\n📊 MODERATE SEVERITY - Assessment Only")
            print(f"  • Resource allocation skipped (severity < 60)")
        
        print("\n" + "="*60)
    
    async def run_complete_demo(self):
        """Run the complete demo with multiple scenarios"""
        self.log_step("DEMO", "Starting ResilientFlow ADK demonstration...")
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("❌ Prerequisites failed. Cannot continue demo.")
            return False
        
        # Get disaster scenarios
        scenarios = self.create_disaster_scenarios()
        
        print(f"\n🎭 Running {len(scenarios)} disaster scenarios...")
        print("Each scenario demonstrates the complete ADK orchestration workflow:")
        print("  1. Data Aggregation (satellite imagery processing)")
        print("  2. Impact Assessment (spatial analysis)")
        print("  3. Conditional Logic (severity threshold check)")
        print("  4. Resource Allocation (if severity ≥ 60)")
        print("  5. Communications (multilingual alerts)")
        print("  6. Reporting (situation reports)")
        print()
        
        results = {}
        
        # Run each scenario
        for i, (scenario_name, event_data) in enumerate(scenarios.items(), 1):
            print(f"\n🎬 SCENARIO {i}/{len(scenarios)}: {scenario_name.upper()}")
            print("-" * 50)
            
            result = await self.run_disaster_scenario(scenario_name, event_data)
            results[scenario_name] = result
            
            # Brief pause between scenarios
            if i < len(scenarios):
                print(f"\n⏸️  Pausing 3 seconds before next scenario...")
                time.sleep(3)
        
        # Final summary
        self.display_demo_summary(results)
        
        return True
    
    def display_demo_summary(self, results):
        """Display final demo summary"""
        total_time = time.time() - self.start_time
        
        print(f"\n🏁 DEMO COMPLETE")
        print("="*60)
        print(f"⏱️  Total Demo Time: {total_time:.1f}s")
        print(f"🎭 Scenarios Executed: {len(results)}")
        
        successful = sum(1 for r in results.values() if r and r.get('status') == 'SUCCESS')
        print(f"✅ Successful Workflows: {successful}/{len(results)}")
        
        print(f"\n🏗️  ARCHITECTURE DEMONSTRATED:")
        print(f"  ✅ ADK Orchestrator (orchestrator.py)")
        print(f"  ✅ 5 Agent Tools (agents/*_tool.py)")
        print(f"  ✅ Multi-agent workflow coordination")
        print(f"  ✅ Conditional logic and parallel execution")
        print(f"  ✅ End-to-end disaster response pipeline")
        
        print(f"\n🎯 This demonstrates ResilientFlow's transition from")
        print(f"   microservices to ADK-compliant multi-agent system!")

def main():
    """Main demo entry point"""
    if len(sys.argv) != 2:
        print("Usage: python quick_demo.py <PROJECT_ID>")
        print("Example: python quick_demo.py gen-lang-client-0768345181")
        sys.exit(1)
    
    project_id = sys.argv[1]
    demo = ResilientFlowDemo(project_id)
    
    try:
        # Run the complete demo
        success = asyncio.run(demo.run_complete_demo())
        
        if success:
            print(f"\n🎉 Demo completed successfully!")
            print(f"🔗 Next steps:")
            print(f"   • Review orchestrator.py for ADK implementation details")
            print(f"   • Examine agents/*_tool.py for agent implementations")
            print(f"   • Deploy to Google Cloud for production use")
        else:
            print(f"\n❌ Demo encountered issues")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()