#!/usr/bin/env python3
"""Read-only PMSM speed/current phase-agreement research prototype.

This module reports signal-fit metrics only. It does not diagnose a machine,
select a maintenance action, or command equipment.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import signal


def _not_evaluated(reason: str) -> dict[str, Any]:
    return {
        "status": "NOT_EVALUATED",
        "reason": reason,
        "phase_fit_r2_by_channel": None,
        "two_channel_mean_r2": None,
        "physical_validation": "UNVALIDATED",
        "diagnostic_claim": False,
    }


def _audit_time_axis(times: np.ndarray) -> dict[str, float]:
    indices = np.arange(times.size, dtype=np.float64)
    slope, intercept = np.polyfit(indices, times, 1)
    fitted = intercept + indices * slope
    intervals = np.diff(times)
    return {
        "linear_fit_sample_rate_hz": float(1.0 / slope),
        "median_interval_sample_rate_hz": float(1.0 / np.median(intervals)),
        "interval_cv_percent": float(100.0 * np.std(intervals) / np.mean(intervals)),
        "max_departure_from_linear_fit_ms": float(1000.0 * np.max(np.abs(times - fitted))),
        "maximum_gap_to_median_interval_ratio": float(np.max(intervals) / np.median(intervals)),
    }


def _fit_r2(values: np.ndarray, phase: np.ndarray) -> float:
    centered = values - float(np.mean(values))
    total = float(np.dot(centered, centered))
    if not np.isfinite(total) or total <= np.finfo(float).tiny:
        raise ValueError("current signal has no measurable variation")
    design = np.column_stack((np.ones(values.size), np.cos(phase), np.sin(phase)))
    coefficients, *_ = np.linalg.lstsq(design, values, rcond=None)
    residual = values - design @ coefficients
    score = 1.0 - float(np.dot(residual, residual)) / total
    return float(np.clip(score, 0.0, 1.0))


def pmsm_phase_agreement(
    current_1_times_s: np.ndarray,
    current_1: np.ndarray,
    current_2_times_s: np.ndarray,
    current_2: np.ndarray,
    speed_times_s: np.ndarray,
    speed_rpm: np.ndarray,
    *,
    motor_topology: str,
    pole_pairs: int,
    motor_configuration_verified: bool,
    common_clock_verified: bool,
    current_unit: str | None = None,
    current_sample_rate_hz: float = 64_000.0,
    decimation: int = 64,
    current_resample_window_s: tuple[float, float] = (0.0, 4.0),
    band_hz: tuple[float, float] = (20.0, 125.0),
    fit_window_s: tuple[float, float] = (0.20, 3.80),
) -> dict[str, Any]:
    """Compute one speed-integrated PMSM phase fit for two synchronous current channels.

    The two `*_verified` flags are explicit caller assertions backed by external
    evidence. The function cannot independently verify a motor nameplate or a
    common physical clock. It returns continuous R² and clock-shape context only.
    """
    if not motor_configuration_verified or motor_topology.upper() != "PMSM":
        return _not_evaluated("verified PMSM motor configuration is required")
    if not isinstance(pole_pairs, int) or pole_pairs <= 0:
        return _not_evaluated("verified positive integer pole-pair count is required")
    if not common_clock_verified:
        return _not_evaluated("common current/speed timing evidence is not verified")
    if not np.isfinite(current_sample_rate_hz) or current_sample_rate_hz <= 0 or not isinstance(decimation, int) or decimation <= 0:
        return _not_evaluated("sample rate and decimation must be finite positive values")
    low_hz, high_hz = band_hz
    start_s, end_s = fit_window_s
    resample_start_s, resample_end_s = current_resample_window_s
    analysis_rate = current_sample_rate_hz / decimation
    if not (0.0 < low_hz < high_hz < current_sample_rate_hz / 2.0):
        return _not_evaluated("analysis band must lie below current-sample Nyquist")
    if high_hz >= analysis_rate / 2.0:
        return _not_evaluated("analysis band must lie below the decimated Nyquist frequency")
    if not (np.isfinite(start_s) and np.isfinite(end_s) and start_s >= 0.0 and end_s > start_s):
        return _not_evaluated("fit window must be finite, positive, and ordered")
    if not (np.isfinite(resample_start_s) and np.isfinite(resample_end_s) and resample_end_s > resample_start_s):
        return _not_evaluated("current resampling window must be finite and ordered")
    resample_start_index = int(round(resample_start_s * current_sample_rate_hz))
    resample_end_index = int(round(resample_end_s * current_sample_rate_hz))
    if resample_end_index <= resample_start_index or not np.isclose(
        (resample_end_s - resample_start_s) * current_sample_rate_hz,
        resample_end_index - resample_start_index,
        rtol=0.0, atol=1e-8,
    ):
        return _not_evaluated("resampling window must span an integer number of current samples")

    t1 = np.asarray(current_1_times_s, dtype=np.float64)
    t2 = np.asarray(current_2_times_s, dtype=np.float64)
    y1 = np.asarray(current_1, dtype=np.float64)
    y2 = np.asarray(current_2, dtype=np.float64)
    ts = np.asarray(speed_times_s, dtype=np.float64)
    ns = np.asarray(speed_rpm, dtype=np.float64)
    if any(a.ndim != 1 for a in (t1, t2, y1, y2, ts, ns)):
        return _not_evaluated("all channels must be one-dimensional arrays")
    if t1.shape != y1.shape or t2.shape != y2.shape or ts.shape != ns.shape:
        return _not_evaluated("each channel time axis must match its value array")
    if t1.size < 8 or t2.size < 8 or ts.size < 2:
        return _not_evaluated("insufficient samples")
    if not all(np.all(np.isfinite(a)) for a in (t1, t2, y1, y2, ts, ns)):
        return _not_evaluated("timestamps and channel values must be finite")
    if np.any(np.diff(t1) <= 0.0) or np.any(np.diff(t2) <= 0.0) or np.any(np.diff(ts) <= 0.0):
        return _not_evaluated("all stored time axes must increase strictly")
    if t1.shape != t2.shape or not np.array_equal(t1, t2):
        return _not_evaluated("two phase-current channels must share an identical stored time axis")

    common_start = max(float(t1[0]), float(ts[0]), start_s)
    common_end = min(float(t1[-1]), float(ts[-1]), end_s)
    if common_end <= common_start or common_start > start_s or common_end < end_s:
        return _not_evaluated("current and speed channels do not cover the complete fit window")
    expected_decimated_count = int(np.floor((end_s - start_s) * analysis_rate))
    if expected_decimated_count < 8:
        return _not_evaluated("fit window contains too few decimated samples")

    # Keep filter edge conditions reproducible: filter the declared current window,
    # not arbitrary extra stored samples beyond the source recipe's interval.
    uniform = np.arange(resample_start_index, resample_end_index, dtype=np.float64) / current_sample_rate_hz
    if uniform.size == 0 or uniform[0] != resample_start_s or uniform[-1] < resample_end_s - 1.0 / current_sample_rate_hz:
        return _not_evaluated("failed to create the declared nominal current grid")
    held_before_start = int(np.count_nonzero(uniform < t1[0]))
    held_after_end = int(np.count_nonzero(uniform > t1[-1]))
    try:
        uniform_1 = np.interp(uniform, t1, y1)
        uniform_2 = np.interp(uniform, t2, y2)
        sos = signal.butter(4, [low_hz, high_hz], btype="bandpass", fs=current_sample_rate_hz, output="sos")
        filtered_1 = signal.sosfiltfilt(sos, uniform_1)[::decimation]
        filtered_2 = signal.sosfiltfilt(sos, uniform_2)[::decimation]
        t_analysis = uniform[::decimation]
        score_mask = (t_analysis >= start_s) & (t_analysis <= end_s)
        query_times = t_analysis[score_mask]
        if query_times.size < 8:
            return _not_evaluated("fit window contains too few decimated samples")
        cycles = np.empty_like(ts)
        cycles[0] = 0.0
        cycles[1:] = np.cumsum(0.5 * (ns[1:] + ns[:-1]) * np.diff(ts)) * pole_pairs / 60.0
        phase = 2.0 * np.pi * np.interp(query_times, ts, cycles)
        score_1 = _fit_r2(filtered_1[score_mask], phase)
        score_2 = _fit_r2(filtered_2[score_mask], phase)
        audit_1 = _audit_time_axis(t1)
        audit_speed = _audit_time_axis(ts)
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
        return _not_evaluated(f"analysis failed: {exc}")

    return {
        "status": "METRIC_ONLY",
        "reason": None,
        "phase_fit_r2_by_channel": {"phase_1": score_1, "phase_2": score_2},
        "two_channel_mean_r2": float((score_1 + score_2) / 2.0),
        "electrical_angle_model": f"theta_e = 2*pi*integral({pole_pairs} * speed_rpm / 60 dt)",
        "pole_pairs": pole_pairs,
        "band_hz": [float(low_hz), float(high_hz)],
        "fit_window_s": [float(start_s), float(end_s)],
        "relative_current_rms_by_channel": {
            "phase_1": float(np.sqrt(np.mean(filtered_1[score_mask] ** 2))),
            "phase_2": float(np.sqrt(np.mean(filtered_2[score_mask] ** 2))),
        },
        "current_unit_metadata": current_unit or "unspecified",
        "current_timebase_audit": audit_1,
        "current_grid_edge_hold_samples_before_stored_axis": held_before_start,
        "current_grid_edge_hold_samples_after_stored_axis": held_after_end,
        "speed_timebase_audit": audit_speed,
        "maximum_gap_is_context_only": True,
        "absolute_cross_channel_offset_is_not_proven_by_r2": True,
        "common_clock_verified_by_caller": True,
        "physical_validation": "UNVALIDATED",
        "diagnostic_claim": False,
        "actuator_or_trip_output": False,
    }
