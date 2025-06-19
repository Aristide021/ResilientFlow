"""
Report Synthesizer Agent - ResilientFlow
Compiles comprehensive PDF situation reports with impact maps, resource tables,
and agent activity logs. Outputs to Cloud Storage with signed URLs.
"""

import os
import time
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import base64

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from google.cloud import storage
from google.cloud import bigquery
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import requests

# Import ResilientFlow common utilities
import sys
sys.path.append('/workspace')
from common import get_logger, PubSubClient, FirestoreClient
from proto import api_pb2


@dataclass
class ReportData:
    """Data structure for situation report"""
    incident_id: str
    report_timestamp: datetime
    summary_stats: Dict[str, Any]
    impact_zones: List[Dict[str, Any]]
    resource_allocations: List[Dict[str, Any]]
    agent_activities: List[Dict[str, Any]]
    critical_alerts: List[Dict[str, Any]]


class ReportSynthesizerAgent:
    """PDF situation report generation and data synthesis agent"""
    
    def __init__(self, project_id: str, region: str = 'us-central1'):
        self.project_id = project_id
        self.region = region
        self.agent_name = 'report_synthesizer'
        self.logger = get_logger(self.agent_name)
        
        # Initialize clients
        self.storage_client = storage.Client(project=project_id)
        self.bigquery_client = bigquery.Client(project=project_id)
        self.pubsub_client = PubSubClient(project_id, self.agent_name)
        self.firestore_client = FirestoreClient(project_id, self.agent_name)
        
        # Configuration
        self.config = {
            'reports_bucket': f'{project_id}-situation-reports',
            'bigquery_dataset': 'resilientflow',
            'report_generation_interval_s': 1800,  # 30 minutes
            'max_zones_per_report': 50,
            'map_image_width': 6,  # inches
            'map_image_height': 4,  # inches
            'url_expiry_hours': 24
        }
        
        # Ensure buckets exist
        self._ensure_storage_buckets()
        
        # Setup subscriptions
        self._setup_subscriptions()
        
        self.logger.info("Report Synthesizer Agent initialized", config=self.config)
    
    def _ensure_storage_buckets(self) -> None:
        """Ensure required Cloud Storage buckets exist"""
        
        try:
            bucket = self.storage_client.bucket(self.config['reports_bucket'])
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(self.config['reports_bucket'])
                self.logger.info(f"Created bucket: {self.config['reports_bucket']}")
            
        except Exception as e:
            self.logger.warning(f"Could not ensure bucket exists", error=str(e))
    
    def _setup_subscriptions(self) -> None:
        """Setup Pub/Sub subscriptions"""
        
        # Subscribe to allocation plans to trigger reports
        self.pubsub_client.subscribe_to_topic(
            'allocation_plans',
            self._handle_allocation_plan,
            api_pb2.AllocationPlan
        )
        
        # Subscribe to impact updates for continuous reporting
        self.pubsub_client.subscribe_to_topic(
            'impact_updates',
            self._handle_impact_update,
            api_pb2.ImpactAssessment
        )
        
        self.logger.info("Pub/Sub subscriptions established")
    
    def _handle_allocation_plan(self, plan: api_pb2.AllocationPlan, attributes: Dict[str, str]) -> None:
        """Handle allocation plan and trigger situation report"""
        
        self.logger.info(
            f"Received allocation plan: {plan.plan_id}",
            zones_count=len(plan.impacted_zones)
        )
        
        # Generate comprehensive situation report
        self._generate_situation_report(plan.plan_id)
    
    def _handle_impact_update(self, assessment: api_pb2.ImpactAssessment, attributes: Dict[str, str]) -> None:
        """Handle impact update for periodic reporting"""
        
        # Only generate reports for critical updates
        if assessment.severity_score >= 85:
            self.logger.info(
                f"Critical impact update received: {assessment.assessment_id}",
                severity=assessment.severity_score
            )
            
            # Generate focused report for critical zone
            self._generate_focused_report(assessment)
    
    def _generate_situation_report(self, incident_id: str) -> Dict[str, str]:
        """Generate comprehensive situation report"""
        
        report_id = f"sitrep_{incident_id}_{int(time.time())}"
        start_time = time.time()
        
        self.logger.info(
            f"Generating situation report",
            report_id=report_id,
            incident_id=incident_id
        )
        
        try:
            # Gather report data
            report_data = self._gather_report_data(incident_id)
            
            # Generate PDF report
            pdf_url = self._generate_pdf_report(report_data, report_id)
            
            # Generate GeoJSON data
            geojson_url = self._generate_geojson_data(report_data, report_id)
            
            # Create situation report message
            situation_report = api_pb2.SituationReport(
                report_id=report_id,
                pdf_url=pdf_url,
                geojson_url=geojson_url,
                generated_ms=int(time.time() * 1000),
                incident_id=incident_id
            )
            
            # Add summary statistics
            for key, value in report_data.summary_stats.items():
                situation_report.summary_stats[key] = str(value)
            
            # Store report metadata in Firestore
            self._store_report_metadata(situation_report, report_data)
            
            # Publish report notification
            self.pubsub_client.publish_proto_message(
                'agent_events',
                situation_report,
                {
                    'event_type': 'situation_report_generated',
                    'urgency': 'normal'
                }
            )
            
            # Update agent state
            self.firestore_client.update_agent_state({
                'last_report_id': report_id,
                'reports_generated_count': self._increment_counter('reports_generated'),
                'status': 'active'
            })
            
            processing_time = (time.time() - start_time) * 1000
            self.logger.agent_action(
                'generate_situation_report',
                'success',
                processing_time,
                report_id=report_id,
                zones_count=len(report_data.impact_zones)
            )
            
            return {
                'report_id': report_id,
                'pdf_url': pdf_url,
                'geojson_url': geojson_url
            }
            
        except Exception as e:
            self.logger.error(
                f"Failed to generate situation report",
                report_id=report_id,
                error=str(e)
            )
            raise
    
    def _generate_focused_report(self, assessment: api_pb2.ImpactAssessment) -> None:
        """Generate focused report for specific critical zone"""
        
        report_id = f"focused_{assessment.assessment_id}_{int(time.time())}"
        
        self.logger.info(
            f"Generating focused report",
            report_id=report_id,
            assessment_id=assessment.assessment_id
        )
        
        try:
            # Create simplified report data for the critical zone
            report_data = ReportData(
                incident_id=f"critical_{assessment.assessment_id}",
                report_timestamp=datetime.now(timezone.utc),
                summary_stats={
                    'critical_zones': 1,
                    'max_severity': assessment.severity_score,
                    'primary_damage_type': assessment.damage_type
                },
                impact_zones=[{
                    'zone_id': assessment.grid_cell_id,
                    'latitude': assessment.latitude,
                    'longitude': assessment.longitude,
                    'severity_score': assessment.severity_score,
                    'damage_type': assessment.damage_type
                }],
                resource_allocations=[],
                agent_activities=[],
                critical_alerts=[]
            )
            
            # Generate quick PDF
            pdf_url = self._generate_pdf_report(report_data, report_id)
            
            self.logger.info(f"Generated focused report", report_id=report_id, pdf_url=pdf_url)
            
        except Exception as e:
            self.logger.error(f"Failed to generate focused report", error=str(e))
    
    def _gather_report_data(self, incident_id: str) -> ReportData:
        """Gather all data needed for situation report"""
        
        self.logger.debug(f"Gathering report data for incident {incident_id}")
        
        # Get impact zones from BigQuery
        impact_zones = self._query_impact_zones()
        
        # Get resource allocations from Firestore
        resource_allocations = self._query_resource_allocations(incident_id)
        
        # Get agent activities
        agent_activities = self._query_agent_activities()
        
        # Get critical alerts
        critical_alerts = self._query_critical_alerts()
        
        # Calculate summary statistics
        summary_stats = self._calculate_summary_stats(
            impact_zones, resource_allocations, agent_activities, critical_alerts
        )
        
        report_data = ReportData(
            incident_id=incident_id,
            report_timestamp=datetime.now(timezone.utc),
            summary_stats=summary_stats,
            impact_zones=impact_zones,
            resource_allocations=resource_allocations,
            agent_activities=agent_activities,
            critical_alerts=critical_alerts
        )
        
        return report_data
    
    def _query_impact_zones(self) -> List[Dict[str, Any]]:
        """Query impact zones from BigQuery"""
        
        query = f"""
        SELECT 
            zone_id,
            center_latitude,
            center_longitude,
            severity_score,
            affected_area_km2,
            damage_types,
            assessment_count,
            confidence,
            last_updated
        FROM `{self.project_id}.{self.config['bigquery_dataset']}.impact_zones`
        WHERE last_updated > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
        ORDER BY severity_score DESC
        LIMIT {self.config['max_zones_per_report']}
        """
        
        try:
            query_job = self.bigquery_client.query(query)
            results = query_job.result()
            
            zones = []
            for row in results:
                zone = {
                    'zone_id': row.zone_id,
                    'latitude': row.center_latitude,
                    'longitude': row.center_longitude,
                    'severity_score': row.severity_score,
                    'affected_area_km2': row.affected_area_km2,
                    'damage_types': row.damage_types,
                    'assessment_count': row.assessment_count,
                    'confidence': row.confidence,
                    'last_updated': row.last_updated.isoformat() if row.last_updated else None
                }
                zones.append(zone)
            
            self.logger.debug(f"Queried {len(zones)} impact zones")
            return zones
            
        except Exception as e:
            self.logger.warning(f"Failed to query impact zones", error=str(e))
            return []
    
    def _query_resource_allocations(self, incident_id: str) -> List[Dict[str, Any]]:
        """Query resource allocations from Firestore"""
        
        try:
            allocations = self.firestore_client.get_active_allocations(incident_id)
            
            simplified_allocations = []
            for allocation_plan in allocations:
                for allocation in allocation_plan.get('allocations', []):
                    simplified_allocation = {
                        'allocation_id': allocation.get('allocation_id'),
                        'resource_type': allocation.get('resource_type'),
                        'quantity': allocation.get('quantity'),
                        'status': allocation.get('status', 'planned'),
                        'zone_id': allocation.get('demand_zone_id'),
                        'facility_id': allocation.get('supply_facility_id')
                    }
                    simplified_allocations.append(simplified_allocation)
            
            self.logger.debug(f"Queried {len(simplified_allocations)} resource allocations")
            return simplified_allocations
            
        except Exception as e:
            self.logger.warning(f"Failed to query resource allocations", error=str(e))
            return []
    
    def _query_agent_activities(self) -> List[Dict[str, Any]]:
        """Query recent agent activities"""
        
        try:
            agent_states = self.firestore_client.get_agent_states()
            
            activities = []
            for state in agent_states:
                activity = {
                    'agent_name': state.get('agent_name'),
                    'status': state.get('status', 'unknown'),
                    'last_activity': state.get('last_heartbeat_ms', 0),
                    'processed_count': state.get('images_processed_count', 0) + 
                                     state.get('allocations_created', 0) + 
                                     state.get('alerts_generated_count', 0)
                }
                activities.append(activity)
            
            self.logger.debug(f"Queried {len(activities)} agent activities")
            return activities
            
        except Exception as e:
            self.logger.warning(f"Failed to query agent activities", error=str(e))
            return []
    
    def _query_critical_alerts(self) -> List[Dict[str, Any]]:
        """Query recent critical alerts"""
        
        try:
            # Query alerts from last 24 hours
            filters = [
                ('created_timestamp', '>', time.time() - 24*3600),
                ('urgency', '==', 'immediate')
            ]
            
            alert_docs = self.firestore_client.query_documents('alerts', filters, order_by='-created_timestamp', limit=20)
            
            alerts = []
            for alert_doc in alert_docs:
                alert = {
                    'alert_id': alert_doc.get('alert_id'),
                    'title': alert_doc.get('title'),
                    'urgency': alert_doc.get('urgency'),
                    'affected_areas': alert_doc.get('affected_areas', []),
                    'created_timestamp': alert_doc.get('created_timestamp'),
                    'event_type': alert_doc.get('event_type')
                }
                alerts.append(alert)
            
            self.logger.debug(f"Queried {len(alerts)} critical alerts")
            return alerts
            
        except Exception as e:
            self.logger.warning(f"Failed to query critical alerts", error=str(e))
            return []
    
    def _calculate_summary_stats(self, impact_zones: List[Dict[str, Any]], 
                                resource_allocations: List[Dict[str, Any]],
                                agent_activities: List[Dict[str, Any]],
                                critical_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for the report"""
        
        stats = {
            'total_impact_zones': len(impact_zones),
            'critical_zones': len([z for z in impact_zones if z['severity_score'] >= 80]),
            'high_severity_zones': len([z for z in impact_zones if z['severity_score'] >= 60]),
            'total_affected_area_km2': sum(z.get('affected_area_km2', 0) for z in impact_zones),
            'max_severity_score': max([z['severity_score'] for z in impact_zones], default=0),
            'avg_severity_score': np.mean([z['severity_score'] for z in impact_zones]) if impact_zones else 0,
            'total_resource_allocations': len(resource_allocations),
            'pending_allocations': len([a for a in resource_allocations if a.get('status') == 'planned']),
            'completed_allocations': len([a for a in resource_allocations if a.get('status') == 'completed']),
            'active_agents': len([a for a in agent_activities if a.get('status') == 'active']),
            'total_alerts_generated': len(critical_alerts),
            'report_generated_at': datetime.now(timezone.utc).isoformat(),
            'data_freshness_hours': 24
        }
        
        # Calculate resource totals
        resource_totals = {}
        for allocation in resource_allocations:
            resource_type = allocation.get('resource_type', 'unknown')
            quantity = allocation.get('quantity', 0)
            resource_totals[resource_type] = resource_totals.get(resource_type, 0) + quantity
        
        stats['resource_totals'] = resource_totals
        
        # Most affected damage types
        damage_types = {}
        for zone in impact_zones:
            for damage_type in zone.get('damage_types', []):
                damage_types[damage_type] = damage_types.get(damage_type, 0) + 1
        
        stats['primary_damage_types'] = sorted(damage_types.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return stats
    
    def _generate_pdf_report(self, report_data: ReportData, report_id: str) -> str:
        """Generate PDF situation report"""
        
        self.logger.debug(f"Generating PDF report {report_id}")
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Title
        title = Paragraph(f"ResilientFlow Situation Report", title_style)
        story.append(title)
        
        subtitle = Paragraph(
            f"Report ID: {report_id}<br/>Generated: {report_data.report_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}<br/>Incident: {report_data.incident_id}",
            styles['Normal']
        )
        story.append(subtitle)
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        
        summary_text = f"""
        <b>Total Impact Zones:</b> {report_data.summary_stats.get('total_impact_zones', 0)}<br/>
        <b>Critical Zones:</b> {report_data.summary_stats.get('critical_zones', 0)}<br/>
        <b>Maximum Severity:</b> {report_data.summary_stats.get('max_severity_score', 0)}/100<br/>
        <b>Total Affected Area:</b> {report_data.summary_stats.get('total_affected_area_km2', 0):.2f} km²<br/>
        <b>Resource Allocations:</b> {report_data.summary_stats.get('total_resource_allocations', 0)}<br/>
        <b>Active Agents:</b> {report_data.summary_stats.get('active_agents', 0)}<br/>
        """
        
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Impact Zones Table
        if report_data.impact_zones:
            story.append(Paragraph("Critical Impact Zones", styles['Heading2']))
            
            zone_data = [['Zone ID', 'Latitude', 'Longitude', 'Severity', 'Area (km²)', 'Damage Types']]
            
            for zone in report_data.impact_zones[:10]:  # Top 10 zones
                zone_data.append([
                    zone.get('zone_id', '')[:20],  # Truncate long IDs
                    f"{zone.get('latitude', 0):.4f}",
                    f"{zone.get('longitude', 0):.4f}",
                    str(zone.get('severity_score', 0)),
                    f"{zone.get('affected_area_km2', 0):.2f}",
                    ', '.join(zone.get('damage_types', []))[:30]
                ])
            
            zone_table = Table(zone_data)
            zone_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(zone_table)
            story.append(Spacer(1, 20))
        
        # Resource Allocations
        if report_data.resource_allocations:
            story.append(Paragraph("Resource Allocations Summary", styles['Heading2']))
            
            # Group by resource type
            resource_summary = {}
            for allocation in report_data.resource_allocations:
                resource_type = allocation.get('resource_type', 'unknown')
                quantity = allocation.get('quantity', 0)
                resource_summary[resource_type] = resource_summary.get(resource_type, 0) + quantity
            
            resource_text = "<br/>".join([
                f"<b>{resource_type.title()}:</b> {quantity} units"
                for resource_type, quantity in resource_summary.items()
            ])
            
            story.append(Paragraph(resource_text, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Agent Status
        if report_data.agent_activities:
            story.append(Paragraph("Agent Swarm Status", styles['Heading2']))
            
            agent_data = [['Agent Name', 'Status', 'Last Activity', 'Items Processed']]
            
            for activity in report_data.agent_activities:
                last_activity = datetime.fromtimestamp(
                    activity.get('last_activity', 0) / 1000
                ).strftime('%H:%M:%S') if activity.get('last_activity') else 'Unknown'
                
                agent_data.append([
                    activity.get('agent_name', '').replace('_', ' ').title(),
                    activity.get('status', 'unknown').title(),
                    last_activity,
                    str(activity.get('processed_count', 0))
                ])
            
            agent_table = Table(agent_data)
            agent_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(agent_table)
        
        # Generate severity map (simplified)
        if report_data.impact_zones:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Impact Severity Map", styles['Heading2']))
            
            map_buffer = self._generate_severity_map(report_data.impact_zones)
            if map_buffer:
                map_image = Image(map_buffer, width=self.config['map_image_width']*inch, 
                                height=self.config['map_image_height']*inch)
                story.append(map_image)
        
        # Build PDF
        doc.build(story)
        
        # Upload to Cloud Storage
        buffer.seek(0)
        pdf_blob_name = f"reports/{report_id}.pdf"
        
        bucket = self.storage_client.bucket(self.config['reports_bucket'])
        blob = bucket.blob(pdf_blob_name)
        blob.upload_from_file(buffer, content_type='application/pdf')
        
        # Generate signed URL
        pdf_url = blob.generate_signed_url(
            expiration=time.time() + self.config['url_expiry_hours'] * 3600,
            method='GET'
        )
        
        self.logger.info(f"Generated PDF report", report_id=report_id, size_bytes=buffer.tell())
        
        return pdf_url
    
    def _generate_severity_map(self, impact_zones: List[Dict[str, Any]]) -> Optional[io.BytesIO]:
        """Generate impact severity map visualization"""
        
        try:
            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(self.config['map_image_width'], self.config['map_image_height']))
            
            # Extract coordinates and severities
            lats = [zone['latitude'] for zone in impact_zones]
            lons = [zone['longitude'] for zone in impact_zones]
            severities = [zone['severity_score'] for zone in impact_zones]
            
            # Create scatter plot
            scatter = ax.scatter(lons, lats, c=severities, cmap='YlOrRd', 
                               s=100, alpha=0.7, edgecolors='black')
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Severity Score', rotation=270, labelpad=15)
            
            # Set labels and title
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.set_title('Impact Severity Map')
            ax.grid(True, alpha=0.3)
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            self.logger.warning(f"Failed to generate severity map", error=str(e))
            return None
    
    def _generate_geojson_data(self, report_data: ReportData, report_id: str) -> str:
        """Generate GeoJSON data for web visualization"""
        
        features = []
        
        # Add impact zones as features
        for zone in report_data.impact_zones:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [zone.get('longitude', 0), zone.get('latitude', 0)]
                },
                'properties': {
                    'zone_id': zone.get('zone_id'),
                    'severity_score': zone.get('severity_score', 0),
                    'damage_types': zone.get('damage_types', []),
                    'affected_area_km2': zone.get('affected_area_km2', 0),
                    'assessment_count': zone.get('assessment_count', 0),
                    'confidence': zone.get('confidence', 0),
                    'type': 'impact_zone'
                }
            }
            features.append(feature)
        
        # Create GeoJSON FeatureCollection
        geojson_data = {
            'type': 'FeatureCollection',
            'metadata': {
                'report_id': report_id,
                'generated_at': report_data.report_timestamp.isoformat(),
                'total_zones': len(report_data.impact_zones),
                'summary_stats': report_data.summary_stats
            },
            'features': features
        }
        
        # Upload to Cloud Storage
        geojson_blob_name = f"geojson/{report_id}.geojson"
        
        bucket = self.storage_client.bucket(self.config['reports_bucket'])
        blob = bucket.blob(geojson_blob_name)
        blob.upload_from_string(
            json.dumps(geojson_data, indent=2),
            content_type='application/geo+json'
        )
        
        # Generate signed URL
        geojson_url = blob.generate_signed_url(
            expiration=time.time() + self.config['url_expiry_hours'] * 3600,
            method='GET'
        )
        
        self.logger.debug(f"Generated GeoJSON data", report_id=report_id, features_count=len(features))
        
        return geojson_url
    
    def _store_report_metadata(self, situation_report: api_pb2.SituationReport, 
                              report_data: ReportData) -> None:
        """Store report metadata in Firestore"""
        
        metadata = {
            'report_id': situation_report.report_id,
            'incident_id': situation_report.incident_id,
            'pdf_url': situation_report.pdf_url,
            'geojson_url': situation_report.geojson_url,
            'generated_ms': situation_report.generated_ms,
            'summary_stats': dict(situation_report.summary_stats),
            'zones_count': len(report_data.impact_zones),
            'allocations_count': len(report_data.resource_allocations),
            'agents_count': len(report_data.agent_activities),
            'alerts_count': len(report_data.critical_alerts),
            'generated_by': self.agent_name
        }
        
        self.firestore_client.write_document('reports', situation_report.report_id, metadata)
    
    def _increment_counter(self, counter_name: str) -> int:
        """Increment and return counter value"""
        
        counter_doc = self.firestore_client.read_document('agent_state', self.agent_name)
        current_value = 0
        
        if counter_doc and counter_name in counter_doc:
            current_value = counter_doc[counter_name]
        
        return current_value + 1
    
    def generate_scheduled_report(self) -> None:
        """Generate scheduled situation report"""
        
        self.logger.info("Generating scheduled situation report")
        
        # Create generic incident ID for scheduled reports
        incident_id = f"scheduled_{int(time.time())}"
        
        try:
            result = self._generate_situation_report(incident_id)
            self.logger.info(
                f"Scheduled report generated successfully",
                report_id=result['report_id']
            )
        except Exception as e:
            self.logger.error(f"Scheduled report generation failed", error=str(e))
    
    def start_monitoring(self) -> None:
        """Start report synthesis monitoring"""
        
        self.logger.info("Starting Report Synthesizer monitoring")
        
        # Update agent status
        self.pubsub_client.broadcast_agent_status('monitoring', {
            'subscribed_topics': ['allocation_plans', 'impact_updates'],
            'reports_bucket': self.config['reports_bucket']
        })
        
        self.logger.info("Report Synthesizer ready to generate reports")


def main():
    """Main entry point"""
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'resilientflow-demo')
    agent = ReportSynthesizerAgent(project_id)
    
    # Start monitoring
    agent.start_monitoring()
    
    # Keep alive with periodic report generation
    try:
        last_report_time = time.time()
        
        while True:
            time.sleep(60)
            
            # Generate scheduled report every interval
            if time.time() - last_report_time >= agent.config['report_generation_interval_s']:
                agent.generate_scheduled_report()
                last_report_time = time.time()
            
            agent.pubsub_client.broadcast_agent_status('monitoring')
            
    except KeyboardInterrupt:
        agent.logger.info("Shutting down Report Synthesizer Agent")
        agent.pubsub_client.shutdown()


if __name__ == '__main__':
    main() 