"""
Shared logging configuration for ResilientFlow agents.
Provides structured logging with correlation IDs for distributed tracing.
"""

import logging
import json
import time
from typing import Dict, Any, Optional
from google.cloud import logging as cloud_logging
import uuid


class StructuredLogger:
    """JSON structured logger with correlation ID support for agent swarm"""
    
    def __init__(self, agent_name: str, correlation_id: Optional[str] = None):
        self.agent_name = agent_name
        self.correlation_id = correlation_id or str(uuid.uuid4())
        
        # Initialize Cloud Logging client
        self.cloud_client = cloud_logging.Client()
        self.cloud_client.setup_logging()
        
        # Configure local logger
        self.logger = logging.getLogger(f"resilientflow.{agent_name}")
        self.logger.setLevel(logging.INFO)
        
        # Remove default handlers to avoid duplication
        self.logger.handlers.clear()
        
        # Add structured handler
        handler = logging.StreamHandler()
        handler.setFormatter(self._get_formatter())
        self.logger.addHandler(handler)
    
    def _get_formatter(self) -> logging.Formatter:
        """Custom formatter for structured JSON logs"""
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": time.time(),
                    "level": record.levelname,
                    "agent": record.name.split('.')[-1],
                    "correlation_id": getattr(record, 'correlation_id', 'unknown'),
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                
                # Add custom fields
                if hasattr(record, 'custom_fields'):
                    log_entry.update(record.custom_fields)
                
                return json.dumps(log_entry)
        
        return StructuredFormatter()
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method with correlation ID injection"""
        extra = {
            'correlation_id': self.correlation_id,
            'custom_fields': kwargs
        }
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def info(self, message: str, **kwargs):
        """Log info level message"""
        self._log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message"""
        self._log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error level message"""
        self._log('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug level message"""
        self._log('DEBUG', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical level message"""
        self._log('CRITICAL', message, **kwargs)
    
    def agent_action(self, action: str, status: str, duration_ms: Optional[float] = None, **kwargs):
        """Log agent-specific actions with standardized format"""
        log_data = {
            'action': action,
            'status': status,
            'agent': self.agent_name
        }
        
        if duration_ms:
            log_data['duration_ms'] = duration_ms
        
        log_data.update(kwargs)
        
        self.info(f"Agent action: {action} -> {status}", **log_data)
    
    def inter_agent_comm(self, target_agent: str, message_type: str, payload_size: int):
        """Log inter-agent communication events"""
        self.info(
            f"Inter-agent comm: {self.agent_name} -> {target_agent}",
            target_agent=target_agent,
            message_type=message_type,
            payload_size_bytes=payload_size,
            comm_type='grpc'
        )


def get_logger(agent_name: str, correlation_id: Optional[str] = None) -> StructuredLogger:
    """Factory function to get a structured logger for an agent"""
    return StructuredLogger(agent_name, correlation_id)


# Performance monitoring decorator
def log_performance(action_name: str):
    """Decorator to automatically log action performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Try to get logger from self if it's a method
            logger = None
            if args and hasattr(args[0], 'logger'):
                logger = args[0].logger
            else:
                logger = get_logger('unknown_agent')
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.agent_action(action_name, 'success', duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.agent_action(action_name, 'error', duration_ms, error=str(e))
                raise
        return wrapper
    return decorator 