"""Compare estimated stems with manually prepared reference stems.

Expected names in both directories: vocals.wav, drums.wav, bass.wav, other.wav.
Optional: guitar.wav and piano.wav.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from app.metrics import si_sdr

STEMS = ("vocals", "drums", "bass", "guitar", "piano", "other")

def load_mono(path: Path, target_sr: int):
    audio, sample_rate = sf.read(path, always_2d=True, dtype="float32")
    audio = np.mean(audio, axis=1)
    if sample_rate != target_sr:
        from math import gcd
        divisor = gcd(int(sample_rate), int(target_sr))
        audio = resample_poly(audio, target_sr // divisor, sample_rate // divisor)
    return audio

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", required=True, type=Path)
    parser.add_argument("--estimated-dir", required=True, type=Path)
    parser.add_argument("--sample-rate", type=int, default=44100)
    args = parser.parse_args()
    report = {"metric": "SI-SDR dB", "sample_rate": args.sample_rate, "stems": {}}
    for stem in STEMS:
        reference_path = args.reference_dir / f"{stem}.wav"
        estimate_path = args.estimated_dir / f"{stem}.wav"
        if not reference_path.exists() or not estimate_path.exists():
            continue
        reference = load_mono(reference_path, args.sample_rate)
        estimate = load_mono(estimate_path, args.sample_rate)
        report["stems"][stem] = {
            "si_sdr_db": round(si_sdr(reference, estimate), 3),
            "reference_samples": int(reference.size),
            "estimated_samples": int(estimate.size),
        }
    if not report["stems"]:
        raise SystemExit("Nenhum par de stems correspondente foi encontrado.")
    values = [item["si_sdr_db"] for item in report["stems"].values()]
    report["macro_average_si_sdr_db"] = round(float(np.mean(values)), 3)
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
