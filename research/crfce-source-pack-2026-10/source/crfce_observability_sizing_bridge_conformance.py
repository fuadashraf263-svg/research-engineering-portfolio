"""Verify the observability reference matches CRFCE's pure sizing binding."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

import crfce_engine_design
import crfce_research


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "engineai-completion" / "run_torque_observability_campaign_20261008.py"
SPEC = importlib.util.spec_from_file_location("torque_observability_campaign", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CAMPAIGN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAMPAIGN)


class CRFCEObservabilitySizingBridgeTests(unittest.TestCase):
    def test_reference_candidate_matches_actual_sizing_topology_binding(self):
        dossier = {
            "schema": crfce_engine_design.RESEARCH_SCHEMA,
            "resolved_inputs": {
                name: {"value": value, "provenance": "REFERENCE_ASSUMPTION"}
                for name, value in crfce_research.REFERENCE.items()
            },
            "headline": {"governed_feasible_point": None},
        }
        design = crfce_engine_design.size_from_operating_point(dossier)
        reference = next(
            row for row in CAMPAIGN.source_topologies()
            if row["topology_id"] == "CRFCE_RESEARCH_REFERENCE"
        )
        self.assertEqual(reference["slots"], design["spec_params"]["slot_count"])
        self.assertEqual(reference["poles"], design["spec_params"]["pole_count"])
        self.assertEqual(reference["pole_pairs"], design["topology_binding"]["pole_pairs"])
        self.assertEqual(reference["poles"], 2 * reference["pole_pairs"])
        self.assertEqual(
            design["topology_binding"]["convention"],
            "pole_count = 2 x pole_pairs",
        )
        self.assertEqual(
            design["origins"]["pole_count"].split(" from research dossier", 1)[0],
            f"DERIVED as 2 x {reference['pole_pairs']} pole pairs",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
