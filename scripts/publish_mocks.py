#!/usr/bin/env python3
"""
Publish mock disaster events and data to test ResilientFlow agent swarm.
Simulates various disaster scenarios and data streams.
"""

import argparse
import time
import random
import json
from typing import Dict, Any, List

# Add common and proto to path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common import PubSubClient, get_logger
from proto import api_pb2


class MockDataPublisher:
    """Publisher for mock disaster data"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.logger = get_logger('mock_publisher')
        self.pubsub_client = PubSubClient(project_id, 'mock_publisher')
        
        # Mock data configurations
        self.disaster_scenarios = [
            {
                'event_type': 'flood',
                'locations': [
                    {'lat': 40.7589, 'lon': -73.9851, 'area': 'Manhattan'},
                    {'lat': 40.6892, 'lon': -73.9442, 'area': 'Brooklyn'},
                    {'lat': 40.8448, 'lon': -73.8648, 'area': 'Bronx'}
                ],
                'severity_range': (60, 95)
            },
            {
                'event_type': 'fire',
                'locations': [
                    {'lat': 34.0522, 'lon': -118.2437, 'area': 'Los Angeles'},
                    {'lat': 34.0200, 'lon': -118.2000, 'area': 'Downtown LA'},
                    {'lat': 34.1000, 'lon': -118.3000, 'area': 'Hollywood'}
                ],
                'severity_range': (70, 100)
            },
            {
                'event_type': 'earthquake',
                'locations': [
                    {'lat': 37.7749, 'lon': -122.4194, 'area': 'San Francisco'},
                    {'lat': 37.8044, 'lon': -122.2711, 'area': 'Oakland'},
                    {'lat': 37.6879, 'lon': -122.4702, 'area': 'San Mateo'}
                ],
                'severity_range': (50, 90)
            }
        ]
    
    def publish_disaster_event(self, event_type: str = None, severity: int = None) -> str:
        """Publish a mock disaster event"""
        
        # Select random scenario if not specified
        if event_type:
            scenario = next((s for s in self.disaster_scenarios if s['event_type'] == event_type), None)
            if not scenario:
                scenario = random.choice(self.disaster_scenarios)
        else:
            scenario = random.choice(self.disaster_scenarios)
        
        # Select random location
        location = random.choice(scenario['locations'])
        
        # Generate severity
        if not severity:
            severity = random.randint(*scenario['severity_range'])
        
        # Create disaster event
        event_id = f"{scenario['event_type']}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        disaster_event = api_pb2.DisasterEvent(
            event_id=event_id,
            source_agent='mock_publisher',
            latitude=location['lat'],
            longitude=location['lon'],
            event_type=scenario['event_type'],
            severity_raw=severity,
            timestamp_ms=int(time.time() * 1000)
        )
        
        # Publish event
        attributes = {
            'urgency': 'critical' if severity >= 80 else 'high' if severity >= 60 else 'medium',
            'area_name': location['area'],
            'requires_immediate_attention': 'true' if severity >= 85 else 'false'
        }
        
        message_id = self.pubsub_client.publish_proto_message(
            'disaster_events',
            disaster_event,
            attributes
        )
        
        self.logger.info(
            f"Published disaster event: {event_id}",
            event_type=scenario['event_type'],
            area=location['area'],
            severity=severity,
            message_id=message_id
        )
        
        return event_id
    
    def publish_impact_assessment(self, lat: float = None, lon: float = None) -> str:
        """Publish a mock impact assessment"""
        
        # Random location if not specified
        if lat is None or lon is None:
            scenario = random.choice(self.disaster_scenarios)
            location = random.choice(scenario['locations'])
            lat, lon = location['lat'], location['lon']
            
            # Add some randomness to coordinates
            lat += random.uniform(-0.01, 0.01)
            lon += random.uniform(-0.01, 0.01)
        
        assessment_id = f"assessment_{int(time.time())}_{random.randint(1000, 9999)}"
        
        damage_types = ['structural', 'flood', 'fire', 'debris', 'landslide']
        damage_type = random.choice(damage_types)
        
        severity_score = random.randint(40, 100)
        confidence = random.uniform(0.6, 0.95)
        
        assessment = api_pb2.ImpactAssessment(
            assessment_id=assessment_id,
            latitude=lat,
            longitude=lon,
            grid_cell_id=f"cell_{lat:.6f}_{lon:.6f}",
            severity_score=severity_score,
            damage_type=damage_type,
            assessed_ms=int(time.time() * 1000)
        )
        
        # Add confidence scores
        assessment.confidence_scores[damage_type] = confidence
        if random.random() > 0.5:  # Sometimes add secondary damage type
            secondary_type = random.choice([t for t in damage_types if t != damage_type])
            assessment.confidence_scores[secondary_type] = confidence * 0.7
        
        # Publish assessment
        attributes = {
            'urgency': 'critical' if severity_score >= 80 else 'high' if severity_score >= 60 else 'medium',
            'damage_type': damage_type,
            'confidence_level': 'high' if confidence >= 0.8 else 'medium'
        }
        
        message_id = self.pubsub_client.publish_proto_message(
            'impact_updates',
            assessment,
            attributes
        )
        
        self.logger.info(
            f"Published impact assessment: {assessment_id}",
            damage_type=damage_type,
            severity=severity_score,
            confidence=confidence,
            message_id=message_id
        )
        
        return assessment_id
    
    def publish_allocation_plan(self, zones: List[str] = None) -> str:
        """Publish a mock allocation plan"""
        
        plan_id = f"plan_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Generate impacted zones
        if not zones:
            zones = [f"zone_{i}_{int(time.time())}" for i in range(random.randint(2, 5))]
        
        # Generate resource totals
        resource_totals = {
            'water': random.randint(1000, 5000),
            'food': random.randint(500, 3000),
            'medical_supplies': random.randint(100, 1000),
            'blankets': random.randint(200, 2000),
            'tents': random.randint(50, 500)
        }
        
        allocation_plan = api_pb2.AllocationPlan(
            plan_id=plan_id,
            impacted_zones=zones,
            resource_totals=resource_totals,
            geojson_url=f"gs://{self.project_id}-allocations/{plan_id}.geojson",
            generated_ms=int(time.time() * 1000)
        )
        
        # Publish plan
        attributes = {
            'urgency': 'high',
            'zones_count': str(len(zones)),
            'total_resources': str(sum(resource_totals.values()))
        }
        
        message_id = self.pubsub_client.publish_proto_message(
            'allocation_plans',
            allocation_plan,
            attributes
        )
        
        self.logger.info(
            f"Published allocation plan: {plan_id}",
            zones_count=len(zones),
            total_resources=sum(resource_totals.values()),
            message_id=message_id
        )
        
        return plan_id
    
    def publish_agent_status(self, agent_name: str = None, status: str = 'active') -> None:
        """Publish agent status update"""
        
        if not agent_name:
            agent_name = random.choice(['data_aggregator', 'impact_assessor', 'resource_allocator', 
                                     'comms_coordinator', 'report_synthesizer'])
        
        status_data = {
            'agent_name': agent_name,
            'status': status,
            'timestamp_ms': int(time.time() * 1000),
            'processed_items': random.randint(10, 100),
            'memory_usage_mb': random.randint(512, 1024),
            'cpu_usage_percent': random.randint(10, 80)
        }
        
        message_id = self.pubsub_client.publish_json_message(
            'agent_events',
            status_data,
            {
                'event_type': 'agent_status',
                'agent_name': agent_name,
                'urgency': 'low'
            }
        )
        
        self.logger.debug(
            f"Published agent status: {agent_name}",
            status=status,
            message_id=message_id
        )
    
    def simulate_disaster_scenario(self, scenario_name: str = 'hurricane', duration_minutes: int = 10) -> None:
        """Simulate a complete disaster scenario with multiple events"""
        
        self.logger.info(
            f"Starting disaster scenario simulation: {scenario_name}",
            duration_minutes=duration_minutes
        )
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        events_published = 0
        assessments_published = 0
        plans_published = 0
        
        while time.time() < end_time:
            current_time = time.time()
            elapsed_minutes = (current_time - start_time) / 60
            
            # Publish disaster events (less frequent at start, more frequent in middle)
            if random.random() < min(0.3, elapsed_minutes / duration_minutes):
                event_type = scenario_name if scenario_name in ['flood', 'fire', 'earthquake'] else None
                severity = random.randint(70, 100) if elapsed_minutes < duration_minutes / 2 else random.randint(50, 85)
                
                self.publish_disaster_event(event_type, severity)
                events_published += 1
            
            # Publish impact assessments (more frequent)
            if random.random() < 0.6:
                self.publish_impact_assessment()
                assessments_published += 1
            
            # Publish allocation plans (less frequent)
            if random.random() < 0.2:
                self.publish_allocation_plan()
                plans_published += 1
            
            # Publish agent status updates
            if random.random() < 0.1:
                self.publish_agent_status()
            
            # Wait before next iteration
            time.sleep(random.uniform(2, 8))
        
        self.logger.info(
            f"Completed disaster scenario simulation",
            scenario=scenario_name,
            duration_minutes=duration_minutes,
            events_published=events_published,
            assessments_published=assessments_published,
            plans_published=plans_published
        )
    
    def shutdown(self):
        """Shutdown the publisher"""
        self.pubsub_client.shutdown()


def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(description='Publish mock data to test ResilientFlow agents')
    parser.add_argument('--project-id', required=True, help='Google Cloud Project ID')
    parser.add_argument('--scenario', choices=['hurricane', 'wildfire', 'earthquake', 'flood'], 
                       default='hurricane', help='Disaster scenario to simulate')
    parser.add_argument('--duration', type=int, default=5, 
                       help='Simulation duration in minutes')
    parser.add_argument('--single-event', action='store_true',
                       help='Publish single event instead of full scenario')
    parser.add_argument('--event-type', choices=['flood', 'fire', 'earthquake'],
                       help='Type of single event to publish')
    parser.add_argument('--severity', type=int, choices=range(1, 101),
                       help='Severity level (1-100) for single event')
    
    args = parser.parse_args()
    
    # Initialize publisher
    publisher = MockDataPublisher(args.project_id)
    
    try:
        if args.single_event:
            # Publish single event
            publisher.logger.info("Publishing single disaster event")
            event_id = publisher.publish_disaster_event(args.event_type, args.severity)
            print(f"✅ Published disaster event: {event_id}")
            
            # Also publish a few related assessments
            for _ in range(random.randint(2, 5)):
                assessment_id = publisher.publish_impact_assessment()
                print(f"✅ Published impact assessment: {assessment_id}")
                time.sleep(1)
            
        else:
            # Run full scenario simulation
            print(f"🌪️  Starting {args.scenario} scenario simulation for {args.duration} minutes...")
            print("📊 Publishing events to Pub/Sub topics:")
            print("  - rf-disaster-events")
            print("  - rf-impact-updates") 
            print("  - rf-allocation-plans")
            print("  - rf-agent-events")
            print("")
            print("📈 Monitor agent activity in Cloud Run logs:")
            print(f"  https://console.cloud.google.com/run?project={args.project_id}")
            print("")
            
            publisher.simulate_disaster_scenario(args.scenario, args.duration)
            
            print("")
            print("✅ Simulation completed!")
            print("🔍 Check the following for results:")
            print("  - Cloud Run service logs for agent processing")
            print("  - BigQuery resilientflow dataset for stored data")
            print("  - Firestore for allocation plans and agent state")
            print("  - Cloud Storage buckets for generated reports")
        
    except KeyboardInterrupt:
        publisher.logger.info("Simulation interrupted by user")
        
    except Exception as e:
        publisher.logger.error(f"Simulation failed", error=str(e))
        raise
        
    finally:
        publisher.shutdown()


if __name__ == '__main__':
    main() 