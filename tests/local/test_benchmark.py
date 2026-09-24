import pytest

from benchmark import amdahl_speedup, estimate_parallel_fraction


def test_amdahl_fully_parallel_scales_linearly():
    assert amdahl_speedup(1.0, 4) == pytest.approx(4.0)


def test_amdahl_fully_serial_has_no_gain():
    assert amdahl_speedup(0.0, 8) == pytest.approx(1.0)


def test_amdahl_known_value():
    # p = 0.9, n = 4  =>  1 / (0.1 + 0.225)
    assert amdahl_speedup(0.9, 4) == pytest.approx(1 / 0.325)


@pytest.mark.parametrize("p", [0.0, 0.5, 0.9, 1.0])
def test_estimate_inverts_amdahl(p):
    workers = 4
    par_time = 10.0 / amdahl_speedup(p, workers)
    assert estimate_parallel_fraction(10.0, par_time, workers) == pytest.approx(p)


def test_estimate_clamps_to_valid_range():
    assert estimate_parallel_fraction(10.0, 20.0, 4) == 0.0  # paralelo mais lento
    assert estimate_parallel_fraction(10.0, 1.0, 4) == 1.0   # superlinear


@pytest.mark.parametrize("seq, par, workers", [(10.0, 5.0, 1), (10.0, 0.0, 4), (0.0, 5.0, 4)])
def test_estimate_degenerate_inputs(seq, par, workers):
    assert estimate_parallel_fraction(seq, par, workers) == 0.0
