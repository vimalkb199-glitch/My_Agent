from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM
import os
import datetime
import tiktoken
import json
from dotenv import load_dotenv
from tracer import AgentTracer
from guardrails import TaskGuardrails
import time
from langtrace_python_sdk import langtrace
from langtrace_python_sdk.utils.with_root_span import with_langtrace_root_span
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

load_dotenv()  # This should be called before accessing os.getenv()

# Initialize Langtrace with proper configuration
api_key = os.getenv("LANGTRACE_API_KEY")
if api_key:
    try:
        langtrace.init(
            api_key=api_key,
            batch=False,  # Send traces immediately
            write_spans_to_console=False  # Disable console output to avoid encoding issues
        )
    except Exception as e:
        print(f"Langtrace initialization failed: {e}")

class TaskPlannerCrew:
    def __init__(self):
        self.llm = LLM(
            model=f"gemini/{os.getenv('MODEL_NAME', 'gemini-2.5-pro')}",
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.7
        )
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.tracer = AgentTracer()
        self.current_trace_id = None
        self.api_calls = []
        self.agent_timings = {}
        self.span_stack = []
        self.task_traces = []
        self.log_results = []
        # Agent-specific cost tracking
        self.agent_costs = {
            'Task Planner': {'input_tokens': 0, 'output_tokens': 0, 'cost': 0},
            'Task Analyzer': {'input_tokens': 0, 'output_tokens': 0, 'cost': 0},
            'Plan Optimizer': {'input_tokens': 0, 'output_tokens': 0, 'cost': 0}
        }
        
        # Initialize NeMo Guardrails
        self.guardrails = TaskGuardrails()
        
    def count_tokens(self, text):
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except:
            return int(len(text.split()) * 1.3)  # Rough estimate
    
    def calculate_cost(self):
        # Gemini 2.0 Flash pricing (approximate)
        input_cost_per_1k = 1.25  # $0.000075 per 1K input tokens
        output_cost_per_1k = 10.00  # $0.0003 per 1K output tokens
        
        input_cost = (self.input_tokens / 1000000) * input_cost_per_1k
        output_cost = (self.output_tokens / 1000000) * output_cost_per_1k
        total_cost = input_cost + output_cost
        
        return {
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost
        }
    
    def calculate_agent_cost(self, agent_name, input_tokens, output_tokens):
        """Calculate cost for a specific agent"""
        input_cost_per_1k = 1.25
        output_cost_per_1k = 10.00
        
        input_cost = (input_tokens / 1000000) * input_cost_per_1k
        output_cost = (output_tokens / 1000000) * output_cost_per_1k
        total_cost = input_cost + output_cost
        
        # Update agent costs
        self.agent_costs[agent_name]['input_tokens'] += input_tokens
        self.agent_costs[agent_name]['output_tokens'] += output_tokens
        self.agent_costs[agent_name]['cost'] += total_cost
        
        # Send cost data to Langtrace
        self.send_cost_to_langtrace(agent_name, input_tokens, output_tokens, total_cost)
        
        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'cost': total_cost
        }
    
    def send_cost_to_langtrace(self, agent_name, input_tokens, output_tokens, cost):
        """Send cost and token data to Langtrace"""
        try:
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(f"{agent_name}_llm_call") as span:
                # Add cost and token attributes
                span.set_attribute("llm.usage.input_tokens", input_tokens)
                span.set_attribute("llm.usage.output_tokens", output_tokens)
                span.set_attribute("llm.usage.total_tokens", input_tokens + output_tokens)
                span.set_attribute("llm.usage.cost", cost)
                span.set_attribute("llm.model_name", "gemini-2.5-pro")
                span.set_attribute("llm.provider", "google")
                span.set_attribute("agent.name", agent_name)
                span.set_status(Status(StatusCode.OK))
        except Exception as e:
            print(f"Error sending cost to Langtrace: {e}")
    
    def save_logs_and_traces_json(self, task_input, result):
        """Save logs and traces as JSON format with duration and agent costs"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"task_logs_traces_{timestamp}.json"
        
        # Calculate total cost by agent
        total_cost_by_agent = 0
        for agent_name, costs in self.agent_costs.items():
            total_cost_by_agent += costs['cost']
        
        logs_traces_data = {
            'task_input': task_input,
            'timestamp': datetime.datetime.now().isoformat(),
            'complexity': result['complexity'],
            'priority': result['priority'],
            'task_traces': result.get('task_traces', []),
            'log_results': result.get('log_results', []),
            'execution_summary': result.get('execution_summary', {}),
            'total_duration': result.get('execution_summary', {}).get('total_duration', 0),
            'agent_cost_breakdown': self.agent_costs,
            'cost_summary': {
                'total_cost_by_agents': total_cost_by_agent,
                'total_input_tokens': sum(costs['input_tokens'] for costs in self.agent_costs.values()),
                'total_output_tokens': sum(costs['output_tokens'] for costs in self.agent_costs.values()),
                'cost_per_agent': {agent: costs['cost'] for agent, costs in self.agent_costs.items()}
            }
        }
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(logs_traces_data, f, indent=2, ensure_ascii=False)
        
        return json_filename
    
    def save_to_file(self, task_input, result, cost_info):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"task_plan_{timestamp}.txt"
        
        content = f"""TASK PLANNING RESULT
{'='*50}

