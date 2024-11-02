
from enum import Enum

CANDLE_COLORS = [
    (255, 100, 20),  # Warm yellow
    (255, 80, 0),    # Orange
    (200, 80, 0),    # Darker orange
    (200, 30, 0),    # Redish orange
    (255, 10, 0),    # Redish orange
]

class AnimationId(Enum):
    CycleFade=1
    Fade=2
    Blink=3
    Chase=4
    TwinkleStars=5
    CandleFlicker=6
    Bouncing=7
