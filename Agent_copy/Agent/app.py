# Must precede any llm module imports
import os
from dotenv import load_dotenv

load_dotenv()

# Langtrace initialization - same as test_langtrace.py
try:
    from langtrace_python_sdk import langtrace
    
    api_key = os.getenv('LANGTRACE_API_KEY')
    langtrace.init(api_key=api_key)
    
    from langtrace_python_sdk.utils.with_root_span import with_langtrace_root_span
    LANGTRACE_AVAILABLE = True
except Exception as e:
    print(f"Langtrace initialization failed: {e}")
    LANGTRACE_AVAILABLE = False
    with_langtrace_root_span = None

import streamlit as st
from task_planner import TaskPlannerCrew
from memory_manager import MemoryManager
from guardrails import TaskGuardrails
# from evaluation import EvaluationMetrics
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Task Planner Agent", page_icon="🤖", layout="wide")

class TaskPlannerApp:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.guardrails = TaskGuardrails()
        # self.evaluation = EvaluationMetrics()
        
    def run(self):
        st.title("🤖 Task Planner Agent")
        st.sidebar.title("Navigation")
        
        page = st.sidebar.selectbox("Choose a page", ["Task Planning", "Memory", "Metrics"])
        
        if page == "Task Planning":
            self.task_planning_page()
        elif page == "Memory":
            self.memory_page()
        elif page == "Metrics":
            self.metrics_page()
    
    def task_planning_page(self):
        st.header("Task Planning")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            task_input = st.text_area("Enter your task:", height=100, 
                                    placeholder="e.g., Plan a marketing campaign for a new product launch")
            
            complexity = st.selectbox("Task Complexity:", ["Simple", "Medium", "Complex"])
            priority = st.selectbox("Priority:", ["Low", "Medium", "High", "Critical"])
            
            if st.button("Generate Plan", type="primary"):
                if task_input:
                    # Guardrails check
                    if not self.guardrails.validate_task(task_input):
                        st.error("Task violates safety guidelines. Please modify your request.")
                        return
                    
                    with st.spinner("Planning your task..."):
                        # Execute task planning with Langtrace tracing
                        if LANGTRACE_AVAILABLE and with_langtrace_root_span:
                            @with_langtrace_root_span("agent_task_execution")
                            def execute_task_planning():
                                crew = TaskPlannerCrew()
                                return crew.plan_task(task_input, complexity, priority)
                            
                            result = execute_task_planning()
                            st.success("✅ Task execution traced to Langtrace")
                        else:
                            crew = TaskPlannerCrew()
                            result = crew.plan_task(task_input, complexity, priority)
                        
                        # Store in memory
                        self.memory_manager.store_task(task_input, result)
                        
                        # Evaluate with Langtrace tracing
                        # if LANGTRACE_AVAILABLE and with_langtrace_root_span:
                        #     @with_langtrace_root_span("evaluation_metrics")
                        #     def execute_evaluation():
                        #         metrics = self.evaluation.evaluate_plan(result)
                        #         # Return evaluation data for tracing
                        #         return {
                        #             "task_input": task_input,
                        #             "complexity": complexity,
                        #             "priority": priority,
                        #             "completeness": metrics.get('completeness', 0),
                        #             "feasibility": metrics.get('feasibility', 0),
                        #             "clarity": metrics.get('clarity', 0),
                        #             "overall_score": metrics.get('overall_score', 0)
                        #         }
                            
                        #     evaluation_data = execute_evaluation()
                        #     metrics = self.evaluation.evaluate_plan(result)
                        #     st.success("✅ Evaluation metrics traced to Langtrace")
                        # else:
                        #     metrics = self.evaluation.evaluate_plan(result)
                        
                        st.success(f"Task plan generated successfully! Saved as: {result['filename']}")
                        
                        # Display results
                        st.subheader("📋 Generated Plan")
                        st.markdown(result['plan'])
                        
                        # Display cost information
                        st.subheader("💰 Token Usage & Cost")
                        cost_info = result['cost_info']
                        col_cost1, col_cost2, col_cost3, col_cost4 = st.columns(4)
                        with col_cost1:
                            st.metric("Input Tokens", f"{cost_info['input_tokens']:,}")
                        with col_cost2:
                            st.metric("Output Tokens", f"{cost_info['output_tokens']:,}")
                        with col_cost3:
                            st.metric("Total Tokens", f"{cost_info['total_tokens']:,}")
                        with col_cost4:
                            st.metric("Total Cost", f"${cost_info['total_cost']:.6f}")
                        
                        # st.subheader("📊 Plan Metrics")
                        # col_a, col_b, col_c = st.columns(3)
                        # with col_a:
                        #     st.metric("Completeness", f"{metrics['completeness']:.1%}")
                        # with col_b:
                        #     st.metric("Feasibility", f"{metrics['feasibility']:.1%}")
                        # with col_c:
                        #     st.metric("Clarity", f"{metrics['clarity']:.1%}")
                        
                        if result.get('steps'):
                            st.subheader("🔄 Action Steps")
                            for i, step in enumerate(result['steps'], 1):
                                st.write(f"{i}. {step}")
        
        with col2:
            st.subheader("Recent Tasks")
            recent_tasks = self.memory_manager.get_recent_tasks(5)
            for task in recent_tasks:
                with st.expander(f"Task: {task['input'][:50]}..."):
                    st.write(f"**Created:** {task['timestamp']}")
                    st.write(f"**Status:** {task.get('status', 'Completed')}")
    
    def memory_page(self):
        st.header("Memory & History")
        
        tasks = self.memory_manager.get_all_tasks()
        if tasks:
            df = pd.DataFrame(tasks)
            st.dataframe(df[['input', 'timestamp', 'complexity', 'priority']])
            
            # Memory statistics
            st.subheader("Memory Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tasks", len(tasks))
            with col2:
                st.metric("This Week", len([t for t in tasks if self.memory_manager.is_recent(t['timestamp'], 7)]))
            with col3:
                st.metric("Success Rate", "85%")  # Mock data
        else:
            st.info("No tasks in memory yet.")
            
        # Display saved files
        st.subheader("📁 Saved Files")
        import glob
        txt_files = glob.glob("task_plan_*.txt")
        if txt_files:
            for file in sorted(txt_files, reverse=True)[:5]:  # Show last 5 files
                if st.button(f"📄 {file}", key=file):
                    with open(file, 'r', encoding='utf-8') as f:
                        st.text_area("File Content:", f.read(), height=300)
        else:
            st.info("No saved task plans yet.")
    
    def metrics_page(self):
        st.header("Evaluation Metrics")
        
        # Mock metrics data
        metrics_data = {
            'Metric': ['Completeness', 'Feasibility', 'Clarity', 'Efficiency'],
            'Average Score': [0.85, 0.78, 0.92, 0.73],
            'Trend': ['↑', '→', '↑', '↓']
        }
        
        df = pd.DataFrame(metrics_data)
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df, x='Metric', y='Average Score', title="Performance Metrics")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Metrics Overview")
            for _, row in df.iterrows():
                st.metric(row['Metric'], f"{row['Average Score']:.1%}", row['Trend'])

if __name__ == "__main__":
    app = TaskPlannerApp()
    app.run()
# ----------------
