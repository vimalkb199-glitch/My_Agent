"""
Minimal NeMo Guardrails Integration
Implements core NeMo Guardrails concepts without requiring the full package
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class RailType(Enum):
    INPUT = "input"
    OUTPUT = "output"
    DIALOG = "dialog"

@dataclass
class RailConfig:
    name: str
    type: RailType
    patterns: List[str]
    action: str
    priority: int = 1

class NemoGuardrailsLite:
    """Lightweight implementation of NeMo Guardrails core functionality"""
    
    def __init__(self):
        self.rails = []
        self.setup_default_rails()
        
    def setup_default_rails(self):
        """Setup default safety rails"""
        # Input rails
        self.add_rail(RailConfig(
            name="jailbreak_detection",
            type=RailType.INPUT,
            patterns=[
                r"ignore.{0,20}previous.{0,20}instructions",
                r"forget.{0,20}everything",
                r"act.{0,20}as.{0,20}different",
                r"pretend.{0,20}you.{0,20}are",
                r"roleplay.{0,20}as",
                r"system.{0,20}prompt",
                r"developer.{0,20}mode"
            ],
            action="block",
            priority=1
        ))
        
        self.add_rail(RailConfig(
            name="harmful_content",
            type=RailType.INPUT,
            patterns=[
                r"how.{0,10}to.{0,10}(kill|murder|harm)",
                r"make.{0,10}(bomb|weapon|drug)",
                r"illegal.{0,10}(activity|action)",
                r"hack.{0,10}(into|system|account)"
            ],
            action="block",
            priority=1
        ))
        
        # Output rails
        self.add_rail(RailConfig(
            name="output_safety",
            type=RailType.OUTPUT,
            patterns=[
                r"(kill|murder|harm).{0,20}(people|person|human)",
                r"here.{0,10}is.{0,10}how.{0,10}to.{0,10}(hack|steal|break)",
                r"instructions.{0,10}for.{0,10}(illegal|harmful)"
            ],
            action="filter",
            priority=1
        ))
    
    def add_rail(self, rail: RailConfig):
        """Add a new rail configuration"""
        self.rails.append(rail)
    
    def check_input(self, text: str) -> Dict[str, Any]:
        """Check input text against input rails"""
        violations = []
        blocked = False
        
        for rail in self.rails:
            if rail.type != RailType.INPUT:
                continue
                
            for pattern in rail.patterns:
                if re.search(pattern, text.lower()):
                    violation = {
                        "rail_name": rail.name,
                        "pattern": pattern,
                        "action": rail.action,
                        "priority": rail.priority
                    }
                    violations.append(violation)
                    
                    if rail.action == "block":
                        blocked = True
        
        return {
            "safe": not blocked,
            "violations": violations,
            "action_required": "block" if blocked else "allow"
        }
    
    def check_output(self, text: str) -> Dict[str, Any]:
        """Check output text against output rails"""
        violations = []
        filtered = False
        
        for rail in self.rails:
            if rail.type != RailType.OUTPUT:
                continue
                
            for pattern in rail.patterns:
                if re.search(pattern, text.lower()):
                    violation = {
                        "rail_name": rail.name,
                        "pattern": pattern,
                        "action": rail.action,
                        "priority": rail.priority
                    }
                    violations.append(violation)
                    
                    if rail.action == "filter":
                        filtered = True
        
        return {
            "safe": not filtered,
            "violations": violations,
            "action_required": "filter" if filtered else "allow"
        }
    
    def validate_conversation(self, input_text: str, output_text: str = None) -> Dict[str, Any]:
        """Validate entire conversation flow"""
        input_check = self.check_input(input_text)
        
        result = {
            "input_safe": input_check["safe"],
            "input_violations": input_check["violations"],
            "overall_safe": input_check["safe"]
        }
        
        if output_text:
            output_check = self.check_output(output_text)
            result.update({
                "output_safe": output_check["safe"],
                "output_violations": output_check["violations"],
                "overall_safe": input_check["safe"] and output_check["safe"]
            })
        
        return result
    
    def get_safety_message(self, violations: List[Dict]) -> str:
        """Generate appropriate safety message based on violations"""
        if not violations:
            return "Content is safe."
        
        high_priority = [v for v in violations if v["priority"] == 1]
        if high_priority:
            return "Content violates safety guidelines and cannot be processed."
        
        return "Content may require review before processing."

class NemoGuardrailsManager:
    """Manager class for integrating NeMo Guardrails with existing systems"""
    
    def __init__(self):
        self.guardrails = NemoGuardrailsLite()
        self.enabled = True
        self.log_violations = True
        
    def validate_task_input(self, task_input: str) -> Dict[str, Any]:
        """Validate task input using NeMo Guardrails"""
        if not self.enabled:
            return {"safe": True, "message": "Guardrails disabled"}
        
        result = self.guardrails.check_input(task_input)
        
        return {
            "safe": result["safe"],
            "violations": result["violations"],
            "message": self.guardrails.get_safety_message(result["violations"]),
            "action": result["action_required"]
        }
    
    def validate_task_output(self, output_text: str) -> Dict[str, Any]:
        """Validate task output using NeMo Guardrails"""
        if not self.enabled:
            return {"safe": True, "message": "Guardrails disabled"}
        
        result = self.guardrails.check_output(output_text)
        
        return {
            "safe": result["safe"],
            "violations": result["violations"],
            "message": self.guardrails.get_safety_message(result["violations"]),
            "action": result["action_required"]
        }
    
    def validate_full_interaction(self, input_text: str, output_text: str) -> Dict[str, Any]:
        """Validate complete input-output interaction"""
        if not self.enabled:
            return {"safe": True, "message": "Guardrails disabled"}
        
        result = self.guardrails.validate_conversation(input_text, output_text)
        
        all_violations = result.get("input_violations", []) + result.get("output_violations", [])
        
        return {
            "input_safe": result["input_safe"],
            "output_safe": result.get("output_safe", True),
            "overall_safe": result["overall_safe"],
            "violations": all_violations,
            "message": self.guardrails.get_safety_message(all_violations)
        }
    
    def add_custom_rail(self, name: str, rail_type: str, patterns: List[str], action: str = "block"):
        """Add custom rail configuration"""
        rail_type_enum = RailType.INPUT if rail_type.lower() == "input" else RailType.OUTPUT
        
        custom_rail = RailConfig(
            name=name,
            type=rail_type_enum,
            patterns=patterns,
            action=action,
            priority=2  # Custom rails have lower priority
        )
        
        self.guardrails.add_rail(custom_rail)
    
    def disable_guardrails(self):
        """Disable guardrails checking"""
        self.enabled = False
    
    def enable_guardrails(self):
        """Enable guardrails checking"""
        self.enabled = True