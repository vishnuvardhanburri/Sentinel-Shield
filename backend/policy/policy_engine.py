"""
Sentinel Shield v2 — Policy Engine
Department-level, YAML-driven policy enforcement.

Policies define per-department rules:
  - What entity types trigger WARN / REDACT / BLOCK
  - Keyword blocklists
  - Allowed models
  - Custom risk thresholds
"""
import os
import re
import yaml
import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PRESETS_DIR = os.path.join(BASE_DIR, "presets")
POLICY_DIR = os.path.join(BASE_DIR, "policies")

logger = logging.getLogger("sentinel.policy")


class EnforcementLevel(str, Enum):
    WARN   = "warn"    # Log and alert, but allow the prompt through
    REDACT = "redact"  # Automatically redact the matched content
    BLOCK  = "block"   # Reject the request entirely


@dataclass
class PolicyRule:
    name: str
    description: str = ""
    entity_types: List[str] = field(default_factory=list)    # Presidio entity types
    keywords: List[str] = field(default_factory=list)         # Exact/regex keywords
    enforcement: EnforcementLevel = EnforcementLevel.REDACT
    risk_threshold: float = 5.0                               # Block if risk >= this
    allowed_models: List[str] = field(default_factory=list)   # Empty = all allowed
    applies_to_departments: List[str] = field(default_factory=list)  # Empty = global


@dataclass
class PolicyDecision:
    action: EnforcementLevel
    triggered_rules: List[str]
    redacted_text: Optional[str] = None
    block_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    model_allowed: bool = True
    policy_name: str = "default"


class PolicyEngine:
    """
    Live-reloadable policy engine.
    Loads YAML policies from presets/ and policies/ directories.
    Department routing: per-dept policy overrides global.
    """

    def __init__(self):
        self._policies: Dict[str, List[PolicyRule]] = {}
        self._global_rules: List[PolicyRule] = []
        self._last_loaded: float = 0

    def reload(self):
        """Reload all YAML policies from presets/ and policies/."""
        self._policies = {}
        self._global_rules = []
        self._last_loaded = os.path.getmtime(__file__) if os.path.exists(__file__) else 0

        for d in [PRESETS_DIR, POLICY_DIR]:
            if not os.path.isdir(d):
                continue
            for filename in os.listdir(d):
                if filename.endswith((".yaml", ".yml")):
                    self._load_file(os.path.join(d, filename))

        logger.info(f"Policy Engine: Loaded {sum(len(v) for v in self._policies.values())} dept rules, "
                    f"{len(self._global_rules)} global rules")

    def _load_file(self, filepath: str):
        """Parse a single YAML policy file."""
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                return

            rules_raw = data.get("rules", [])
            dept = data.get("department")  # None = global

            for r in rules_raw:
                rule = PolicyRule(
                    name=r.get("name", "unnamed"),
                    description=r.get("description", ""),
                    entity_types=r.get("entity_types", []),
                    keywords=r.get("keywords", []),
                    enforcement=EnforcementLevel(r.get("enforcement", "redact")),
                    risk_threshold=float(r.get("risk_threshold", 5.0)),
                    allowed_models=r.get("allowed_models", []),
                    applies_to_departments=r.get("departments", [dept] if dept else []),
                )

                if dept:
                    self._policies.setdefault(dept.upper(), []).append(rule)
                else:
                    self._global_rules.append(rule)

        except Exception as e:
            logger.warning(f"Policy load error for {filepath}: {e}")

    def _get_rules_for(self, department: Optional[str]) -> List[PolicyRule]:
        """Return global rules + department-specific rules merged."""
        if not self._policies and not self._global_rules:
            self.reload()
        dept_key = (department or "").upper()
        return self._global_rules + self._policies.get(dept_key, [])

    def evaluate(
        self,
        prompt: str,
        findings: List[Dict[str, Any]],
        risk_score: float,
        department: Optional[str],
        model: Optional[str] = None,
    ) -> PolicyDecision:
        """
        Evaluate a prompt + scan findings against relevant policies.
        Returns a PolicyDecision with the enforcement action.
        """
        rules = self._get_rules_for(department)
        triggered: List[str] = []
        worst_action = EnforcementLevel.WARN
        warnings: List[str] = []
        block_reason: Optional[str] = None
        model_allowed = True

        for rule in rules:
            matched = False

            # 1. Entity type match
            if rule.entity_types:
                found_types = {f.get("label", "") for f in findings}
                if found_types & set(rule.entity_types):
                    matched = True

            # 2. Keyword match
            if rule.keywords and not matched:
                for kw in rule.keywords:
                    if re.search(kw, prompt, re.IGNORECASE):
                        matched = True
                        break

            # 3. Risk threshold
            if rule.risk_threshold and risk_score >= rule.risk_threshold:
                matched = True

            if matched:
                triggered.append(rule.name)
                # Escalate to worst action
                if rule.enforcement == EnforcementLevel.BLOCK:
                    worst_action = EnforcementLevel.BLOCK
                    block_reason = f"Policy '{rule.name}' blocked: {rule.description or 'High risk content'}"
                elif rule.enforcement == EnforcementLevel.REDACT and worst_action != EnforcementLevel.BLOCK:
                    worst_action = EnforcementLevel.REDACT
                else:
                    warnings.append(f"Policy '{rule.name}' warned: {rule.description}")

                # Check model allowlist
                if rule.allowed_models and model and model not in rule.allowed_models:
                    model_allowed = False
                    warnings.append(f"Model '{model}' not in allowlist for policy '{rule.name}'")

        return PolicyDecision(
            action=worst_action,
            triggered_rules=triggered,
            block_reason=block_reason,
            warnings=warnings,
            model_allowed=model_allowed,
            policy_name=f"{department or 'GLOBAL'}_policy",
        )

    def list_policies(self) -> Dict[str, Any]:
        """Return a summary of all loaded policies (for admin dashboard)."""
        if not self._policies and not self._global_rules:
            self.reload()
        return {
            "global_rules": len(self._global_rules),
            "department_policies": {k: len(v) for k, v in self._policies.items()},
            "total_rules": len(self._global_rules) + sum(len(v) for v in self._policies.values()),
        }


# Singleton
policy_engine = PolicyEngine()
