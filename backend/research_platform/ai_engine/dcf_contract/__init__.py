"""
ai_engine/dcf_contract
───────────────────────
Contract layer between research_platform and the DCF model.

Quick usage:
    from ai_engine.dcf_contract import run_dcf, read_dcf_output, write_assumptions

    # Run DCF for a session
    result = run_dcf(session, model_version="base")

    # Write assumptions manually
    path = write_assumptions(session, model_version="analyst")

    # Read existing DCF output
    data = read_dcf_output(session.session_dir)
"""

from ai_engine.dcf_contract.writer import (
    write_assumptions,
    write_base_assumptions,
    write_analyst_assumptions,
    write_data_driven_assumptions,
)
from ai_engine.dcf_contract.reader import (
    read_dcf_output,
    get_valuation_summary,
    get_scenarios_for_platform,
)
from ai_engine.dcf_contract.runner import (
    run_dcf,
    run_all_versions,
    refresh_from_output,
)
from ai_engine.dcf_contract.schema import (
    empty_assumptions,
    empty_output,
    validate_assumptions,
    validate_output,
    SCHEMA_VERSION,
)

__all__ = [
    "run_dcf", "run_all_versions", "refresh_from_output",
    "write_assumptions", "write_base_assumptions",
    "write_analyst_assumptions", "write_data_driven_assumptions",
    "read_dcf_output", "get_valuation_summary", "get_scenarios_for_platform",
    "empty_assumptions", "empty_output",
    "validate_assumptions", "validate_output",
    "SCHEMA_VERSION",
]
