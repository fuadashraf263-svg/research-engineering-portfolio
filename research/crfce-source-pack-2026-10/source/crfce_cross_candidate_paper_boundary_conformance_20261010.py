"""R362 contract: generated CRFCE paper keeps machine candidates distinct."""
from __future__ import annotations

import inspect
import unittest

import crfce_paper as paper


class CrossCandidatePaperBoundaryTests(unittest.TestCase):
    def test_boundary_names_each_conflicting_candidate_without_conflation(self):
        text = paper._candidate_identity_boundary(self._passport())
        for expected in (
            "R7 CRFCE package-paper/STEP documentary baseline: 24 stator slots / 4 rotor poles",
            "manual visual transcription, unverified, and not applied to the current analysis",
            "This paper's CRFCE analysis parameterization: 24 stator slots / 6 rotor poles",
            "3 pole pairs; REFERENCE_ASSUMPTION",
            "R5-C is a separate plan: three-phase, 48 slots / 8 poles, permanent-magnet machine",
            "retained 8-slot / 6-pole SRM results are surrogate-only",
            "not interchangeable",
            "does not establish the released revision or as-built machine",
        ):
            self.assertIn(expected, text)

    def test_generated_paper_calls_the_candidate_boundary_helper(self):
        source = inspect.getsource(paper._markdown)
        self.assertIn("_candidate_identity_boundary(passport)", source)

    def test_analysis_parameterization_is_read_from_passport_not_hard_coded(self):
        passport = self._passport()
        passport["sizing"]["spec_params"].update({"slot_count": 48, "pole_count": 8})
        passport["sizing"]["topology_binding"].update({
            "pole_pairs": 4,
            "pole_pairs_provenance": "USER_SUPPLIED_UNVERIFIED",
        })
        text = paper._candidate_identity_boundary(passport)
        self.assertIn(
            "This paper's CRFCE analysis parameterization: 48 stator slots / 8 rotor poles "
            "(4 pole pairs; USER_SUPPLIED_UNVERIFIED)",
            text,
        )
        self.assertIn("documentary baseline: 24 stator slots / 4 rotor poles", text)

    @staticmethod
    def _passport():
        return {
            "sizing": {
                "spec_params": {"slot_count": 24, "pole_count": 6},
                "topology_binding": {
                    "pole_pairs": 3,
                    "pole_pairs_provenance": "REFERENCE_ASSUMPTION",
                },
            },
        }


if __name__ == "__main__":
    unittest.main(verbosity=2)
