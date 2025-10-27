import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json

@dataclass
class TraceEvent:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float]
    duration: Optional[float]
    status: str
    metadata: Dict[str, Any]
    tags: Dict[str, str]

class AgentTracer:
    def __init__(self):
        self.traces: Dict[str, List[TraceEvent]] = {}
        self.active_spans: Dict[str, TraceEvent] = {}
    
    def start_trace(self, operation_name: str, metadata: Dict = None) -> str:
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        event = TraceEvent(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation_name=operation_name,
            start_time=time.time(),
            end_time=None,
            duration=None,
            status="STARTED",
            metadata=metadata or {},
            tags={"trace_type": "root"}
        )
        
        self.traces[trace_id] = [event]
        self.active_spans[span_id] = event
        return trace_id
    
    def start_span(self, trace_id: str, operation_name: str, parent_span_id: str = None, metadata: Dict = None) -> str:
        span_id = str(uuid.uuid4())
        
        event = TraceEvent(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            end_time=None,
            duration=None,
            status="STARTED",
            metadata=metadata or {},
            tags={}
        )
        
        if trace_id in self.traces:
            self.traces[trace_id].append(event)
        else:
            self.traces[trace_id] = [event]
        
        self.active_spans[span_id] = event
        return span_id
    
    def end_span(self, span_id: str, status: str = "SUCCESS", metadata: Dict = None):
        if span_id in self.active_spans:
            event = self.active_spans[span_id]
            event.end_time = time.time()
            event.duration = event.end_time - event.start_time
            event.status = status
            if metadata:
                event.metadata.update(metadata)
            del self.active_spans[span_id]
    
    def add_event(self, span_id: str, event_name: str, attributes: Dict = None):
        if span_id in self.active_spans:
            event = self.active_spans[span_id]
            if 'events' not in event.metadata:
                event.metadata['events'] = []
            event.metadata['events'].append({
                'name': event_name,
                'timestamp': time.time(),
                'attributes': attributes or {}
            })
    
    def get_trace(self, trace_id: str) -> List[TraceEvent]:
        return self.traces.get(trace_id, [])
    
    def get_all_traces(self) -> Dict[str, List[TraceEvent]]:
        return self.traces
    
    def export_traces(self, filename: str = None):
        if not filename:
            filename = f"traces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {}
        for trace_id, events in self.traces.items():
            export_data[trace_id] = [asdict(event) for event in events]
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return filename