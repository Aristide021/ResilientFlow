#!/usr/bin/env python3
"""
Load sample inventory data into ResilientFlow Firestore.
Creates demo facilities, vehicles, and resource inventory.
"""

import argparse
import time
import random
from typing import Dict, List

# Add common to path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common import FirestoreClient, get_logger


def load_sample_facilities(firestore_client: FirestoreClient) -> List[str]:
    """Load sample disaster relief facilities"""
    
    logger = get_logger('inventory_loader')
    
    facilities = [
        {
            'facility_id': 'warehouse_nyc_001',
            'name': 'NYC Emergency Warehouse #1',
            'latitude': 40.7589,
            'longitude': -73.9851,
            'facility_type': 'warehouse',
            'capacity': {'water': 10000, 'food': 8000, 'medical_supplies': 2000, 'blankets': 5000, 'tents': 1000}
        },
        {
            'facility_id': 'warehouse_nyc_002', 
            'name': 'Brooklyn Distribution Center',
            'latitude': 40.6892,
            'longitude': -73.9442,
            'facility_type': 'warehouse',
            'capacity': {'water': 15000, 'food': 12000, 'medical_supplies': 3000, 'blankets': 8000, 'tents': 1500}
        },
        {
            'facility_id': 'hospital_manhattan_001',
            'name': 'Manhattan Emergency Medical Center',
            'latitude': 40.7614,
            'longitude': -73.9776,
            'facility_type': 'hospital',
            'capacity': {'medical_supplies': 5000, 'water': 2000, 'food': 1000}
        },
        {
            'facility_id': 'shelter_bronx_001',
            'name': 'Bronx Emergency Shelter',
            'latitude': 40.8448,
            'longitude': -73.8648,
            'facility_type': 'shelter',
            'capacity': {'blankets': 10000, 'food': 5000, 'water': 3000, 'tents': 500}
        },
        {
            'facility_id': 'warehouse_la_001',
            'name': 'Los Angeles Relief Warehouse',
            'latitude': 34.0522,
            'longitude': -118.2437,
            'facility_type': 'warehouse',
            'capacity': {'water': 20000, 'food': 15000, 'medical_supplies': 4000, 'blankets': 12000, 'tents': 2000}
        }
    ]
    
    facility_ids = []
    
    for facility in facilities:
        firestore_client.register_facility(
            facility['facility_id'],
            facility['name'],
            facility['latitude'],
            facility['longitude'],
            facility['facility_type'],
            facility['capacity']
        )
        facility_ids.append(facility['facility_id'])
        logger.info(f"Registered facility: {facility['name']}")
    
    logger.info(f"Loaded {len(facilities)} facilities")
    return facility_ids


def load_sample_vehicles(firestore_client: FirestoreClient) -> List[str]:
    """Load sample emergency vehicles"""
    
    logger = get_logger('inventory_loader')
    
    vehicles = [
        {'vehicle_id': 'truck_001', 'type': 'truck', 'capacity': 5000, 'lat': 40.7589, 'lon': -73.9851},
        {'vehicle_id': 'truck_002', 'type': 'truck', 'capacity': 5000, 'lat': 40.6892, 'lon': -73.9442},
        {'vehicle_id': 'truck_003', 'type': 'truck', 'capacity': 3000, 'lat': 40.7614, 'lon': -73.9776},
        {'vehicle_id': 'helicopter_001', 'type': 'helicopter', 'capacity': 1000, 'lat': 40.7589, 'lon': -73.9851},
        {'vehicle_id': 'helicopter_002', 'type': 'helicopter', 'capacity': 1200, 'lat': 34.0522, 'lon': -118.2437},
        {'vehicle_id': 'boat_001', 'type': 'boat', 'capacity': 2000, 'lat': 40.7000, 'lon': -74.0000},
        {'vehicle_id': 'truck_la_001', 'type': 'truck', 'capacity': 4000, 'lat': 34.0522, 'lon': -118.2437},
        {'vehicle_id': 'truck_la_002', 'type': 'truck', 'capacity': 4500, 'lat': 34.0200, 'lon': -118.2000}
    ]
    
    vehicle_ids = []
    
    for vehicle in vehicles:
        firestore_client.register_vehicle(
            vehicle['vehicle_id'],
            vehicle['type'],
            vehicle['capacity'],
            vehicle['lat'],
            vehicle['lon']
        )
        vehicle_ids.append(vehicle['vehicle_id'])
        logger.info(f"Registered vehicle: {vehicle['vehicle_id']} ({vehicle['type']})")
    
    logger.info(f"Loaded {len(vehicles)} vehicles")
    return vehicle_ids


