"""
Resource Allocator Tool - ResilientFlow
ADK-compatible tool for resource optimization and logistics planning.
Refactored from the original agent to be callable rather than a long-running service.
"""

import os
import sys
import time
import uuid
import asyncio
import random
from typing import Dict, Any, List, Optional

def get_logger(name: str):
    """Simple logger for demo purposes"""
    import logging
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

async def optimize_resource_allocation(
    impact_data: Dict[str, Any] = None,
    project_id: str = None,
    region: str = 'us-central1'
) -> Dict[str, Any]:
    """
    ADK Tool: Optimize resource allocation and generate logistics plans.
    """
    
    logger = get_logger('resource_allocator_tool')
    allocation_id = f"allocation_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    if not impact_data:
        impact_data = {"overall_severity": 75, "clusters": []}
    
    logger.info(f"Starting resource allocation optimization", 
                extra={'allocation_id': allocation_id,
                      'severity': impact_data.get('overall_severity', 0)})
    
    # Simulate processing time
    await asyncio.sleep(1.2)
    
    overall_severity = impact_data.get('overall_severity', 75)
    clusters = impact_data.get('clusters', [])
    
    # Generate resource allocations based on severity and clusters
    allocations = []
    total_resources = 0
    
    if overall_severity >= 80:
        # High severity - deploy maximum resources
        resource_types = ['ambulance', 'fire_truck', 'rescue_helicopter', 'mobile_hospital']
        base_count = 5
    elif overall_severity >= 60:
        # Medium severity
        resource_types = ['ambulance', 'fire_truck', 'rescue_team']
        base_count = 3
    else:
        # Low severity
        resource_types = ['ambulance', 'rescue_team']
        base_count = 2
    
    # Create allocations for each cluster or default location
    locations = clusters if clusters else [{"center_lat": 34.0522, "center_lon": -118.2437, "severity_score": overall_severity}]
    
    for i, location in enumerate(locations):
        for resource_type in resource_types:
            count = max(1, base_count - i)  # Fewer resources for secondary locations
            
            allocation = {
                "allocation_id": f"{allocation_id}_{resource_type}_{i}",
                "resource_type": resource_type,
                "quantity": count,
                "target_lat": location.get('center_lat', 34.0522),
                "target_lon": location.get('center_lon', -118.2437),
                "priority": _calculate_priority(location.get('severity_score', overall_severity)),
                "estimated_arrival_minutes": random.randint(15, 45),
                "deployment_status": "planned"
            }
            allocations.append(allocation)
            total_resources += count
    
    # Generate supply requirements
    supply_plan = _generate_supply_plan(overall_severity, len(locations))
    
    # Generate vehicle routing
    vehicle_routes = _generate_vehicle_routes(allocations)
    
    result = {
        "allocation_id": allocation_id,
        "overall_severity": overall_severity,
        "total_resources": total_resources,
        "allocations": allocations,
        "supply_plan": supply_plan,
        "vehicle_routes": vehicle_routes,
        "estimated_cost": total_resources * 15000,  # $15k per resource
        "deployment_time_estimate_minutes": max([a["estimated_arrival_minutes"] for a in allocations] or [30]),
        "processing_time_ms": 1200,
        "status": "SUCCESS"
    }
    
    logger.info(f"Resource allocation optimization completed",
               extra={'allocation_id': allocation_id,
                     'total_resources': total_resources,
                     'allocations': len(allocations)})
    
    return result


def _calculate_priority(severity: int) -> str:
    """Calculate priority level based on severity"""
    if severity >= 80:
        return "CRITICAL"
    elif severity >= 60:
        return "HIGH"
    elif severity >= 40:
        return "MEDIUM"
    else:
        return "LOW"


def _generate_supply_plan(severity: int, location_count: int) -> Dict[str, Any]:
    """Generate supply requirements plan"""
    base_supplies = {
        "medical_kits": 50,
        "water_bottles": 1000,
        "emergency_blankets": 200,
        "food_rations": 500
    }
    
    # Scale supplies based on severity and locations
    multiplier = (severity / 100.0) * location_count
    
    return {
        "supply_id": f"supply_{int(time.time() * 1000)}",
        "requirements": {
            item: int(quantity * multiplier) 
            for item, quantity in base_supplies.items()
        },
        "distribution_points": location_count,
        "estimated_delivery_hours": 6 if severity >= 80 else 12
    }


def _generate_vehicle_routes(allocations: List[Dict]) -> List[Dict]:
    """Generate optimal vehicle routing plans"""
    routes = []
    
    # Group allocations by location
    location_groups = {}
    for allocation in allocations:
        key = f"{allocation['target_lat']:.4f}_{allocation['target_lon']:.4f}"
        if key not in location_groups:
            location_groups[key] = []
        location_groups[key].append(allocation)
    
    # Create routes for each location group
    for i, (location_key, group_allocations) in enumerate(location_groups.items()):
        lat, lon = location_key.split('_')
        
        route = {
            "route_id": f"route_{i}",
            "destination_lat": float(lat),
            "destination_lon": float(lon),
            "resource_count": len(group_allocations),
            "vehicle_types": list(set([a["resource_type"] for a in group_allocations])),
            "estimated_distance_km": random.randint(25, 75),
            "estimated_duration_minutes": random.randint(30, 90),
            "fuel_cost_estimate": random.randint(150, 400)
        }
        routes.append(route)
    
    return routes 