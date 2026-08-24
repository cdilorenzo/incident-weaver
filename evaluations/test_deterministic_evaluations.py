"""Runs the curated Slice 009 evaluation cases as part of the deterministic test suite.

These are probabilistic-AI-quality-style evaluations executed against a fake model
(TestModel); no live LLM credentials are used or required. See README.md.
"""

from __future__ import annotations

import pytest

from cases import EVALUATION_CASES
from runner import EvaluationCase, format_report, run_case


@pytest.mark.parametrize("case", EVALUATION_CASES, ids=lambda case: case.case_id)
def test_evaluation_case_meets_its_expected_properties(case: EvaluationCase) -> None:
    result = run_case(case)

    assert result.passed, format_report([result])
