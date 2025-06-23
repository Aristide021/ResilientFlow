#!/usr/bin/env python3
"""
ResilientFlow Agent Sequence Visualizer
Real-time visualization of agent interactions via Pub/Sub traces
"""

import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from google.cloud import pubsub_v1
import json
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
import os

# Set matplotlib backend for web
import matplotlib
matplotlib.use('Agg')

# Page config
st.set_page_config(
    page_title="ResilientFlow Agent Visualizer",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Agent colors and positions
AGENT_CONFIG = {
    "data_aggregator": {"color": "#FF6B6B", "pos": (0, 2), "emoji": "📡"},
    "impact_assessor": {"color": "#4ECDC4", "pos": (2, 2), "emoji": "🗺️"},
    "resource_allocator": {"color": "#45B7D1", "pos": (4, 2), "emoji": "🚚"},
    "comms_coordinator": {"color": "#96CEB4", "pos": (1, 0), "emoji": "📢"},
    "report_synthesizer": {"color": "#FFEAA7", "pos": (3, 0), "emoji": "📄"}
}

class AgentVisualizer:
    def __init__(self):
        self.messages = deque(maxlen=100)  # Keep last 100 messages
        self.agent_stats = defaultdict(int)
        self.edge_weights = defaultdict(int)
        self.last_activity = {}
        
    def add_message(self, trace_data):
        """Add a new trace message"""
        timestamp = datetime.now()
        self.messages.append({
            "timestamp": timestamp,
            "data": trace_data
        })
        
        # Update stats
        source = trace_data.get("source_agent", "unknown")
        target = trace_data.get("target_agent", "unknown")
        
        self.agent_stats[source] += 1
        self.edge_weights[(source, target)] += 1
        self.last_activity[source] = timestamp
        
    def create_network_graph(self):
        """Create NetworkX graph for visualization"""
        G = nx.DiGraph()
        
        # Add nodes (agents)
        for agent, config in AGENT_CONFIG.items():
            G.add_node(agent, **config)
            
        # Add edges from recent messages (last 30 seconds)
        recent_cutoff = datetime.now() - timedelta(seconds=30)
        recent_edges = defaultdict(int)
        
        for msg in self.messages:
            if msg["timestamp"] > recent_cutoff:
                source = msg["data"].get("source_agent")
                target = msg["data"].get("target_agent")
                if source and target and source != target:
                    recent_edges[(source, target)] += 1
                    
        # Add edges to graph
        for (source, target), weight in recent_edges.items():
            if source in AGENT_CONFIG and target in AGENT_CONFIG:
                G.add_edge(source, target, weight=weight)
                
        return G
        
    def draw_network(self):
        """Draw the network visualization"""
        G = self.create_network_graph()
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.set_facecolor('#1e1e1e')
        fig.patch.set_facecolor('#1e1e1e')
        
        # Get positions
        pos = {agent: config["pos"] for agent, config in AGENT_CONFIG.items()}
        
        # Draw nodes
        for agent, config in AGENT_CONFIG.items():
            x, y = pos[agent]
            
            # Agent activity indicator
            last_active = self.last_activity.get(agent)
            if last_active and (datetime.now() - last_active).seconds < 5:
                # Recently active - larger, brighter
                circle = patches.Circle((x, y), 0.3, color=config["color"], 
                                      alpha=0.9, linewidth=3, edgecolor='white')
            else:
                # Inactive - smaller, dimmer
                circle = patches.Circle((x, y), 0.2, color=config["color"], 
                                      alpha=0.6, linewidth=1, edgecolor='gray')
            
            ax.add_patch(circle)
            
            # Agent label
            ax.text(x, y-0.5, f'{config["emoji"]}\n{agent.replace("_", "\n")}', 
                   ha='center', va='center', fontsize=8, color='white', weight='bold')
                   
        # Draw edges with animation effect
        for edge in G.edges(data=True):
            source, target = edge[0], edge[1]
            weight = edge[2].get('weight', 1)
            
            x1, y1 = pos[source]
            x2, y2 = pos[target]
            
            # Arrow with thickness based on message frequency
            arrow_width = min(weight * 0.5, 3.0)
            ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                       arrowprops=dict(arrowstyle='->', lw=arrow_width, 
                                     color='#00ff88', alpha=0.8))
                                     
            # Message count label
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x, mid_y, str(weight), ha='center', va='center',
                   fontsize=10, color='#00ff88', weight='bold',
                   bbox=dict(boxstyle="round,pad=0.1", facecolor='black', alpha=0.7))
        
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 3)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('ResilientFlow Agent Communication', 
                    fontsize=16, color='white', weight='bold', pad=20)
        
        return fig

