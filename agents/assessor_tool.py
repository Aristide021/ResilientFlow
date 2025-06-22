"""
Impact Assessor Tool - ResilientFlow
ADK-compatible tool for spatial analysis and heat map generation.
Refactored from the original agent to be callable rather than a long-running service.
"""

import os
import sys
import time
import uuid
import asyncio
import random
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

def get_logger(name: str):
    """Simple logger for demo purposes"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

async def analyze_impact(
    disaster_events: List[Dict] = None,
    project_id: str = None,
    region: str = 'us-central1'
) -> Dict[str, Any]:
    """
    ADK Tool: Analyze spatial impact and generate heat maps from disaster events.
    """
    
    logger = get_logger('impact_assessor_tool')
    assessment_id = f"assessment_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    if not disaster_events:
        disaster_events = [
            {"latitude": 34.0522, "longitude": -118.2437, "severity_raw": 75, "event_type": "structural"}
        ]
    
    logger.info(f"Starting impact assessment", 
                extra={'assessment_id': assessment_id,
                      'events_count': len(disaster_events)})
    
    # Simulate processing time
    await asyncio.sleep(1.2)
    
    # Generate clusters from events
    clusters = []
    total_affected_population = 0
    overall_severity = 0
    
    for i, event in enumerate(disaster_events):
        cluster = {
            "cluster_id": f"cluster_{i+1}",
            "center_lat": event.get("latitude", 34.0522),
            "center_lon": event.get("longitude", -118.2437),
            "radius_km": random.uniform(1.5, 4.0),
            "severity": event.get("severity_raw", 70),
            "event_count": 1,
            "population_affected": random.randint(10000, 50000),
            "damage_types": [event.get("event_type", "structural")]
        }
        clusters.append(cluster)
        total_affected_population += cluster["population_affected"]
        overall_severity = max(overall_severity, cluster["severity"])
    
    # If no events, create a default scenario
    if not clusters:
        clusters = [{
            "cluster_id": "cluster_1",
            "center_lat": 34.0522,
            "center_lon": -118.2437,
            "radius_km": 2.5,
            "severity": 75,
            "event_count": 1,
            "population_affected": 25000,
            "damage_types": ["structural"]
        }]
        total_affected_population = 25000
        overall_severity = 75
    
    # Generate heat map data
    heat_map_url = f"gs://resilientflow-maps/heatmap_{assessment_id}.png"
    
    result = {
        "assessment_id": assessment_id,
        "overall_severity": overall_severity,
        "total_clusters": len(clusters),
        "affected_population": total_affected_population,
        "clusters": clusters,
        "heat_map_url": heat_map_url,
        "analysis_timestamp": datetime.now().isoformat(),
        "processing_time_ms": 1200,
        "status": "SUCCESS"
    }
    
    logger.info(f"Impact assessment completed successfully",
               extra={'assessment_id': assessment_id,
                     'clusters': len(clusters),
                     'severity': overall_severity})
    
    return result