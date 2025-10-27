import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import statistics

@dataclass
class MetricData:
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    metadata: Dict[str, Any]

class MetricsCollector:
    def __init__(self, storage_file: str = "metrics_data.json"):
        self.storage_file = storage_file
        self.metrics: List[MetricData] = []
        self.load_metrics()
    
    def load_metrics(self):
        """Load metrics from storage file"""
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
                self.metrics = [
                    MetricData(
                        name=m['name'],
                        value=m['value'],
                        timestamp=datetime.fromisoformat(m['timestamp']),
                        tags=m['tags'],
                        metadata=m['metadata']
                    ) for m in data
                ]
        except (FileNotFoundError, json.JSONDecodeError):
            self.metrics = []
    
    def save_metrics(self):
        """Save metrics to storage file"""
        data = [
            {
                'name': m.name,
                'value': m.value,
                'timestamp': m.timestamp.isoformat(),
                'tags': m.tags,
                'metadata': m.metadata
            } for m in self.metrics
        ]
        with open(self.storage_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None, metadata: Dict[str, Any] = None):
        """Record a single metric"""
        metric = MetricData(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metadata=metadata or {}
        )
        self.metrics.append(metric)
        self.save_metrics()
    
    def record_task_metrics(self, task_result: Dict, evaluation_metrics: Dict):
        """Record metrics from task execution and evaluation"""
        timestamp = datetime.now()
        
        # Cost metrics
        cost_info = task_result.get('cost_info', {})
        self.record_metric('token_usage_input', cost_info.get('input_tokens', 0), 
                          {'type': 'tokens'}, {'task_complexity': task_result.get('complexity')})
        self.record_metric('token_usage_output', cost_info.get('output_tokens', 0), 
                          {'type': 'tokens'}, {'task_complexity': task_result.get('complexity')})
        self.record_metric('cost_total', cost_info.get('total_cost', 0), 
                          {'type': 'cost'}, {'task_priority': task_result.get('priority')})
        
        # Quality metrics
        for metric_name, value in evaluation_metrics.items():
            if isinstance(value, (int, float)):
                self.record_metric(f'quality_{metric_name}', value, 
                                 {'type': 'quality'}, {'task_complexity': task_result.get('complexity')})
    
    def get_metrics_by_name(self, name: str, hours: int = 24) -> List[MetricData]:
        """Get metrics by name within time window"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics if m.name == name and m.timestamp >= cutoff]
    
    def get_average_metric(self, name: str, hours: int = 24) -> float:
        """Get average value for a metric"""
        metrics = self.get_metrics_by_name(name, hours)
        if not metrics:
            return 0.0
        return statistics.mean([m.value for m in metrics])
    
    def get_metric_trend(self, name: str, hours: int = 24) -> List[float]:
        """Get trend data for a metric"""
        metrics = self.get_metrics_by_name(name, hours)
        return [m.value for m in sorted(metrics, key=lambda x: x.timestamp)]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        summary = {
            'total_metrics': len(self.metrics),
            'last_24h': len([m for m in self.metrics if m.timestamp >= datetime.now() - timedelta(hours=24)]),
            'averages': {},
            'trends': {}
        }
        
        # Key metrics to track
        key_metrics = [
            'quality_completeness', 'quality_feasibility', 'quality_clarity', 
            'quality_efficiency', 'token_usage_total', 'cost_total'
        ]
        
        for metric in key_metrics:
            summary['averages'][metric] = self.get_average_metric(metric)
            trend = self.get_metric_trend(metric, 168)  # 7 days
            if len(trend) >= 2:
                summary['trends'][metric] = 'up' if trend[-1] > trend[0] else 'down'
            else:
                summary['trends'][metric] = 'stable'
        
        return summary
    
    def get_cost_analysis(self) -> Dict[str, Any]:
        """Analyze cost metrics"""
        cost_metrics = self.get_metrics_by_name('cost_total', 168)  # 7 days
        
        if not cost_metrics:
            return {'total_cost': 0, 'avg_cost_per_task': 0, 'cost_trend': 'stable'}
        
        total_cost = sum(m.value for m in cost_metrics)
        avg_cost = statistics.mean([m.value for m in cost_metrics])
        
        # Calculate trend
        if len(cost_metrics) >= 2:
            recent_avg = statistics.mean([m.value for m in cost_metrics[-5:]])
            older_avg = statistics.mean([m.value for m in cost_metrics[:-5]]) if len(cost_metrics) > 5 else recent_avg
            trend = 'up' if recent_avg > older_avg * 1.1 else 'down' if recent_avg < older_avg * 0.9 else 'stable'
        else:
            trend = 'stable'
        
        return {
            'total_cost': total_cost,
            'avg_cost_per_task': avg_cost,
            'cost_trend': trend,
            'tasks_analyzed': len(cost_metrics)
        }
    
    def get_quality_metrics(self) -> Dict[str, float]:
        """Get quality metrics summary"""
        quality_metrics = ['completeness', 'feasibility', 'clarity', 'efficiency']
        results = {}
        
        for metric in quality_metrics:
            avg = self.get_average_metric(f'quality_{metric}')
            results[metric] = avg
        
        return results
    
    def cleanup_old_metrics(self, days: int = 30):
        """Remove metrics older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        self.metrics = [m for m in self.metrics if m.timestamp >= cutoff]
        self.save_metrics()