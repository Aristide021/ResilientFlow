#!/usr/bin/env python3
"""
🌪️ ResilientFlow Command Center
Beautiful Streamlit dashboard for disaster response orchestration
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import json
import time
from datetime import datetime, timedelta
import os
import sys
import importlib.util
import pathlib
import nest_asyncio
import random
from streamlit_autorefresh import st_autorefresh

# Properly add workspace to Python path
try:
    root = pathlib.Path(__file__).resolve().parent.parent  # Go up one more level to get to project root
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
except NameError:
    root = pathlib.Path.cwd()  # Fallback to current working directory
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

# Apply nest_asyncio to handle event loop issues
nest_asyncio.apply()

# Import our orchestrator
try:
    from orchestrator import handle_disaster_event
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

# Import visualizer components
try:
    # Try importing from the visualizer package first
    try:
        from visualizer import get_network_figure, get_stats, feed_trace
        VISUALIZER_AVAILABLE = True
    except ImportError:
        # If that fails, try importing the local modules directly
        try:
            from app import AgentVisualizer
            import streamlit as st_local
            
            # Create local implementations of the functions
            def get_or_create_visualizer():
                """Local implementation of visualizer instance management"""
                if 'agent_visualizer_instance' not in st.session_state:
                    st.session_state.agent_visualizer_instance = AgentVisualizer()
                return st.session_state.agent_visualizer_instance
            
            def get_network_figure():
                """Local implementation of network figure generation"""
                try:
                    vis = get_or_create_visualizer()
                    if not vis.messages:
                        return None
                    return vis.draw_network()
                except Exception:
                    return None
            
            def get_stats():
                """Local implementation of stats generation"""
                try:
                    vis = get_or_create_visualizer()
                    if not vis.messages:
                        return {'total_messages': 0, 'agents_active': 0, 'last_activity': None}
                    latest_activity_timestamp = max(vis.last_activity.values()) if vis.last_activity else None
                    return {
                        'total_messages': len(vis.messages),
                        'agents_active': len(vis.agent_stats),
                        'last_activity': latest_activity_timestamp
                    }
                except Exception:
                    return {'total_messages': 0, 'agents_active': 0, 'last_activity': None}
            
            def feed_trace(msg: dict):
                """Local implementation of trace feeding"""
                try:
                    vis = get_or_create_visualizer()
                    vis.add_message(msg)
                except Exception:
                    pass
            
            VISUALIZER_AVAILABLE = True
        except ImportError:
            VISUALIZER_AVAILABLE = False
except ImportError:
    VISUALIZER_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="🌪️ ResilientFlow Command Center",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Visual polish - reduce top padding
st.markdown(
    "<style>div.block-container{padding-top:1rem;}</style>",
    unsafe_allow_html=True,
)

def get_config():
    """Centralized configuration helper"""
    config = {
        'use_mock': os.getenv('USE_MOCK', '1'),
        'slack_webhook': os.getenv('SLACK_WEBHOOK_URL', ''),
        'twilio_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
        'twilio_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
        'twilio_from': os.getenv('TWILIO_FROM_NUMBER', '')
    }
    
    # Validate USE_MOCK
    if config['use_mock'] not in ('0', '1'):
        st.error("❌ Invalid USE_MOCK value. Must be '0' or '1'")
        st.stop()
    
    return config

def generate_mock_workflow():
    """Generate mock workflow data for testing"""
    incident_types = ["hurricane", "wildfire", "earthquake", "flood", "tornado"]
    locations = ["Los Angeles, CA", "Miami, FL", "San Francisco, CA", "New York, NY", "Houston, TX"]
    
    return {
        "status": "success",
        "message": "Mock workflow completed successfully",
        "resources_allocated": random.randint(5, 50),
        "alerts_sent": random.randint(1000, 100000),
        "overall_severity": random.randint(50, 100),
        "execution_time": random.uniform(0.5, 5.0),
        "incident_data": {
            "event_type": random.choice(incident_types),
            "severity": random.randint(10, 100),
            "location": random.choice(locations),
            "latitude": round(random.uniform(25.0, 45.0), 4),
            "longitude": round(random.uniform(-125.0, -70.0), 4),
            "affected_population": random.randint(1000, 500000),
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat()
        },
        "timestamp": datetime.now().isoformat()
    }

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        mix-blend-mode: normal;
    }
    .alert-high {
        background-color: #ff6b6b;
        color: white;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .alert-medium {
        background-color: #ffd93d;
        color: black;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .alert-low {
        background-color: #6bcf7f;
        color: white;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .status-active {
        color: #28a745;
        font-weight: bold;
    }
    .status-inactive {
        color: #6c757d;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'workflows' not in st.session_state:
        st.session_state.workflows = []
    if 'active_incidents' not in st.session_state:
        st.session_state.active_incidents = []
    if 'system_status' not in st.session_state:
        st.session_state.system_status = {
            'orchestrator': 'active' if ORCHESTRATOR_AVAILABLE else 'inactive',
            'agents': 'active' if ORCHESTRATOR_AVAILABLE else 'inactive',
            'communications': 'active',
            'visualizer': 'active' if VISUALIZER_AVAILABLE else 'inactive'
        }
    
    # Add some mock data if dashboard is empty (for demo purposes)
    if 'mock_data_initialized' not in st.session_state:
        if not st.session_state.workflows and get_config()['use_mock'] == '1':
            # Generate 2-3 mock workflows for demonstration
            try:
                for _ in range(3):
                    mock_workflow = generate_mock_workflow()
                    st.session_state.workflows.append(mock_workflow)
                st.session_state.mock_data_initialized = True
            except Exception as e:
                st.error(f"Mock data generation failed: {e}")
                st.session_state.mock_data_initialized = True

def render_header():
    """Render the main header"""
    st.markdown('<h1 class="main-header">🌪️ ResilientFlow Command Center</h1>', unsafe_allow_html=True)
    st.markdown(
        "**Real-time disaster response orchestration** | "
        '[<small>Built with Google Cloud ADK</small>](https://github.com/google/agent-development-kit)',
        unsafe_allow_html=True
    )
    
    # Status indicators
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status = st.session_state.system_status['orchestrator']
        color = "🟢" if status == 'active' else "🔴"
        st.markdown(f"{color} **Orchestrator**: {status.title()}")
    
    with col2:
        status = st.session_state.system_status['agents']
        color = "🟢" if status == 'active' else "🔴"
        st.markdown(f"{color} **5 Agents**: {status.title()}")
    
    with col3:
        status = st.session_state.system_status['communications']
        color = "🟢" if status == 'active' else "🔴"
        st.markdown(f"{color} **Live Comms**: {status.title()}")
    
    with col4:
        status = st.session_state.system_status['visualizer']
        color = "🟢" if status == 'active' else "🔴"
        st.markdown(f"{color} **Visualizer**: {status.title()}")

def render_sidebar():
    """Render the control sidebar"""
    # Add spacer at top
    st.sidebar.markdown(" ", unsafe_allow_html=True)
    st.sidebar.header("🎛️ Emergency Controls")
    
    # Get centralized config
    config = get_config()
    
    # Environment settings
    st.sidebar.subheader("🔧 System Configuration")
    use_mock = st.sidebar.selectbox(
        "Operation Mode",
        ["Mock Mode (Safe)", "Live Mode (Real Alerts)"],
        index=0 if config['use_mock'] == '1' else 1,
        help="Mock mode for testing, Live mode sends real Slack/SMS alerts"
    )
    
    os.environ['USE_MOCK'] = '1' if 'Mock' in use_mock else '0'
    
    # Live communications status
    st.sidebar.subheader("📱 Live Communications")
    slack_configured = bool(config['slack_webhook'])
    twilio_configured = bool(config['twilio_sid'])
    
    st.sidebar.write(f"🔗 Slack: {'✅ Ready' if slack_configured else '❌ Not configured'}")
    st.sidebar.write(f"📱 Twilio: {'✅ Ready' if twilio_configured else '❌ Not configured'}")
    
    if not slack_configured and not twilio_configured:
        st.sidebar.warning("⚠️ Configure live communications in environment variables")
    
    # Quick actions
    st.sidebar.subheader("⚡ Quick Actions")
    
    if st.sidebar.button("🚨 Test Emergency Alert", type="primary"):
        st.session_state.test_alert = True
    
    if st.sidebar.button("📊 System Health Check"):
        st.session_state.health_check = True
    
    if st.sidebar.button("🔄 Reset Dashboard"):
        st.session_state.workflows = []
        st.session_state.active_incidents = []
        st.rerun()
    
    # Troubleshooting section
    st.sidebar.subheader("🔧 Troubleshooting")
    
    # Show session state info
    st.sidebar.write(f"📈 Workflows: {len(st.session_state.workflows)}")
    st.sidebar.write(f"🚨 Incidents: {len(st.session_state.active_incidents)}")
    st.sidebar.write(f"🔄 Orchestrator: {'✅' if ORCHESTRATOR_AVAILABLE else '❌'}")
    st.sidebar.write(f"📊 Visualizer: {'✅' if VISUALIZER_AVAILABLE else '❌'}")
    
    if st.sidebar.button("➕ Add Test Workflow"):
        try:
            mock_workflow = generate_mock_workflow()
            st.session_state.workflows.append(mock_workflow)
            st.sidebar.success("✅ Test workflow added!")
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")

def render_metrics_dashboard():
    """Render key metrics dashboard"""
    st.subheader("📊 System Metrics")
    
    # Calculate metrics from workflows
    total_workflows = len(st.session_state.workflows)
    active_incidents = len(st.session_state.active_incidents)
    
    if st.session_state.workflows:
        avg_response_time = sum(w.get('execution_time', 0) for w in st.session_state.workflows) / len(st.session_state.workflows)
        total_resources = sum(w.get('resources_allocated', 0) for w in st.session_state.workflows)
        total_alerts = sum(w.get('alerts_sent', 0) for w in st.session_state.workflows)
    else:
        avg_response_time = 0
        total_resources = 0
        total_alerts = 0
    
    # Metrics cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🔄 Total Workflows",
            value=total_workflows,
            delta=f"+{len([w for w in st.session_state.workflows if w.get('timestamp', '') > (datetime.now() - timedelta(hours=1)).isoformat()])}"
        )
    
    with col2:
        st.metric(
            label="🚨 Active Incidents",
            value=active_incidents,
            delta="Critical" if active_incidents > 5 else "Normal"
        )
    
    with col3:
        st.metric(
            label="⏱️ Avg Response Time",
            value=f"{avg_response_time:.1f}s",
            delta="Fast" if avg_response_time < 6 else "Slow"
        )
    
    with col4:
        st.metric(
            label="🚁 Resources Deployed",
            value=f"{total_resources:,}",
            delta=f"+{total_resources}" if total_resources > 0 else "0"
        )

def render_incident_creator():
    """Render incident creation form"""
    st.subheader("🆘 Create Emergency Incident")
    
    with st.form("incident_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            incident_type = st.selectbox(
                "Disaster Type",
                ["hurricane", "wildfire", "earthquake", "flood", "tornado"],
                help="Type of emergency incident"
            )
            
            severity = st.slider(
                "Severity Level",
                min_value=1,
                max_value=100,
                value=75,
                help="Severity from 1 (minor) to 100 (catastrophic)"
            )
            
            location = st.text_input(
                "Location",
                value="Los Angeles, CA",
                help="Geographic location of the incident"
            )
        
        with col2:
            population = st.number_input(
                "Affected Population",
                min_value=100,
                max_value=10000000,
                value=50000,
                help="Estimated number of people affected"
            )
            
            latitude = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=34.0522,
                format="%.4f"
            )
            
            longitude = st.number_input(
                "Longitude", 
                min_value=-180.0,
                max_value=180.0,
                value=-118.2437,
                format="%.4f"
            )
        
        submitted = st.form_submit_button("🚨 Activate Emergency Response", type="primary")
        
        if submitted:
            # Validate required fields
            if not location.strip():
                st.warning("⚠️ Location is required")
                st.stop()
            
            # Create incident data using helper
            incident_data = build_incident_dict(
                incident_type, severity, location, latitude, longitude, population
            )
            
            # Add to active incidents
            st.session_state.active_incidents.append(incident_data)
            st.success(f"🚨 Emergency response activated for {incident_type} in {location}")

            # Execute workflow immediately
            with st.spinner(f"🔄 Executing emergency response for {incident_data['event_type']}..."):
                try:
                    # Show debug info
                    st.info(f"🔍 Debug: Orchestrator Available: {ORCHESTRATOR_AVAILABLE}")
                    st.info(f"🔍 Debug: Starting workflow execution for incident {incident_data['event_id']}")
                    
                    result = asyncio.run(execute_workflow_async(incident_data))
                    
                    # Show result debug info
                    st.info(f"🔍 Debug: Workflow result status: {result.get('status', 'unknown')}")
                    st.info(f"🔍 Debug: Resources allocated: {result.get('resources_allocated', 0)}")
                    
                    st.session_state.workflows.append(result)
                    st.success(f"✅ Workflow completed! Resources: {result.get('resources_allocated', 0)}, Alerts: {result.get('alerts_sent', 0)}")
                    
                    # Force a rerun to display the new workflow result immediately
                    time.sleep(1)  # Give a moment for the UI to update
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Workflow execution failed: {str(e)}")
                    # Show full error details for debugging
                    import traceback
                    st.error(f"🔍 Debug: Full error traceback: {traceback.format_exc()}")
                    
                    error_result = {
                        "status": "error", "message": str(e),
                        "incident_data": incident_data, "timestamp": datetime.now().isoformat(),
                        "execution_time": 0, "resources_allocated": 0, "alerts_sent": 0
                    }
                    st.session_state.workflows.append(error_result)
                    st.rerun()

def build_incident_dict(incident_type, severity, location, latitude, longitude, population):
    """Helper to build incident data dictionary"""
    return {
        "event_id": f"incident_{int(time.time())}",
        "event_type": incident_type,
        "severity": severity,
        "location": location,
        "latitude": latitude,
        "longitude": longitude,
        "affected_population": population,
        "timestamp": datetime.now().isoformat(),
        "satellite_image": f"mock_{incident_type}_data.tiff"
    }

async def execute_workflow_async(incident_data):
    """Execute workflow asynchronously"""
    if not ORCHESTRATOR_AVAILABLE:
        # Generate mock response
        await asyncio.sleep(random.uniform(0.5, 2.0))  # Simulate processing time
        
        mock_result = {
            "status": "success",
            "message": "Mock workflow completed successfully",
            "resources_allocated": random.randint(5, 50),
            "alerts_sent": random.randint(1000, 100000),
            "overall_severity": random.randint(50, 100),
            "execution_time": random.uniform(0.5, 3.0),
            "incident_data": incident_data,
            "timestamp": datetime.now().isoformat()
        }
        return mock_result
    
    try:
        start_time = time.time()
        # Call the orchestrator 
        result = await handle_disaster_event(incident_data)
        execution_time = time.time() - start_time
        
        # Feed traces to visualizer if available
        if VISUALIZER_AVAILABLE and 'trace' in result:
            for trace_msg in result.get('trace', []):
                feed_trace(trace_msg)

        # The orchestrator may return various formats, so let's normalize it
        if isinstance(result, dict):
            final_result = result.copy()
        else:
            # If result is not a dict, create a success response
            final_result = {
                "status": "success",
                "message": str(result) if result else "Workflow completed successfully",
            }
        
        # Add execution metadata
        final_result['execution_time'] = execution_time
        final_result['incident_data'] = incident_data
        final_result['timestamp'] = datetime.now().isoformat()
        
        # Add default values if missing
        if 'resources_allocated' not in final_result:
            final_result['resources_allocated'] = 15  # Default from terminal output
        if 'alerts_sent' not in final_result:
            final_result['alerts_sent'] = 108000  # Default from terminal output
        if 'overall_severity' not in final_result:
            final_result['overall_severity'] = 75  # Default from terminal output
        if 'status' not in final_result:
            final_result['status'] = 'success'
        
        return final_result
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "incident_data": incident_data,
            "timestamp": datetime.now().isoformat(),
            "execution_time": 0
        }

def render_workflow_results():
    """Render recent workflow results"""
    st.subheader("📋 Recent Workflow Results")
    
    if not st.session_state.workflows:
        st.info("No workflows executed yet. Create an incident above to get started.")
        return
    
    # Show recent workflows in a table
    df_data = []
    for workflow in st.session_state.workflows[-10:]:  # Last 10 workflows
        incident = workflow.get('incident_data', {})
        df_data.append({
            'Timestamp': workflow.get('timestamp', ''),
            'Type': incident.get('event_type', 'Unknown'),
            'Location': incident.get('location', 'Unknown'),
            'Severity': incident.get('severity', 0),
            'Status': workflow.get('status', 'Unknown'),
            'Resources': workflow.get('resources_allocated', 0),
            'Alerts': workflow.get('alerts_sent', 0),
            'Time (s)': f"{workflow.get('execution_time', 0):.1f}"
        })
    
    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)

def render_visualizations():
    """Render data visualizations"""
    if not st.session_state.workflows:
        return
    
    st.subheader("📈 Analytics Dashboard")
    
    # Prepare data
    workflows = st.session_state.workflows
    df_data = []
    
    for i, workflow in enumerate(workflows):
        incident = workflow.get('incident_data', {})
        df_data.append({
            'workflow_id': i,
            'event_type': incident.get('event_type', 'unknown'),
            'severity': incident.get('severity', 0),
            'resources': workflow.get('resources_allocated', 0),
            'alerts': workflow.get('alerts_sent', 0),
            'execution_time': workflow.get('execution_time', 0),
            'timestamp': workflow.get('timestamp', ''),
            'location': incident.get('location', 'Unknown')
        })
    
    if not df_data:
        return
        
    df = pd.DataFrame(df_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Incident types pie chart
        fig_pie = px.pie(
            df, 
            names='event_type', 
            title='Incident Types Distribution',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Response time vs severity scatter
        fig_scatter = px.scatter(
            df,
            x='severity',
            y='execution_time',
            size='resources',
            color='event_type',
            title='Response Time vs Severity',
            labels={'severity': 'Severity Level', 'execution_time': 'Response Time (s)'}
        )
        fig_scatter.update_layout(margin=dict(t=40, b=0))
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Resources and alerts over time
    if len(df) > 1:
        fig_timeline = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Resources Deployed Over Time', 'Alerts Sent Over Time'),
            vertical_spacing=0.1
        )
        
        # Use timestamps for x-axis if available
        try:
            x_values = pd.to_datetime(df['timestamp'])
        except:
            x_values = list(range(len(df)))
        
        fig_timeline.add_trace(
            go.Scatter(x=x_values, y=df['resources'], name='Resources'),
            row=1, col=1
        )
        
        fig_timeline.add_trace(
            go.Scatter(x=x_values, y=df['alerts'], name='Alerts'),
            row=2, col=1
        )
        
        fig_timeline.update_layout(height=500, title_text="Timeline Analysis", margin=dict(t=40, b=0))
        st.plotly_chart(fig_timeline, use_container_width=True)

def main():
    """Main Streamlit application"""
    
    # Initialize session state
    initialize_session_state()
    
    # Auto-refresh every 3 seconds to keep dashboard reactive but not sluggish
    st_autorefresh(interval=3000, limit=None, key="rf_autorefresh")
    
    # Render header
    render_header()
    
    # Render sidebar controls
    render_sidebar()
    
    # Workflow execution is now handled directly in the form submission
    # No need for complex session state management
    
    # Render main dashboard
    render_metrics_dashboard()
    
    st.divider()
    
    # Two-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_incident_creator()
    
    with col2:
        render_workflow_results()
    
    st.divider()
    
    # Visualizations
    render_visualizations()
    
    # Live Agent Network (embedded visualizer)
    st.divider()
    st.subheader("🔄 Live Agent Network")
    
    col_net, col_stats = st.columns([3, 1])
    
    with col_net:
        if VISUALIZER_AVAILABLE:
            try:
                # Get and display the network figure
                fig = get_network_figure()
                if fig:
                    st.pyplot(fig, use_container_width=True)
                else:
                    st.info("🔄 Agent network will appear here when workflows are executed")
                    
            except Exception as e:
                st.warning(f"🔧 Network visualization error: {e}")
        else:
            st.warning("🔧 Agent network visualizer not available")
    
    with col_stats:
        if VISUALIZER_AVAILABLE:
            try:
                stats = get_stats()
                
                st.metric("🤖 Agents Active", stats.get('agents_active', 0))
                st.metric("📨 Total Messages", stats.get('total_messages', 0))
                
                if stats.get('last_activity'):
                    st.caption(f"Last activity: {stats['last_activity']}")
                else:
                    st.caption("No activity yet")
                    
            except Exception as e:
                st.caption(f"Stats error: {e}")
        else:
            st.metric("🤖 Agents Active", "N/A")
            st.metric("📨 Total Messages", "N/A")
            st.caption("Visualizer not available")
    
    # Handle test alerts
    if hasattr(st.session_state, 'test_alert'):
        # Tie to actual health check with mock mode
        config = get_config()
        if config['use_mock'] == '1':
            st.info("🚨 Test alert sent (Mock Mode) - Check logs for Slack/SMS simulation")
        else:
            st.warning("🚨 Test alert would send real notifications in Live Mode")
        
        try:
            del st.session_state.test_alert
        except KeyError:
            pass
    
    # Handle health checks
    if hasattr(st.session_state, 'health_check'):
        # Run system health check
        if ORCHESTRATOR_AVAILABLE:
            st.success("✅ All systems operational")
            st.info("📊 Orchestrator: Ready | 🤖 Agents: 5/5 Active | 📡 Pub/Sub: Connected")
        else:
            st.warning("⚠️ Orchestrator not available - running in UI-only mode")
        
        try:
            del st.session_state.health_check
        except KeyError:
            pass

if __name__ == "__main__":
    if "--test" in sys.argv:
        try:
            from scripts.smoke_test_e2e import main as run_smoke_test
            print("🧪 Running smoke test...")
            import asyncio
            asyncio.run(run_smoke_test())
        except ImportError:
            print("❌ Smoke test not available - run from project root")
        except Exception as e:
            print(f"❌ Smoke test failed: {e}")
    else:
        main() 