"""
Communications Coordinator Tool - ResilientFlow
ADK-compatible tool for generating and sending multilingual emergency alerts.
Refactored from the original agent to be callable rather than a long-running service.
"""

import os
import sys
import time
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional

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

async def coordinate_communications(
    allocation_plan: Dict[str, Any] = None,
    project_id: str = None,
    region: str = 'us-central1'
) -> Dict[str, Any]:
    """
    ADK Tool: Generate and send multilingual emergency alerts and communications.
    """
    
    logger = get_logger('comms_coordinator_tool')
    comm_id = f"comm_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    
    if not allocation_plan:
        allocation_plan = {"overall_severity": 75, "allocations": []}
    
    logger.info(f"Starting communications coordination", 
                extra={'comm_id': comm_id,
                      'severity': allocation_plan.get('overall_severity', 0)})
    
    # Simulate processing time
    await asyncio.sleep(0.6)
    
    overall_severity = allocation_plan.get('overall_severity', 75)
    allocations = allocation_plan.get('allocations', [])
    
    # Determine alert level and channels based on severity
    if overall_severity >= 80:
        alert_level = "CRITICAL"
        channels = ["sms", "push_notification", "social_media", "emergency_broadcast"]
    elif overall_severity >= 60:
        alert_level = "HIGH"
        channels = ["sms", "push_notification", "social_media"]
    else:
        alert_level = "MEDIUM"
        channels = ["push_notification", "social_media"]
    
    # Generate multilingual alerts
    alerts = _generate_multilingual_alerts(overall_severity, alert_level, allocations)
    
    # Simulate sending alerts across channels
    channel_results = []
    total_sent = 0
    
    for channel in channels:
        result = await _send_alerts_to_channel(channel, alerts, overall_severity)
        channel_results.append(result)
        total_sent += result["messages_sent"]
    
    result = {
        "comm_id": comm_id,
        "alert_level": alert_level,
        "overall_severity": overall_severity,
        "alerts_sent": total_sent,
        "channels_used": len(channels),
        "channel_results": channel_results,
        "multilingual_alerts": alerts,
        "estimated_reach": total_sent * 2.3,  # Average reach multiplier
        "processing_time_ms": 600,
        "status": "SUCCESS"
    }
    
    logger.info(f"Communications coordination completed",
               extra={'comm_id': comm_id,
                     'alerts_sent': total_sent,
                     'channels': len(channels)})
    
    return result


def _generate_multilingual_alerts(severity: int, alert_level: str, allocations: List[Dict]) -> List[Dict]:
    """Generate alerts in multiple languages (simplified for demo)"""
    
    # Base alert message based on severity
    if severity >= 80:
        base_message = f"🚨 EMERGENCY: Major disaster event in progress. Severity {severity}/100. Seek immediate shelter. Emergency resources deployed."
    elif severity >= 60:
        base_message = f"⚠️ ALERT: Significant emergency situation. Severity {severity}/100. Stay informed and prepared."
    else:
        base_message = f"📢 NOTICE: Emergency response in progress. Severity {severity}/100. Follow official guidance."
    
    # Translations (simplified for demo)
    translations = {
        "english": base_message,
        "spanish": f"🚨 EMERGENCIA: Evento de desastre mayor en progreso. Severidad {severity}/100. Busque refugio inmediato.",
        "french": f"🚨 URGENCE: Événement de catastrophe majeure en cours. Sévérité {severity}/100. Cherchez un abri immédiat."
    }
    
    alerts = []
    for i, (lang, message) in enumerate(translations.items()):
        alert = {
            "alert_id": f"alert_{int(time.time() * 1000)}_{lang}",
            "language": lang,
            "message": message,
            "alert_level": alert_level,
            "character_count": len(message),
            "timestamp": int(time.time() * 1000)
        }
        alerts.append(alert)
    
    return alerts


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