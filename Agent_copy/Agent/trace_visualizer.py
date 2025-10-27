import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Any
import json

class TraceVisualizer:
    def __init__(self):
        self.traces = []
        
    def create_execution_trace(self, trace_data: Dict) -> go.Figure:
        """Create a Gantt chart showing agent execution timeline"""
        
        # Convert trace data to DataFrame
        df_data = []
        for trace_id, events in trace_data.items():
            for event in events:
                if event.get('end_time'):
                    df_data.append({
                        'Agent': event['operation_name'],
                        'Start': datetime.fromtimestamp(event['start_time']),
                        'Finish': datetime.fromtimestamp(event['end_time']),
                        'Duration': f"{event['duration']:.2f}s",
                        'Status': event['status'],
                        'Trace_ID': trace_id
                    })
        
        if not df_data:
            return self._create_empty_trace()
            
        df = pd.DataFrame(df_data)
        
        # Create Gantt chart
        fig = px.timeline(df, 
                         x_start="Start", 
                         x_end="Finish",
                         y="Agent",
                         color="Status",
                         hover_data=["Duration"],
                         title="Agent Execution Timeline")
        
        fig.update_layout(
            height=400,
            xaxis_title="Time",
            yaxis_title="Agent/Operation",
            showlegend=True
        )
        
        return fig
    
    def create_api_calls_trace(self, api_calls: List[Dict]) -> go.Figure:
        """Create timeline showing API calls and their durations"""
        
        if not api_calls:
            return self._create_empty_api_trace()
            
        fig = go.Figure()
        
        for i, call in enumerate(api_calls):
            fig.add_trace(go.Scatter(
                x=[call['timestamp'], call['timestamp'] + call['duration']],
                y=[i, i],
                mode='lines+markers',
                name=f"{call['api_name']} ({call['duration']:.2f}s)",
                line=dict(width=8),
                marker=dict(size=10),
                hovertemplate=f"<b>{call['api_name']}</b><br>" +
                             f"Duration: {call['duration']:.2f}s<br>" +
                             f"Status: {call['status']}<br>" +
                             f"Tokens: {call.get('tokens', 'N/A')}<extra></extra>"
            ))
        
        fig.update_layout(
            title="API Calls Timeline",
            xaxis_title="Time (seconds)",
            yaxis_title="API Call",
            height=300,
            showlegend=False
        )
        
        return fig
    
    def create_token_usage_chart(self, token_data: Dict) -> go.Figure:
        """Create bar chart showing token usage by agent"""
        
        agents = list(token_data.keys())
        input_tokens = [token_data[agent]['input'] for agent in agents]
        output_tokens = [token_data[agent]['output'] for agent in agents]
        
        fig = go.Figure(data=[
            go.Bar(name='Input Tokens', x=agents, y=input_tokens),
            go.Bar(name='Output Tokens', x=agents, y=output_tokens)
        ])
        
        fig.update_layout(
            title="Token Usage by Agent",
            xaxis_title="Agent",
            yaxis_title="Token Count",
            barmode='stack',
            height=300
        )
        
        return fig
    
    def create_performance_waterfall(self, performance_data: List[Dict]) -> go.Figure:
        """Create waterfall chart showing cumulative execution time"""
        
        agents = [item['agent'] for item in performance_data]
        durations = [item['duration'] for item in performance_data]
        
        fig = go.Figure(go.Waterfall(
            name="Execution Time",
            orientation="v",
            measure=["relative"] * len(agents),
            x=agents,
            textposition="outside",
            text=[f"{d:.2f}s" for d in durations],
            y=durations,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        
        fig.update_layout(
            title="Cumulative Execution Time by Agent",
            xaxis_title="Agent",
            yaxis_title="Duration (seconds)",
            height=400
        )
        
        return fig
    
    def _create_empty_trace(self) -> go.Figure:
        """Create empty trace chart"""
        fig = go.Figure()
        fig.add_annotation(
            text="No trace data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title="Agent Execution Timeline", height=400)
        return fig
    
    def _create_empty_api_trace(self) -> go.Figure:
        """Create empty API trace chart"""
        fig = go.Figure()
        fig.add_annotation(
            text="No API calls recorded",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(title="API Calls Timeline", height=300)
        return fig
    
    def generate_trace_summary(self, trace_data: Dict) -> Dict:
        """Generate summary statistics from trace data"""
        
        total_duration = 0
        agent_count = 0
        api_calls = 0
        total_tokens = 0
        
        for trace_id, events in trace_data.items():
            for event in events:
                if event.get('duration'):
                    total_duration += event['duration']
                    agent_count += 1
                
                if 'api_calls' in event.get('metadata', {}):
                    api_calls += len(event['metadata']['api_calls'])
                
                if 'tokens' in event.get('metadata', {}):
                    total_tokens += event['metadata']['tokens']
        
        return {
            'total_duration': total_duration,
            'agent_operations': agent_count,
            'api_calls': api_calls,
            'total_tokens': total_tokens,
            'avg_operation_time': total_duration / max(1, agent_count)
        }