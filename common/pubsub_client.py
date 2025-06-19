"""
Shared Pub/Sub client for ResilientFlow agent communication.
Handles message publishing, subscription, and protobuf serialization.
"""

import json
import time
from typing import Dict, Any, Optional, Callable, List
from google.cloud import pubsub_v1
from google.protobuf import message
from concurrent.futures import ThreadPoolExecutor
import threading

from .logging import get_logger, log_performance


class PubSubClient:
    """Centralized Pub/Sub client for agent swarm communication"""
    
    def __init__(self, project_id: str, agent_name: str):
        self.project_id = project_id
        self.agent_name = agent_name
        self.logger = get_logger(agent_name)
        
        # Initialize clients
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        
        # Topic and subscription paths
        self.topics = {
            'agent_events': f'projects/{project_id}/topics/rf-agent-events',
            'disaster_events': f'projects/{project_id}/topics/rf-disaster-events',
            'impact_updates': f'projects/{project_id}/topics/rf-impact-updates',
            'allocation_plans': f'projects/{project_id}/topics/rf-allocation-plans',
            'alert_broadcasts': f'projects/{project_id}/topics/rf-alert-broadcasts'
        }
        
        # Active subscriptions
        self._subscriptions: Dict[str, threading.Thread] = {}
        self._subscription_callbacks: Dict[str, Callable] = {}
        self._shutdown_event = threading.Event()
    
    @log_performance("publish_message")
    def publish_proto_message(self, topic_key: str, proto_message: message.Message, 
                             attributes: Optional[Dict[str, str]] = None) -> str:
        """Publish a protobuf message to specified topic"""
        
        if topic_key not in self.topics:
            raise ValueError(f"Unknown topic key: {topic_key}")
        
        topic_path = self.topics[topic_key]
        
        # Serialize protobuf message
        data = proto_message.SerializeToString()
        
        # Add default attributes
        msg_attributes = {
            'source_agent': self.agent_name,
            'message_type': proto_message.__class__.__name__,
            'timestamp': str(int(time.time() * 1000))
        }
        
        if attributes:
            msg_attributes.update(attributes)
        
        # Publish message
        future = self.publisher.publish(topic_path, data, **msg_attributes)
        message_id = future.result()  # Block until published
        
        self.logger.info(
            f"Published {proto_message.__class__.__name__} to {topic_key}",
            topic=topic_path,
            message_id=message_id,
            payload_size=len(data)
        )
        
        return message_id
    
    @log_performance("publish_json")
    def publish_json_message(self, topic_key: str, data: Dict[str, Any],
                            attributes: Optional[Dict[str, str]] = None) -> str:
        """Publish JSON data to specified topic"""
        
        if topic_key not in self.topics:
            raise ValueError(f"Unknown topic key: {topic_key}")
        
        topic_path = self.topics[topic_key]
        
        # Serialize JSON
        json_data = json.dumps(data).encode('utf-8')
        
        # Add default attributes
        msg_attributes = {
            'source_agent': self.agent_name,
            'message_type': 'json',
            'timestamp': str(int(time.time() * 1000))
        }
        
        if attributes:
            msg_attributes.update(attributes)
        
        # Publish message
        future = self.publisher.publish(topic_path, json_data, **msg_attributes)
        message_id = future.result()
        
        self.logger.info(
            f"Published JSON message to {topic_key}",
            topic=topic_path,
            message_id=message_id,
            payload_size=len(json_data)
        )
        
        return message_id
    
    def subscribe_to_topic(self, topic_key: str, callback: Callable[[Any, Dict[str, str]], None],
                          proto_class: Optional[type] = None) -> None:
        """Subscribe to a topic with automatic message deserialization"""
        
        if topic_key not in self.topics:
            raise ValueError(f"Unknown topic key: {topic_key}")
        
        subscription_name = f'rf-{self.agent_name}-{topic_key}'
        subscription_path = f'projects/{self.project_id}/subscriptions/{subscription_name}'
        
        self._subscription_callbacks[topic_key] = callback
        
        def message_handler(message):
            try:
                # Get message attributes
                attributes = dict(message.attributes)
                
                # Deserialize based on message type
                if proto_class and attributes.get('message_type') == proto_class.__name__:
                    # Deserialize protobuf
                    proto_message = proto_class()
                    proto_message.ParseFromString(message.data)
                    callback(proto_message, attributes)
                else:
                    # Try JSON deserialization
                    try:
                        json_data = json.loads(message.data.decode('utf-8'))
                        callback(json_data, attributes)
                    except json.JSONDecodeError:
                        # Fall back to raw bytes
                        callback(message.data, attributes)
                
                message.ack()
                
                self.logger.debug(
                    f"Processed message from {topic_key}",
                    message_id=message.message_id,
                    source_agent=attributes.get('source_agent', 'unknown')
                )
                
            except Exception as e:
                self.logger.error(
                    f"Error processing message from {topic_key}",
                    error=str(e),
                    message_id=message.message_id
                )
                message.nack()
        
        # Start subscription in background thread
        def subscription_thread():
            flow_control = pubsub_v1.types.FlowControl(max_messages=100)
            
            with self.subscriber:
                try:
                    streaming_pull_future = self.subscriber.subscribe(
                        subscription_path,
                        callback=message_handler,
                        flow_control=flow_control
                    )
                    
                    self.logger.info(f"Started subscription to {topic_key}")
                    
                    # Keep subscription alive until shutdown
                    while not self._shutdown_event.is_set():
                        try:
                            streaming_pull_future.result(timeout=1.0)
                        except Exception:
                            # Timeout is expected, check shutdown event
                            continue
                    
                    streaming_pull_future.cancel()
                    
                except Exception as e:
                    self.logger.error(f"Subscription error for {topic_key}", error=str(e))
        
        thread = threading.Thread(target=subscription_thread, daemon=True)
        thread.start()
        self._subscriptions[topic_key] = thread
    
    def broadcast_agent_status(self, status: str, additional_data: Optional[Dict[str, Any]] = None):
        """Broadcast agent status to the swarm"""
        status_data = {
            'agent_name': self.agent_name,
            'status': status,
            'timestamp_ms': int(time.time() * 1000)
        }
        
        if additional_data:
            status_data.update(additional_data)
        
        self.publish_json_message('agent_events', status_data, {
            'event_type': 'agent_status',
            'urgency': 'low'
        })
    
    def shutdown(self):
        """Gracefully shutdown all subscriptions"""
        self.logger.info("Shutting down Pub/Sub client")
        self._shutdown_event.set()
        
        # Wait for subscription threads to finish
        for topic_key, thread in self._subscriptions.items():
            thread.join(timeout=5.0)
            if thread.is_alive():
                self.logger.warning(f"Subscription thread for {topic_key} did not shutdown cleanly")


