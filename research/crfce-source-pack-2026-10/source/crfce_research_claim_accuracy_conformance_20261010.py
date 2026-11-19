"""Guard CRFCE notch-factor wording and provenance against CAD/FEA overclaims."""
from __future__ import annotations

import contextlib
import io
import unittest

import crfce_research as research


class NotchClaimAccuracyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            cls.report = research.deep_research()
            cls.reply = research.chat_answer()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            research._print(cls.report)
        cls.cli = out.getvalue().lower()

    def test_module_summary_does_not_claim_real_slot_geometry(self):
        summary = " ".join((research.__doc__ or "").lower().split())
        self.assertIn("analytic inglis", summary)
        self.assertIn("scalar depth/radius", summary)
        self.assertNotIn("on the real slot-root geometry", summary)

    def test_notch_factor_records_scalar_model_and_unbound_geometry(self):
        model = self.report["rotor_structural"]["tooth_root_notch_model_basis"]
        self.assertEqual(model["capability"], "mechanics.stress_concentration.notch")
        self.assertEqual(model["standing"], "PARAMETERIZED_NOTCH_MODEL_NOT_CAD_DERIVED")
        self.assertEqual(model["geometry_binding"], "NONE")
        self.assertIsNone(model["cad_geometry_sha256"])
        self.assertEqual(model["fea_status"], "NOT_PERFORMED")
        self.assertEqual(model["dimensions"]["depth_m"], {
            "value": research.REFERENCE["slot_root_depth_m"],
            "provenance": "REFERENCE_ASSUMPTION",
        })
        self.assertEqual(model["dimensions"]["root_radius_m"], {
            "value": research.REFERENCE["slot_root_radius_m"],
            "provenance": "REFERENCE_ASSUMPTION",
        })

    def test_unverified_user_dimensions_keep_their_provenance(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = research.deep_research({
                "slot_root_depth_m": 0.004,
                "slot_root_radius_m": 0.0007,
            })
        basis = result["rotor_structural"]["tooth_root_notch_model_basis"]
        self.assertEqual(basis["dimensions"]["depth_m"], {
            "value": 0.004, "provenance": "USER_SUPPLIED_UNVERIFIED"})
        self.assertEqual(basis["dimensions"]["root_radius_m"], {
            "value": 0.0007, "provenance": "USER_SUPPLIED_UNVERIFIED"})
        self.assertEqual(result["physical_validation"], "NOT_DEMONSTRATED")
        self.assertFalse(result["release_authorized"])

    def test_chat_copy_disclaims_cad_and_local_fea_measurement(self):
        answer = self.reply["answer"].lower()
        self.assertIn("analytic notch model", answer)
        self.assertIn("not cad-derived", answer)
        self.assertIn("not a local-stress fea measurement", answer)
        self.assertNotIn("kt from the slot geometry", answer)

    def test_cli_copy_disclaims_cad_derivation(self):
        self.assertIn("not cad-derived", self.cli)
        self.assertIn("not a local-stress fea measurement", self.cli)
        self.assertNotIn("governed from geometry", self.cli)

    def test_residual_unknowns_name_missing_geometry_binding(self):
        residual = " ".join(self.report["residual_unknowns"]).lower()
        self.assertIn("cad", residual)
        self.assertIn("not bound", residual)
        self.assertIn("local fea", residual)


if __name__ == "__main__":
    unittest.main(verbosity=2)
