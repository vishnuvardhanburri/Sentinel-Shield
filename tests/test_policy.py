"""
Sovereign Shield v2 — Policy Engine Tests
Tests YAML policy loading, rule compilation, and enforcement decisions.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

import pytest
import yaml
import tempfile
from policy.policy_engine import PolicyEngine, EnforcementLevel
from policy.rule_compiler import RuleCompiler


SAMPLE_POLICY_YAML = """
department: TEST_DEPT
policy_name: Test Policy

rules:
  - name: Block PHI
    description: Block direct patient name in prompts
    keywords:
      - "patient name"
      - "sarah johnson"
    enforcement: block
    risk_threshold: 6.0

  - name: Redact SSN
    description: Redact SSN entity types
    entity_types:
      - "PII (SSN)"
      - US_SSN
    enforcement: redact
    risk_threshold: 3.0

  - name: Warn Medical Terms
    description: Warn on clinical language
    keywords:
      - diagnosis
      - prescription
    enforcement: warn
    risk_threshold: 2.0
"""

INVALID_POLICY_YAML = """
rules:
  - name: Bad Rule
    enforcement: obliterate
    risk_threshold: 999
"""


class TestRuleCompiler:
    @pytest.fixture
    def compiler(self):
        return RuleCompiler()

    def test_valid_yaml_compiles(self, compiler):
        result = compiler.validate_yaml(SAMPLE_POLICY_YAML)
        assert result["valid"] is True
        assert result["rules_parsed"] == 3

    def test_invalid_enforcement_level(self, compiler):
        result = compiler.validate_yaml(INVALID_POLICY_YAML)
        # Should not crash; should report errors or use safe defaults
        assert isinstance(result, dict)

    def test_department_extracted(self, compiler):
        result = compiler.validate_yaml(SAMPLE_POLICY_YAML)
        assert result["department"] == "TEST_DEPT"

    def test_bad_yaml_syntax(self, compiler):
        bad_yaml = "rules:\n  - name: [unclosed"
        result = compiler.validate_yaml(bad_yaml)
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_compile_from_file(self, compiler, tmp_path):
        policy_file = tmp_path / "test_policy.yaml"
        policy_file.write_text(SAMPLE_POLICY_YAML)
        rules = compiler.compile_file(str(policy_file))
        assert len(rules) == 3


class TestPolicyEngine:
    @pytest.fixture
    def engine(self, tmp_path):
        """Create a PolicyEngine pointed at a temp presets directory."""
        # Write a test policy
        policy_file = tmp_path / "test_policy.yaml"
        policy_file.write_text(SAMPLE_POLICY_YAML)
        eng = PolicyEngine.__new__(PolicyEngine)
        eng._policies = {}
        eng._global_rules = []
        eng._last_loaded = 0
        eng._load_file(str(policy_file))
        return eng

    def test_block_on_keyword(self, engine):
        decision = engine.evaluate(
            prompt="What is the patient name Sarah Johnson?",
            findings=[],
            risk_score=2.0,
            department="TEST_DEPT",
        )
        assert decision.action == EnforcementLevel.BLOCK
        assert len(decision.triggered_rules) > 0

    def test_redact_on_entity_type(self, engine):
        decision = engine.evaluate(
            prompt="Some text",
            findings=[{"label": "PII (SSN)", "type": "PII"}],
            risk_score=3.5,
            department="TEST_DEPT",
        )
        assert decision.action in (EnforcementLevel.REDACT, EnforcementLevel.BLOCK)

    def test_warn_on_clinical_keyword(self, engine):
        decision = engine.evaluate(
            prompt="What is the diagnosis for the case?",
            findings=[],
            risk_score=2.5,
            department="TEST_DEPT",
        )
        # Should warn (not block) — below block threshold
        assert decision.action == EnforcementLevel.WARN

    def test_clean_prompt_no_trigger(self, engine):
        decision = engine.evaluate(
            prompt="What is our Q3 revenue?",
            findings=[],
            risk_score=0.0,
            department="TEST_DEPT",
        )
        # No rules triggered
        assert len(decision.triggered_rules) == 0

    def test_block_overrides_redact(self, engine):
        """When both BLOCK and REDACT rules match, BLOCK must win."""
        decision = engine.evaluate(
            prompt="patient name Sarah Johnson has SSN",
            findings=[{"label": "PII (SSN)", "type": "PII"}],
            risk_score=8.0,
            department="TEST_DEPT",
        )
        assert decision.action == EnforcementLevel.BLOCK

    def test_list_policies(self, engine):
        summary = engine.list_policies()
        assert isinstance(summary, dict)
        assert "total_rules" in summary
