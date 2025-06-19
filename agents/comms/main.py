"""
Communications Coordinator Agent - ResilientFlow
Handles multilingual alert synthesis and distribution via FCM, SMS, and social media.
Generates CAP (Common Alerting Protocol) XML and coordinates public communications.
"""

import os
import time
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech
import firebase_admin
from firebase_admin import credentials, messaging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Import ResilientFlow common utilities
import sys
sys.path.append('/workspace')
from common import get_logger, PubSubClient, FirestoreClient
from proto import api_pb2


@dataclass
class AlertTemplate:
    """Template for generating alerts"""
    urgency: str  # "immediate", "expected", "future"
    severity: str  # "extreme", "severe", "moderate", "minor"
    certainty: str  # "observed", "likely", "possible", "unlikely"
    template_en: str
    template_es: str
    template_fr: str


class CommunicationsCoordinatorAgent:
    """Multilingual communications and alert distribution agent"""
    
    def __init__(self, project_id: str, region: str = 'us-central1'):
        self.project_id = project_id
        self.region = region
        self.agent_name = 'comms_coordinator'
        self.logger = get_logger(self.agent_name)
        
        # Initialize clients
        self.pubsub_client = PubSubClient(project_id, self.agent_name)
        self.firestore_client = FirestoreClient(project_id, self.agent_name)
        
        # Initialize translation client
        self.translate_client = translate.Client()
        
        # Initialize text-to-speech client
        self.tts_client = texttospeech.TextToSpeechClient()
        
        # Initialize Firebase (for FCM)
        self._initialize_firebase()
        
        # Configuration
        self.config = {
            'supported_languages': ['en', 'es', 'fr'],
            'default_language': 'en',
            'alert_expiry_hours': 24,
            'max_message_length': 160,  # SMS constraint
            'fcm_topic_prefix': 'resilientflow',
            'cap_identifier_prefix': 'resilientflow.emergency',
            'social_media_enabled': False  # Would integrate with Twitter API
        }
        
        # Alert templates
        self.alert_templates = {
            'flood': AlertTemplate(
                urgency='immediate',
                severity='severe',
                certainty='observed',
                template_en='FLOOD ALERT: Flooding detected in {area}. Severity: {severity}/100. Avoid the area and seek higher ground. More info: {url}',
                template_es='ALERTA DE INUNDACIÓN: Inundación detectada en {area}. Gravedad: {severity}/100. Evite el área y busque terreno elevado. Más información: {url}',
                template_fr='ALERTE INONDATION: Inondation détectée à {area}. Gravité: {severity}/100. Évitez la zone et cherchez un terrain plus élevé. Plus d\'infos: {url}'
            ),
            'fire': AlertTemplate(
                urgency='immediate',
                severity='extreme',
                certainty='observed',
                template_en='FIRE ALERT: Fire detected in {area}. Severity: {severity}/100. Evacuate immediately if in the area. More info: {url}',
                template_es='ALERTA DE INCENDIO: Incendio detectado en {area}. Gravedad: {severity}/100. Evacúe inmediatamente si está en el área. Más información: {url}',
                template_fr='ALERTE INCENDIE: Incendie détecté à {area}. Gravité: {severity}/100. Évacuez immédiatement si vous êtes dans la zone. Plus d\'infos: {url}'
            ),
            'earthquake': AlertTemplate(
                urgency='immediate',
                severity='extreme',
                certainty='observed',
                template_en='EARTHQUAKE ALERT: Seismic activity detected in {area}. Severity: {severity}/100. Drop, cover, and hold on. More info: {url}',
                template_es='ALERTA DE TERREMOTO: Actividad sísmica detectada en {area}. Gravedad: {severity}/100. Agáchese, cúbrase y agárrese. Más información: {url}',
                template_fr='ALERTE SÉISME: Activité sismique détectée à {area}. Gravité: {severity}/100. Baissez-vous, couvrez-vous et tenez-vous. Plus d\'infos: {url}'
            ),
            'general': AlertTemplate(
                urgency='expected',
                severity='moderate',
                certainty='likely',
                template_en='EMERGENCY ALERT: {event_type} in {area}. Severity: {severity}/100. Follow local emergency instructions. More info: {url}',
                template_es='ALERTA DE EMERGENCIA: {event_type} en {area}. Gravedad: {severity}/100. Siga las instrucciones de emergencia locales. Más información: {url}',
                template_fr='ALERTE URGENCE: {event_type} à {area}. Gravité: {severity}/100. Suivez les instructions d\'urgence locales. Plus d\'infos: {url}'
            )
        }
        
        # Setup subscriptions
        self._setup_subscriptions()
        
        self.logger.info("Communications Coordinator Agent initialized", config=self.config)
    
    def _initialize_firebase(self) -> None:
        """Initialize Firebase Admin SDK for FCM"""
        
        try:
            # In production, use service account key
            # For demo, initialize with default credentials
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            
            self.logger.info("Firebase initialized for FCM")
            
        except Exception as e:
            self.logger.warning(f"Could not initialize Firebase", error=str(e))
    
    def _setup_subscriptions(self) -> None:
        """Setup Pub/Sub subscriptions"""
        
        # Subscribe to disaster events for immediate alerts
        self.pubsub_client.subscribe_to_topic(
            'disaster_events',
            self._handle_disaster_event,
            api_pb2.DisasterEvent
        )
        
        # Subscribe to impact updates for ongoing communications
        self.pubsub_client.subscribe_to_topic(
            'impact_updates',
            self._handle_impact_update,
            api_pb2.ImpactAssessment
        )
        
        # Subscribe to allocation plans for logistics updates
        self.pubsub_client.subscribe_to_topic(
            'allocation_plans',
            self._handle_allocation_plan,
            api_pb2.AllocationPlan
        )
        
        self.logger.info("Pub/Sub subscriptions established")
    
    def _handle_disaster_event(self, event: api_pb2.DisasterEvent, attributes: Dict[str, str]) -> None:
        """Handle disaster event for immediate alert generation"""
        
        self.logger.info(
            f"Received disaster event: {event.event_id}",
            event_type=event.event_type,
            severity=event.severity_raw,
            urgency=attributes.get('urgency', 'unknown')
        )
        
        # Generate immediate alert for high-severity events
        if event.severity_raw >= 70 or attributes.get('urgency') == 'critical':
            self._generate_emergency_alert(event)
    
    def _handle_impact_update(self, assessment: api_pb2.ImpactAssessment, attributes: Dict[str, str]) -> None:
        """Handle impact assessment for situational updates"""
        
        self.logger.info(
            f"Received impact update: {assessment.assessment_id}",
            severity=assessment.severity_score,
            damage_type=assessment.damage_type
        )
        
        # Generate situational update for critical assessments
        if assessment.severity_score >= 80:
            self._generate_situational_update(assessment)
    
    def _handle_allocation_plan(self, plan: api_pb2.AllocationPlan, attributes: Dict[str, str]) -> None:
        """Handle allocation plan for logistics communications"""
        
        self.logger.info(
            f"Received allocation plan: {plan.plan_id}",
            zones_count=len(plan.impacted_zones)
        )
        
        # Generate logistics update
        self._generate_logistics_update(plan)
    
    def _generate_emergency_alert(self, event: api_pb2.DisasterEvent) -> None:
        """Generate and distribute emergency alert"""
        
        alert_id = f"alert_{event.event_id}_{int(time.time())}"
        
        self.logger.info(
            f"Generating emergency alert",
            alert_id=alert_id,
            event_type=event.event_type
        )
        
        try:
            # Get area name (simplified - would use reverse geocoding in production)
            area_name = self._get_area_name(event.latitude, event.longitude)
            
            # Select template
            template = self.alert_templates.get(event.event_type, self.alert_templates['general'])
            
            # Generate multilingual messages
            messages = self._generate_multilingual_messages(
                template,
                {
                    'area': area_name,
                    'severity': event.severity_raw,
                    'event_type': event.event_type.title(),
                    'url': f'https://resilientflow.app/alerts/{alert_id}'
                }
            )
            
            # Create alert messages
            alert_messages = []
            for lang_code, message_text in messages.items():
                alert_message = api_pb2.AlertMessage(
                    alert_id=f"{alert_id}_{lang_code}",
                    language_code=lang_code,
                    title=f"Emergency Alert - {event.event_type.title()}",
                    body=message_text,
                    urgency=template.urgency,
                    affected_areas=[area_name],
                    expires_ms=int((time.time() + self.config['alert_expiry_hours'] * 3600) * 1000)
                )
                alert_messages.append(alert_message)
            
            # Generate CAP XML
            cap_xml_url = self._generate_cap_xml(event, template, area_name, alert_id)
            
            # Update alert messages with CAP URL
            for alert_message in alert_messages:
                alert_message.cap_xml_url = cap_xml_url
            
            # Distribute alerts
            self._distribute_alerts(alert_messages, event)
            
            # Store alert in Firestore
            self._store_alert_record(alert_messages[0], event)
            
            # Update agent state
            self.firestore_client.update_agent_state({
                'last_alert_id': alert_id,
                'alerts_generated_count': self._increment_counter('alerts_generated'),
                'status': 'active'
            })
            
            self.logger.agent_action(
                'generate_emergency_alert',
                'success',
                duration_ms=None,
                alert_id=alert_id,
                languages_count=len(messages)
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to generate emergency alert",
                alert_id=alert_id,
                error=str(e)
            )
            raise
    
    def _generate_situational_update(self, assessment: api_pb2.ImpactAssessment) -> None:
        """Generate situational update for ongoing incidents"""
        
        update_id = f"update_{assessment.assessment_id}_{int(time.time())}"
        
        self.logger.info(
            f"Generating situational update",
            update_id=update_id,
            damage_type=assessment.damage_type
        )
        
        try:
            area_name = self._get_area_name(assessment.latitude, assessment.longitude)
            
            # Create update message
            update_template = f"SITUATION UPDATE: {assessment.damage_type} impact in {{area}}. Current severity: {{severity}}/100. Latest assessment from disaster response team. More info: {{url}}"
            
            messages = {}
            for lang_code in self.config['supported_languages']:
                if lang_code == 'en':
                    message_text = update_template.format(
                        area=area_name,
                        severity=assessment.severity_score,
                        url=f'https://resilientflow.app/updates/{update_id}'
                    )
                else:
                    # Translate message
                    translated = self.translate_client.translate(
                        update_template,
                        target_language=lang_code,
                        source_language='en'
                    )
                    message_text = translated['translatedText'].format(
                        area=area_name,
                        severity=assessment.severity_score,
                        url=f'https://resilientflow.app/updates/{update_id}'
                    )
                
                messages[lang_code] = message_text
            
            # Create alert messages
            alert_messages = []
            for lang_code, message_text in messages.items():
                alert_message = api_pb2.AlertMessage(
                    alert_id=f"{update_id}_{lang_code}",
                    language_code=lang_code,
                    title=f"Situation Update - {assessment.damage_type.title()}",
                    body=message_text,
                    urgency='expected',
                    affected_areas=[area_name],
                    expires_ms=int((time.time() + 12 * 3600) * 1000)  # 12 hour expiry
                )
                alert_messages.append(alert_message)
            
            # Distribute updates (lower priority than emergency alerts)
            self._distribute_updates(alert_messages)
            
            self.logger.info(f"Generated situational update", update_id=update_id)
            
        except Exception as e:
            self.logger.error(f"Failed to generate situational update", error=str(e))
    
    def _generate_logistics_update(self, plan: api_pb2.AllocationPlan) -> None:
        """Generate logistics update for resource allocation"""
        
        update_id = f"logistics_{plan.plan_id}_{int(time.time())}"
        
        self.logger.info(
            f"Generating logistics update",
            update_id=update_id,
            zones_count=len(plan.impacted_zones)
        )
        
        try:
            # Create logistics message
            resource_summary = ", ".join([f"{k}: {v}" for k, v in plan.resource_totals.items()])
            
            logistics_template = f"LOGISTICS UPDATE: Emergency resources deployed to {{zones_count}} zones. Resources: {{resources}}. Distribution in progress. Track at: {{url}}"
            
            messages = {}
            for lang_code in self.config['supported_languages']:
                if lang_code == 'en':
                    message_text = logistics_template.format(
                        zones_count=len(plan.impacted_zones),
                        resources=resource_summary,
                        url=f'https://resilientflow.app/logistics/{plan.plan_id}'
                    )
                else:
                    # Translate message
                    translated = self.translate_client.translate(
                        logistics_template,
                        target_language=lang_code,
                        source_language='en'
                    )
                    message_text = translated['translatedText'].format(
                        zones_count=len(plan.impacted_zones),
                        resources=resource_summary,
                        url=f'https://resilientflow.app/logistics/{plan.plan_id}'
                    )
                
                messages[lang_code] = message_text
            
            # Create alert messages
            alert_messages = []
            for lang_code, message_text in messages.items():
                alert_message = api_pb2.AlertMessage(
                    alert_id=f"{update_id}_{lang_code}",
                    language_code=lang_code,
                    title="Logistics Update - Resource Deployment",
                    body=message_text,
                    urgency='expected',
                    affected_areas=plan.impacted_zones,
                    expires_ms=int((time.time() + 6 * 3600) * 1000)  # 6 hour expiry
                )
                alert_messages.append(alert_message)
            
            # Distribute logistics updates
            self._distribute_updates(alert_messages)
            
            self.logger.info(f"Generated logistics update", update_id=update_id)
            
        except Exception as e:
            self.logger.error(f"Failed to generate logistics update", error=str(e))
    
    def _get_area_name(self, latitude: float, longitude: float) -> str:
        """Get human-readable area name for coordinates"""
        
        # Simplified area naming - would use reverse geocoding in production
        # For demo, create area name based on coordinates
        
        if 40.0 <= latitude <= 41.0 and -75.0 <= longitude <= -73.0:
            return "New York Metro Area"
        elif 33.0 <= latitude <= 34.5 and -119.0 <= longitude <= -117.0:
            return "Los Angeles Area"
        elif 37.0 <= latitude <= 38.0 and -123.0 <= longitude <= -121.0:
            return "San Francisco Bay Area"
        else:
            return f"Area {latitude:.2f}°N, {abs(longitude):.2f}°W"
    
    def _generate_multilingual_messages(self, template: AlertTemplate, 
                                       variables: Dict[str, Any]) -> Dict[str, str]:
        """Generate multilingual messages from template"""
        
        messages = {}
        
        # English
        messages['en'] = template.template_en.format(**variables)
        
        # Spanish
        messages['es'] = template.template_es.format(**variables)
        
        # French
        messages['fr'] = template.template_fr.format(**variables)
        
        # For additional languages, use translation API
        for lang_code in self.config['supported_languages']:
            if lang_code not in messages:
                try:
                    translated = self.translate_client.translate(
                        messages['en'],
                        target_language=lang_code,
                        source_language='en'
                    )
                    messages[lang_code] = translated['translatedText']
                except Exception as e:
                    self.logger.warning(f"Translation failed for {lang_code}", error=str(e))
                    messages[lang_code] = messages['en']  # Fallback to English
        
        # Truncate messages for SMS if needed
        for lang_code, message in messages.items():
            if len(message) > self.config['max_message_length']:
                messages[lang_code] = message[:self.config['max_message_length']-3] + "..."
        
        return messages
    
    def _generate_cap_xml(self, event: api_pb2.DisasterEvent, template: AlertTemplate,
                         area_name: str, alert_id: str) -> str:
        """Generate CAP (Common Alerting Protocol) XML"""
        
        # Create CAP XML structure
        cap = ET.Element('alert', xmlns='urn:oasis:names:tc:emergency:cap:1.2')
        
        # Identifier
        identifier = ET.SubElement(cap, 'identifier')
        identifier.text = f"{self.config['cap_identifier_prefix']}.{alert_id}"
        
        # Sender
        sender = ET.SubElement(cap, 'sender')
        sender.text = 'resilientflow@emergency.gov'
        
        # Sent
        sent = ET.SubElement(cap, 'sent')
        sent.text = datetime.now(timezone.utc).isoformat()
        
        # Status
        status = ET.SubElement(cap, 'status')
        status.text = 'Actual'
        
        # Message type
        msgType = ET.SubElement(cap, 'msgType')
        msgType.text = 'Alert'
        
        # Scope
        scope = ET.SubElement(cap, 'scope')
        scope.text = 'Public'
        
        # Info element
        info = ET.SubElement(cap, 'info')
        
        # Language
        language = ET.SubElement(info, 'language')
        language.text = 'en-US'
        
        # Category
        category = ET.SubElement(info, 'category')
        if event.event_type in ['flood', 'fire', 'earthquake']:
            category.text = 'Geo'
        else:
            category.text = 'Other'
        
        # Event
        event_elem = ET.SubElement(info, 'event')
        event_elem.text = event.event_type.title()
        
        # Urgency
        urgency = ET.SubElement(info, 'urgency')
        urgency.text = template.urgency.title()
        
        # Severity
        severity = ET.SubElement(info, 'severity')
        severity.text = template.severity.title()
        
        # Certainty
        certainty = ET.SubElement(info, 'certainty')
        certainty.text = template.certainty.title()
        
        # Headline
        headline = ET.SubElement(info, 'headline')
        headline.text = f"{event.event_type.title()} Alert for {area_name}"
        
        # Description
        description = ET.SubElement(info, 'description')
        description.text = f"Emergency situation detected: {event.event_type} in {area_name} with severity level {event.severity_raw}/100."
        
        # Area
        area = ET.SubElement(info, 'area')
        areaDesc = ET.SubElement(area, 'areaDesc')
        areaDesc.text = area_name
        
        # Circle (approximate area)
        circle = ET.SubElement(area, 'circle')
        circle.text = f"{event.latitude},{event.longitude} 5.0"  # 5km radius
        
        # Convert to string
        cap_xml = ET.tostring(cap, encoding='unicode')
        
        # Store CAP XML (in production, would upload to Cloud Storage)
        cap_url = f"https://resilientflow.app/cap/{alert_id}.xml"
        
        self.logger.debug(f"Generated CAP XML", alert_id=alert_id, url=cap_url)
        
        return cap_url
    
    def _distribute_alerts(self, alert_messages: List[api_pb2.AlertMessage], 
                          event: api_pb2.DisasterEvent) -> None:
        """Distribute emergency alerts via multiple channels"""
        
        for alert_message in alert_messages:
            try:
                # Firebase Cloud Messaging
                self._send_fcm_alert(alert_message, high_priority=True)
                
                # SMS (would integrate with SMS provider)
                self._send_sms_alert(alert_message)
                
                # Social media (would integrate with Twitter/Facebook APIs)
                if self.config['social_media_enabled']:
                    self._post_social_media_alert(alert_message)
                
                # Publish to alert broadcasts topic
                self.pubsub_client.publish_proto_message(
                    'alert_broadcasts',
                    alert_message,
                    {
                        'urgency': alert_message.urgency,
                        'language': alert_message.language_code,
                        'event_type': event.event_type
                    }
                )
                
                self.logger.info(
                    f"Distributed emergency alert",
                    alert_id=alert_message.alert_id,
                    language=alert_message.language_code
                )
                
            except Exception as e:
                self.logger.error(
                    f"Failed to distribute alert",
                    alert_id=alert_message.alert_id,
                    error=str(e)
                )
    
    def _distribute_updates(self, alert_messages: List[api_pb2.AlertMessage]) -> None:
        """Distribute non-emergency updates"""
        
        for alert_message in alert_messages:
            try:
                # FCM with lower priority
                self._send_fcm_alert(alert_message, high_priority=False)
                
                # Publish to alert broadcasts topic
                self.pubsub_client.publish_proto_message(
                    'alert_broadcasts',
                    alert_message,
                    {
                        'urgency': alert_message.urgency,
                        'language': alert_message.language_code,
                        'message_type': 'update'
                    }
                )
                
                self.logger.debug(
                    f"Distributed update",
                    alert_id=alert_message.alert_id,
                    language=alert_message.language_code
                )
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to distribute update",
                    alert_id=alert_message.alert_id,
                    error=str(e)
                )
    
    def _send_fcm_alert(self, alert_message: api_pb2.AlertMessage, high_priority: bool = True) -> None:
        """Send alert via Firebase Cloud Messaging"""
        
        try:
            # Create FCM message
            fcm_message = messaging.Message(
                data={
                    'alert_id': alert_message.alert_id,
                    'urgency': alert_message.urgency,
                    'cap_url': alert_message.cap_xml_url
                },
                notification=messaging.Notification(
                    title=alert_message.title,
                    body=alert_message.body
                ),
                android=messaging.AndroidConfig(
                    priority='high' if high_priority else 'normal',
                    notification=messaging.AndroidNotification(
                        icon='emergency_icon',
                        color='#FF0000' if high_priority else '#FFA500'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=alert_message.title,
                                body=alert_message.body
                            ),
                            badge=1,
                            sound='emergency.wav' if high_priority else 'default'
                        )
                    )
                ),
                topic=f"{self.config['fcm_topic_prefix']}_{alert_message.language_code}"
            )
            
            # Send message
            response = messaging.send(fcm_message)
            
            self.logger.debug(
                f"Sent FCM alert",
                alert_id=alert_message.alert_id,
                message_id=response
            )
            
        except Exception as e:
            self.logger.error(f"FCM send failed", error=str(e))
    
    def _send_sms_alert(self, alert_message: api_pb2.AlertMessage) -> None:
        """Send alert via SMS (mock implementation)"""
        
        # In production, would integrate with SMS provider like Twilio
        self.logger.info(
            f"SMS alert sent (mock)",
            alert_id=alert_message.alert_id,
            language=alert_message.language_code,
            message_length=len(alert_message.body)
        )
    
    def _post_social_media_alert(self, alert_message: api_pb2.AlertMessage) -> None:
        """Post alert to social media (mock implementation)"""
        
        # In production, would integrate with Twitter/Facebook APIs
        self.logger.info(
            f"Social media alert posted (mock)",
            alert_id=alert_message.alert_id,
            language=alert_message.language_code
        )
    
    def _store_alert_record(self, alert_message: api_pb2.AlertMessage, 
                           event: api_pb2.DisasterEvent) -> None:
        """Store alert record for tracking and analysis"""
        
        alert_record = {
            'alert_id': alert_message.alert_id,
            'event_id': event.event_id,
            'language_code': alert_message.language_code,
            'title': alert_message.title,
            'body': alert_message.body,
            'urgency': alert_message.urgency,
            'affected_areas': alert_message.affected_areas,
            'cap_xml_url': alert_message.cap_xml_url,
            'expires_ms': alert_message.expires_ms,
            'created_timestamp': time.time(),
            'distribution_channels': ['fcm', 'sms', 'pubsub'],
            'event_type': event.event_type,
            'event_severity': event.severity_raw
        }
        
        self.firestore_client.write_document(
            'alerts',
            alert_message.alert_id,
            alert_record
        )
    
    def _increment_counter(self, counter_name: str) -> int:
        """Increment and return counter value"""
        
        counter_doc = self.firestore_client.read_document('agent_state', self.agent_name)
        current_value = 0
        
        if counter_doc and counter_name in counter_doc:
            current_value = counter_doc[counter_name]
        
        return current_value + 1
    
    def start_monitoring(self) -> None:
        """Start communications monitoring"""
        
        self.logger.info("Starting Communications Coordinator monitoring")
        
        # Update agent status
        self.pubsub_client.broadcast_agent_status('monitoring', {
            'subscribed_topics': ['disaster_events', 'impact_updates', 'allocation_plans'],
            'supported_languages': self.config['supported_languages']
        })
        
        self.logger.info("Communications Coordinator ready to generate alerts")


def main():
    """Main entry point"""
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'resilientflow-demo')
    agent = CommunicationsCoordinatorAgent(project_id)
    
    # Start monitoring
    agent.start_monitoring()
    
    # Keep alive
    try:
        while True:
            time.sleep(60)
            agent.pubsub_client.broadcast_agent_status('monitoring')
            
    except KeyboardInterrupt:
        agent.logger.info("Shutting down Communications Coordinator Agent")
        agent.pubsub_client.shutdown()


if __name__ == '__main__':
    main() 