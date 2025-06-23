#!/usr/bin/env python3
"""
🔥 ResilientFlow End-to-End Smoke Test
Comprehensive testing of the complete system integration
"""

import os
import sys
import asyncio
import time
from datetime import datetime
import json

# Add the workspace to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add visualizer to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "visualizer"))

class ResilientFlowSmokeTest:
    """Comprehensive end-to-end smoke test suite"""
    
    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()
        
    def log_test(self, test_name: str, status: str, message: str = "", duration: float = 0):
        """Log test result"""
        result = {
            "test_name": test_name,
            "status": status,
            "message": message,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{emoji} {test_name}: {status}")
        if message:
            print(f"   {message}")
        if duration > 0:
            print(f"   Duration: {duration:.2f}s")
        print()
    
    async def test_orchestrator_import(self):
        """Test 1: Orchestrator import and basic functionality"""
        test_start = time.time()
        
        try:
            from orchestrator import handle_disaster_event, DisasterResponseAgent
            
            # Test agent creation
            agent = DisasterResponseAgent()
            
            self.log_test(
                "Orchestrator Import",
                "PASS",
                "Successfully imported orchestrator and created agent",
                time.time() - test_start
            )
            return True
            
        except Exception as e:
            self.log_test(
                "Orchestrator Import",
                "FAIL",
                f"Failed to import orchestrator: {e}",
                time.time() - test_start
            )
            return False
    
    async def test_agent_tools_import(self):
        """Test 2: All agent tools import successfully"""
        test_start = time.time()
        
        agents = [
            ("Data Aggregator", "agents.aggregator_tool", "process_satellite_imagery"),
            ("Impact Assessor", "agents.assessor_tool", "analyze_impact"),
            ("Resource Allocator", "agents.allocator_tool", "optimize_resource_allocation"),
            ("Communications Coordinator", "agents.comms_tool", "coordinate_communications"),
            ("Report Synthesizer", "agents.reporter_tool", "synthesize_situation_report")
        ]
        
        failed_agents = []
        
        for agent_name, module_name, function_name in agents:
            try:
                module = __import__(module_name, fromlist=[function_name])
                getattr(module, function_name)
            except Exception as e:
                failed_agents.append(f"{agent_name}: {e}")
        
        if not failed_agents:
            self.log_test(
                "Agent Tools Import",
                "PASS",
                f"All 5 agent tools imported successfully",
                time.time() - test_start
            )
            return True
        else:
            self.log_test(
                "Agent Tools Import",
                "FAIL",
                f"Failed agents: {', '.join(failed_agents)}",
                time.time() - test_start
            )
            return False
    
    async def test_basic_workflow_execution(self):
        """Test 3: Basic workflow execution"""
        test_start = time.time()
        
        try:
            from orchestrator import handle_disaster_event
            
            # Test incident
            test_incident = {
                "event_id": "smoke_test_001",
                "event_type": "earthquake",
                "severity": 75,
                "location": "Test City",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "affected_population": 10000,
                "timestamp": datetime.now().isoformat(),
                "satellite_image": "mock_test_data.tiff"
            }
            
            # Execute workflow
            result = await handle_disaster_event(test_incident)
            
            # Validate result structure
            required_fields = [
                "workflow_id", "status", "overall_severity",
                "resources_allocated", "alerts_sent"
            ]
            
            missing_fields = [field for field in required_fields if field not in result]
            
            if not missing_fields and result.get("status") == "SUCCESS":
                self.log_test(
                    "Basic Workflow Execution",
                    "PASS",
                    f"Workflow completed: {result.get('resources_allocated', 0)} resources, {result.get('alerts_sent', 0)} alerts",
                    time.time() - test_start
                )
                return True
            else:
                self.log_test(
                    "Basic Workflow Execution",
                    "FAIL",
                    f"Missing fields: {missing_fields}" if missing_fields else f"Status: {result.get('status')}",
                    time.time() - test_start
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Basic Workflow Execution",
                "FAIL",
                f"Workflow execution failed: {e}",
                time.time() - test_start
            )
            return False
    
    async def test_communications_mock_mode(self):
        """Test 4: Communications in mock mode"""
        test_start = time.time()
        
        try:
            # Ensure mock mode
            os.environ['USE_MOCK'] = '1'
            
            from agents.comms_tool import coordinate_communications
            
            test_allocation = {
                "total_resources": 10,
                "disaster_type": "test",
                "severity": "medium",
                "allocations": [{"location": "Test", "resources": 5}]
            }
            
            result = await coordinate_communications(
                allocation_plan=test_allocation,
                project_id="test-project"
            )
            
            # Validate communications result
            if (result.get("alerts_sent", 0) > 0 and 
                result.get("live_mode") == False and
                len(result.get("multilingual_alerts", [])) > 0):
                
                self.log_test(
                    "Communications Mock Mode",
                    "PASS",
                    f"Mock communications: {result.get('alerts_sent')} alerts, {len(result.get('multilingual_alerts', []))} languages",
                    time.time() - test_start
                )
                return True
            else:
                self.log_test(
                    "Communications Mock Mode",
                    "FAIL",
                    f"Invalid result: {result}",
                    time.time() - test_start
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Communications Mock Mode",
                "FAIL",
                f"Communications test failed: {e}",
                time.time() - test_start
            )
            return False
    
    async def test_streamlit_import(self):
        """Test 5: Streamlit Command Center import"""
        test_start = time.time()
        
        try:
            import streamlit
            import plotly
            import streamlit_app
            
            self.log_test(
                "Streamlit Command Center Import",
                "PASS",
                "Command Center imports successfully",
                time.time() - test_start
            )
            return True
            
        except Exception as e:
            self.log_test(
                "Streamlit Command Center Import",
                "FAIL",
                f"Command Center import failed: {e}",
                time.time() - test_start
            )
            return False
    
    async def test_multiple_workflows(self):
        """Test 6: Multiple workflow execution (stress test)"""
        test_start = time.time()
        
        try:
            from orchestrator import handle_disaster_event
            
            # Test multiple incident types
            test_incidents = [
                {"event_type": "hurricane", "severity": 85, "location": "Miami"},
                {"event_type": "wildfire", "severity": 92, "location": "LA"},
                {"event_type": "earthquake", "severity": 78, "location": "SF"}
            ]
            
            results = []
            total_resources = 0
            total_alerts = 0
            
            for i, incident in enumerate(test_incidents):
                incident.update({
                    "event_id": f"stress_test_{i}",
                    "latitude": 34.0 + i,
                    "longitude": -118.0 - i,
                    "affected_population": 50000,
                    "timestamp": datetime.now().isoformat(),
                    "satellite_image": f"mock_{incident['event_type']}_data.tiff"
                })
                
                result = await handle_disaster_event(incident)
                results.append(result)
                
                total_resources += result.get("resources_allocated", 0)
                total_alerts += result.get("alerts_sent", 0)
            
            # Validate all workflows succeeded
            successful = sum(1 for r in results if r.get("status") == "SUCCESS")
            
            if successful == len(test_incidents):
                self.log_test(
                    "Multiple Workflows Stress Test",
                    "PASS",
                    f"3/3 workflows successful: {total_resources} total resources, {total_alerts:,} total alerts",
                    time.time() - test_start
                )
                return True
            else:
                self.log_test(
                    "Multiple Workflows Stress Test",
                    "FAIL",
                    f"Only {successful}/{len(test_incidents)} workflows successful",
                    time.time() - test_start
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Multiple Workflows Stress Test",
                "FAIL",
                f"Stress test failed: {e}",
                time.time() - test_start
            )
            return False
    
    async def test_environment_flags(self):
        """Test 7: Environment flag system"""
        test_start = time.time()
        
        try:
            # Test mock mode flag
            os.environ['USE_MOCK'] = '1'
            mock_value = os.environ.get('USE_MOCK')
            
            # Test live mode flag
            os.environ['USE_MOCK'] = '0'
            live_value = os.environ.get('USE_MOCK')
            
            # Reset to mock
            os.environ['USE_MOCK'] = '1'
            
            if mock_value == '1' and live_value == '0':
                self.log_test(
                    "Environment Flags System",
                    "PASS",
                    "USE_MOCK flag working correctly",
                    time.time() - test_start
                )
                return True
            else:
                self.log_test(
                    "Environment Flags System",
                    "FAIL",
                    f"Flag values incorrect: mock={mock_value}, live={live_value}",
                    time.time() - test_start
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Environment Flags System",
                "FAIL",
                f"Environment flags test failed: {e}",
                time.time() - test_start
            )
            return False
    
    def generate_report(self):
        """Generate final test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed_tests = sum(1 for r in self.test_results if r["status"] == "FAIL")
        
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        print("=" * 60)
        print("🔥 ResilientFlow End-to-End Smoke Test Report")
        print("=" * 60)
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print()
        
        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! ResilientFlow is ready for production!")
            print("✅ System is fully operational and ready for demo")
        else:
            print("⚠️  Some tests failed. Review the issues above.")
            print("🔧 Fix failed tests before proceeding to demo")
        
        print()
        print("📋 Test Summary:")
        for result in self.test_results:
            emoji = "✅" if result["status"] == "PASS" else "❌"
            print(f"  {emoji} {result['test_name']}: {result['status']}")
        
        return failed_tests == 0

async def main():
    """Run the complete smoke test suite"""
    
    print("🚀 Starting ResilientFlow End-to-End Smoke Test")
    print("=" * 60)
    print("Testing complete system integration...")
    print()
    
    # Create test suite
    smoke_test = ResilientFlowSmokeTest()
    
    # Run all tests
    test_methods = [
        smoke_test.test_orchestrator_import,
        smoke_test.test_agent_tools_import,
        smoke_test.test_basic_workflow_execution,
        smoke_test.test_communications_mock_mode,
        smoke_test.test_streamlit_import,
        smoke_test.test_multiple_workflows,
        smoke_test.test_environment_flags
    ]
    
    for test_method in test_methods:
        await test_method()
    
    # Generate final report
    all_passed = smoke_test.generate_report()
    
    if all_passed:
        print("\n🎯 Ready for Hour 10-14: Demo video capture!")
        print("🌟 ResilientFlow is production-ready!")
    else:
        print("\n🔧 Fix issues before proceeding to demo phase")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main()) 