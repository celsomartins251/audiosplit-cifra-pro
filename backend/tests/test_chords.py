import numpy as np

from app import chord_recognition as chords


def test_sustained_c_major_is_returned_as_one_non_overlapping_event(monkeypatch):
    sample_rate = 22050
    duration = 4.0
    audio = np.ones(int(sample_rate * duration), dtype=np.float32)
    chroma = np.zeros((12, 180), dtype=np.float32)
    chroma[[0, 4, 7], :] = 1.0

    monkeypatch.setattr(chords.librosa, "load", lambda *args, **kwargs: (audio, sample_rate))
    monkeypatch.setattr(
        chords.librosa.feature,
        "chroma_cqt",
        lambda **kwargs: chroma,
    )

    events = chords.recognize_chords("synthetic.wav")

    assert len(events) == 1
    assert events[0]["label"] == "C"
    assert events[0]["start"] == 0.0
    assert events[0]["end"] <= duration
    assert events[0]["end"] - events[0]["start"] >= 0.35
    assert 0.0 <= events[0]["confidence"] <= 1.0


def test_silence_is_not_forced_into_a_chord(monkeypatch):
    sample_rate = 22050
    audio = np.zeros(sample_rate * 2, dtype=np.float32)
    chroma = np.zeros((12, 100), dtype=np.float32)

    monkeypatch.setattr(chords.librosa, "load", lambda *args, **kwargs: (audio, sample_rate))
    monkeypatch.setattr(
        chords.librosa.feature,
        "chroma_cqt",
        lambda **kwargs: chroma,
    )

    assert chords.recognize_chords("silence.wav") == []