Original Task: {task_input}
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Complexity: {result['complexity']}
Priority: {result['priority']}

PLAN:
{'-'*30}
{result['plan']}

ACTION STEPS:
{'-'*30}
"""        
        for i, step in enumerate(result['steps'], 1):
            content += f"{i}. {step}\n"
        
        # Add task traces and log results
        if 'task_traces' in result and result['task_traces']:
            content += "\n\nTASK TRACES:\n" + "-"*30 + "\n"
            for trace in result['task_traces']:
                content += f"Operation: {trace['operation']}\n"
                content += f"Duration: {trace['duration']:.3f}s\n"
                content += f"Status: {trace['status']}\n"
                if 'details' in trace:
                    content += f"Details: {trace['details']}\n"
                content += "\n"
        
        if 'log_results' in result and result['log_results']:
            content += "\nLOG RESULTS:\n" + "-"*30 + "\n"
            for log in result['log_results']:
                content += f"[{log['timestamp']}] {log['level']}: {log['message']}\n"
                if 'duration' in log:
                    content += f"Duration: {log['duration']:.3f}s\n"
                content += "\n"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filename
    
    def create_agents(self):
        # Trace agent creation
        agent_span = self.tracer.start_span(self.current_trace_id, "Agent Creation")
        self.span_stack.append(agent_span)
        
        start_time = time.time()
        
        planner_agent = Agent(
            role='Task Planner',
            goal='Create detailed, actionable task plans',
            backstory='Expert at breaking down complex tasks into manageable steps',
            llm=self.llm,
            verbose=True
        )
        
        analyzer_agent = Agent(
            role='Task Analyzer',
            goal='Analyze task feasibility and requirements',
            backstory='Specialist in evaluating task complexity and resource requirements',
            llm=self.llm,
            verbose=True
        )
        
        optimizer_agent = Agent(
            role='Plan Optimizer',
            goal='Optimize task plans for efficiency',
            backstory='Expert at streamlining processes and eliminating redundancies',
            llm=self.llm,
            verbose=True
        )
        
        duration = time.time() - start_time
        
        # Record API call for agent creation
        self.api_calls.append({
            'api_name': 'Agent Creation',
            'timestamp': start_time,
            'duration': duration,
            'status': 'SUCCESS',
            'tokens': 0
        })
        
        # Add to task traces
        self.task_traces.append({
            'operation': 'Agent Creation',
            'duration': duration,
            'status': 'SUCCESS',
            'details': 'Created 3 agents: Task Planner, Task Analyzer, Plan Optimizer'
        })
        
        # Add to log results
        self.log_results.append({
            'timestamp': datetime.datetime.fromtimestamp(start_time).isoformat(),
            'level': 'INFO',
            'message': 'Agent creation completed successfully',
            'duration': duration
        })
        
        self.tracer.end_span(agent_span, "SUCCESS", {
            'agents_created': 3,
            'creation_time': time.time() - start_time
        })
        self.span_stack.pop()
        return planner_agent, analyzer_agent, optimizer_agent
    
    def create_tasks(self, task_input, complexity, priority):
        # Trace task creation
        task_span = self.tracer.start_span(self.current_trace_id, "Task Creation")
        self.span_stack.append(task_span)
        
        planner_agent, analyzer_agent, optimizer_agent = self.create_agents()
        
        # Estimate tokens for each task and calculate costs
        analysis_desc = f"""
            Analyze the following task: "{task_input}"
            Complexity: {complexity}
            Priority: {priority}
            
            Provide:
            1. Task breakdown analysis
            2. Required resources
            3. Potential challenges
            4. Time estimation
            """
        
        planning_desc = f"""
            Based on the analysis, create a detailed plan for: "{task_input}"
            
            Include:
            1. Step-by-step action items
            2. Timeline and milestones
            3. Success criteria
            4. Risk mitigation strategies
            """
        
        optimization_desc = """
            Optimize the generated plan for maximum efficiency:
            1. Eliminate redundancies
            2. Identify parallel activities
            3. Suggest automation opportunities
            4. Provide final optimized plan
            """
        
        # Calculate estimated tokens for each agent
        analyzer_input_tokens = self.count_tokens(analysis_desc)
        planner_input_tokens = self.count_tokens(planning_desc)
        optimizer_input_tokens = self.count_tokens(optimization_desc)
        
        # Estimate output tokens (rough estimate)
        analyzer_output_tokens = int(analyzer_input_tokens * 1.5)
        planner_output_tokens = int(planner_input_tokens * 2.0)
        optimizer_output_tokens = int(optimizer_input_tokens * 1.8)
        
        # Calculate costs for each agent
        self.calculate_agent_cost('Task Analyzer', analyzer_input_tokens, analyzer_output_tokens)
        self.calculate_agent_cost('Task Planner', planner_input_tokens, planner_output_tokens)
        self.calculate_agent_cost('Plan Optimizer', optimizer_input_tokens, optimizer_output_tokens)
        
        analysis_task = Task(
            description=analysis_desc,
            agent=analyzer_agent,
            expected_output="Detailed task analysis with requirements and challenges"
        )
        
        planning_task = Task(
            description=planning_desc,
            agent=planner_agent,
            expected_output="Comprehensive task plan with actionable steps",
            context=[analysis_task]
        )
        
        optimization_task = Task(
            description=optimization_desc,
            agent=optimizer_agent,
            expected_output="Optimized task plan with efficiency improvements",
            context=[planning_task]
        )
        
        self.tracer.end_span(task_span, "SUCCESS", {'tasks_created': 3})
        self.span_stack.pop()
        return [analysis_task, planning_task, optimization_task]
    
    @with_langtrace_root_span("task_planning")
    def plan_task(self, task_input, complexity="Medium", priority="Medium"):
        # Validate input with NeMo Guardrails
        guardrails_result = self.guardrails.validate_with_nemo_guardrails(task_input)
        
        if not guardrails_result["input_safe"]:
            cost_info = {'total_tokens': 0, 'total_cost': 0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0, 'output_cost': 0}
            return {
                'plan': 'Task rejected due to safety concerns.',
                'steps': ['Please provide a safe and appropriate task.'],
                'complexity': complexity,
                'priority': priority,
                'status': 'Rejected',
                'guardrails_result': guardrails_result,
                'task_traces': [],
                'log_results': [],
                'execution_summary': {},
                'metrics': cost_info,
                'cost_info': cost_info,
                'agent_cost_breakdown': self.agent_costs,
                'cost_summary': {'total_cost_by_agents': 0, 'total_input_tokens': 0, 'total_output_tokens': 0},
                'filename': 'task_rejected_by_guardrails.txt',
                'json_filename': 'task_rejected_by_guardrails.json'
            }
        
        # Start main trace
        self.current_trace_id = self.tracer.start_trace("Task Planning", {
            'task_input': task_input[:100],
            'complexity': complexity,
            'priority': priority,
            'guardrails_passed': True
        })
        
        start_time = time.time()
        
        # Count input tokens
        self.input_tokens = self.count_tokens(task_input)
        
        # Create tasks with tracing
        tasks = self.create_tasks(task_input, complexity, priority)
        
        # Execute crew with tracing
        crew_span = self.tracer.start_span(self.current_trace_id, "Crew Execution")
        self.span_stack.append(crew_span)
        
        crew_start = time.time()
        
        crew = Crew(
            agents=[task.agent for task in tasks],
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        # Trace individual task executions
        for i, task in enumerate(tasks):
            task_exec_span = self.tracer.start_span(self.current_trace_id, f"Task_{i+1}_Execution", crew_span)
            self.tracer.add_event(task_exec_span, "task_started", {'task_description': task.description[:100]})
        
        result = crew.kickoff()
        
        crew_duration = time.time() - crew_start
        
        # Record API call for crew execution
        self.api_calls.append({
            'api_name': 'Crew Execution',
            'timestamp': crew_start,
            'duration': crew_duration,
            'status': 'SUCCESS',
            'tokens': self.output_tokens
        })
        
        # Add to task traces with agent cost information
        self.task_traces.append({
            'operation': 'Crew Execution',
            'duration': crew_duration,
            'status': 'SUCCESS',
            'details': f'Executed {len(tasks)} tasks sequentially',
            'agent_costs': {
                agent_name: {
                    'tokens_used': costs['input_tokens'] + costs['output_tokens'],
                    'cost': costs['cost']
                } for agent_name, costs in self.agent_costs.items()
            }
        })
        
        # Add to log results
        self.log_results.append({
            'timestamp': datetime.datetime.fromtimestamp(crew_start).isoformat(),
            'level': 'INFO',
            'message': f'Crew execution completed in {crew_duration:.3f}s',
            'duration': crew_duration
        })
        
        self.tracer.end_span(crew_span, "SUCCESS", {
            'agents_count': len(tasks),
            'execution_time': crew_duration,
            'tasks_completed': len(tasks)
        })
        self.span_stack.pop()
        
        # Count output tokens
        result_text = str(result)
        self.output_tokens = self.count_tokens(result_text)
        self.total_tokens = self.input_tokens + self.output_tokens
        
        # Calculate costs
        cost_info = self.calculate_cost()
        
        # Validate output with NeMo Guardrails
        output_guardrails_result = self.guardrails.validate_with_nemo_guardrails(task_input, result_text)
        
        # Parse result into structured format
        plan_result = {
            'plan': result_text,
            'steps': self.extract_steps(result_text),
            'complexity': complexity,
            'priority': priority,
            'status': 'Generated' if output_guardrails_result["output_safe"] else 'Generated with Warnings',
            'guardrails_result': output_guardrails_result,
            'task_traces': self.task_traces,
            'log_results': self.log_results,
            'execution_summary': self.get_execution_summary(),
            'metrics': cost_info,  # Separate metrics section
            'cost_info': cost_info,  # Backward compatibility
            'agent_cost_breakdown': self.agent_costs,
            'cost_summary': {
                'total_cost_by_agents': sum(costs['cost'] for costs in self.agent_costs.values()),
                'total_input_tokens': sum(costs['input_tokens'] for costs in self.agent_costs.values()),
                'total_output_tokens': sum(costs['output_tokens'] for costs in self.agent_costs.values()),
                'cost_per_agent': {agent: costs['cost'] for agent, costs in self.agent_costs.items()}
            }
        }
        
        # Save to file
        filename = self.save_to_file(task_input, plan_result, cost_info)
        json_filename = self.save_logs_and_traces_json(task_input, plan_result)
        plan_result['filename'] = filename
        plan_result['json_filename'] = json_filename
        
        # End main trace - find the root span
        root_spans = [event for event in self.tracer.get_trace(self.current_trace_id) if event.operation_name == "Task Planning"]
        if root_spans:
            root_span = root_spans[0]
            self.tracer.end_span(root_span.span_id, "SUCCESS", {
                'total_tokens': self.total_tokens,
                'total_cost': cost_info['total_cost']
            })
        
        return plan_result
    
    def extract_steps(self, plan_text):
        # Simple step extraction
        lines = plan_text.split('\n')
        steps = []
        for line in lines:
            line = line.strip()
            if line and any(marker in line.lower() for marker in ['step', '1.', '2.', '3.', '-', '*']):
                steps.append(line)
        return steps[:10] if steps else ["Review and execute the generated plan"]
    
    def get_trace_data(self):
        """Get trace data for visualization"""
        if self.current_trace_id:
            return self.tracer.get_all_traces()
        return {}
    
    def get_execution_summary(self):
        """Get execution summary with timing data"""
        trace_data = self.get_trace_data()
        
        summary = {
            'total_operations': 0,
            'total_duration': 0,
            'agent_breakdown': {},
            'api_calls': self.api_calls
        }
        
        for trace_id, events in trace_data.items():
            for event in events:
                if hasattr(event, 'duration') and event.duration:
                    summary['total_operations'] += 1
                    summary['total_duration'] += event.duration
                    
                    agent_name = event.operation_name
                    if agent_name not in summary['agent_breakdown']:
                        summary['agent_breakdown'][agent_name] = {
                            'duration': 0,
                            'operations': 0
                        }
                    
                    summary['agent_breakdown'][agent_name]['duration'] += event.duration
                    summary['agent_breakdown'][agent_name]['operations'] += 1
        
        return summary
    

    
    def get_trace_visualizations(self):
        """Return empty visualization data since visualizations are removed"""
        return {
            'execution_timeline': None,
            'api_calls_timeline': None,
            'performance_waterfall': None
        }
    
    def export_trace_data(self, filename=None):
        """Export trace data to file"""
        return self.tracer.export_traces(filename)

def main():
    # Initialize the task planner
    planner = TaskPlannerCrew()
    
    print("Task Planner - CrewAI Implementation")
    print("=" * 40)
    
    # Get user input
    task_input = input("\nEnter the task you want to plan: ")
    
    if not task_input.strip():
        print("No task provided. Exiting.")
        return
    
    # Get complexity and priority
    complexity = input("Enter complexity (Low/Medium/High) [Medium]: ").strip() or "Medium"
    priority = input("Enter priority (Low/Medium/High) [Medium]: ").strip() or "Medium"
    
    print(f"\nPlanning task: {task_input}")
    print(f"Complexity: {complexity}, Priority: {priority}")
    print("\nGenerating plan... (this may take a moment)\n")
    
    try:
        # Generate the plan
        result = planner.plan_task(task_input, complexity, priority)
        
        # Display results
        print("\n" + "=" * 50)
        print("TASK PLAN GENERATED SUCCESSFULLY")
        print("=" * 50)
        
        print(f"\nComplexity: {result['complexity']}")
        print(f"Priority: {result['priority']}")
        print(f"Status: {result['status']}")
        
        # Display guardrails information
        if 'guardrails_result' in result:
            guardrails = result['guardrails_result']
            print(f"\nNEMO GUARDRAILS STATUS:")
            print("-" * 25)
            print(f"Input Safe: {guardrails['input_safe']}")
            print(f"Output Safe: {guardrails['output_safe']}")
            print(f"Overall Safe: {guardrails['overall_safe']}")
            
            if 'nemo_message' in guardrails:
                print(f"Safety Message: {guardrails['nemo_message']}")
            
            if 'nemo_violations' in guardrails and guardrails['nemo_violations']:
                print(f"\nViolations Detected:")
                for violation in guardrails['nemo_violations']:
                    print(f"  - {violation['rail_name']}: {violation['action']}")
            
            if 'output_checks' in guardrails and 'quality_check' in guardrails['output_checks']:
                quality = guardrails['output_checks']['quality_check']
                print(f"Output Quality Score: {quality['overall_quality']:.2f}")
        
        print("\nACTION STEPS:")
        print("-" * 20)
        for i, step in enumerate(result['steps'], 1):
            print(f"{i}. {step}")
        
        # Display task traces
        if 'task_traces' in result and result['task_traces']:
            print(f"\nTASK TRACES:")
            print("-" * 20)
            for trace in result['task_traces']:
                print(f"• {trace['operation']}: {trace['duration']:.3f}s ({trace['status']})")
        
        # Display log results
        if 'log_results' in result and result['log_results']:
            print(f"\nLOG RESULTS:")
            print("-" * 20)
            for log in result['log_results']:
                duration_info = f" ({log['duration']:.3f}s)" if 'duration' in log else ""
                print(f"• [{log['level']}] {log['message']}{duration_info}")
        
        print(f"\nPlan saved to: {result['filename']}")
        print(f"Logs & Traces JSON saved to: {result['json_filename']}")
        
        # Display metrics as separate section
        print(f"\n" + "=" * 50)
        print("METRICS")
        print("=" * 50)
        cost = result['metrics']
        print(f"Total Tokens: {cost['total_tokens']:,}")
        print(f"Total Cost: ${cost['total_cost']:.6f}")
        print(f"Input Tokens: {cost['input_tokens']:,}")
        print(f"Output Tokens: {cost['output_tokens']:,}")
        
        # Display agent cost breakdown
        if 'agent_cost_breakdown' in result:
            print(f"\n" + "=" * 50)
            print("AGENT COST BREAKDOWN")
            print("=" * 50)
            for agent_name, costs in result['agent_cost_breakdown'].items():
                print(f"\n{agent_name}:")
                print(f"  Input Tokens: {costs['input_tokens']:,}")
                print(f"  Output Tokens: {costs['output_tokens']:,}")
                print(f"  Total Tokens: {costs['input_tokens'] + costs['output_tokens']:,}")
                print(f"  Cost: ${costs['cost']:.6f}")
            
            if 'cost_summary' in result:
                summary = result['cost_summary']
                print(f"\nCOST SUMMARY:")
                print(f"Total Cost by All Agents: ${summary['total_cost_by_agents']:.6f}")
                print(f"Total Input Tokens: {summary['total_input_tokens']:,}")
                print(f"Total Output Tokens: {summary['total_output_tokens']:,}")
        
    except Exception as e:
        print(f"Error generating plan: {str(e)}")
        print("Please check your API key and internet connection.")

if __name__ == "__main__":
    main()
# ----------------------
