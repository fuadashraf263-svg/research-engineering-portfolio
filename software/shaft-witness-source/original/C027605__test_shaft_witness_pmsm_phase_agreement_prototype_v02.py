import unittest

import numpy as np

from shaft_witness_pmsm_phase_agreement_prototype_v02 import pmsm_phase_agreement


def synthetic_inputs(sample_rate_hz=8000):
    t_current = np.arange(4 * sample_rate_hz, dtype=np.float64) / sample_rate_hz
    t_speed = np.arange(4001, dtype=np.float64) / 1000.0
    rpm = 900.0 + 120.0 * np.sin(2.0 * np.pi * 0.3 * t_speed)
    cycles = np.zeros_like(t_speed)
    cycles[1:] = np.cumsum(0.5 * (rpm[1:] + rpm[:-1]) * np.diff(t_speed)) * 4.0 / 60.0
    phase = 2.0 * np.pi * np.interp(t_current, t_speed, cycles)
    current_1 = np.cos(phase)
    current_2 = 0.9 * np.cos(phase - 2.0 * np.pi / 3.0)
    return t_current, current_1, current_2, t_speed, rpm


def run_feature(data, **overrides):
    t, c1, c2, ts, rpm = data
    kwargs = {
        "motor_topology": "PMSM",
        "pole_pairs": 4,
        "motor_configuration_verified": True,
        "common_clock_verified": True,
        "current_sample_rate_hz": 8000.0,
        "decimation": 8,
    }
    kwargs.update(overrides)
    return pmsm_phase_agreement(t, c1, t, c2, ts, rpm, **kwargs)


class PmsmPhaseAgreementPrototypeTests(unittest.TestCase):
    def setUp(self):
        self.data = synthetic_inputs()

    def test_verified_synthetic_pmsm_returns_metric_only(self):
        result = run_feature(self.data)
        self.assertEqual(result["status"], "METRIC_ONLY")
        self.assertGreater(result["two_channel_mean_r2"], 0.99)
        self.assertFalse(result["diagnostic_claim"])
        self.assertFalse(result["actuator_or_trip_output"])

    def test_samples_after_declared_four_second_window_do_not_change_scores(self):
        t, c1, c2, ts, rpm = self.data
        extra_t = t[-1] + np.arange(1, 2001, dtype=np.float64) / 8000.0
        extended = (
            np.concatenate((t, extra_t)),
            np.concatenate((c1, np.full(extra_t.size, 1000.0))),
            np.concatenate((c2, np.full(extra_t.size, -1000.0))),
            ts,
            rpm,
        )
        original_result = run_feature(self.data)
        extended_result = run_feature(extended)
        self.assertEqual(extended_result["status"], "METRIC_ONLY")
        np.testing.assert_allclose(
            [extended_result["phase_fit_r2_by_channel"]["phase_1"],
             extended_result["phase_fit_r2_by_channel"]["phase_2"],
             extended_result["two_channel_mean_r2"]],
            [original_result["phase_fit_r2_by_channel"]["phase_1"],
             original_result["phase_fit_r2_by_channel"]["phase_2"],
             original_result["two_channel_mean_r2"]],
            rtol=0.0,
            atol=1e-14,
        )

    def test_short_stored_tail_uses_and_reports_numpy_endpoint_hold(self):
        t, c1, c2, ts, rpm = self.data
        keep = t <= 3.90
        shortened = (t[keep], c1[keep], c2[keep], ts, rpm)
        result = run_feature(shortened)
        self.assertEqual(result["status"], "METRIC_ONLY")
        self.assertEqual(result["current_grid_edge_hold_samples_before_stored_axis"], 0)
        self.assertGreater(result["current_grid_edge_hold_samples_after_stored_axis"], 0)

    def test_unverified_motor_configuration_returns_not_evaluated(self):
        result = run_feature(self.data, motor_configuration_verified=False)
        self.assertEqual(result["status"], "NOT_EVALUATED")
        self.assertIsNone(result["two_channel_mean_r2"])

    def test_unverified_common_clock_returns_not_evaluated(self):
        result = run_feature(self.data, common_clock_verified=False)
        self.assertEqual(result["status"], "NOT_EVALUATED")

    def test_non_pmsm_motor_returns_not_evaluated(self):
        result = run_feature(self.data, motor_topology="induction")
        self.assertEqual(result["status"], "NOT_EVALUATED")

    def test_current_channels_must_share_identical_axis(self):
        t, c1, c2, ts, rpm = self.data
        result = pmsm_phase_agreement(t, c1, t + 1e-6, c2, ts, rpm,
                                      motor_topology="PMSM", pole_pairs=4,
                                      motor_configuration_verified=True, common_clock_verified=True,
                                      current_sample_rate_hz=8000.0, decimation=8)
        self.assertEqual(result["status"], "NOT_EVALUATED")

    def test_nonmonotonic_or_insufficient_axes_return_not_evaluated(self):
        t, c1, c2, ts, rpm = self.data
        bad_t = t.copy()
        bad_t[10] = bad_t[9]
        bad = pmsm_phase_agreement(bad_t, c1, bad_t, c2, ts, rpm,
                                   motor_topology="PMSM", pole_pairs=4,
                                   motor_configuration_verified=True, common_clock_verified=True,
                                   current_sample_rate_hz=8000.0, decimation=8)
        self.assertEqual(bad["status"], "NOT_EVALUATED")
        short_mask = (t >= 0.3) & (t <= 3.5)
        short = pmsm_phase_agreement(t[short_mask], c1[short_mask], t[short_mask], c2[short_mask], ts, rpm,
                                     motor_topology="PMSM", pole_pairs=4,
                                     motor_configuration_verified=True, common_clock_verified=True,
                                     current_sample_rate_hz=8000.0, decimation=8)
        self.assertEqual(short["status"], "NOT_EVALUATED")


if __name__ == "__main__":
    unittest.main()