def load_sample_inventory(firestore_client: FirestoreClient, facility_ids: List[str]) -> None:
    """Load sample resource inventory"""
    
    logger = get_logger('inventory_loader')
    
    resource_types = ['water', 'food', 'medical_supplies', 'blankets', 'tents', 'generators']
    
    total_items = 0
    
    for facility_id in facility_ids:
        for resource_type in resource_types:
            # Generate realistic inventory quantities
            if resource_type == 'water':
                quantity = random.randint(1000, 5000)
            elif resource_type == 'food':
                quantity = random.randint(500, 3000)
            elif resource_type == 'medical_supplies':
                quantity = random.randint(100, 1000)
            elif resource_type == 'blankets':
                quantity = random.randint(200, 2000)
            elif resource_type == 'tents':
                quantity = random.randint(50, 500)
            elif resource_type == 'generators':
                quantity = random.randint(5, 50)
            else:
                quantity = random.randint(100, 1000)
            
            firestore_client.update_resource_inventory(
                resource_type,
                facility_id,
                quantity,
                'set'
            )
            
            total_items += quantity
            logger.debug(f"Added {quantity} {resource_type} to {facility_id}")
    
    logger.info(f"Loaded inventory: {total_items} total items across {len(facility_ids)} facilities")


def create_sample_incidents(firestore_client: FirestoreClient) -> None:
    """Create sample incident records"""
    
    logger = get_logger('inventory_loader')
    
    incidents = [
        {
            'incident_id': 'hurricane_sandy_2024',
            'incident_type': 'hurricane',
            'status': 'active',
            'severity': 85,
            'affected_areas': ['New York', 'New Jersey', 'Connecticut'],
            'start_time': int(time.time() * 1000) - 86400000,  # 1 day ago
            'description': 'Hurricane Sandy 2024 - Category 3 hurricane affecting Northeast US'
        },
        {
            'incident_id': 'wildfire_ca_2024',
            'incident_type': 'wildfire',
            'status': 'monitoring',
            'severity': 70,
            'affected_areas': ['Los Angeles County', 'Ventura County'],
            'start_time': int(time.time() * 1000) - 172800000,  # 2 days ago
            'description': 'California wildfire threatening residential areas'
        },
        {
            'incident_id': 'earthquake_sf_2024',
            'incident_type': 'earthquake',
            'status': 'resolved',
            'severity': 60,
            'affected_areas': ['San Francisco', 'Oakland'],
            'start_time': int(time.time() * 1000) - 604800000,  # 1 week ago
            'description': 'Magnitude 6.2 earthquake in San Francisco Bay Area'
        }
    ]
    
    for incident in incidents:
        firestore_client.write_document('incidents', incident['incident_id'], incident)
        logger.info(f"Created incident: {incident['incident_id']}")
    
    logger.info(f"Created {len(incidents)} sample incidents")


