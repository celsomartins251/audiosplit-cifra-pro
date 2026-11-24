"""Scale-invariant SDR metric for stem benchmark comparisons."""
import numpy as np

def si_sdr(reference: np.ndarray, estimate: np.ndarray) -> float:
    reference = np.asarray(reference, dtype=np.float64).reshape(-1)
    estimate = np.asarray(estimate, dtype=np.float64).reshape(-1)
    length = min(reference.size, estimate.size)
    if length == 0:
        raise ValueError("Sinais vazios não podem ser comparados.")
    reference = reference[:length] - np.mean(reference[:length])
    estimate = estimate[:length] - np.mean(estimate[:length])
    energy = float(np.dot(reference, reference))
    if energy < 1e-12:
        raise ValueError("Stem de referência sem energia suficiente.")
    scale = float(np.dot(estimate, reference)) / energy
    target = scale * reference
    noise = estimate - target
    ratio = (float(np.dot(target, target)) + 1e-12) / (float(np.dot(noise, noise)) + 1e-12)
    return float(10.0 * np.log10(ratio))
