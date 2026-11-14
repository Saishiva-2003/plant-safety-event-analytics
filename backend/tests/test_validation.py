"""Validation + reproducibility tests (starter scale -> fast)."""
from generator.run import generate
from scripts.validate import validate


def test_validator_passes_and_flags_exactly_the_labelled_anomalies(tmp_path):
    generate("starter", 20261022, tmp_path, verbose=False)
    s = validate(tmp_path, write=False, verbose=False)
    assert s["overall"] == "PASS"
    assert s["failed"] == 0
    assert s["expected_anomalies"] == 5          # the 5 injected edge-case types


def test_same_seed_same_checksums(tmp_path):
    m1 = generate("starter", 20261022, tmp_path / "a", verbose=False)
    m2 = generate("starter", 20261022, tmp_path / "b", verbose=False)
    assert m1["combined_sha256"] == m2["combined_sha256"]


def test_different_seed_different_data(tmp_path):
    m1 = generate("starter", 20261022, tmp_path / "a", verbose=False)
    m2 = generate("starter", 1, tmp_path / "b", verbose=False)
    assert m1["combined_sha256"] != m2["combined_sha256"]