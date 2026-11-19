"""Source-only checks that CRFCE reference outputs do not overstate validation."""
from __future__ import annotations

import unittest
from pathlib import Path

import crfce_engine_design as design
import crfce_paper as paper


ROOT = Path(__file__).resolve().parent
DESIGN_SOURCE = (ROOT / "crfce_engine_design.py").read_text(encoding="utf-8")
PAPER_SOURCE = (ROOT / "crfce_paper.py").read_text(encoding="utf-8")


class CrfceClaimBoundaryTests(unittest.TestCase):
    def test_module_description_is_candidate_not_lab_producible_claim(self):
        self.assertIn("unvalidated CRFCE reference-design candidate", design.__doc__)
        self.assertNotIn("real, lab-producible", design.__doc__)

    def test_candidate_scope_explicitly_separates_analysis_geometry_and_physical_status(self):
        scope = design.candidate_evidence_scope()
        self.assertEqual(scope["geometry"], "PARAMETRIC_CANDIDATE_NOT_RELEASED_OR_AS_BUILT")
        self.assertEqual(scope["torque"], "ANALYTICAL_SHEAR_ESTIMATE_NOT_FIELD_SOLVE")
        self.assertEqual(scope["rotor"], "IPM_STYLE_GEOMETRIC_PROXY_NOT_RELUCTANCE_ROTOR")
        self.assertEqual(scope["manufacturing"], "PRELIMINARY_SCREEN_NOT_QUALIFICATION")
        self.assertEqual(scope["physical_validation"], "NOT_DEMONSTRATED")
        self.assertIs(scope["release_authorized"], False)

    def test_paper_scope_guard_accepts_exact_candidate_scope(self):
        scope = design.candidate_evidence_scope()
        self.assertEqual(paper._require_candidate_scope({"reference_candidate_scope": scope}), scope)

    def test_paper_scope_guard_refuses_missing_or_promoted_scope(self):
        with self.assertRaises(ValueError):
            paper._require_candidate_scope({})
        promoted = design.candidate_evidence_scope()
        promoted["release_authorized"] = True
        with self.assertRaises(ValueError):
            paper._require_candidate_scope({"reference_candidate_scope": promoted})

    def test_passport_and_chat_use_candidate_scope_and_no_asbuilt_notch_key(self):
        self.assertIn('"reference_candidate_scope": candidate_evidence_scope()', DESIGN_SOURCE)
        self.assertIn("CRFCE virtual reference candidate study", DESIGN_SOURCE)
        self.assertIn('"rotor_bridge_Kt_candidate"', DESIGN_SOURCE)
        self.assertNotIn("rotor_bridge_Kt_asbuilt", DESIGN_SOURCE)
        self.assertNotIn("on the as-built geometry with stated electric loading", DESIGN_SOURCE)
        self.assertNotIn("Use the as-built rotor pocket depth", DESIGN_SOURCE)

    def test_requirements_matrix_calls_torque_and_geometry_checks_candidate_scoped(self):
        self.assertIn("reference-case analytical torque estimate", DESIGN_SOURCE)
        self.assertIn("candidate solid dimensions match parametric specification", DESIGN_SOURCE)
        self.assertNotIn("em.machine_torque on the as-built geometry", DESIGN_SOURCE)

    def test_generated_paper_prints_candidate_boundary(self):
        self.assertIn('passport.get("reference_candidate_scope")', PAPER_SOURCE)
        self.assertIn("not bound to released/as-built hardware", PAPER_SOURCE)
        self.assertNotIn("rotor_bridge_Kt_asbuilt", PAPER_SOURCE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
