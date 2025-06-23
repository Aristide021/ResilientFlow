"""
ResilientFlow - ADK-based Disaster Response Orchestrator
This is the main orchestrator that defines and executes the multi-agent disaster response workflow
using the Google Agent Development Kit (ADK).
"""

import os
import sys
import asyncio
from typing import Dict, Any, List
from datetime import datetime

# Add the workspace to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import ADK components
from google.adk.agents import Agent
from google.adk.tools.base_tool import BaseTool
from google.genai import types

# Proto import removed for demo - not needed for ADK functionality

# Import our refactored agent tools
from agents.aggregator_tool import process_satellite_imagery
from agents.assessor_tool import analyze_impact
from agents.allocator_tool import optimize_resource_allocation
from agents.comms_tool import coordinate_communications
from agents.reporter_tool import synthesize_situation_report

# Import Pub/Sub client for visualizer events
try:
    from google.cloud import pubsub_v1
    import json
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    print("⚠️  Google Cloud Pub/Sub not available - visualizer events disabled")


class SimplePubSubClient:
    """Simplified Pub/Sub client for visualizer events"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = f'projects/{project_id}/topics/rf-visualizer-events'
    
    def publish_json_message(self, data: dict):
        """Publish JSON data to visualizer topic"""
        try:
            json_data = json.dumps(data).encode('utf-8')
            future = self.publisher.publish(self.topic_path, json_data)
            return future.result()  # Block until published
        except Exception as e:
            print(f"⚠️  Failed to publish to Pub/Sub: {e}")
            return None


class DisasterResponseOrchestrator:
    """
    Main orchestrator for the ResilientFlow disaster response system.
    Uses ADK to define and execute the multi-agent workflow.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """Set up structured logging"""
        import logging
        logger = logging.getLogger('resilientflow.orchestrator')
        logger.setLevel(logging.INFO)
        return logger


