import numpy as np
import pytest

from app.metrics import si_sdr


def test_si_sdr_is_high_for_clean_scaled_reference():
    time = np.arange(22050, dtype=np.float64) / 22050
    reference = np.sin(2 * np.pi * 440 * time)
    estimate = 0.35 * reference
    assert si_sdr(reference, estimate) > 80


def test_si_sdr_rejects_silent_reference():
    with pytest.raises(ValueError):
        si_sdr(np.zeros(1000), np.ones(1000))
