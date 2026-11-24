"""Baseline chroma-template chord recognizer. Outputs estimates, not ground truth."""
from __future__ import annotations

import numpy as np
import librosa

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
QUALITIES = {
    "": [0, 4, 7],
    "m": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "m7": [0, 3, 7, 10],
    "mMaj7": [0, 3, 7, 11],
    "m7b5": [0, 3, 6, 10],
    "dim7": [0, 3, 6, 9],
    "6": [0, 4, 7, 9],
    "m6": [0, 3, 7, 9],
    "add9": [0, 2, 4, 7],
    "9": [0, 2, 4, 7, 10],
    "maj9": [0, 2, 4, 7, 11],
    "m9": [0, 2, 3, 7, 10],
    "11": [0, 2, 4, 5, 7, 10],
    "13": [0, 2, 4, 7, 9, 10],
    "7b9": [0, 1, 4, 7, 10],
    "7#9": [0, 3, 4, 7, 10],
    "7#11": [0, 4, 6, 7, 10],
    "7b13": [0, 4, 7, 8, 10],
    "maj7#11": [0, 4, 6, 7, 11],
}

def _templates():
    matrix, labels = [], []
    for root, root_name in enumerate(NOTE_NAMES):
        for quality, intervals in QUALITIES.items():
            template = np.zeros(12, dtype=np.float32)
            template[(root + np.asarray(intervals)) % 12] = 1.0
            template /= np.linalg.norm(template)
            matrix.append(template)
            labels.append(root_name + quality)
    return np.stack(matrix, axis=0), labels

TEMPLATES, LABELS = _templates()

def recognize_chords(audio_path: str, window_seconds: float = 0.75, hop_seconds: float = 0.10):
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    if y.size < sr // 2:
        return []
    hop = 512
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop, n_chroma=12)
    # A janela curta reduz o borramento temporal nas trocas de acorde; o hop menor
    # melhora a resolução dos eventos sem tratar cada quadro como uma certeza.
    frames_per_window = max(2, int(window_seconds * sr / hop))
    frames_per_hop = max(1, int(hop_seconds * sr / hop))
    events = []
    for center_frame in range(0, chroma.shape[1], frames_per_hop):
        # Classify a centered analysis window, but assign only its central hop interval.
        # This prevents overlapping chord events in the exported timeline.
        start_frame = max(0, center_frame - frames_per_window // 2)
        end_frame = min(chroma.shape[1], center_frame + (frames_per_window + 1) // 2)
        if end_frame - start_frame < 2:
            continue
        profile = np.mean(chroma[:, start_frame:end_frame], axis=1)
        norm = float(np.linalg.norm(profile))
        if norm < 1e-7:
            continue
        profile = profile / norm
        scores = TEMPLATES @ profile
        order = np.argsort(scores)
        best = int(order[-1])
        best_score = float(scores[best])
        second_score = float(scores[order[-2]])
        margin = max(0.0, best_score - second_score)
        # Conservative abstention: ambiguous frames are not forced into a chord.
        if best_score < 0.48 or margin < 0.015:
            continue
        duration = len(y) / sr
        start = min(duration, center_frame * hop / sr)
        end = min(duration, (center_frame + frames_per_hop) * hop / sr)
        # CQT may expose padded frames beyond the original signal duration.
        # Never emit zero-length or reversed events at the audio boundary.
        if end <= start:
            continue
        events.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "label": LABELS[best],
            "confidence": round(min(1.0, best_score * (0.65 + margin)), 3),
            "source": "librosa-chroma-template-baseline",
        })
    if not events:
        return []
    # Collapse consecutive overlapping windows with the same chord into intervals.
    merged = []
    for event in events:
        if merged and merged[-1]["label"] == event["label"] and event["start"] <= merged[-1]["end"] + hop_seconds * 1.6:
            merged[-1]["end"] = event["end"]
            merged[-1]["confidence"] = round((merged[-1]["confidence"] + event["confidence"]) / 2, 3)
        else:
            merged.append(event.copy())
    # Remove very short isolated guesses; retain longer changes and sustained chords.
    return [e for e in merged if e["end"] - e["start"] >= 0.35]