def load_agent_configurations(firestore_client: FirestoreClient) -> None:
    """Load agent configuration data"""
    
    logger = get_logger('inventory_loader')
    
    agent_configs = {
        'data_aggregator': {
            'agent_name': 'data_aggregator',
            'status': 'active',
            'config': {
                'supported_formats': ['.tif', '.tiff', '.jpg', '.jpeg', '.png'],
                'confidence_threshold': 0.7,
                'processing_timeout_s': 300
            },
            'capabilities': ['satellite_image_processing', 'damage_detection', 'vision_ai'],
            'last_heartbeat_ms': int(time.time() * 1000)
        },
        'impact_assessor': {
            'agent_name': 'impact_assessor',
            'status': 'active',
            'config': {
                'grid_size_degrees': 0.001,
                'clustering_distance_km': 1.0,
                'severity_threshold_critical': 80
            },
            'capabilities': ['spatial_analysis', 'impact_assessment', 'heat_map_generation'],
            'last_heartbeat_ms': int(time.time() * 1000)
        },
        'resource_allocator': {
            'agent_name': 'resource_allocator',
            'status': 'active',
            'config': {
                'optimization_timeout_s': 30,
                'max_vehicle_capacity_kg': 5000,
                'coverage_target_percentage': 85.0
            },
            'capabilities': ['logistics_optimization', 'resource_allocation', 'route_planning'],
            'last_heartbeat_ms': int(time.time() * 1000)
        },
        'comms_coordinator': {
            'agent_name': 'comms_coordinator',
            'status': 'active',
            'config': {
                'supported_languages': ['en', 'es', 'fr'],
                'alert_expiry_hours': 24,
                'max_message_length': 160
            },
            'capabilities': ['multilingual_alerts', 'fcm_push', 'sms_alerts', 'cap_xml'],
            'last_heartbeat_ms': int(time.time() * 1000)
        },
        'report_synthesizer': {
            'agent_name': 'report_synthesizer',
            'status': 'active',
            'config': {
                'report_generation_interval_s': 1800,
                'max_zones_per_report': 50,
                'url_expiry_hours': 24
            },
            'capabilities': ['pdf_generation', 'geojson_export', 'data_visualization'],
            'last_heartbeat_ms': int(time.time() * 1000)
        }
    }
    
    for agent_name, config in agent_configs.items():
        firestore_client.write_document('agent_state', agent_name, config)
        logger.info(f"Configured agent: {agent_name}")
    
    logger.info(f"Configured {len(agent_configs)} agents")


def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(description='Load sample inventory data into ResilientFlow')
    parser.add_argument('--project-id', required=True, help='Google Cloud Project ID')
    parser.add_argument('--clear-existing', action='store_true', help='Clear existing data first')
    
    args = parser.parse_args()
    
    # Initialize logger
    logger = get_logger('inventory_loader')
    logger.info(f"Loading sample data for project: {args.project_id}")
    
    # Initialize Firestore client
    firestore_client = FirestoreClient(args.project_id, 'inventory_loader')
    
    try:
        # Load sample data
        logger.info("Loading sample facilities...")
        facility_ids = load_sample_facilities(firestore_client)
        
        logger.info("Loading sample vehicles...")
        vehicle_ids = load_sample_vehicles(firestore_client)
        
        logger.info("Loading sample inventory...")
        load_sample_inventory(firestore_client, facility_ids)
        
        logger.info("Creating sample incidents...")
        create_sample_incidents(firestore_client)
        
        logger.info("Loading agent configurations...")
        load_agent_configurations(firestore_client)
        
        logger.info("✅ Sample data loading completed successfully!")
        
        # Display summary
        print("\n📊 Sample Data Summary:")
        print(f"  Facilities: {len(facility_ids)}")
        print(f"  Vehicles: {len(vehicle_ids)}")
        print(f"  Resource Types: 6 (water, food, medical_supplies, blankets, tents, generators)")
        print(f"  Incidents: 3")
        print(f"  Agents Configured: 5")
        print("\n🎯 Data is ready for ResilientFlow agent processing!")
        
    except Exception as e:
        logger.error(f"Failed to load sample data", error=str(e))
        raise


if __name__ == '__main__':
    main() 