def pubsub_listener(project_id, subscription_name, visualizer):
    """Listen to Pub/Sub messages in background thread"""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    
    def callback(message):
        try:
            data = json.loads(message.data.decode('utf-8'))
            if 'TRACE' in data.get('message', ''):
                visualizer.add_message(data)
            message.ack()
        except Exception as e:
            st.error(f"Error processing message: {e}")
            message.ack()
    
    try:
        # Non-blocking pull
        flow_control = pubsub_v1.types.FlowControl(max_messages=10)
        subscriber.subscribe(subscription_path, callback=callback, 
                           flow_control=flow_control)
    except Exception as e:
        st.error(f"Failed to connect to Pub/Sub: {e}")

def main():
    st.title("🌪️ ResilientFlow Agent Visualizer")
    st.markdown("Real-time visualization of disaster relief agent communications")
    
    # Sidebar controls
    st.sidebar.header("Configuration")
    project_id = st.sidebar.text_input("GCP Project ID", 
                                       value=os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    subscription_name = st.sidebar.text_input("Pub/Sub Subscription", 
                                              value="rf-visualizer-events-sub")
    
    auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh Interval (s)", 1, 10, 2)
    
    # Initialize visualizer
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = AgentVisualizer()
        
    visualizer = st.session_state.visualizer
    
    # Start Pub/Sub listener
    if project_id and subscription_name:
        if 'pubsub_thread' not in st.session_state:
            thread = threading.Thread(
                target=pubsub_listener, 
                args=(project_id, subscription_name, visualizer),
                daemon=True
            )
            thread.start()
            st.session_state.pubsub_thread = thread
            st.sidebar.success("✅ Connected to Pub/Sub")
    else:
        st.sidebar.warning("⚠️ Enter Project ID and Subscription")
    
    # Main visualization area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Agent Network")
        
        # Create and display network graph
        try:
            fig = visualizer.draw_network()
            st.pyplot(fig)
            plt.close(fig)  # Prevent memory leaks
        except Exception as e:
            st.error(f"Error creating visualization: {e}")
    
    with col2:
        st.subheader("Agent Statistics")
        
        # Agent activity stats
        for agent, count in visualizer.agent_stats.items():
            last_active = visualizer.last_activity.get(agent)
            if last_active:
                time_ago = (datetime.now() - last_active).seconds
                status = "🟢" if time_ago < 10 else "🟡" if time_ago < 60 else "🔴"
            else:
                status = "⚪"
                
            st.metric(
                label=f"{status} {agent.replace('_', ' ').title()}",
                value=count,
                delta=f"Last: {time_ago}s ago" if last_active else "Never"
            )
        
        st.subheader("Recent Messages")
        
        # Show recent trace messages
        recent_messages = list(visualizer.messages)[-5:]  # Last 5 messages
        for msg in reversed(recent_messages):
            timestamp = msg["timestamp"].strftime("%H:%M:%S")
            data = msg["data"]
            source = data.get("source_agent", "?")
            action = data.get("action", "unknown")
            
            st.text(f"{timestamp}")
            st.text(f"  {source} → {action}")
            st.text("---")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
    
    # Manual refresh button
    if st.button("🔄 Refresh Now"):
        st.rerun()
        
    # Demo data generator
    st.sidebar.markdown("---")
    st.sidebar.subheader("Demo Mode")
    
    if st.sidebar.button("🎮 Generate Demo Data"):
        # Add some demo trace messages
        demo_traces = [
            {"source_agent": "data_aggregator", "target_agent": "impact_assessor", 
             "action": "process_satellite_image", "correlation_id": "demo_001"},
            {"source_agent": "impact_assessor", "target_agent": "resource_allocator", 
             "action": "update_impact_zones", "correlation_id": "demo_001"},
            {"source_agent": "resource_allocator", "target_agent": "comms_coordinator", 
             "action": "allocation_complete", "correlation_id": "demo_001"},
            {"source_agent": "comms_coordinator", "target_agent": "report_synthesizer", 
             "action": "alerts_sent", "correlation_id": "demo_001"}
        ]
        
        for trace in demo_traces:
            visualizer.add_message(trace)
            time.sleep(0.5)
        
        st.sidebar.success("✅ Demo data generated!")
        st.rerun()

if __name__ == "__main__":
    main() 