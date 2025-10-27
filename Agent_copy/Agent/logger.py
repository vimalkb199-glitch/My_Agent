import logging
import json
from datetime import datetime
from typing import Dict, Any
import os

class AgentLogger:
    def __init__(self, log_level=logging.INFO):
        self.logger = logging.getLogger('agent_logger')
        self.logger.setLevel(log_level)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # File handler for general logs
        file_handler = logging.FileHandler(f'logs/agent_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler.setLevel(log_level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Structured logging for metrics
        self.metrics_logger = logging.getLogger('metrics_logger')
        metrics_handler = logging.FileHandler(f'logs/metrics_{datetime.now().strftime("%Y%m%d")}.jsonl')
        self.metrics_logger.addHandler(metrics_handler)
        self.metrics_logger.setLevel(logging.INFO)
    
    def log_task_start(self, task_id: str, task_input: str, complexity: str, priority: str):
        self.logger.info(f"Task started - ID: {task_id}, Complexity: {complexity}, Priority: {priority}")
        self.logger.debug(f"Task input: {task_input}")
    
    def log_task_complete(self, task_id: str, duration: float, token_usage: Dict):
        self.logger.info(f"Task completed - ID: {task_id}, Duration: {duration:.2f}s")
        self.logger.info(f"Token usage - Input: {token_usage.get('input_tokens', 0)}, Output: {token_usage.get('output_tokens', 0)}")
    
    def log_agent_action(self, agent_name: str, action: str, details: Dict = None):
        self.logger.info(f"Agent action - {agent_name}: {action}")
        if details:
            self.logger.debug(f"Action details: {json.dumps(details)}")
    
    def log_error(self, error_type: str, error_message: str, context: Dict = None):
        self.logger.error(f"Error - {error_type}: {error_message}")
        if context:
            self.logger.error(f"Error context: {json.dumps(context)}")
    
    def log_performance_metric(self, metric_name: str, value: float, metadata: Dict = None):
        metric_data = {
            'timestamp': datetime.now().isoformat(),
            'metric_name': metric_name,
            'value': value,
            'metadata': metadata or {}
        }
        self.metrics_logger.info(json.dumps(metric_data))
    
    def log_tool_usage(self, tool_name: str, duration: float, success: bool, metadata: Dict = None):
        self.logger.info(f"Tool usage - {tool_name}: {'SUCCESS' if success else 'FAILED'} ({duration:.2f}s)")
        
        # Log to metrics
        self.log_performance_metric('tool_usage', duration, {
            'tool_name': tool_name,
            'success': success,
            **(metadata or {})
        })
    
    def log_memory_operation(self, operation: str, details: Dict = None):
        self.logger.debug(f"Memory operation: {operation}")
        if details:
            self.logger.debug(f"Memory details: {json.dumps(details)}")
    
    def log_evaluation_result(self, task_id: str, metrics: Dict):
        self.logger.info(f"Evaluation completed - Task: {task_id}")
        for metric, value in metrics.items():
            if isinstance(value, (int, float)):
                self.logger.info(f"Metric {metric}: {value:.3f}")
                self.log_performance_metric(f'evaluation_{metric}', value, {'task_id': task_id})