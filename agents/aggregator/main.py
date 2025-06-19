"""
Data Aggregator Agent - ResilientFlow
Processes satellite imagery for damage detection using Vertex AI Vision.
Triggered by Cloud Storage uploads and publishes detections to BigQuery GIS.
"""

import os
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from google.cloud import storage, bigquery
from google.cloud import aiplatform as vertex_ai
from google.cloud.functions_v1 import CloudFunctionsServiceClient
import numpy as np
from PIL import Image
import io

# Import ResilientFlow common utilities
import sys
sys.path.append('/workspace')
from common import get_logger, PubSubClient, FirestoreClient
from proto import api_pb2


class DataAggregatorAgent:
    """Satellite imagery processing agent with damage detection"""
    
    def __init__(self, project_id: str, region: str = 'us-central1'):
        self.project_id = project_id
        self.region = region
        self.agent_name = 'data_aggregator'
        self.logger = get_logger(self.agent_name)
        
        # Initialize clients
        self.storage_client = storage.Client(project=project_id)
        self.bigquery_client = bigquery.Client(project=project_id)
        self.pubsub_client = PubSubClient(project_id, self.agent_name)
        self.firestore_client = FirestoreClient(project_id, self.agent_name)
        
        # Initialize Vertex AI
        vertex_ai.init(project=project_id, location=region)
        
        # Configuration
        self.config = {
            'input_bucket': f'{project_id}-satellite-imagery',
            'output_bucket': f'{project_id}-processed-imagery',
            'bigquery_dataset': 'resilientflow',
            'damage_detection_model': f'projects/{project_id}/locations/{region}/models/damage-detector',
            'confidence_threshold': 0.7,
            'supported_formats': ['.tif', '.tiff', '.jpg', '.jpeg', '.png']
        }
        
        self.logger.info("Data Aggregator Agent initialized", config=self.config)
    
    def process_satellite_image(self, bucket_name: str, blob_name: str) -> Dict[str, Any]:
        """Process new satellite image for damage detection"""
        
        processing_id = str(uuid.uuid4())
        start_time = time.time()
        
        self.logger.info(
            f"Processing satellite image: {blob_name}",
            processing_id=processing_id,
            bucket=bucket_name
        )
        
        try:
            # Download image from Cloud Storage
            image_data = self._download_image(bucket_name, blob_name)
            
            # Extract metadata
            metadata = self._extract_image_metadata(bucket_name, blob_name)
            
            # Run damage detection
            detections = self._detect_damage(image_data, metadata)
            
            # Process detections into impact assessments
            assessments = self._process_detections(detections, metadata, processing_id)
            
            # Store results in BigQuery
            self._store_assessments_bq(assessments)
            
            # Publish high-severity detections to Pub/Sub
            critical_assessments = [a for a in assessments if a.severity_score >= 80]
            if critical_assessments:
                self._publish_critical_alerts(critical_assessments)
            
            # Update agent state
            self.firestore_client.update_agent_state({
                'last_processing_id': processing_id,
                'images_processed_count': self._increment_counter('images_processed'),
                'status': 'active'
            })
            
            processing_time = (time.time() - start_time) * 1000
            self.logger.agent_action(
                'process_satellite_image', 
                'success', 
                processing_time,
                processing_id=processing_id,
                detections_count=len(assessments),
                critical_count=len(critical_assessments)
            )
            
            return {
                'processing_id': processing_id,
                'assessments_count': len(assessments),
                'critical_count': len(critical_assessments),
                'processing_time_ms': processing_time
            }
            
        except Exception as e:
            self.logger.error(
                f"Error processing satellite image: {blob_name}",
                error=str(e),
                processing_id=processing_id
            )
            raise
    
    def _download_image(self, bucket_name: str, blob_name: str) -> bytes:
        """Download image from Cloud Storage"""
        
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            raise ValueError(f"Image {blob_name} not found in bucket {bucket_name}")
        
        # Check file format
        file_ext = os.path.splitext(blob_name)[1].lower()
        if file_ext not in self.config['supported_formats']:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        image_data = blob.download_as_bytes()
        
        self.logger.debug(
            f"Downloaded image {blob_name}",
            size_bytes=len(image_data),
            format=file_ext
        )
        
        return image_data
    
    def _extract_image_metadata(self, bucket_name: str, blob_name: str) -> Dict[str, Any]:
        """Extract metadata from image file and Cloud Storage"""
        
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.reload()  # Refresh metadata
        
        metadata = {
            'filename': blob_name,
            'size_bytes': blob.size,
            'content_type': blob.content_type,
            'created_time': blob.time_created.isoformat() if blob.time_created else None,
            'updated_time': blob.updated.isoformat() if blob.updated else None,
        }
        
        # Extract custom metadata (e.g., GPS coordinates, sensor info)
        if blob.metadata:
            metadata.update(blob.metadata)
        
        # Try to extract GPS coordinates from filename pattern or metadata
        # Example: "satellite_2024-01-15_lat40.7128_lon-74.0060.tif"
        if '_lat' in blob_name and '_lon' in blob_name:
            try:
                parts = blob_name.split('_')
                for part in parts:
                    if part.startswith('lat'):
                        metadata['latitude'] = float(part[3:])
                    elif part.startswith('lon'):
                        metadata['longitude'] = float(part[3:])
            except (ValueError, IndexError):
                self.logger.warning(f"Could not parse coordinates from filename: {blob_name}")
        
        # Set default coordinates if not found (for demo purposes)
        if 'latitude' not in metadata:
            metadata['latitude'] = 40.7128  # Default to NYC
            metadata['longitude'] = -74.0060
        
        return metadata
    
    def _detect_damage(self, image_data: bytes, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run damage detection using Vertex AI Vision model"""
        
        try:
            # For demo purposes, simulate damage detection
            # In production, this would call a custom Vertex AI model
            
            # Load image for analysis
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            
            # Simulate damage detection results
            detections = []
            
            # Generate random damage detections for demo
            import random
            random.seed(int(time.time()))  # Different results each time
            
            damage_types = ['structural', 'flood', 'fire', 'debris']
            num_detections = random.randint(0, 5)
            
            for i in range(num_detections):
                # Random bounding box
                x1 = random.randint(0, width // 2)
                y1 = random.randint(0, height // 2)
                x2 = random.randint(x1, width)
                y2 = random.randint(y1, height)
                
                damage_type = random.choice(damage_types)
                confidence = random.uniform(0.5, 0.95)
                
                detection = {
                    'damage_type': damage_type,
                    'confidence': confidence,
                    'bounding_box': {
                        'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2
                    },
                    'severity_raw': int(confidence * 100),
                    'pixel_area': (x2 - x1) * (y2 - y1)
                }
                
                # Only include high-confidence detections
                if confidence >= self.config['confidence_threshold']:
                    detections.append(detection)
            
            self.logger.info(
                f"Damage detection completed",
                total_detections=len(detections),
                damage_types=[d['damage_type'] for d in detections]
            )
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Damage detection failed", error=str(e))
            return []
    
    def _process_detections(self, detections: List[Dict[str, Any]], 
                           metadata: Dict[str, Any], processing_id: str) -> List[api_pb2.ImpactAssessment]:
        """Convert detections to impact assessments"""
        
        assessments = []
        
        for i, detection in enumerate(detections):
            assessment_id = f"{processing_id}_{i}"
            
            # Calculate severity score based on damage type and confidence
            severity_multiplier = {
                'structural': 1.0,
                'flood': 0.8,
                'fire': 0.9,
                'debris': 0.6
            }
            
            base_severity = detection['severity_raw']
            multiplier = severity_multiplier.get(detection['damage_type'], 0.7)
            severity_score = min(100, int(base_severity * multiplier))
            
            # Create protobuf message
            assessment = api_pb2.ImpactAssessment(
                assessment_id=assessment_id,
                latitude=metadata.get('latitude', 0.0),
                longitude=metadata.get('longitude', 0.0),
                grid_cell_id=self._get_grid_cell_id(
                    metadata.get('latitude', 0.0),
                    metadata.get('longitude', 0.0)
                ),
                severity_score=severity_score,
                damage_type=detection['damage_type'],
                assessed_ms=int(time.time() * 1000)
            )
            
            # Add confidence scores
            assessment.confidence_scores[detection['damage_type']] = detection['confidence']
            
            assessments.append(assessment)
        
        return assessments
    
    def _get_grid_cell_id(self, lat: float, lon: float, precision: int = 6) -> str:
        """Generate grid cell ID for spatial indexing"""
        # Simple grid system - round to precision decimal places
        grid_lat = round(lat, precision)
        grid_lon = round(lon, precision)
        return f"cell_{grid_lat}_{grid_lon}"
    
    def _store_assessments_bq(self, assessments: List[api_pb2.ImpactAssessment]) -> None:
        """Store impact assessments in BigQuery GIS"""
        
        if not assessments:
            return
        
        table_id = f"{self.project_id}.{self.config['bigquery_dataset']}.impact_assessments"
        
        # Convert protobuf messages to BigQuery rows
        rows = []
        for assessment in assessments:
            row = {
                'assessment_id': assessment.assessment_id,
                'latitude': assessment.latitude,
                'longitude': assessment.longitude,
                'grid_cell_id': assessment.grid_cell_id,
                'severity_score': assessment.severity_score,
                'damage_type': assessment.damage_type,
                'confidence_scores': dict(assessment.confidence_scores),
                'assessed_timestamp': time.strftime(
                    '%Y-%m-%d %H:%M:%S UTC',
                    time.gmtime(assessment.assessed_ms / 1000)
                ),
                'assessed_ms': assessment.assessed_ms,
                'source_agent': self.agent_name
            }
            rows.append(row)
        
        # Insert rows into BigQuery
        table_ref = self.bigquery_client.get_table(table_id)
        errors = self.bigquery_client.insert_rows_json(table_ref, rows)
        
        if errors:
            self.logger.error(f"BigQuery insert errors", errors=errors)
            raise Exception(f"Failed to insert assessments: {errors}")
        
        self.logger.info(
            f"Stored {len(rows)} assessments in BigQuery",
            table=table_id
        )
    
    def _publish_critical_alerts(self, assessments: List[api_pb2.ImpactAssessment]) -> None:
        """Publish critical assessments to Pub/Sub for immediate attention"""
        
        for assessment in assessments:
            # Convert to disaster event for broader distribution
            disaster_event = api_pb2.DisasterEvent(
                event_id=f"critical_{assessment.assessment_id}",
                source_agent=self.agent_name,
                latitude=assessment.latitude,
                longitude=assessment.longitude,
                event_type=assessment.damage_type,
                severity_raw=assessment.severity_score,
                timestamp_ms=assessment.assessed_ms
            )
            
            # Publish to disaster events topic
            self.pubsub_client.publish_proto_message(
                'disaster_events',
                disaster_event,
                {
                    'urgency': 'critical',
                    'requires_immediate_attention': 'true'
                }
            )
            
            self.logger.info(
                f"Published critical alert",
                event_id=disaster_event.event_id,
                severity=assessment.severity_score
            )
    
    def _increment_counter(self, counter_name: str) -> int:
        """Increment and return counter value"""
        # Simple counter implementation using Firestore
        counter_doc = self.firestore_client.read_document('agent_state', self.agent_name)
        current_value = 0
        
        if counter_doc and counter_name in counter_doc:
            current_value = counter_doc[counter_name]
        
        new_value = current_value + 1
        return new_value
    
    def start_monitoring(self) -> None:
        """Start monitoring for new satellite images"""
        
        self.logger.info("Starting satellite image monitoring")
        
        # Update agent status
        self.pubsub_client.broadcast_agent_status('monitoring', {
            'monitored_bucket': self.config['input_bucket'],
            'supported_formats': self.config['supported_formats']
        })
        
        # In production, this would be triggered by Cloud Storage notifications
        # For demo, we'll simulate processing
        self.logger.info(
            "Agent ready to process satellite imagery",
            input_bucket=self.config['input_bucket']
        )


def cloud_function_handler(cloud_event, context):
    """Cloud Function entry point for Cloud Storage triggers"""
    
    # Extract event data
    bucket_name = cloud_event['bucket']
    blob_name = cloud_event['name']
    
    # Initialize agent
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
    agent = DataAggregatorAgent(project_id)
    
    # Process the image
    result = agent.process_satellite_image(bucket_name, blob_name)
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }


def main():
    """Main entry point for standalone execution"""
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'resilientflow-demo')
    agent = DataAggregatorAgent(project_id)
    
    # Start monitoring
    agent.start_monitoring()
    
    # Keep alive
    try:
        while True:
            time.sleep(60)
            agent.pubsub_client.broadcast_agent_status('monitoring')
    except KeyboardInterrupt:
        agent.logger.info("Shutting down Data Aggregator Agent")
        agent.pubsub_client.shutdown()


if __name__ == '__main__':
    main() 