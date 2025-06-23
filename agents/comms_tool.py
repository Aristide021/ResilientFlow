#!/usr/bin/env python3
"""
ResilientFlow Communications Coordinator Agent Tool
Handles multilingual emergency communications and alert distribution.
Now with live Slack and Twilio integration for real emergency channels.
"""

import os
import logging
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Live communications configuration
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER', '+1234567890')
USE_MOCK = os.environ.get('USE_MOCK', '1') == '1'

class LiveSlackNotifier:
    """Send emergency alerts to Slack channels"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def send_alert(self, message: str, severity: str = "high") -> Dict[str, Any]:
        """Send emergency alert to Slack"""
        
        # Choose emoji and color based on severity
        emoji_map = {
            "critical": "🚨",
            "high": "⚠️", 
            "medium": "🔔",
            "low": "ℹ️"
        }
        
        color_map = {
            "critical": "#FF0000",
            "high": "#FF8C00",
            "medium": "#FFD700", 
            "low": "#32CD32"
        }
        
        emoji = emoji_map.get(severity, "🔔")
        color = color_map.get(severity, "#FFD700")
        
        payload = {
            "text": f"{emoji} ResilientFlow Emergency Alert",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Emergency Alert",
                            "value": message,
                            "short": False
                        },
                        {
                            "title": "Severity",
                            "value": severity.upper(),
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            return {
                "status": "success",
                "platform": "slack",
                "message_id": response.headers.get("X-Slack-Request-Id", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return {
                "status": "error",
                "platform": "slack", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

class LiveTwilioNotifier:
    """Send emergency SMS alerts via Twilio"""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    
    async def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send emergency SMS via Twilio"""
        
        # Truncate message to SMS limits
        if len(message) > 160:
            message = message[:157] + "..."
        
        payload = {
            "From": self.from_number,
            "To": to_number,
            "Body": f"🚨 EMERGENCY ALERT: {message}"
        }
        
        try:
            response = requests.post(
                self.base_url,
                data=payload,
                auth=(self.account_sid, self.auth_token),
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                "status": "success",
                "platform": "twilio_sms",
                "message_sid": result.get("sid"),
                "to": to_number,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {e}")
            return {
                "status": "error",
                "platform": "twilio_sms",
                "to": to_number,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

async def coordinate_communications(
    allocation_plan: Dict[str, Any],
    project_id: str
) -> Dict[str, Any]:
    """
    Coordinate emergency communications across multiple channels.
    Now supports live Slack and Twilio integration.
    
    Args:
        allocation_plan: Resource allocation data from the allocator agent
        project_id: Google Cloud project ID
    
    Returns:
        Dictionary containing communication results and statistics
    """
    
    logger.info("Starting communications coordination")
    start_time = time.time()
    
    try:
        # Extract key information from allocation plan
        total_resources = allocation_plan.get("total_resources", 0)
        allocations = allocation_plan.get("allocations", [])
        severity = allocation_plan.get("severity", "medium")
        
        # Generate emergency message
        emergency_message = generate_emergency_message(allocation_plan)
        
        # Initialize live communication results
        live_results = []
        
        # Send live communications if not using mock
        if not USE_MOCK:
            logger.info("Sending live emergency communications")
            
            # Send Slack alert if configured
            if SLACK_WEBHOOK_URL:
                slack_notifier = LiveSlackNotifier(SLACK_WEBHOOK_URL)
                slack_result = await slack_notifier.send_alert(
                    emergency_message, 
                    severity
                )
                live_results.append(slack_result)
                logger.info(f"Slack alert sent: {slack_result['status']}")
            
            # Send SMS alerts if Twilio is configured
            if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
                twilio_notifier = LiveTwilioNotifier(
                    TWILIO_ACCOUNT_SID,
                    TWILIO_AUTH_TOKEN, 
                    TWILIO_FROM_NUMBER
                )
                
                # Send to emergency contact numbers (mock for demo)
                emergency_contacts = [
                    "+1234567890",  # Emergency coordinator
                    "+1234567891",  # Backup coordinator
                ]
                
                for contact in emergency_contacts:
                    sms_result = await twilio_notifier.send_sms(
                        contact,
                        emergency_message
                    )
                    live_results.append(sms_result)
                    logger.info(f"SMS sent to {contact}: {sms_result['status']}")
        
        # Generate multilingual alerts
        multilingual_alerts = generate_multilingual_alerts(emergency_message)
        
        # Simulate alert distribution
        distribution_results = await simulate_alert_distribution(
            multilingual_alerts,
            allocations
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        result = {
            "communication_id": f"comm_{int(time.time())}",
            "emergency_message": emergency_message,
            "multilingual_alerts": multilingual_alerts,
            "live_communications": live_results,
            "distribution_results": distribution_results,
            "alerts_sent": distribution_results["total_alerts"],
            "channels_used": len(multilingual_alerts) + len(live_results),
            "processing_time_ms": processing_time,
            "timestamp": datetime.now().isoformat(),
            "live_mode": not USE_MOCK
        }
        
        logger.info("Communications coordination completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Communications coordination failed: {e}")
        raise

def generate_emergency_message(allocation_plan: Dict[str, Any]) -> str:
    """Generate the core emergency message"""
    
    total_resources = allocation_plan.get("total_resources", 0)
    disaster_type = allocation_plan.get("disaster_type", "emergency")
    affected_areas = len(allocation_plan.get("allocations", []))
    
    return (
        f"EMERGENCY RESPONSE ACTIVATED: {disaster_type.upper()} incident detected. "
        f"{total_resources} emergency resources deployed across {affected_areas} affected areas. "
        f"Follow evacuation procedures and emergency protocols immediately."
    )

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

async def _send_alerts_to_channel(channel: str, alerts: List[Dict], severity: int) -> Dict[str, Any]:
    """Simulate sending alerts to a specific channel"""
    
    # Channel-specific configurations
    channel_configs = {
        "sms": {"success_rate": 0.95, "latency_ms": 500, "cost_per_message": 0.05},
        "push_notification": {"success_rate": 0.88, "latency_ms": 200, "cost_per_message": 0.01},
        "social_media": {"success_rate": 0.99, "latency_ms": 100, "cost_per_message": 0.001},
        "emergency_broadcast": {"success_rate": 1.0, "latency_ms": 2000, "cost_per_message": 5.00}
    }
    
    config = channel_configs.get(channel, {"success_rate": 0.9, "latency_ms": 300, "cost_per_message": 0.02})
    
    # Simulate network latency
    await asyncio.sleep(config["latency_ms"] / 1000.0)
    
    # Calculate reach based on severity and channel
    base_reach = {
        "sms": 500,
        "push_notification": 1500,
        "social_media": 5000,
        "emergency_broadcast": 10000
    }
    
    reach_multiplier = min(2.0, severity / 50.0)  # Higher severity = more reach
    estimated_reach = int(base_reach.get(channel, 1000) * reach_multiplier)
    
    messages_sent = int(len(alerts) * estimated_reach * config["success_rate"])
    
    return {
        "channel": channel,
        "messages_sent": messages_sent,
        "success_rate": config["success_rate"],
        "latency_ms": config["latency_ms"],
        "estimated_cost": messages_sent * config["cost_per_message"],
        "estimated_reach": estimated_reach
    }

def generate_multilingual_alerts(emergency_message: str) -> List[Dict[str, Any]]:
    """Generate multilingual versions of the emergency message"""
    
    # Simplified translations for demo
    translations = {
        "english": emergency_message,
        "spanish": emergency_message.replace("EMERGENCY RESPONSE ACTIVATED", "RESPUESTA DE EMERGENCIA ACTIVADA")
                                  .replace("incident detected", "incidente detectado")
                                  .replace("emergency resources deployed", "recursos de emergencia desplegados")
                                  .replace("Follow evacuation procedures", "Siga los procedimientos de evacuación"),
        "french": emergency_message.replace("EMERGENCY RESPONSE ACTIVATED", "RÉPONSE D'URGENCE ACTIVÉE")
                                 .replace("incident detected", "incident détecté")
                                 .replace("emergency resources deployed", "ressources d'urgence déployées")
                                 .replace("Follow evacuation procedures", "Suivez les procédures d'évacuation"),
        "mandarin": "紧急响应已启动：检测到紧急事件。已部署紧急资源。立即遵循疏散程序。"
    }
    
    alerts = []
    for lang, message in translations.items():
        alert = {
            "alert_id": f"alert_{int(time.time())}_{lang}",
            "language": lang,
            "message": message,
            "character_count": len(message),
            "timestamp": datetime.now().isoformat()
        }
        alerts.append(alert)
    
    return alerts

async def simulate_alert_distribution(
    multilingual_alerts: List[Dict[str, Any]], 
    allocations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Simulate the distribution of alerts across multiple channels"""
    
    # Determine channels based on severity and allocations
    num_allocations = len(allocations)
    if num_allocations >= 5:
        channels = ["sms", "push_notification", "social_media", "emergency_broadcast"]
    elif num_allocations >= 3:
        channels = ["sms", "push_notification", "social_media"]
    else:
        channels = ["push_notification", "social_media"]
    
    # Simulate distribution across channels
    channel_results = []
    total_alerts = 0
    
    for channel in channels:
        # Calculate reach per channel
        base_reach = {
            "sms": 1000,
            "push_notification": 3000,
            "social_media": 8000,
            "emergency_broadcast": 15000
        }
        
        reach = base_reach.get(channel, 2000)
        alerts_per_channel = reach * len(multilingual_alerts)
        
        channel_result = {
            "channel": channel,
            "alerts_sent": alerts_per_channel,
            "reach": reach,
            "languages": len(multilingual_alerts)
        }
        
        channel_results.append(channel_result)
        total_alerts += alerts_per_channel
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
    
    return {
        "total_alerts": total_alerts,
        "channels_used": len(channels),
        "channel_results": channel_results,
        "languages_supported": len(multilingual_alerts)
    } 