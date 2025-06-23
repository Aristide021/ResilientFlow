# visualizer/__init__.py
# Simplified module for trace-based visualization (network visualization removed)

def feed_trace(msg: dict):
    """Feed a trace message for simple logging (placeholder for compatibility)."""
    # This is now a placeholder since we switched to trace-based rendering
    # in streamlit_app.py rather than network visualization
    pass

def get_stats():
    """Get basic stats (placeholder for compatibility)."""
    return {'total_messages': 0, 'agents_active': 0, 'last_activity': None}

def get_network_figure():
    """Network figure is no longer used - trace visualization used instead."""
    return None 