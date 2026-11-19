"""Conformance for exact CRFCE research-input retention and geometry binding."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

import crfce_engine_design as engine
import crfce_paper as paper
import crfce_research as research


class ResolvedTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = research.deep_research()
        cls.two_pair = research.deep_research({
            "pole_pairs": 2.0,
            "rpm": 3000.0,
            "rotor_r_m": 0.07,
            "L_stack_m": 0.2,
            "electric_loading_peak_A_per_m": 90000.0,
            "spatial_phase_factor": 0.4,
            "rotor_SF_min": 1.7,
        })

    def test_exact_resolved_values_and_origins_are_retained(self):
        resolved = self.reference["resolved_inputs"]
        self.assertEqual(self.reference["schema"], "engineai.crfce_research.v2")
        self.assertEqual(set(resolved), set(research.REFERENCE))
        for name, value in research.REFERENCE.items():
            self.assertEqual(resolved[name]["value"], value)
            self.assertEqual(resolved[name]["provenance"], "REFERENCE_ASSUMPTION")
            self.assertEqual(resolved[name]["provenance"],
                             self.reference["input_provenance"][name])

    def test_user_override_value_and_unverified_origin_are_retained(self):
        resolved = self.two_pair["resolved_inputs"]
        self.assertEqual(resolved["pole_pairs"], {
            "value": 2.0, "provenance": "USER_SUPPLIED_UNVERIFIED"})
        self.assertEqual(resolved["rpm"], {
            "value": 3000.0, "provenance": "USER_SUPPLIED_UNVERIFIED"})
        self.assertEqual(resolved["B_T"]["provenance"], "REFERENCE_ASSUMPTION")

    def test_reference_geometry_derives_six_poles_from_three_pairs(self):
        sizing = engine.size_from_operating_point(self.reference)
        self.assertEqual(sizing["spec_params"]["pole_count"], 6)
        self.assertEqual(sizing["spec_params"]["rotor_outer_diameter"], 120.0)
        self.assertEqual(sizing["spec_params"]["stack_length"], 120.0)
        self.assertEqual(sizing["topology_binding"], {
            "pole_pairs": 3,
            "pole_pairs_provenance": "REFERENCE_ASSUMPTION",
            "pole_count": 6,
            "convention": "pole_count = 2 x pole_pairs"})
        self.assertIn("2 x 3 pole pairs", sizing["origins"]["pole_count"])

    def test_override_geometry_tracks_the_same_two_pair_dossier(self):
        sizing = engine.size_from_operating_point(self.two_pair)
        self.assertEqual(sizing["spec_params"]["pole_count"], 4)
        self.assertEqual(sizing["spec_params"]["rotor_outer_diameter"], 140.0)
        self.assertEqual(sizing["spec_params"]["stack_length"], 200.0)
        self.assertEqual(sizing["topology_binding"]["pole_pairs_provenance"],
                         "USER_SUPPLIED_UNVERIFIED")
        checks = engine.as_designed_checks(
            sizing, {"spec": sizing["spec_params"]})
        self.assertEqual(checks["electric_loading_peak_A_per_m"], 90000.0)
        self.assertEqual(checks["spatial_phase_factor"], 0.4)
        self.assertEqual(checks["rotor_SF_min"], 1.7)
        self.assertIn("rotor_meets_required_SF", checks)

    def test_methods_text_contains_every_resolved_input_value_and_provenance(self):
        sizing = engine.size_from_operating_point(self.two_pair)
        dossier = {
            "reconciliation": {"enhancement_assumed_Kt": 2.5,
                               "enhancement_peak_power_kW": 0.0,
                               "governed_feasible_power_kW": 0.0},
            "adversarial_battery": {"caught": 0, "attacks": 0},
            "cryogenic_thermal": {},
            "optimization_sweep": {"feasible_points": 0, "grid_points_evaluated": 0},
        }
        passport = {
            "schema": "test", "maturity_level": "UNASSESSED",
            "physical_validation": "NOT_DEMONSTRATED", "operating_point": {},
            "as_designed_checks": {"rotor_SF_min": 1.7}, "manufacturability": {
                "min_feature_mm": 0.5, "min_wall_required_mm": 0.3,
                "features_mm": {"slot_bridge_mm": 0.5},
                "alt_metal_AM": {"min_wall_mm": 1.0}},
            "bom": {"total_mass_kg": 0.0, "rows": []}, "sizing": sizing,
            "governed_receipt_count": 0, "governed_receipts": [],
            "not_demonstrated": [], "boundary": "test-only synthetic fixture",
        }
        text = paper._markdown(passport, dossier, {
            "cross": "cross.png", "burden": "burden.png", "reqs": "reqs.png"})
        self.assertIn("not inferred from the optimized operating point", text)
        self.assertIn("| pole_pairs | 2 | pairs | USER_SUPPLIED_UNVERIFIED |", text)
        self.assertIn("| rotor_r_m | 0.07 | m | USER_SUPPLIED_UNVERIFIED |", text)
        self.assertIn("| electric_loading_peak_A_per_m | 90000 | A/m | USER_SUPPLIED_UNVERIFIED |", text)
        self.assertIn("not a local-stress FEA measurement", text)
        self.assertIn("not a validated CRFCE rotor design", text)
        self.assertIn("compared with the 1.7 minimum target", text)
        self.assertIn("do not constitute a validated FEA or physical test", text)
        self.assertNotIn("measured from the generated geometry", text)
        self.assertNotIn("on the built geometry", text)
        self.assertNotIn("Every quantity in this paper is produced", text)
        self.assertNotIn("Every number in the paper is copied", paper.__doc__)
        self.assertIn("Every resolved study input is printed", paper.__doc__)
        self.assertEqual(text.count("| REFERENCE_ASSUMPTION |") +
                         text.count("| USER_SUPPLIED_UNVERIFIED |"),
                         len(research.REFERENCE))
        html = paper._html(text, Path.cwd())
        self.assertIn("<th>Resolved value</th>", html)
        self.assertIn("<td>90000</td>", html)

    def test_paper_refuses_incomplete_research_input_snapshot(self):
        with self.assertRaisesRegex(ValueError, "exact resolved inputs"):
            paper._resolved_research_inputs_markdown({"research_inputs": {"schema": "v1"}})

    def test_resolved_user_overrides_recheck_cross_field_invariants(self):
        malformed = deepcopy(self.two_pair)
        malformed["resolved_inputs"]["support_r_inner_m"]["value"] = 0.04
        malformed["resolved_inputs"]["support_r_inner_m"]["provenance"] = "USER_SUPPLIED_UNVERIFIED"
        malformed["resolved_inputs"]["support_r_outer_m"]["value"] = 0.03
        malformed["resolved_inputs"]["support_r_outer_m"]["provenance"] = "USER_SUPPLIED_UNVERIFIED"
        with self.assertRaisesRegex(ValueError, "support_r_inner_m must be smaller"):
            engine.size_from_operating_point(malformed)

    def test_independent_conflicting_pole_count_is_refused(self):
        with self.assertRaisesRegex(ValueError, "must match"):
            engine.size_from_operating_point(self.reference, pole_count=4)

    def test_missing_or_unknown_topology_provenance_is_refused(self):
        missing = deepcopy(self.reference)
        del missing["resolved_inputs"]
        with self.assertRaisesRegex(ValueError, "exact input set"):
            engine.size_from_operating_point(missing)

        forged = deepcopy(self.reference)
        forged["resolved_inputs"]["pole_pairs"]["provenance"] = "VERIFIED_MEASURED"
        with self.assertRaisesRegex(ValueError, "provenance is unrecognized"):
            engine.size_from_operating_point(forged)


if __name__ == "__main__":
    unittest.main(verbosity=2)
