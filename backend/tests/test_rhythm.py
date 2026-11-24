import numpy as np
import soundfile as sf

from app.rhythm import analyze_rhythm


def test_click_track_tempo_is_estimated_near_120_bpm(tmp_path):
    sample_rate = 22050
    duration = 8.0
    signal = np.zeros(int(sample_rate * duration), dtype=np.float32)
    click = np.hanning(180).astype(np.float32)
    for onset in np.arange(0.0, duration, 0.5):
        start = int(onset * sample_rate)
        signal[start:start + len(click)] += click
    audio_path = tmp_path / "120-bpm-click.wav"
    sf.write(audio_path, signal, sample_rate)

    result = analyze_rhythm(str(audio_path))

    assert result["tempo_bpm"] is not None
    assert abs(result["tempo_bpm"] - 120) < 8
    assert len(result["beats"]) >= 8
