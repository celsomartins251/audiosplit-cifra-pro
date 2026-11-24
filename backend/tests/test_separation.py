from pathlib import Path
import subprocess

import pytest

from app import pipeline


@pytest.mark.parametrize(
    ("model_name", "expected"),
    [
        ("htdemucs_ft", ("vocals", "drums", "bass", "other")),
        ("htdemucs_6s", ("vocals", "drums", "bass", "guitar", "piano", "other")),
    ],
)
def test_expected_stems_for_supported_demucs_models(model_name, expected):
    assert pipeline._expected_stems(model_name) == expected


def test_demucs_runner_uses_configured_model_and_returns_all_stems(tmp_path, monkeypatch):
    source = tmp_path / "song.wav"
    source.write_bytes(b"test")
    output = tmp_path / "separated"
    model_name = "htdemucs_6s"
    monkeypatch.setattr(pipeline, "SEPARATION_MODEL", model_name)
    monkeypatch.setenv("DEMUCS_SHIFTS", "3")

    def fake_run(command, **kwargs):
        assert command[command.index("-n") + 1] == model_name
        assert command[command.index("--shifts") + 1] == "3"
        stem_dir = output / model_name / source.stem
        stem_dir.mkdir(parents=True)
        for stem in pipeline._expected_stems(model_name):
            (stem_dir / f"{stem}.wav").write_bytes(b"wav")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    stems = pipeline._run_demucs(source, output)

    assert set(stems) == set(pipeline._expected_stems(model_name))
    assert all(Path(path).is_file() for path in stems.values())


def test_demucs_runner_rejects_incomplete_stem_set(tmp_path, monkeypatch):
    source = tmp_path / "song.wav"
    source.write_bytes(b"test")
    output = tmp_path / "separated"
    monkeypatch.setattr(pipeline, "SEPARATION_MODEL", "htdemucs_ft")

    def fake_run(command, **kwargs):
        stem_dir = output / "htdemucs_ft" / source.stem
        stem_dir.mkdir(parents=True)
        (stem_dir / "vocals.wav").write_bytes(b"wav")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="Separação incompleta"):
        pipeline._run_demucs(source, output)
