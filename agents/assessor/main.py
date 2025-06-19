"""
Impact Assessor Agent - ResilientFlow
Performs spatial analysis on disaster data to generate weighted impact heat-maps.
Uses BigQuery GIS for geospatial joins and ML for clustering analysis.
"""

import os
import time
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from google.cloud import bigquery
from google.cloud.bigquery import Client as BQClient
import geojson
import numpy as np
from dataclasses import dataclass

# Import ResilientFlow common utilities
import sys
sys.path.append('/workspace')
from common import get_logger, PubSubClient, FirestoreClient
from proto import api_pb2


@dataclass
class ImpactZone:
    """Represents an impact zone with aggregated severity"""
    zone_id: str
    center_lat: float
    center_lon: float
    severity_score: float
    affected_area_km2: float
    damage_types: List[str]
    assessment_count: int
    confidence: float


class ImpactAssessorAgent:
    """Spatial analysis and heat-map generation agent"""
    
    def __init__(self, project_id: str, region: str = 'us-central1'):
        self.project_id = project_id
        self.region = region
        self.agent_name = 'impact_assessor'
        self.logger = get_logger(self.agent_name)
        
        # Initialize clients
        self.bigquery_client = bigquery.Client(project=project_id)
        self.pubsub_client = PubSubClient(project_id, self.agent_name)
        self.firestore_client = FirestoreClient(project_id, self.agent_name)
        
        # Configuration
        self.config = {
            'bigquery_dataset': 'resilientflow',
            'grid_size_degrees': 0.001,  # ~100m resolution
            'severity_threshold_critical': 80,
            'severity_threshold_high': 60,
            'clustering_distance_km': 1.0,
            'heat_map_update_interval_s': 30,
            'max_assessments_per_analysis': 10000
        }
        
        # Setup BigQuery tables
        self._ensure_bigquery_tables()
        
        # Subscribe to relevant topics
        self._setup_subscriptions()
        
        self.logger.info("Impact Assessor Agent initialized", config=self.config)
    
    def _ensure_bigquery_tables(self) -> None:
        """Create BigQuery tables if they don't exist"""
        
        dataset_id = self.config['bigquery_dataset']
        
        # Create dataset if it doesn't exist
        try:
            self.bigquery_client.create_dataset(dataset_id, exists_ok=True)
        except Exception as e:
            self.logger.warning(f"Could not create dataset {dataset_id}", error=str(e))
        
        # Table schemas
        tables = {
            'impact_assessments': [
                bigquery.SchemaField('assessment_id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('latitude', 'FLOAT', mode='REQUIRED'),
                bigquery.SchemaField('longitude', 'FLOAT', mode='REQUIRED'),
                bigquery.SchemaField('grid_cell_id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('severity_score', 'INTEGER', mode='REQUIRED'),
                bigquery.SchemaField('damage_type', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('confidence_scores', 'JSON', mode='NULLABLE'),
                bigquery.SchemaField('assessed_timestamp', 'TIMESTAMP', mode='REQUIRED'),
                bigquery.SchemaField('assessed_ms', 'INTEGER', mode='REQUIRED'),
                bigquery.SchemaField('source_agent', 'STRING', mode='REQUIRED'),
            ],
            'impact_zones': [
                bigquery.SchemaField('zone_id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('center_latitude', 'FLOAT', mode='REQUIRED'),
                bigquery.SchemaField('center_longitude', 'FLOAT', mode='REQUIRED'),
                bigquery.SchemaField('severity_score', 'FLOAT', mode='REQUIRED'),
                bigquery.SchemaField('affected_area_km2', 'FLOAT', mode='REQUIRED'),
                bigquery.SchemaField('damage_types', 'STRING', mode='REPEATED'),
                bigquery.SchemaField('assessment_count', 'INTEGER', mode='REQUIRED'),
                bigquery.SchemaField('confidence', 'FLOAT', mode='REQUIRED'),
                bigquery.SchemaField('last_updated', 'TIMESTAMP', mode='REQUIRED'),
                bigquery.SchemaField('geojson_polygon', 'STRING', mode='NULLABLE'),
            ],
            'heat_map_tiles': [
                bigquery.SchemaField('tile_id', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('zoom_level', 'INTEGER', mode='REQUIRED'),
                bigquery.SchemaField('tile_x', 'INTEGER', mode='REQUIRED'),
                bigquery.SchemaField('tile_y', 'INTEGER', mode='REQUIRED'),
                bigquery.SchemaField('severity_grid', 'JSON', mode='REQUIRED'),
                bigquery.SchemaField('generated_timestamp', 'TIMESTAMP', mode='REQUIRED'),
                bigquery.SchemaField('data_sources', 'STRING', mode='REPEATED'),
            ]
        }
        
        # Create tables
        for table_name, schema in tables.items():
            table_id = f"{self.project_id}.{dataset_id}.{table_name}"
            table = bigquery.Table(table_id, schema=schema)
            
            try:
                self.bigquery_client.create_table(table, exists_ok=True)
                self.logger.debug(f"Ensured table exists: {table_name}")
            except Exception as e:
                self.logger.error(f"Failed to create table {table_name}", error=str(e))
    
    def _setup_subscriptions(self) -> None:
        """Setup Pub/Sub subscriptions for incoming data"""
        
        # Subscribe to disaster events
        self.pubsub_client.subscribe_to_topic(
            'disaster_events',
            self._handle_disaster_event,
            api_pb2.DisasterEvent
        )
        
        # Subscribe to impact updates 
        self.pubsub_client.subscribe_to_topic(
            'impact_updates',
            self._handle_impact_update
        )
        
        self.logger.info("Pub/Sub subscriptions established")
    
    def _handle_disaster_event(self, event: api_pb2.DisasterEvent, attributes: Dict[str, str]) -> None:
        """Handle incoming disaster event for impact analysis"""
        
        self.logger.info(
            f"Received disaster event: {event.event_id}",
            event_type=event.event_type,
            severity=event.severity_raw,
            source=event.source_agent
        )
        
        try:
            # Trigger impact analysis for the affected area
            self._analyze_impact_area(
                event.latitude,
                event.longitude,
                event.event_type,
                event.severity_raw
            )
            
        except Exception as e:
            self.logger.error(
                f"Error handling disaster event {event.event_id}",
                error=str(e)
            )
    
    def _handle_impact_update(self, data: Dict[str, Any], attributes: Dict[str, str]) -> None:
        """Handle general impact update messages"""
        
        self.logger.debug("Received impact update", data=data)
        
        # Trigger heat-map regeneration if needed
        if data.get('trigger_heat_map_update'):
            self._generate_heat_map_tiles()
    
    def _analyze_impact_area(self, center_lat: float, center_lon: float,
                           event_type: str, severity: int, radius_km: float = 5.0) -> None:
        """Analyze impact in a specific geographic area"""
        
        analysis_id = str(uuid.uuid4())
        start_time = time.time()
        
        self.logger.info(
            f"Starting impact analysis for area",
            analysis_id=analysis_id,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km
        )
        
        try:
            # Query assessments in the area
            assessments = self._query_assessments_in_area(
                center_lat, center_lon, radius_km
            )
            
            if not assessments:
                self.logger.info(f"No assessments found in area", analysis_id=analysis_id)
                return
            
            # Perform spatial clustering
            zones = self._perform_spatial_clustering(assessments)
            
            # Calculate weighted severity scores
            enriched_zones = self._calculate_zone_severity(zones, assessments)
            
            # Store zones in BigQuery
            self._store_impact_zones(enriched_zones)
            
            # Generate alerts for critical zones
            critical_zones = [z for z in enriched_zones if z.severity_score >= self.config['severity_threshold_critical']]
            if critical_zones:
                self._publish_critical_zone_alerts(critical_zones)
            
            # Update heat-map tiles for affected area
            self._update_heat_map_tiles(center_lat, center_lon, radius_km)
            
            # Update agent state
            self.firestore_client.update_agent_state({
                'last_analysis_id': analysis_id,
                'zones_analyzed': len(enriched_zones),
                'critical_zones': len(critical_zones),
                'status': 'active'
            })
            
            processing_time = (time.time() - start_time) * 1000
            self.logger.agent_action(
                'analyze_impact_area',
                'success',
                processing_time,
                analysis_id=analysis_id,
                zones_count=len(enriched_zones),
                critical_count=len(critical_zones)
            )
            
        except Exception as e:
            self.logger.error(
                f"Impact analysis failed",
                analysis_id=analysis_id,
                error=str(e)
            )
            raise
    
    def _query_assessments_in_area(self, center_lat: float, center_lon: float,
                                  radius_km: float) -> List[Dict[str, Any]]:
        """Query impact assessments within specified radius"""
        
        # Use BigQuery GIS functions for spatial query
        query = f"""
        SELECT 
            assessment_id,
            latitude,
            longitude,
            grid_cell_id,
            severity_score,
            damage_type,
            confidence_scores,
            assessed_ms,
            source_agent
        FROM `{self.project_id}.{self.config['bigquery_dataset']}.impact_assessments`
        WHERE ST_DWITHIN(
            ST_GEOGPOINT(longitude, latitude),
            ST_GEOGPOINT({center_lon}, {center_lat}),
            {radius_km * 1000}  -- Convert km to meters
        )
        AND assessed_ms > {int((time.time() - 24*3600) * 1000)}  -- Last 24 hours
        ORDER BY severity_score DESC
        LIMIT {self.config['max_assessments_per_analysis']}
        """
        
        query_job = self.bigquery_client.query(query)
        results = query_job.result()
        
        assessments = []
        for row in results:
            assessment = {
                'assessment_id': row.assessment_id,
                'latitude': row.latitude,
                'longitude': row.longitude,
                'grid_cell_id': row.grid_cell_id,
                'severity_score': row.severity_score,
                'damage_type': row.damage_type,
                'confidence_scores': json.loads(row.confidence_scores) if row.confidence_scores else {},
                'assessed_ms': row.assessed_ms,
                'source_agent': row.source_agent
            }
            assessments.append(assessment)
        
        self.logger.debug(
            f"Queried {len(assessments)} assessments in area",
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km
        )
        
        return assessments
    
    def _perform_spatial_clustering(self, assessments: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Cluster assessments by spatial proximity"""
        
        if not assessments:
            return []
        
        # Simple distance-based clustering
        clusters = []
        unassigned = assessments.copy()
        
        while unassigned:
            # Start new cluster with first unassigned assessment
            seed = unassigned.pop(0)
            cluster = [seed]
            
            # Find nearby assessments
            i = 0
            while i < len(unassigned):
                assessment = unassigned[i]
                
                # Calculate distance to any point in cluster
                min_distance = min(
                    self._haversine_distance(
                        seed['latitude'], seed['longitude'],
                        assessment['latitude'], assessment['longitude']
                    )
                    for seed in cluster
                )
                
                if min_distance <= self.config['clustering_distance_km']:
                    cluster.append(unassigned.pop(i))
                else:
                    i += 1
            
            clusters.append(cluster)
        
        self.logger.debug(f"Created {len(clusters)} spatial clusters")
        return clusters
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in km"""
        
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Earth's radius in km
        
        return c * r
    
    def _calculate_zone_severity(self, clusters: List[List[Dict[str, Any]]],
                               assessments: List[Dict[str, Any]]) -> List[ImpactZone]:
        """Calculate weighted severity scores for impact zones"""
        
        zones = []
        
        for i, cluster in enumerate(clusters):
            if not cluster:
                continue
            
            zone_id = f"zone_{int(time.time())}_{i}"
            
            # Calculate center point
            center_lat = sum(a['latitude'] for a in cluster) / len(cluster)
            center_lon = sum(a['longitude'] for a in cluster) / len(cluster)
            
            # Calculate weighted severity score
            total_weight = 0
            weighted_severity = 0
            
            for assessment in cluster:
                # Weight by confidence and recency
                confidence = sum(assessment['confidence_scores'].values()) / len(assessment['confidence_scores']) if assessment['confidence_scores'] else 0.5
                
                # Recent assessments get higher weight
                age_hours = (time.time() * 1000 - assessment['assessed_ms']) / (1000 * 3600)
                recency_weight = max(0.1, 1.0 - (age_hours / 24))  # Decay over 24 hours
                
                weight = confidence * recency_weight
                weighted_severity += assessment['severity_score'] * weight
                total_weight += weight
            
            if total_weight > 0:
                final_severity = weighted_severity / total_weight
            else:
                final_severity = sum(a['severity_score'] for a in cluster) / len(cluster)
            
            # Estimate affected area (simplified)
            if len(cluster) > 1:
                # Calculate bounding box area
                lats = [a['latitude'] for a in cluster]
                lons = [a['longitude'] for a in cluster]
                
                lat_range = max(lats) - min(lats)
                lon_range = max(lons) - min(lons)
                
                # Rough area calculation
                area_km2 = lat_range * lon_range * 111 * 111  # Degrees to km approximation
            else:
                area_km2 = 0.01  # Default 1 hectare for single point
            
            # Collect damage types
            damage_types = list(set(a['damage_type'] for a in cluster))
            
            # Overall confidence
            confidences = [
                sum(a['confidence_scores'].values()) / len(a['confidence_scores'])
                for a in cluster if a['confidence_scores']
            ]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            
            zone = ImpactZone(
                zone_id=zone_id,
                center_lat=center_lat,
                center_lon=center_lon,
                severity_score=final_severity,
                affected_area_km2=area_km2,
                damage_types=damage_types,
                assessment_count=len(cluster),
                confidence=overall_confidence
            )
            
            zones.append(zone)
        
        return zones
    
    def _store_impact_zones(self, zones: List[ImpactZone]) -> None:
        """Store impact zones in BigQuery"""
        
        if not zones:
            return
        
        table_id = f"{self.project_id}.{self.config['bigquery_dataset']}.impact_zones"
        
        rows = []
        for zone in zones:
            row = {
                'zone_id': zone.zone_id,
                'center_latitude': zone.center_lat,
                'center_longitude': zone.center_lon,
                'severity_score': zone.severity_score,
                'affected_area_km2': zone.affected_area_km2,
                'damage_types': zone.damage_types,
                'assessment_count': zone.assessment_count,
                'confidence': zone.confidence,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                'geojson_polygon': None  # Would generate actual polygon in production
            }
            rows.append(row)
        
        table_ref = self.bigquery_client.get_table(table_id)
        errors = self.bigquery_client.insert_rows_json(table_ref, rows)
        
        if errors:
            self.logger.error(f"BigQuery insert errors for zones", errors=errors)
            raise Exception(f"Failed to insert zones: {errors}")
        
        self.logger.info(f"Stored {len(rows)} impact zones in BigQuery")
    
    def _publish_critical_zone_alerts(self, zones: List[ImpactZone]) -> None:
        """Publish alerts for critical impact zones"""
        
        for zone in zones:
            # Create impact assessment message
            assessment = api_pb2.ImpactAssessment(
                assessment_id=f"zone_{zone.zone_id}",
                latitude=zone.center_lat,
                longitude=zone.center_lon,
                grid_cell_id=f"zone_{zone.zone_id}",
                severity_score=int(zone.severity_score),
                damage_type='|'.join(zone.damage_types),
                assessed_ms=int(time.time() * 1000)
            )
            
            # Set confidence scores
            for damage_type in zone.damage_types:
                assessment.confidence_scores[damage_type] = zone.confidence
            
            # Publish to impact updates topic
            self.pubsub_client.publish_proto_message(
                'impact_updates',
                assessment,
                {
                    'urgency': 'critical',
                    'zone_type': 'aggregated',
                    'assessment_count': str(zone.assessment_count)
                }
            )
            
            self.logger.info(
                f"Published critical zone alert",
                zone_id=zone.zone_id,
                severity=zone.severity_score
            )
    
    def _update_heat_map_tiles(self, center_lat: float, center_lon: float, radius_km: float) -> None:
        """Update heat-map tiles for affected area"""
        
        # Calculate tile boundaries (simplified - would use proper tile math in production)
        # For demo, just update a few tiles around the center
        
        tiles_updated = 0
        zoom_level = 12  # Example zoom level
        
        # Generate simplified heat-map data
        for x_offset in range(-2, 3):
            for y_offset in range(-2, 3):
                tile_x = int(center_lon * 1000) + x_offset
                tile_y = int(center_lat * 1000) + y_offset
                tile_id = f"{zoom_level}_{tile_x}_{tile_y}"
                
                # Query data for this tile
                severity_grid = self._generate_tile_severity_grid(
                    center_lat + (y_offset * 0.01),
                    center_lon + (x_offset * 0.01)
                )
                
                # Store tile in BigQuery
                self._store_heat_map_tile(tile_id, zoom_level, tile_x, tile_y, severity_grid)
                tiles_updated += 1
        
        self.logger.info(f"Updated {tiles_updated} heat-map tiles")
    
    def _generate_tile_severity_grid(self, center_lat: float, center_lon: float) -> Dict[str, Any]:
        """Generate severity grid for a map tile"""
        
        # Simplified grid generation - would use proper spatial queries in production
        grid_size = 10  # 10x10 grid per tile
        grid = []
        
        for i in range(grid_size):
            row = []
            for j in range(grid_size):
                # Query severity at this grid point
                lat = center_lat + (i - grid_size/2) * 0.001
                lon = center_lon + (j - grid_size/2) * 0.001
                
                # Simplified severity calculation
                severity = self._get_point_severity(lat, lon)
                row.append(severity)
            
            grid.append(row)
        
        return {
            'grid': grid,
            'center_lat': center_lat,
            'center_lon': center_lon,
            'grid_size': grid_size,
            'resolution_degrees': 0.001
        }
    
    def _get_point_severity(self, lat: float, lon: float) -> int:
        """Get severity score for a specific point (simplified)"""
        
        # In production, this would query actual assessments
        # For demo, return random severity based on location
        import hashlib
        location_hash = hashlib.md5(f"{lat:.6f}_{lon:.6f}".encode()).hexdigest()
        return int(location_hash[:2], 16) % 100
    
    def _store_heat_map_tile(self, tile_id: str, zoom_level: int, tile_x: int, tile_y: int,
                            severity_grid: Dict[str, Any]) -> None:
        """Store heat-map tile in BigQuery"""
        
        table_id = f"{self.project_id}.{self.config['bigquery_dataset']}.heat_map_tiles"
        
        row = {
            'tile_id': tile_id,
            'zoom_level': zoom_level,
            'tile_x': tile_x,
            'tile_y': tile_y,
            'severity_grid': json.dumps(severity_grid),
            'generated_timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            'data_sources': [self.agent_name]
        }
        
        table_ref = self.bigquery_client.get_table(table_id)
        errors = self.bigquery_client.insert_rows_json(table_ref, [row])
        
        if errors:
            self.logger.warning(f"Error storing heat-map tile {tile_id}", errors=errors)
        else:
            self.logger.debug(f"Stored heat-map tile {tile_id}")
    
    def _generate_heat_map_tiles(self) -> None:
        """Generate heat-map tiles for all active impact zones"""
        
        self.logger.info("Generating heat-map tiles for all zones")
        
        # Query active zones
        query = f"""
        SELECT center_latitude, center_longitude, severity_score
        FROM `{self.project_id}.{self.config['bigquery_dataset']}.impact_zones`
        WHERE last_updated > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        AND severity_score >= {self.config['severity_threshold_high']}
        """
        
        query_job = self.bigquery_client.query(query)
        results = query_job.result()
        
        tiles_generated = 0
        for row in results:
            self._update_heat_map_tiles(
                row.center_latitude,
                row.center_longitude,
                2.0  # 2km radius
            )
            tiles_generated += 1
        
        self.logger.info(f"Generated heat-map tiles for {tiles_generated} zones")
    
    def start_monitoring(self) -> None:
        """Start the impact assessment monitoring loop"""
        
        self.logger.info("Starting Impact Assessor monitoring")
        
        # Update agent status
        self.pubsub_client.broadcast_agent_status('monitoring', {
            'subscribed_topics': ['disaster_events', 'impact_updates'],
            'grid_size_degrees': self.config['grid_size_degrees']
        })
        
        self.logger.info("Impact Assessor ready to process events")


def main():
    """Main entry point"""
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'resilientflow-demo')
    agent = ImpactAssessorAgent(project_id)
    
    # Start monitoring
    agent.start_monitoring()
    
    # Keep alive
    try:
        while True:
            time.sleep(60)
            
            # Periodic heat-map update
            agent._generate_heat_map_tiles()
            
            # Broadcast status
            agent.pubsub_client.broadcast_agent_status('monitoring')
            
    except KeyboardInterrupt:
        agent.logger.info("Shutting down Impact Assessor Agent")
        agent.pubsub_client.shutdown()


if __name__ == '__main__':
    main() 