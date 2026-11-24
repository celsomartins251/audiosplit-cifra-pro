import numpy as np
import soundfile as sf

from app.chord_recognition import recognize_chords


def _tone_chord(frequencies, seconds=3.0, sample_rate=22050):
    time = np.arange(int(sample_rate * seconds), dtype=np.float32) / sample_rate
    signal = sum(0.25 * np.sin(2 * np.pi * frequency * time) for frequency in frequencies)
    return signal.astype(np.float32)


def test_c_major_control_is_recognized(tmp_path):
    audio_path = tmp_path / "c-major.wav"
    sf.write(audio_path, _tone_chord([261.63, 329.63, 392.00]), 22050)

    events = recognize_chords(str(audio_path))

    assert events
    assert events[0]["label"] == "C"
    assert events[0]["start"] == 0.0
    assert events[0]["end"] <= 3.0


def test_chord_events_never_overlap(tmp_path):
    audio_path = tmp_path / "progression.wav"
    signal = np.concatenate([
        _tone_chord([261.63, 329.63, 392.00], 2.0),
        _tone_chord([196.00, 246.94, 293.66, 392.00], 2.0),
        _tone_chord([220.00, 261.63, 329.63], 2.0),
    ])
    sf.write(audio_path, signal, 22050)

    events = recognize_chords(str(audio_path))

    assert events
    for previous, current in zip(events, events[1:]):
        assert previous["end"] <= current["start"] + 0.001
    assert all(event["end"] > event["start"] for event in events)

def test_control_progression_detects_three_distinct_chords(tmp_path):
    sample_rate = 22050
    sections = [
        _tone_chord([261.63, 329.63, 392.00], 2.0, sample_rate),
        _tone_chord([196.00, 246.94, 293.66, 392.00], 2.0, sample_rate),
        _tone_chord([220.00, 261.63, 329.63], 2.0, sample_rate),
    ]
    audio_path = tmp_path / "c-g-am.wav"
    sf.write(audio_path, np.concatenate(sections), sample_rate)

    events = recognize_chords(str(audio_path))
    labels = {event["label"] for event in events}

    assert {"C", "G", "Am"}.issubset(labels)