class MessageBuffer:
    """Buffer for batching messages before publishing"""
    
    def __init__(self, pubsub_client: PubSubClient, topic_key: str, 
                 max_size: int = 100, flush_interval: float = 5.0):
        self.pubsub_client = pubsub_client
        self.topic_key = topic_key
        self.max_size = max_size
        self.flush_interval = flush_interval
        
        self._buffer: List[Dict[str, Any]] = []
        self._last_flush = time.time()
        self._lock = threading.Lock()
        
        # Start background flush thread
        self._flush_thread = threading.Thread(target=self._periodic_flush, daemon=True)
        self._shutdown = threading.Event()
        self._flush_thread.start()
    
    def add_message(self, data: Dict[str, Any], attributes: Optional[Dict[str, str]] = None):
        """Add message to buffer, auto-flush if needed"""
        with self._lock:
            self._buffer.append({
                'data': data,
                'attributes': attributes or {}
            })
            
            if len(self._buffer) >= self.max_size:
                self._flush_buffer()
    
    def _flush_buffer(self):
        """Flush all buffered messages"""
        if not self._buffer:
            return
        
        messages_to_send = self._buffer.copy()
        self._buffer.clear()
        self._last_flush = time.time()
        
        # Send messages in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            for msg in messages_to_send:
                executor.submit(
                    self.pubsub_client.publish_json_message,
                    self.topic_key,
                    msg['data'],
                    msg['attributes']
                )
    
    def _periodic_flush(self):
        """Background thread for periodic flushing"""
        while not self._shutdown.is_set():
            time.sleep(1.0)  # Check every second
            
            with self._lock:
                if (time.time() - self._last_flush) >= self.flush_interval and self._buffer:
                    self._flush_buffer()
    
    def force_flush(self):
        """Force immediate flush of buffer"""
        with self._lock:
            self._flush_buffer()
    
    def shutdown(self):
        """Shutdown buffer and flush remaining messages"""
        self._shutdown.set()
        self.force_flush()
        self._flush_thread.join(timeout=5.0) 