# Define the main disaster response agent using ADK
class DisasterResponseAgent:
    """Main ADK agent that orchestrates the disaster response workflow"""
    
    def __init__(self):
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0768345181')
        
        # Initialize Pub/Sub client for visualizer events
        if PUBSUB_AVAILABLE:
            try:
                self.pubsub = SimplePubSubClient(self.project_id)
                self.visualizer_enabled = True
            except Exception as e:
                print(f"⚠️  Pub/Sub initialization failed: {e}")
                self.visualizer_enabled = False
        else:
            self.visualizer_enabled = False
        
    def _publish_workflow_event(self, event_type: str, step_name: str, data: Dict[str, Any] = None):
        """Publish workflow events for visualizer"""
        if not self.visualizer_enabled:
            return
            
        try:
            event_data = {
                "event_type": event_type,
                "step_name": step_name,
                "timestamp": datetime.now().isoformat(),
                "source_agent": "orchestrator",
                "target_agent": step_name.lower().replace(" ", "_"),
                "message": f"TRACE: {event_type} - {step_name}",
                "data": data or {}
            }
            
            # Publish to visualizer topic (for standalone visualizer)
            self.pubsub.publish_json_message(event_data)
            
            # Also feed directly to embedded visualizer (for Command Center)
            try:
                from visualizer import feed_trace
                feed_trace(event_data)
            except ImportError:
                # Visualizer not available in this environment
                pass
            
        except Exception as e:
            print(f"⚠️  Failed to publish visualizer event: {e}")
        
    async def process_disaster_event(
        self, 
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main workflow orchestration function.
        Takes a disaster event and processes it through all agent stages.
        """
        
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self._log_workflow_start(workflow_id, event_data)
        self._publish_workflow_event("workflow_start", "Orchestrator", {
            "workflow_id": workflow_id,
            "event_data": event_data
        })
        
        # Initialize workflow state
        workflow_state = {
            "workflow_id": workflow_id,
            "start_time": datetime.now()
        }
        
        try:
            # Step 1: Data Aggregation
            # Process satellite imagery to detect damage
            self._publish_workflow_event("step_start", "Data Aggregation")
            
            if "satellite_image" in event_data:
                # Handle both string and dict satellite data
                satellite_data = event_data["satellite_image"]
                if isinstance(satellite_data, str):
                    # Convert string to dict format expected by the agent
                    satellite_dict = {
                        "bucket": "mock-bucket",
                        "blob_name": satellite_data
                    }
                else:
                    satellite_dict = satellite_data
                    
                aggregation_result = await self._run_data_aggregation(satellite_dict)
            else:
                # Create a mock aggregation result if no satellite data
                aggregation_result = self._create_mock_aggregation_result(event_data)
            
            workflow_state["aggregation_result"] = aggregation_result
            self._publish_workflow_event("step_complete", "Data Aggregation", {
                "result_size": len(str(aggregation_result)),
                "detections": aggregation_result.get("detections_count", 0)
            })
            
            # Step 2: Impact Assessment
            # Analyze the spatial impact and generate heat maps
            self._publish_workflow_event("step_start", "Impact Assessment")
            impact_assessment = await self._run_impact_assessment(aggregation_result)
            workflow_state["impact_assessment"] = impact_assessment
            self._publish_workflow_event("step_complete", "Impact Assessment", {
                "severity": impact_assessment.get("overall_severity", 0),
                "clusters": impact_assessment.get("total_clusters", 0)
            })
            
            # Step 3: Conditional Logic - Only proceed if severity is high enough
            severity = impact_assessment.get("overall_severity", 0)
            if severity >= 60:
                self._publish_workflow_event("conditional_check", "Severity Check", {
                    "severity": severity,
                    "threshold": 60,
                    "proceed": True
                })
                
                # Step 4: Resource Allocation (runs if severe enough)
                self._publish_workflow_event("step_start", "Resource Allocation")
                allocation_plan = await self._run_resource_allocation(impact_assessment)
                workflow_state["allocation_plan"] = allocation_plan
                self._publish_workflow_event("step_complete", "Resource Allocation", {
                    "total_resources": allocation_plan.get("total_resources", 0),
                    "allocations": len(allocation_plan.get("allocations", []))
                })
                
                # Step 5 & 6: Parallel execution of Communications and Reporting
                self._publish_workflow_event("parallel_start", "Communications & Reporting")
                
                comm_result, report_result = await asyncio.gather(
                    self._run_communications_coordination(allocation_plan),
                    self._run_situation_reporting(allocation_plan, impact_assessment)
                )
                
                workflow_state["communications_result"] = comm_result
                workflow_state["report_result"] = report_result
                
                self._publish_workflow_event("parallel_complete", "Communications & Reporting", {
                    "alerts_sent": comm_result.get("alerts_sent", 0),
                    "reports_generated": report_result.get("reports_count", 0)
                })
                
            else:
                self._log_low_severity_skip(severity)
                self._publish_workflow_event("conditional_check", "Severity Check", {
                    "severity": severity,
                    "threshold": 60,
                    "proceed": False
                })
                workflow_state["allocation_plan"] = None
                workflow_state["communications_result"] = None
                workflow_state["report_result"] = None
            
            # Compile final workflow result
            final_result = self._compile_final_result(workflow_state)
            workflow_state["final_result"] = final_result
            
            self._log_workflow_completion(workflow_id, final_result)
            self._publish_workflow_event("workflow_complete", "Orchestrator", {
                "workflow_id": workflow_id,
                "status": "SUCCESS",
                "final_result": final_result
            })
            
            return final_result
            
        except Exception as e:
            self._log_workflow_error(workflow_id, str(e))
            self._publish_workflow_event("workflow_error", "Orchestrator", {
                "workflow_id": workflow_id,
                "error": str(e)
            })
            workflow_state["error"] = str(e)
            raise
    
    async def _run_data_aggregation(self, satellite_data: Dict) -> Dict:
        """Execute the data aggregation agent"""
        self._log_step_start("Data Aggregation")
        
        result = await process_satellite_imagery(
            bucket_name=satellite_data.get("bucket"),
            blob_name=satellite_data.get("blob_name"),
            project_id=self.project_id
        )
        
        self._log_step_completion("Data Aggregation", result)
        return result
    
    async def _run_impact_assessment(self, aggregation_result: Dict) -> Dict:
        """Execute the impact assessment agent"""
        self._log_step_start("Impact Assessment")
        
        result = await analyze_impact(
            disaster_events=aggregation_result.get("disaster_events", []),
            project_id=self.project_id
        )
        
        self._log_step_completion("Impact Assessment", result)
        return result
    
    async def _run_resource_allocation(self, impact_assessment: Dict) -> Dict:
        """Execute the resource allocation agent"""
        self._log_step_start("Resource Allocation")
        
        result = await optimize_resource_allocation(
            impact_data=impact_assessment,
            project_id=self.project_id
        )
        
        self._log_step_completion("Resource Allocation", result)
        return result
    
    async def _run_communications_coordination(self, allocation_plan: Dict) -> Dict:
        """Execute the communications coordination agent"""
        self._log_step_start("Communications Coordination")
        
        result = await coordinate_communications(
            allocation_plan=allocation_plan,
            project_id=self.project_id
        )
        
        self._log_step_completion("Communications Coordination", result)
        return result
    
    async def _run_situation_reporting(self, allocation_plan: Dict, impact_assessment: Dict) -> Dict:
        """Execute the situation reporting agent"""
        self._log_step_start("Situation Reporting")
        
        result = await synthesize_situation_report(
            allocation_plan=allocation_plan,
            impact_assessment=impact_assessment,
            project_id=self.project_id
        )
        
        self._log_step_completion("Situation Reporting", result)
        return result
    
    def _create_mock_aggregation_result(self, event_data: Dict) -> Dict:
        """Create a mock aggregation result when no satellite data is available"""
        return {
            "processing_id": f"mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "disaster_events": [
                {
                    "event_id": event_data.get("event_id", "mock_event"),
                    "latitude": event_data.get("latitude", 34.0522),
                    "longitude": event_data.get("longitude", -118.2437),
                    "event_type": event_data.get("event_type", "earthquake"),
                    "severity_raw": event_data.get("severity", 75),
                    "timestamp_ms": int(datetime.now().timestamp() * 1000)
                }
            ],
            "assessments_stored": 1,
            "processing_time_ms": 100
        }
    
    def _compile_final_result(self, workflow_state: Dict) -> Dict:
        """Compile the final workflow result from all agent outputs"""
        return {
            "workflow_id": workflow_state.get("workflow_id"),
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
            "steps_completed": {
                "data_aggregation": workflow_state.get("aggregation_result") is not None,
                "impact_assessment": workflow_state.get("impact_assessment") is not None,
                "resource_allocation": workflow_state.get("allocation_plan") is not None,
                "communications": workflow_state.get("communications_result") is not None,
                "reporting": workflow_state.get("report_result") is not None
            },
            "overall_severity": workflow_state.get("impact_assessment", {}).get("overall_severity", 0),
            "resources_allocated": workflow_state.get("allocation_plan", {}).get("total_resources", 0),
            "alerts_sent": workflow_state.get("communications_result", {}).get("alerts_sent", 0),
            "reports_generated": workflow_state.get("report_result", {}).get("reports_count", 0)
        }
    
    def _log_workflow_start(self, workflow_id: str, event_data: Dict):
        print(f"🚨 Starting ResilientFlow workflow: {workflow_id}")
        print(f"📍 Event Type: {event_data.get('event_type', 'unknown')}")
        print(f"📍 Location: {event_data.get('latitude', 'N/A')}, {event_data.get('longitude', 'N/A')}")
    
    def _log_step_start(self, step_name: str):
        print(f"🔄 Executing: {step_name}")
    
    def _log_step_completion(self, step_name: str, result: Dict):
        print(f"✅ Completed: {step_name} - {len(str(result))} bytes of data")
    
    def _log_low_severity_skip(self, severity: float):
        print(f"ℹ️  Low severity ({severity}) - Skipping resource allocation and communications")
    
    def _log_workflow_completion(self, workflow_id: str, result: Dict):
        print(f"🎉 Workflow {workflow_id} completed successfully")
        print(f"📊 Final severity: {result.get('overall_severity', 0)}")
        print(f"🚁 Resources allocated: {result.get('resources_allocated', 0)}")
        print(f"📢 Alerts sent: {result.get('alerts_sent', 0)}")
    
    def _log_workflow_error(self, workflow_id: str, error: str):
        print(f"❌ Workflow {workflow_id} failed: {error}")


async def handle_disaster_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the disaster response workflow.
    This function can be called by external systems or the demo script.
    """
    agent = DisasterResponseAgent()
    return await agent.process_disaster_event(event_data)


async def main():
    """
    Main function for running the orchestrator in standalone mode.
    This demonstrates how the workflow executes.
    """
    print("🌊 ResilientFlow ADK Orchestrator Starting...")
    
    # Example disaster event
    test_event = {
        "event_id": "demo_earthquake_001",
        "event_type": "earthquake",
        "latitude": 34.0522,
        "longitude": -118.2437,
        "severity": 85,
        "timestamp": datetime.now().isoformat(),
        "description": "Major earthquake in Los Angeles area"
    }
    
    try:
        result = await handle_disaster_event(test_event)
        print("\n🎊 Demo completed successfully!")
        print(f"Results: {result}")
        
    except Exception as e:
        print(f"\n💥 Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 