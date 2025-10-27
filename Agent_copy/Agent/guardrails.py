import re
from typing import List, Dict, Any
import json
import os
from nemo_guardrails_integration import NemoGuardrailsManager

class TaskGuardrails:
    def __init__(self):
        self.forbidden_keywords = [
            'illegal', 'harmful', 'dangerous', 'violent', 'hack', 'exploit',
            'malware', 'virus', 'fraud', 'scam', 'phishing','hijack'
        ]
        
        self.sensitive_topics = [
            'personal information', 'private data', 'confidential',
            'classified', 'secret', 'password', 'credit card'
        ]
        
        # Initialize NeMo Guardrails Manager
        self.nemo_manager = NemoGuardrailsManager()
        self.guardrails_enabled = True
        
        # Add custom rails for existing keywords
        self._setup_custom_rails()
    
    def validate_task(self, task_input: str) -> bool:
        """Validate if task is safe and appropriate"""
        task_lower = task_input.lower()
        
        # Check for forbidden keywords
        if any(keyword in task_lower for keyword in self.forbidden_keywords):
            return False
        
        # Check for sensitive topics
        if any(topic in task_lower for topic in self.sensitive_topics):
            return False
        
        # Check task length
        if len(task_input.strip()) < 10:
            return False
        
        # Check for excessive special characters
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', task_input)) / len(task_input)
        if special_char_ratio > 0.3:
            return False
        
        return True
    
    def get_safety_score(self, task_input: str) -> float:
        """Return safety score between 0 and 1"""
        score = 1.0
        task_lower = task_input.lower()
        
        # Deduct for each violation
        for keyword in self.forbidden_keywords:
            if keyword in task_lower:
                score -= 0.2
        
        for topic in self.sensitive_topics:
            if topic in task_lower:
                score -= 0.1
        
        return max(0.0, score)
    
    def sanitize_task(self, task_input: str) -> str:
        """Clean and sanitize task input"""
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', task_input.strip())
        
        # Remove potentially harmful patterns
        sanitized = re.sub(r'<[^>]*>', '', sanitized)  # Remove HTML tags
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def get_violation_reasons(self, task_input: str) -> List[str]:
        """Get list of violation reasons"""
        reasons = []
        task_lower = task_input.lower()
        
        for keyword in self.forbidden_keywords:
            if keyword in task_lower:
                reasons.append(f"Contains forbidden keyword: {keyword}")
        
        for topic in self.sensitive_topics:
            if topic in task_lower:
                reasons.append(f"References sensitive topic: {topic}")
        
        if len(task_input.strip()) < 10:
            reasons.append("Task description too short")
        
        return reasons
    
    def _setup_custom_rails(self):
        """Setup custom rails based on existing keywords and topics"""
        # Convert forbidden keywords to patterns
        keyword_patterns = [rf"\b{keyword}\b" for keyword in self.forbidden_keywords]
        self.nemo_manager.add_custom_rail(
            name="forbidden_keywords",
            rail_type="input",
            patterns=keyword_patterns,
            action="block"
        )
        
        # Convert sensitive topics to patterns
        topic_patterns = [rf"{topic.replace(' ', '.{0,5}')}" for topic in self.sensitive_topics]
        self.nemo_manager.add_custom_rail(
            name="sensitive_topics",
            rail_type="input",
            patterns=topic_patterns,
            action="block"
        )
    
    def check_jailbreak_attempt(self, text: str) -> Dict[str, Any]:
        """Check for jailbreak attempts using NeMo Guardrails patterns"""
        jailbreak_patterns = [
            r'ignore.{0,20}previous.{0,20}instructions',
            r'forget.{0,20}everything',
            r'act.{0,20}as.{0,20}different',
            r'pretend.{0,20}you.{0,20}are',
            r'roleplay.{0,20}as',
            r'system.{0,20}prompt',
            r'developer.{0,20}mode'
        ]
        
        text_lower = text.lower()
        violations = []
        
        for pattern in jailbreak_patterns:
            if re.search(pattern, text_lower):
                violations.append(f"Potential jailbreak pattern: {pattern}")
        
        return {
            "is_jailbreak": len(violations) > 0,
            "confidence": min(len(violations) * 0.3, 1.0),
            "violations": violations
        }
    
    def check_harmful_content(self, text: str) -> Dict[str, Any]:
        """Enhanced harmful content detection"""
        harmful_categories = {
            "violence": ["kill", "murder", "assault", "attack", "harm", "hurt"],
            "illegal": ["drugs", "weapons", "bomb", "steal", "robbery"],
            "hate_speech": ["racist", "sexist", "discriminate", "hate"],
            "self_harm": ["suicide", "self-harm", "cutting", "overdose"]
        }
        
        text_lower = text.lower()
        detected_categories = []
        
        for category, keywords in harmful_categories.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_categories.append(category)
        
        return {
            "is_harmful": len(detected_categories) > 0,
            "categories": detected_categories,
            "confidence": min(len(detected_categories) * 0.4, 1.0)
        }
    
    def check_output_quality(self, output: str) -> Dict[str, Any]:
        """Check output quality using NeMo Guardrails principles"""
        quality_checks = {
            "factual_accuracy": self._check_factual_claims(output),
            "bias_detection": self._check_bias(output),
            "coherence": self._check_coherence(output),
            "completeness": self._check_completeness(output)
        }
        
        overall_score = sum(check["score"] for check in quality_checks.values()) / len(quality_checks)
        
        return {
            "overall_quality": overall_score,
            "checks": quality_checks,
            "passed": overall_score >= 0.7
        }
    
    def _check_factual_claims(self, text: str) -> Dict[str, Any]:
        """Basic factual claim checking"""
        # Simple heuristics for factual claims
        claim_indicators = ["according to", "studies show", "research indicates", "fact:", "proven"]
        unsupported_indicators = ["i think", "maybe", "possibly", "might be"]
        
        text_lower = text.lower()
        has_claims = any(indicator in text_lower for indicator in claim_indicators)
        has_uncertainty = any(indicator in text_lower for indicator in unsupported_indicators)
        
        score = 0.8 if has_claims and not has_uncertainty else 0.6 if not has_claims else 0.4
        
        return {"score": score, "has_claims": has_claims, "has_uncertainty": has_uncertainty}
    
    def _check_bias(self, text: str) -> Dict[str, Any]:
        """Check for potential bias in output"""
        bias_indicators = [
            "always", "never", "all", "none", "everyone", "nobody",
            "obviously", "clearly", "definitely", "certainly"
        ]
        
        text_lower = text.lower()
        bias_count = sum(1 for indicator in bias_indicators if indicator in text_lower)
        
        score = max(0.2, 1.0 - (bias_count * 0.1))
        
        return {"score": score, "bias_indicators_found": bias_count}
    
    def _check_coherence(self, text: str) -> Dict[str, Any]:
        """Check text coherence"""
        sentences = text.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        # Coherence based on sentence length variation
        score = 0.8 if 10 <= avg_sentence_length <= 25 else 0.6
        
        return {"score": score, "avg_sentence_length": avg_sentence_length}
    
    def _check_completeness(self, text: str) -> Dict[str, Any]:
        """Check if output is complete"""
        completion_indicators = ["in conclusion", "finally", "to summarize", "overall"]
        incomplete_indicators = ["...", "etc.", "and so on", "among others"]
        
        text_lower = text.lower()
        has_completion = any(indicator in text_lower for indicator in completion_indicators)
        has_incomplete = any(indicator in text_lower for indicator in incomplete_indicators)
        
        score = 0.9 if has_completion and not has_incomplete else 0.7 if not has_incomplete else 0.5
        
        return {"score": score, "has_completion": has_completion, "has_incomplete": has_incomplete}
    
    def validate_with_nemo_guardrails(self, input_text: str, output_text: str = None) -> Dict[str, Any]:
        """Comprehensive validation using real NeMo Guardrails approach"""
        if not self.guardrails_enabled:
            return {"input_safe": True, "output_safe": True, "overall_safe": True}
        
        # Use NeMo Guardrails for validation
        if output_text:
            # Full interaction validation
            nemo_result = self.nemo_manager.validate_full_interaction(input_text, output_text)
            
            # Combine with legacy checks for backward compatibility
            legacy_input_safe = self.validate_task(input_text)
            legacy_output_quality = self.check_output_quality(output_text)
            
            return {
                "input_safe": nemo_result["input_safe"] and legacy_input_safe,
                "output_safe": nemo_result["output_safe"] and legacy_output_quality["passed"],
                "overall_safe": nemo_result["overall_safe"] and legacy_input_safe and legacy_output_quality["passed"],
                "nemo_violations": nemo_result["violations"],
                "nemo_message": nemo_result["message"],
                "input_checks": {
                    "basic_validation": legacy_input_safe,
                    "nemo_validation": nemo_result["input_safe"],
                    "safety_score": self.get_safety_score(input_text)
                },
                "output_checks": {
                    "quality_check": legacy_output_quality,
                    "nemo_validation": nemo_result["output_safe"]
                }
            }
        else:
            # Input-only validation
            nemo_result = self.nemo_manager.validate_task_input(input_text)
            legacy_safe = self.validate_task(input_text)
            
            return {
                "input_safe": nemo_result["safe"] and legacy_safe,
                "output_safe": True,
                "overall_safe": nemo_result["safe"] and legacy_safe,
                "nemo_violations": nemo_result["violations"],
                "nemo_message": nemo_result["message"],
                "input_checks": {
                    "basic_validation": legacy_safe,
                    "nemo_validation": nemo_result["safe"],
                    "safety_score": self.get_safety_score(input_text)
                }
            }