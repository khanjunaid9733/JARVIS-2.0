---
name: science-fourier-transform
description: Compute FFT and visualize frequency spectra of signals.
---

# Fourier Transform Skill

## Purpose
Compute FFT and visualize frequency spectra of signals.

## When to Activate
Activate when the user asks to:
- FFT
- Fourier transform
- frequency spectrum
- signal analysis

## Core Workflows

```python
import numpy.fft; freq = np.fft.fft(signal); np.fft.fftfreq(n, d=1/sample_rate)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
