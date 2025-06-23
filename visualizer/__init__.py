# visualizer/__init__.py
import streamlit as st
from .app import AgentVisualizer

def get_or_create_visualizer() -> AgentVisualizer:
    """
    Get the visualizer instance from session state, creating it if it doesn't exist.
    This ensures that we use a single, persistent visualizer object across reruns.
    """
    if 'agent_visualizer_instance' not in st.session_state:
        st.session_state.agent_visualizer_instance = AgentVisualizer()
    return st.session_state.agent_visualizer_instance

def get_network_figure():
    """Get the current network visualization figure from the cached instance."""
    try:
        vis = get_or_create_visualizer()
        # Only draw if there are messages to display
        if not vis.messages:
            return None
        # This now uses the existing state of the visualizer, not rebuilding it
        return vis.draw_network()
    except Exception:
        # Fallback if an error occurs
        return None

def feed_trace(msg: dict):
    """Feed a trace message to the persistent visualizer instance."""
    try:
        vis = get_or_create_visualizer()
        vis.add_message(msg)
    except Exception:
        # Gracefully handle if streamlit context is not available
        pass

def get_stats():
    """Get current visualizer statistics from the cached instance."""
    try:
        vis = get_or_create_visualizer()
        
        if not vis.messages:
            return {'total_messages': 0, 'agents_active': 0, 'last_activity': None}
        
        # Get the timestamp of the most recent activity across all agents
        latest_activity_timestamp = max(vis.last_activity.values()) if vis.last_activity else None
        
        return {
            'total_messages': len(vis.messages),
            'agents_active': len(vis.agent_stats),
            'last_activity': latest_activity_timestamp
        }
    except Exception:
        # Fallback stats if an error occurs
        return {'total_messages': 0, 'agents_active': 0, 'last_activity': None} 