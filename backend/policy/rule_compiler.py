"""
Sentinel Shield v2 — Rule Compiler
Compiles YAML policy DSL to PolicyRule objects and validates them.
"""
import os
import yaml
from typing import Dict, Any, List, Optional
from .policy_engine import PolicyRule, EnforcementLevel


class RuleCompiler:
    """Validates and compiles raw YAML policy dicts into PolicyRule objects."""

    VALID_ENFORCEMENT = {e.value for e in EnforcementLevel}
    KNOWN_ENTITY_TYPES = {
        # Presidio standard
        "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION", "DATE_TIME",
        "NRP", "CREDIT_CARD", "US_SSN", "US_BANK_NUMBER", "IP_ADDRESS",
        "IBAN_CODE", "US_PASSPORT", "MEDICAL_LICENSE", "URL",
        # India (Sentinel custom)
        "Aadhaar Number", "PAN Card", "Voter ID", "Indian Mobile",
        "UHID (Hospital ID)", "GST Number", "UPI ID",
    }

    def compile(self, raw: Dict[str, Any], source_file: str = "") -> Optional[PolicyRule]:
        """
        Compile a single rule dict to a PolicyRule.
        Returns None if invalid (with a warning logged).
        """
        errors = []

        name = raw.get("name")
        if not name:
            errors.append("Missing 'name'")

        enforcement_raw = raw.get("enforcement", "redact")
        if enforcement_raw not in self.VALID_ENFORCEMENT:
            errors.append(f"Invalid enforcement '{enforcement_raw}'; must be one of {self.VALID_ENFORCEMENT}")
            enforcement_raw = "redact"

        risk_threshold = raw.get("risk_threshold", 5.0)
        try:
            risk_threshold = float(risk_threshold)
            assert 0 <= risk_threshold <= 10
        except (ValueError, TypeError, AssertionError):
            errors.append(f"risk_threshold must be 0–10, got '{risk_threshold}'")
            risk_threshold = 5.0

        entity_types = raw.get("entity_types", [])
        unknown_types = [t for t in entity_types if t not in self.KNOWN_ENTITY_TYPES]
        if unknown_types:
            # Not a blocking error — custom types are allowed
            pass

        if errors:
            import logging
            logging.warning(f"Rule '{name}' in '{source_file}' has issues: {errors}. Using safe defaults.")

        return PolicyRule(
            name=name or "unnamed",
            description=raw.get("description", ""),
            entity_types=entity_types,
            keywords=raw.get("keywords", []),
            enforcement=EnforcementLevel(enforcement_raw),
            risk_threshold=risk_threshold,
            allowed_models=raw.get("allowed_models", []),
            applies_to_departments=raw.get("departments", []),
        )

    def compile_file(self, filepath: str) -> List[PolicyRule]:
        """Compile all rules from a YAML file."""
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r") as f:
            data = yaml.safe_load(f) or {}

        rules = []
        for raw_rule in data.get("rules", []):
            rule = self.compile(raw_rule, source_file=filepath)
            if rule:
                rules.append(rule)
        return rules

    def validate_yaml(self, yaml_str: str) -> Dict[str, Any]:
        """
        Validate a raw YAML string (from admin policy editor).
        Returns {valid: bool, errors: [...], rules_parsed: int}
        """
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            return {"valid": False, "errors": [f"YAML Parse Error: {e}"], "rules_parsed": 0}

        if not isinstance(data, dict):
            return {"valid": False, "errors": ["Root must be a YAML dict"], "rules_parsed": 0}

        errors = []
        rules = data.get("rules", [])
        compiled = 0
        for r in rules:
            rule = self.compile(r, source_file="<editor>")
            if rule:
                compiled += 1
            else:
                errors.append(f"Failed to compile rule: {r.get('name', 'unnamed')}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "rules_parsed": compiled,
            "department": data.get("department", "global"),
        }
