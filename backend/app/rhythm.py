"""Tempo and beat tracking baseline."""
import numpy as np
import librosa

def analyze_rhythm(audio_path: str):
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    if y.size < sr:
        return {"tempo_bpm": None, "beats": [], "source": "librosa-beat-tracking"}
    hop_length = 512
    onset_envelope = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    tempo, beat_times = librosa.beat.beat_track(onset_envelope=onset_envelope, sr=sr, hop_length=hop_length, units="time")
    tempo_values = np.asarray(tempo).reshape(-1)
    bpm = float(tempo_values[0]) if tempo_values.size else None
    return {
        "tempo_bpm": round(bpm, 2) if bpm and np.isfinite(bpm) else None,
        "beats": [round(float(value), 3) for value in beat_times],
        "source": "librosa-beat-tracking-estimate",
        "note": "BPM e pulsos estimados; compasso e sensação de tempo não são inferidos automaticamente.",
    }
