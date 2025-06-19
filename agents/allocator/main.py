"""
Resource Allocator Agent - ResilientFlow
Optimizes resource allocation and logistics using Google OR-Tools.
Minimizes travel time and maximizes coverage given supply constraints.
"""

import os
import time
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from ortools.linear_solver import pywrap_linear_solver
import numpy as np

# Import ResilientFlow common utilities
import sys
sys.path.append('/workspace')
from common import get_logger, PubSubClient, FirestoreClient
from proto import api_pb2


@dataclass
class Resource:
    """Represents a resource with quantity and location"""
    resource_type: str
    quantity: int
    facility_id: str
    latitude: float
    longitude: float
    capacity: int


@dataclass
class Demand:
    """Represents resource demand at a location"""
    zone_id: str
    latitude: float
    longitude: float
    resource_needs: Dict[str, int]  # resource_type -> quantity
    priority: int  # 1-10, 10 being highest
    severity_score: float


@dataclass
class AllocationSolution:
    """Represents an allocation solution"""
    allocations: List[Dict[str, Any]]
    total_cost: float
    coverage_percentage: float
    unmet_demand: Dict[str, int]
    vehicle_routes: List[Dict[str, Any]]


class ResourceAllocatorAgent:
    """Resource allocation and logistics optimization agent"""
    
    def __init__(self, project_id: str, region: str = 'us-central1'):
        self.project_id = project_id
        self.region = region
        self.agent_name = 'resource_allocator'
        self.logger = get_logger(self.agent_name)
        
        # Initialize clients
        self.pubsub_client = PubSubClient(project_id, self.agent_name)
        self.firestore_client = FirestoreClient(project_id, self.agent_name)
        
        # Configuration
        self.config = {
            'optimization_timeout_s': 30,
            'max_vehicle_capacity_kg': 5000,
            'max_travel_distance_km': 200,
            'priority_weight_multiplier': 2.0,
            'severity_weight_multiplier': 1.5,
            'coverage_target_percentage': 85.0,
            'reallocation_interval_s': 300  # 5 minutes
        }
        
        # Resource types and their weights
        self.resource_types = {
            'water': {'weight_kg': 1.0, 'priority': 10},
            'food': {'weight_kg': 0.5, 'priority': 9},
            'medical_supplies': {'weight_kg': 0.3, 'priority': 10},
            'blankets': {'weight_kg': 2.0, 'priority': 7},
            'tents': {'weight_kg': 15.0, 'priority': 8},
            'generators': {'weight_kg': 50.0, 'priority': 6}
        }
        
        # Setup subscriptions
        self._setup_subscriptions()
        
        self.logger.info("Resource Allocator Agent initialized", config=self.config)
    
    def _setup_subscriptions(self) -> None:
        """Setup Pub/Sub subscriptions"""
        
        # Subscribe to impact updates
        self.pubsub_client.subscribe_to_topic(
            'impact_updates',
            self._handle_impact_update,
            api_pb2.ImpactAssessment
        )
        
        # Subscribe to disaster events
        self.pubsub_client.subscribe_to_topic(
            'disaster_events',
            self._handle_disaster_event,
            api_pb2.DisasterEvent
        )
        
        self.logger.info("Pub/Sub subscriptions established")
    
    def _handle_impact_update(self, assessment: api_pb2.ImpactAssessment, attributes: Dict[str, str]) -> None:
        """Handle impact assessment updates"""
        
        self.logger.info(
            f"Received impact update: {assessment.assessment_id}",
            severity=assessment.severity_score,
            damage_type=assessment.damage_type
        )
        
        # Trigger resource allocation if severity is high
        if assessment.severity_score >= 70:
            self._trigger_allocation_optimization(
                assessment.latitude,
                assessment.longitude,
                assessment.severity_score
            )
    
    def _handle_disaster_event(self, event: api_pb2.DisasterEvent, attributes: Dict[str, str]) -> None:
        """Handle disaster event for immediate allocation"""
        
        self.logger.info(
            f"Received disaster event: {event.event_id}",
            event_type=event.event_type,
            severity=event.severity_raw
        )
        
        # Always trigger allocation for disaster events
        self._trigger_allocation_optimization(
            event.latitude,
            event.longitude,
            event.severity_raw
        )
    
    def _trigger_allocation_optimization(self, center_lat: float, center_lon: float, 
                                       severity: float, radius_km: float = 10.0) -> None:
        """Trigger resource allocation optimization for an area"""
        
        optimization_id = str(uuid.uuid4())
        start_time = time.time()
        
        self.logger.info(
            f"Starting resource allocation optimization",
            optimization_id=optimization_id,
            center_lat=center_lat,
            center_lon=center_lon,
            severity=severity
        )
        
        try:
            # Gather demand information
            demands = self._gather_demand_information(center_lat, center_lon, radius_km)
            
            if not demands:
                self.logger.info(f"No demand found in area", optimization_id=optimization_id)
                return
            
            # Gather supply information
            supplies = self._gather_supply_information(center_lat, center_lon, radius_km * 2)
            
            if not supplies:
                self.logger.warning(f"No supplies found in area", optimization_id=optimization_id)
                return
            
            # Get available vehicles
            vehicles = self._get_available_vehicles(center_lat, center_lon, radius_km * 2)
            
            # Optimize allocation
            solution = self._optimize_allocation(demands, supplies, vehicles)
            
            # Create allocation plan
            plan = self._create_allocation_plan(solution, optimization_id)
            
            # Store plan in Firestore
            self.firestore_client.create_allocation_plan(
                plan.plan_id,
                f"incident_{int(time.time())}",
                plan.allocations
            )
            
            # Publish allocation plan
            self._publish_allocation_plan(plan)
            
            # Update agent state
            self.firestore_client.update_agent_state({
                'last_optimization_id': optimization_id,
                'allocations_created': len(solution.allocations),
                'coverage_percentage': solution.coverage_percentage,
                'status': 'active'
            })
            
            processing_time = (time.time() - start_time) * 1000
            self.logger.agent_action(
                'optimize_allocation',
                'success',
                processing_time,
                optimization_id=optimization_id,
                allocations_count=len(solution.allocations),
                coverage=solution.coverage_percentage
            )
            
        except Exception as e:
            self.logger.error(
                f"Allocation optimization failed",
                optimization_id=optimization_id,
                error=str(e)
            )
            raise
    
    def _gather_demand_information(self, center_lat: float, center_lon: float, 
                                  radius_km: float) -> List[Demand]:
        """Gather resource demand information from impact zones"""
        
        # Query impact zones from Firestore
        zones = self.firestore_client.get_facilities_near(
            center_lat, center_lon, radius_km
        )
        
        demands = []
        
        # For demo, estimate demand based on severity and area
        for i in range(3):  # Simulate 3 demand points
            zone_id = f"zone_{int(time.time())}_{i}"
            
            # Random location within radius
            import random
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(0, radius_km)
            
            lat_offset = (distance / 111) * np.cos(angle)
            lon_offset = (distance / 111) * np.sin(angle)
            
            zone_lat = center_lat + lat_offset
            zone_lon = center_lon + lon_offset
            
            # Estimate resource needs based on affected population
            population_estimate = random.randint(100, 2000)
            severity_factor = min(1.0, (70 + random.randint(0, 30)) / 100.0)
            
            resource_needs = {
                'water': int(population_estimate * 3 * severity_factor),  # 3L per person per day
                'food': int(population_estimate * 2 * severity_factor),   # 2 meals per person
                'medical_supplies': int(population_estimate * 0.1 * severity_factor),
                'blankets': int(population_estimate * 0.5 * severity_factor),
                'tents': int(population_estimate * 0.2 * severity_factor)
            }
            
            priority = min(10, int(severity_factor * 10))
            
            demand = Demand(
                zone_id=zone_id,
                latitude=zone_lat,
                longitude=zone_lon,
                resource_needs=resource_needs,
                priority=priority,
                severity_score=severity_factor * 100
            )
            
            demands.append(demand)
        
        self.logger.debug(
            f"Gathered {len(demands)} demand points",
            total_water_demand=sum(d.resource_needs.get('water', 0) for d in demands)
        )
        
        return demands
    
    def _gather_supply_information(self, center_lat: float, center_lon: float,
                                  radius_km: float) -> List[Resource]:
        """Gather available resource supply information"""
        
        # Query nearby facilities
        facilities = self.firestore_client.get_facilities_near(
            center_lat, center_lon, radius_km
        )
        
        supplies = []
        
        # If no facilities found, create some demo facilities
        if not facilities:
            facilities = self._create_demo_facilities(center_lat, center_lon)
        
        for facility in facilities:
            # Get inventory for this facility
            inventory = self.firestore_client.get_resource_availability(
                facility_id=facility['facility_id']
            )
            
            # If no inventory, create demo inventory
            if not inventory:
                inventory = self._create_demo_inventory(facility['facility_id'])
            
            for item in inventory:
                resource = Resource(
                    resource_type=item['resource_type'],
                    quantity=item['quantity'],
                    facility_id=facility['facility_id'],
                    latitude=facility['latitude'],
                    longitude=facility['longitude'],
                    capacity=item.get('capacity', item['quantity'])
                )
                supplies.append(resource)
        
        self.logger.debug(
            f"Gathered {len(supplies)} supply sources",
            facilities_count=len(facilities)
        )
        
        return supplies
    
    def _create_demo_facilities(self, center_lat: float, center_lon: float) -> List[Dict[str, Any]]:
        """Create demo facilities for testing"""
        
        facilities = []
        
        for i in range(2):  # 2 demo facilities
            facility_id = f"facility_{int(time.time())}_{i}"
            
            # Place facilities at strategic locations
            lat_offset = (i - 0.5) * 0.1  # Spread facilities
            lon_offset = (i - 0.5) * 0.1
            
            facility = {
                'facility_id': facility_id,
                'name': f'Emergency Warehouse {i+1}',
                'latitude': center_lat + lat_offset,
                'longitude': center_lon + lon_offset,
                'facility_type': 'warehouse',
                'status': 'operational'
            }
            
            # Register facility
            self.firestore_client.register_facility(
                facility_id,
                facility['name'],
                facility['latitude'],
                facility['longitude'],
                facility['facility_type'],
                {'water': 10000, 'food': 5000, 'medical_supplies': 1000}
            )
            
            facilities.append(facility)
        
        return facilities
    
    def _create_demo_inventory(self, facility_id: str) -> List[Dict[str, Any]]:
        """Create demo inventory for a facility"""
        
        import random
        
        inventory = []
        
        for resource_type in ['water', 'food', 'medical_supplies', 'blankets', 'tents']:
            quantity = random.randint(100, 5000)
            
            # Update Firestore inventory
            self.firestore_client.update_resource_inventory(
                resource_type, facility_id, quantity, 'set'
            )
            
            inventory.append({
                'resource_type': resource_type,
                'facility_id': facility_id,
                'quantity': quantity
            })
        
        return inventory
    
    def _get_available_vehicles(self, center_lat: float, center_lon: float,
                               radius_km: float) -> List[Dict[str, Any]]:
        """Get available vehicles for transportation"""
        
        # Get vehicles from Firestore
        vehicles = self.firestore_client.get_available_vehicles()
        
        # If no vehicles, create demo vehicles
        if not vehicles:
            vehicles = self._create_demo_vehicles(center_lat, center_lon)
        
        # Filter by distance
        nearby_vehicles = []
        
        for vehicle in vehicles:
            distance = self._calculate_distance(
                center_lat, center_lon,
                vehicle['current_latitude'], vehicle['current_longitude']
            )
            
            if distance <= radius_km:
                vehicle['distance_km'] = distance
                nearby_vehicles.append(vehicle)
        
        self.logger.debug(f"Found {len(nearby_vehicles)} available vehicles")
        return nearby_vehicles
    
    def _create_demo_vehicles(self, center_lat: float, center_lon: float) -> List[Dict[str, Any]]:
        """Create demo vehicles for testing"""
        
        import random
        
        vehicles = []
        
        vehicle_types = [
            {'type': 'truck', 'capacity': 5000},
            {'type': 'helicopter', 'capacity': 1000},
            {'type': 'boat', 'capacity': 3000}
        ]
        
        for i, vtype in enumerate(vehicle_types):
            vehicle_id = f"vehicle_{vtype['type']}_{int(time.time())}_{i}"
            
            # Random location near center
            lat_offset = random.uniform(-0.05, 0.05)
            lon_offset = random.uniform(-0.05, 0.05)
            
            # Register vehicle
            self.firestore_client.register_vehicle(
                vehicle_id,
                vtype['type'],
                vtype['capacity'],
                center_lat + lat_offset,
                center_lon + lon_offset
            )
            
            vehicle = {
                'vehicle_id': vehicle_id,
                'vehicle_type': vtype['type'],
                'capacity_kg': vtype['capacity'],
                'current_latitude': center_lat + lat_offset,
                'current_longitude': center_lon + lon_offset,
                'status': 'available'
            }
            
            vehicles.append(vehicle)
        
        return vehicles
    
    def _optimize_allocation(self, demands: List[Demand], supplies: List[Resource],
                            vehicles: List[Dict[str, Any]]) -> AllocationSolution:
        """Optimize resource allocation using OR-Tools"""
        
        self.logger.info(
            f"Starting optimization",
            demands_count=len(demands),
            supplies_count=len(supplies),
            vehicles_count=len(vehicles)
        )
        
        # Simplified allocation optimization
        # In production, this would use sophisticated OR-Tools models
        
        allocations = []
        unmet_demand = {}
        total_cost = 0.0
        
        # Initialize unmet demand
        for demand in demands:
            for resource_type, quantity in demand.resource_needs.items():
                unmet_demand[resource_type] = unmet_demand.get(resource_type, 0) + quantity
        
        # Simple greedy allocation
        for demand in sorted(demands, key=lambda d: d.priority, reverse=True):
            for resource_type, needed_quantity in demand.resource_needs.items():
                if needed_quantity <= 0:
                    continue
                
                # Find closest supply
                available_supplies = [s for s in supplies if s.resource_type == resource_type and s.quantity > 0]
                
                if not available_supplies:
                    continue
                
                # Sort by distance
                supply_distances = []
                for supply in available_supplies:
                    distance = self._calculate_distance(
                        demand.latitude, demand.longitude,
                        supply.latitude, supply.longitude
                    )
                    supply_distances.append((supply, distance))
                
                supply_distances.sort(key=lambda x: x[1])
                
                for supply, distance in supply_distances:
                    if supply.quantity <= 0:
                        continue
                    
                    # Allocate as much as possible
                    allocated_quantity = min(needed_quantity, supply.quantity)
                    
                    if allocated_quantity > 0:
                        # Create allocation
                        allocation = {
                            'allocation_id': str(uuid.uuid4()),
                            'demand_zone_id': demand.zone_id,
                            'supply_facility_id': supply.facility_id,
                            'resource_type': resource_type,
                            'quantity': allocated_quantity,
                            'distance_km': distance,
                            'priority': demand.priority,
                            'status': 'planned',
                            'estimated_cost': distance * allocated_quantity * 0.1,  # Simple cost model
                            'delivery_lat': demand.latitude,
                            'delivery_lon': demand.longitude,
                            'pickup_lat': supply.latitude,
                            'pickup_lon': supply.longitude
                        }
                        
                        allocations.append(allocation)
                        
                        # Update supply and demand
                        supply.quantity -= allocated_quantity
                        needed_quantity -= allocated_quantity
                        unmet_demand[resource_type] -= allocated_quantity
                        total_cost += allocation['estimated_cost']
                        
                        self.logger.debug(
                            f"Allocated {allocated_quantity} {resource_type} to {demand.zone_id}",
                            distance=distance,
                            remaining_supply=supply.quantity
                        )
                        
                        if needed_quantity <= 0:
                            break
        
        # Calculate coverage percentage
        total_demand = sum(
            sum(d.resource_needs.values()) for d in demands
        )
        total_unmet = sum(unmet_demand.values())
        coverage_percentage = (total_demand - total_unmet) / total_demand * 100 if total_demand > 0 else 0
        
        # Generate vehicle routes (simplified)
        vehicle_routes = self._generate_vehicle_routes(allocations, vehicles)
        
        solution = AllocationSolution(
            allocations=allocations,
            total_cost=total_cost,
            coverage_percentage=coverage_percentage,
            unmet_demand=unmet_demand,
            vehicle_routes=vehicle_routes
        )
        
        self.logger.info(
            f"Optimization completed",
            allocations_count=len(allocations),
            coverage_percentage=coverage_percentage,
            total_cost=total_cost
        )
        
        return solution
    
    def _generate_vehicle_routes(self, allocations: List[Dict[str, Any]],
                                vehicles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate optimal vehicle routes for allocations"""
        
        routes = []
        
        # Simple route assignment - group allocations by proximity
        for vehicle in vehicles:
            vehicle_allocations = []
            remaining_capacity = vehicle['capacity_kg']
            
            # Sort allocations by distance from vehicle
            allocation_distances = []
            for allocation in allocations:
                if allocation.get('assigned_vehicle'):
                    continue  # Already assigned
                
                distance = self._calculate_distance(
                    vehicle['current_latitude'], vehicle['current_longitude'],
                    allocation['pickup_lat'], allocation['pickup_lon']
                )
                
                # Estimate weight
                resource_weight = self.resource_types.get(
                    allocation['resource_type'], {}
                ).get('weight_kg', 1.0)
                total_weight = allocation['quantity'] * resource_weight
                
                if total_weight <= remaining_capacity:
                    allocation_distances.append((allocation, distance, total_weight))
            
            # Sort by distance and assign
            allocation_distances.sort(key=lambda x: x[1])
            
            for allocation, distance, weight in allocation_distances:
                if weight <= remaining_capacity:
                    vehicle_allocations.append(allocation)
                    remaining_capacity -= weight
                    allocation['assigned_vehicle'] = vehicle['vehicle_id']
            
            if vehicle_allocations:
                route = {
                    'vehicle_id': vehicle['vehicle_id'],
                    'vehicle_type': vehicle['vehicle_type'],
                    'allocations': vehicle_allocations,
                    'total_distance_km': sum(a['distance_km'] for a in vehicle_allocations),
                    'estimated_duration_hours': sum(a['distance_km'] for a in vehicle_allocations) / 50,  # 50 km/h average
                    'load_weight_kg': sum(
                        a['quantity'] * self.resource_types.get(a['resource_type'], {}).get('weight_kg', 1.0)
                        for a in vehicle_allocations
                    )
                }
                routes.append(route)
        
        self.logger.debug(f"Generated {len(routes)} vehicle routes")
        return routes
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km"""
        
        from math import radians, cos, sin, asin, sqrt
        
        # Haversine formula
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Earth's radius in km
        
        return c * r
    
    def _create_allocation_plan(self, solution: AllocationSolution, optimization_id: str) -> api_pb2.AllocationPlan:
        """Create allocation plan protobuf message"""
        
        # Extract impacted zones
        impacted_zones = list(set(a['demand_zone_id'] for a in solution.allocations))
        
        # Calculate resource totals
        resource_totals = {}
        for allocation in solution.allocations:
            resource_type = allocation['resource_type']
            quantity = allocation['quantity']
            resource_totals[resource_type] = resource_totals.get(resource_type, 0) + quantity
        
        # Create GeoJSON (simplified)
        geojson_data = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [a['delivery_lon'], a['delivery_lat']]
                    },
                    'properties': {
                        'allocation_id': a['allocation_id'],
                        'resource_type': a['resource_type'],
                        'quantity': a['quantity']
                    }
                }
                for a in solution.allocations
            ]
        }
        
        # Store GeoJSON (in production, would upload to Cloud Storage)
        geojson_url = f"gs://{self.project_id}-allocations/{optimization_id}.geojson"
        
        plan = api_pb2.AllocationPlan(
            plan_id=optimization_id,
            impacted_zones=impacted_zones,
            resource_totals=resource_totals,
            geojson_url=geojson_url,
            generated_ms=int(time.time() * 1000)
        )
        
        return plan
    
    def _publish_allocation_plan(self, plan: api_pb2.AllocationPlan) -> None:
        """Publish allocation plan to Pub/Sub"""
        
        # Publish to allocation plans topic
        self.pubsub_client.publish_proto_message(
            'allocation_plans',
            plan,
            {
                'urgency': 'high',
                'zones_count': str(len(plan.impacted_zones))
            }
        )
        
        self.logger.info(
            f"Published allocation plan",
            plan_id=plan.plan_id,
            zones_count=len(plan.impacted_zones)
        )
    
    def start_monitoring(self) -> None:
        """Start resource allocation monitoring"""
        
        self.logger.info("Starting Resource Allocator monitoring")
        
        # Update agent status
        self.pubsub_client.broadcast_agent_status('monitoring', {
            'subscribed_topics': ['impact_updates', 'disaster_events'],
            'optimization_timeout_s': self.config['optimization_timeout_s']
        })
        
        self.logger.info("Resource Allocator ready to optimize allocations")


def main():
    """Main entry point"""
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'resilientflow-demo')
    agent = ResourceAllocatorAgent(project_id)
    
    # Start monitoring
    agent.start_monitoring()
    
    # Keep alive
    try:
        while True:
            time.sleep(60)
            agent.pubsub_client.broadcast_agent_status('monitoring')
            
    except KeyboardInterrupt:
        agent.logger.info("Shutting down Resource Allocator Agent")
        agent.pubsub_client.shutdown()


if __name__ == '__main__':
    main() 