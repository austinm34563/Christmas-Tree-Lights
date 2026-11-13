from enum import Enum

from visualization import (
    FftVisualization,
    WaveformVisualization,
    BeatVisualization,
    EnergyVisualization,
)

class VisualizationnId(Enum):
    FFT=1
    Waveform=2
    Beat=3
    Energy=4

VISUALIZATIONS = {
    "FFT": {
        "id": VisualizationnId.FFT.value,
        "description": "Frequency visualization of audio on LEDs."
    },
    "Waveform": {
        "id": VisualizationnId.Waveform.value,
        "description": "Displays audio amplitude across the LED strip."
    },
    "Beat": {
        "id": VisualizationnId.Beat.value,
        "description": "Flashes the whole strip when audio energy rises sharply."
    },
    "Energy": {
        "id": VisualizationnId.Energy.value,
        "description": "A loudness meter: quiet audio lights few LEDs, while loud audio lights most or all of the strip."
    },
}

# Map visualizations to their corresponding classes
VISUALIZATION_MAPPING = {
    VisualizationnId.FFT.value: FftVisualization,
    VisualizationnId.Waveform.value: WaveformVisualization,
    VisualizationnId.Beat.value: BeatVisualization,
    VisualizationnId.Energy.value: EnergyVisualization,
}
