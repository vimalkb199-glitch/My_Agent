# import re
# from typing import Dict, List
# from datetime import datetime

# class EvaluationMetrics:
#     def __init__(self):
#         self.metrics_history = []
    
#     def evaluate_plan(self, plan_result: Dict) -> Dict:
#         """Evaluate the quality of a generated plan"""
#         plan_text = plan_result.get('plan', '')
#         steps = plan_result.get('steps', [])
        
#         completeness = self._evaluate_completeness(plan_text, steps)
#         feasibility = self._evaluate_feasibility(plan_text)
#         clarity = self._evaluate_clarity(plan_text)
#         efficiency = self._evaluate_efficiency(steps)
        
#         metrics = {
#             'completeness': completeness,
#             'feasibility': feasibility,
#             'clarity': clarity,
#             'efficiency': efficiency,
#             'overall_score': (completeness + feasibility + clarity + efficiency) / 4,
#             'timestamp': datetime.now().isoformat()
#         }
        
#         self.metrics_history.append(metrics)
#         return metrics
    
#     def _evaluate_completeness(self, plan_text: str, steps: List[str]) -> float:
#         """Evaluate how complete the plan is"""
#         score = 0.0
        
#         # Check for key components
#         if 'objective' in plan_text.lower() or 'goal' in plan_text.lower():
#             score += 0.2
#         if len(steps) >= 3:
#             score += 0.3
#         if 'timeline' in plan_text.lower() or 'deadline' in plan_text.lower():
#             score += 0.2
#         if 'resource' in plan_text.lower():
#             score += 0.15
#         if 'risk' in plan_text.lower() or 'challenge' in plan_text.lower():
#             score += 0.15
        
#         return min(1.0, score)
    
#     def _evaluate_feasibility(self, plan_text: str) -> float:
#         """Evaluate how feasible the plan is"""
#         score = 0.8  # Base score
        
#         # Deduct for unrealistic elements
#         unrealistic_keywords = ['impossible', 'unlimited', 'infinite', 'perfect']
#         for keyword in unrealistic_keywords:
#             if keyword in plan_text.lower():
#                 score -= 0.2
        
#         # Check for realistic timeframes
#         if re.search(r'\d+\s*(day|week|month|hour)', plan_text.lower()):
#             score += 0.1
        
#         return max(0.0, min(1.0, score))
    
#     def _evaluate_clarity(self, plan_text: str) -> float:
#         """Evaluate how clear and understandable the plan is"""
#         score = 0.0
        
#         # Check structure
#         if len(plan_text.split('\n')) >= 5:
#             score += 0.3
        
#         # Check for clear action words
#         action_words = ['create', 'develop', 'implement', 'analyze', 'design', 'execute']
#         action_count = sum(1 for word in action_words if word in plan_text.lower())
#         score += min(0.3, action_count * 0.1)
        
#         # Check for numbered steps or bullets
#         if re.search(r'\d+\.|\*|\-', plan_text):
#             score += 0.2
        
#         # Check readability (sentence length)
#         sentences = re.split(r'[.!?]+', plan_text)
#         avg_length = sum(len(s.split()) for s in sentences if s.strip()) / max(1, len(sentences))
#         if 10 <= avg_length <= 25:
#             score += 0.2
        
#         return min(1.0, score)
    
#     def _evaluate_efficiency(self, steps: List[str]) -> float:
#         """Evaluate the efficiency of the plan steps"""
#         if not steps:
#             return 0.5
        
#         score = 0.7  # Base score
        
#         # Optimal number of steps
#         num_steps = len(steps)
#         if 3 <= num_steps <= 8:
#             score += 0.2
#         elif num_steps > 10:
#             score -= 0.1
        
#         # Check for parallel activities
#         parallel_keywords = ['simultaneously', 'parallel', 'concurrently', 'meanwhile']
#         if any(keyword in ' '.join(steps).lower() for keyword in parallel_keywords):
#             score += 0.1
        
#         return min(1.0, score)
    
#     def get_average_metrics(self) -> Dict:
#         """Get average metrics across all evaluations"""
#         if not self.metrics_history:
#             return {}
        
#         metrics = ['completeness', 'feasibility', 'clarity', 'efficiency', 'overall_score']
#         averages = {}
        
#         for metric in metrics:
#             values = [m[metric] for m in self.metrics_history if metric in m]
#             averages[metric] = sum(values) / len(values) if values else 0.0
        
#         return averages
    
#     def get_metrics_trend(self, metric_name: str, last_n: int = 5) -> List[float]:
#         """Get trend for a specific metric"""
#         recent_metrics = self.metrics_history[-last_n:]
#         return [m.get(metric_name, 0.0) for m in recent_metrics]
    
#     def generate_feedback(self, metrics: Dict) -> str:
#         """Generate human-readable feedback based on metrics"""
#         feedback = []
        
#         if metrics['completeness'] < 0.7:
#             feedback.append("Consider adding more details about objectives, timeline, and resources.")
        
#         if metrics['feasibility'] < 0.7:
#             feedback.append("Review the plan for realistic expectations and achievable goals.")
        
#         if metrics['clarity'] < 0.7:
#             feedback.append("Improve plan structure with clearer steps and action items.")
        
#         if metrics['efficiency'] < 0.7:
#             feedback.append("Look for opportunities to streamline steps and identify parallel activities.")
        
#         if not feedback:
#             feedback.append("Great plan! All metrics look good.")
        
#         return " ".join(feedback)