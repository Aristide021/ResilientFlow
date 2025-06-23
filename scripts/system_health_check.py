#!/usr/bin/env python3
"""
🩺 ResilientFlow System Health Check
Comprehensive validation of all system components for disaster response readiness
"""

import os
import sys
import asyncio
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Add the workspace to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ResilientFlowHealthCheck:
    """Comprehensive system health checker for ResilientFlow"""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now()
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0768345181')
        
    def log_check(self, component: str, status: str, message: str = "", details: Dict = None, duration: float = 0):
        """Log health check result"""
        result = {
            "component": component,
            "status": status,  # HEALTHY, UNHEALTHY, WARNING, UNKNOWN
            "message": message,
            "details": details or {},
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        emoji = "✅" if status == "HEALTHY" else "❌" if status == "UNHEALTHY" else "⚠️" if status == "WARNING" else "❓"
        print(f"{emoji} {component}: {status}")
        if message:
            print(f"   {message}")
        if duration > 0:
            print(f"   Check duration: {duration:.2f}s")
        print()
    
    async def check_orchestrator_health(self) -> bool:
        """Check orchestrator core functionality"""
        check_start = time.time()
        
        try:
            from orchestrator import handle_disaster_event, DisasterResponseAgent
            
            # Test agent creation
            agent = DisasterResponseAgent()
            
            # Test quick workflow execution
            test_incident = {
                "event_id": "health_check_001",
                "event_type": "test",
                "severity": 65,  # Above threshold
                "location": "Health Check",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "affected_population": 1000,
                "timestamp": datetime.now().isoformat(),
                "satellite_image": "mock_health_test.tiff"
            }
            
            # Run minimal workflow
            result = await handle_disaster_event(test_incident)
            
            # Validate result
            if (result.get("status") == "SUCCESS" and 
                result.get("resources_allocated", 0) > 0 and
                result.get("alerts_sent", 0) > 0):
                
                self.log_check(
                    "Orchestrator Core",
                    "HEALTHY",
                    f"Workflow completed: {result.get('resources_allocated')} resources, {result.get('alerts_sent')} alerts",
                    {"workflow_id": result.get("workflow_id")},
                    time.time() - check_start
                )
                return True
            else:
                self.log_check(
                    "Orchestrator Core",
                    "UNHEALTHY",
                    f"Workflow failed validation: {result}",
                    {"result": result},
                    time.time() - check_start
                )
                return False
                
        except Exception as e:
            self.log_check(
                "Orchestrator Core",
                "UNHEALTHY",
                f"Orchestrator check failed: {e}",
                {"error": str(e)},
                time.time() - check_start
            )
            return False
    
    async def check_agent_tools_health(self) -> bool:
        """Check all 5 agent tools"""
        check_start = time.time()
        
        agents = [
            ("Data Aggregator", "agents.aggregator_tool", "process_satellite_imagery"),
            ("Impact Assessor", "agents.assessor_tool", "analyze_impact"),
            ("Resource Allocator", "agents.allocator_tool", "optimize_resource_allocation"),
            ("Communications Coordinator", "agents.comms_tool", "coordinate_communications"),
            ("Report Synthesizer", "agents.reporter_tool", "synthesize_situation_report")
        ]
        
        healthy_agents = 0
        agent_details = {}
        
        for agent_name, module_name, function_name in agents:
            try:
                module = __import__(module_name, fromlist=[function_name])
                func = getattr(module, function_name)
                agent_details[agent_name] = "HEALTHY"
                healthy_agents += 1
            except Exception as e:
                agent_details[agent_name] = f"UNHEALTHY: {e}"
        
        if healthy_agents == len(agents):
            self.log_check(
                "Agent Tools",
                "HEALTHY",
                f"All {len(agents)} agent tools available",
                agent_details,
                time.time() - check_start
            )
            return True
        elif healthy_agents > 0:
            self.log_check(
                "Agent Tools",
                "WARNING",
                f"{healthy_agents}/{len(agents)} agent tools available",
                agent_details,
                time.time() - check_start
            )
            return False
        else:
            self.log_check(
                "Agent Tools",
                "UNHEALTHY",
                "No agent tools available",
                agent_details,
                time.time() - check_start
            )
            return False
    
    async def check_communications_health(self) -> bool:
        """Check communications systems"""
        check_start = time.time()
        
        try:
            # Check environment variables
            config = {
                'use_mock': os.getenv('USE_MOCK', '1'),
                'slack_webhook': os.getenv('SLACK_WEBHOOK_URL', ''),
                'twilio_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
                'twilio_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
                'twilio_from': os.getenv('TWILIO_FROM_NUMBER', '')
            }
            
            # Test communications in mock mode
            os.environ['USE_MOCK'] = '1'
            from agents.comms_tool import coordinate_communications
            
            test_allocation = {
                "total_resources": 5,
                "disaster_type": "health_check",
                "severity": "medium",
                "allocations": [{"location": "Test", "resources": 5}]
            }
            
            result = await coordinate_communications(
                allocation_plan=test_allocation,
                project_id=self.project_id
            )
            
            # Validate mock communications
            mock_healthy = (result.get("alerts_sent", 0) > 0 and
                           len(result.get("multilingual_alerts", [])) > 0)
            
            # Check live communications configuration
            slack_configured = bool(config['slack_webhook'])
            twilio_configured = bool(config['twilio_sid'] and config['twilio_token'])
            
            if mock_healthy:
                if slack_configured and twilio_configured:
                    status = "HEALTHY"
                    message = "Mock communications working, live channels configured"
                elif slack_configured or twilio_configured:
                    status = "WARNING"
                    message = "Mock communications working, partial live configuration"
                else:
                    status = "WARNING"
                    message = "Mock communications working, no live channels configured"
                
                self.log_check(
                    "Communications",
                    status,
                    message,
                    {
                        "mock_alerts": result.get("alerts_sent", 0),
                        "languages": len(result.get("multilingual_alerts", [])),
                        "slack_configured": slack_configured,
                        "twilio_configured": twilio_configured
                    },
                    time.time() - check_start
                )
                return status == "HEALTHY"
            else:
                self.log_check(
                    "Communications",
                    "UNHEALTHY",
                    "Mock communications failed",
                    {"result": result},
                    time.time() - check_start
                )
                return False
                
        except Exception as e:
            self.log_check(
                "Communications",
                "UNHEALTHY",
                f"Communications check failed: {e}",
                {"error": str(e)},
                time.time() - check_start
            )
            return False
    
    async def check_visualizer_health(self) -> bool:
        """Check visualizer and dashboard"""
        check_start = time.time()
        
        try:
            # Check Streamlit imports
            import streamlit
            import plotly
            
            # Check command center import
            try:
                # Try importing from visualizer directory
                sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "visualizer"))
                import streamlit_app
                dashboard_available = True
            except ImportError:
                dashboard_available = False
            
            # Check visualizer components (trace-based, no network viz)
            viz_components = True  # Always available with trace-based approach
            
            if dashboard_available and viz_components:
                self.log_check(
                    "Visualizer & Dashboard",
                    "HEALTHY",
                    "Command center and visualization components available",
                    {
                        "streamlit_version": streamlit.__version__,
                        "plotly_available": True,
                        "dashboard_available": dashboard_available,
                        "viz_components": viz_components
                    },
                    time.time() - check_start
                )
                return True
            elif dashboard_available:
                self.log_check(
                    "Visualizer & Dashboard",
                    "WARNING",
                    "Dashboard available but some visualization components missing",
                    {
                        "dashboard_available": dashboard_available,
                        "viz_components": viz_components
                    },
                    time.time() - check_start
                )
                return False
            else:
                self.log_check(
                    "Visualizer & Dashboard",
                    "UNHEALTHY",
                    "Dashboard not available",
                    {
                        "dashboard_available": dashboard_available,
                        "viz_components": viz_components
                    },
                    time.time() - check_start
                )
                return False
                
        except Exception as e:
            self.log_check(
                "Visualizer & Dashboard",
                "UNHEALTHY",
                f"Visualizer check failed: {e}",
                {"error": str(e)},
                time.time() - check_start
            )
            return False
    
    async def check_environment_health(self) -> bool:
        """Check environment configuration"""
        check_start = time.time()
        
        try:
            # Check required environment variables
            env_vars = {
                'GOOGLE_CLOUD_PROJECT': os.getenv('GOOGLE_CLOUD_PROJECT'),
                'USE_MOCK': os.getenv('USE_MOCK', '1'),
                'SLACK_WEBHOOK_URL': os.getenv('SLACK_WEBHOOK_URL', ''),
                'TWILIO_ACCOUNT_SID': os.getenv('TWILIO_ACCOUNT_SID', ''),
                'TWILIO_AUTH_TOKEN': os.getenv('TWILIO_AUTH_TOKEN', ''),
                'TWILIO_FROM_NUMBER': os.getenv('TWILIO_FROM_NUMBER', '')
            }
            
            # Check Python dependencies
            dependencies = []
            try:
                import google.cloud
                dependencies.append(("google-cloud", "AVAILABLE"))
            except ImportError:
                dependencies.append(("google-cloud", "MISSING"))
            
            try:
                import streamlit
                dependencies.append(("streamlit", "AVAILABLE"))
            except ImportError:
                dependencies.append(("streamlit", "MISSING"))
            
            try:
                import plotly
                dependencies.append(("plotly", "AVAILABLE"))
            except ImportError:
                dependencies.append(("plotly", "MISSING"))
            
            # Validate configuration
            project_configured = bool(env_vars['GOOGLE_CLOUD_PROJECT'])
            mock_mode_valid = env_vars['USE_MOCK'] in ('0', '1')
            deps_available = all(status == "AVAILABLE" for _, status in dependencies)
            
            if project_configured and mock_mode_valid and deps_available:
                self.log_check(
                    "Environment Configuration",
                    "HEALTHY",
                    "All environment variables and dependencies configured",
                    {
                        "project_id": env_vars['GOOGLE_CLOUD_PROJECT'],
                        "mock_mode": env_vars['USE_MOCK'],
                        "dependencies": dict(dependencies)
                    },
                    time.time() - check_start
                )
                return True
            else:
                issues = []
                if not project_configured:
                    issues.append("GOOGLE_CLOUD_PROJECT not set")
                if not mock_mode_valid:
                    issues.append("USE_MOCK invalid")
                if not deps_available:
                    issues.append("Missing dependencies")
                
                self.log_check(
                    "Environment Configuration",
                    "WARNING" if len(issues) == 1 else "UNHEALTHY",
                    f"Configuration issues: {', '.join(issues)}",
                    {
                        "issues": issues,
                        "env_vars": env_vars,
                        "dependencies": dict(dependencies)
                    },
                    time.time() - check_start
                )
                return False
                
        except Exception as e:
            self.log_check(
                "Environment Configuration",
                "UNHEALTHY",
                f"Environment check failed: {e}",
                {"error": str(e)},
                time.time() - check_start
            )
            return False
    
    async def check_performance_health(self) -> bool:
        """Check system performance characteristics"""
        check_start = time.time()
        
        try:
            # Quick workflow performance test
            from orchestrator import handle_disaster_event
            
            perf_test_incident = {
                "event_id": "perf_test_001",
                "event_type": "performance_test",
                "severity": 75,
                "location": "Performance Test",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "affected_population": 5000,
                "timestamp": datetime.now().isoformat(),
                "satellite_image": "mock_perf_test.tiff"
            }
            
            # Time the workflow
            workflow_start = time.time()
            result = await handle_disaster_event(perf_test_incident)
            workflow_duration = time.time() - workflow_start
            
            # Performance thresholds
            excellent_threshold = 5.0  # seconds
            good_threshold = 10.0
            poor_threshold = 20.0
            
            if workflow_duration <= excellent_threshold:
                status = "HEALTHY"
                message = f"Excellent performance: {workflow_duration:.1f}s"
            elif workflow_duration <= good_threshold:
                status = "HEALTHY"
                message = f"Good performance: {workflow_duration:.1f}s"
            elif workflow_duration <= poor_threshold:
                status = "WARNING"
                message = f"Acceptable performance: {workflow_duration:.1f}s"
            else:
                status = "UNHEALTHY"
                message = f"Poor performance: {workflow_duration:.1f}s"
            
            self.log_check(
                "Performance",
                status,
                message,
                {
                    "workflow_duration": workflow_duration,
                    "resources_allocated": result.get("resources_allocated", 0),
                    "alerts_sent": result.get("alerts_sent", 0),
                    "thresholds": {
                        "excellent": excellent_threshold,
                        "good": good_threshold,
                        "poor": poor_threshold
                    }
                },
                time.time() - check_start
            )
            return status in ["HEALTHY", "WARNING"]
            
        except Exception as e:
            self.log_check(
                "Performance",
                "UNHEALTHY",
                f"Performance check failed: {e}",
                {"error": str(e)},
                time.time() - check_start
            )
            return False
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        total_checks = len(self.results)
        healthy_count = sum(1 for r in self.results if r["status"] == "HEALTHY")
        warning_count = sum(1 for r in self.results if r["status"] == "WARNING")
        unhealthy_count = sum(1 for r in self.results if r["status"] == "UNHEALTHY")
        
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        # Overall system status
        if unhealthy_count > 0:
            overall_status = "UNHEALTHY"
        elif warning_count > 0:
            overall_status = "WARNING"
        else:
            overall_status = "HEALTHY"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "total_duration": total_duration,
            "summary": {
                "total_checks": total_checks,
                "healthy": healthy_count,
                "warning": warning_count,
                "unhealthy": unhealthy_count
            },
            "details": self.results,
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on health check results"""
        recommendations = []
        
        for result in self.results:
            if result["status"] == "UNHEALTHY":
                component = result["component"]
                if "Orchestrator" in component:
                    recommendations.append("🔧 Check orchestrator.py imports and dependencies")
                elif "Agent Tools" in component:
                    recommendations.append("🔧 Verify all agent tool files in agents/ directory")
                elif "Communications" in component:
                    recommendations.append("🔧 Configure SLACK_WEBHOOK_URL and Twilio credentials")
                elif "Visualizer" in component:
                    recommendations.append("🔧 Install missing visualization dependencies")
                elif "Environment" in component:
                    recommendations.append("🔧 Set GOOGLE_CLOUD_PROJECT environment variable")
                elif "Performance" in component:
                    recommendations.append("🔧 Check system resources and optimize workflow")
            
            elif result["status"] == "WARNING":
                component = result["component"]
                if "Communications" in component:
                    recommendations.append("⚡ Configure live communication channels for production")
                elif "Performance" in component:
                    recommendations.append("⚡ Consider performance optimization for better response times")
        
        # Remove duplicates
        return list(set(recommendations))
    
    def display_health_report(self, report: Dict[str, Any]):
        """Display formatted health report"""
        print("=" * 70)
        print("🩺 ResilientFlow System Health Report")
        print("=" * 70)
        
        # Overall status
        status_emoji = "✅" if report["overall_status"] == "HEALTHY" else "⚠️" if report["overall_status"] == "WARNING" else "❌"
        print(f"🎯 Overall Status: {status_emoji} {report['overall_status']}")
        print(f"⏱️  Total Check Duration: {report['total_duration']:.2f}s")
        print(f"📊 Checks: {report['summary']['healthy']}✅ {report['summary']['warning']}⚠️ {report['summary']['unhealthy']}❌")
        print()
        
        # Component breakdown
        print("📋 Component Health:")
        for result in report["details"]:
            emoji = "✅" if result["status"] == "HEALTHY" else "⚠️" if result["status"] == "WARNING" else "❌"
            print(f"  {emoji} {result['component']}: {result['status']}")
        print()
        
        # Recommendations
        if report["recommendations"]:
            print("💡 Recommendations:")
            for rec in report["recommendations"]:
                print(f"  {rec}")
            print()
        
        # Readiness assessment
        if report["overall_status"] == "HEALTHY":
            print("🚀 SYSTEM READY FOR DISASTER RESPONSE OPERATIONS!")
            print("✅ All critical components are healthy and operational")
        elif report["overall_status"] == "WARNING":
            print("⚠️  SYSTEM OPERATIONAL WITH WARNINGS")
            print("🔧 Address warnings before production deployment")
        else:
            print("❌ SYSTEM NOT READY FOR OPERATIONS")
            print("🚨 Critical issues must be resolved before deployment")
        
        print()
        print(f"📝 Report saved with {len(report['details'])} detailed check results")

async def main():
    """Run comprehensive system health check"""
    print("Starting ResilientFlow System Health Check")
    print("=" * 60)
    print("Validating all components for disaster response readiness...")
    print()
    
    # Create health checker
    health_checker = ResilientFlowHealthCheck()
    
    # Run all health checks
    await health_checker.check_environment_health()
    await health_checker.check_orchestrator_health()
    await health_checker.check_agent_tools_health()
    await health_checker.check_communications_health()
    await health_checker.check_visualizer_health()
    await health_checker.check_performance_health()
    
    # Generate and display report
    report = health_checker.generate_health_report()
    health_checker.display_health_report(report)
    
    # Save report to file
    report_filename = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Detailed report saved to: {report_filename}")
    except Exception as e:
        print(f"Could not save report: {e}")
    
    return report["overall_status"] == "HEALTHY"

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nHealth check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nHealth check failed with error: {e}")
        sys.exit(1) 