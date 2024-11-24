
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
    Twinkle=8
    TwinkleCycle=9
    Cover=10

ANIMATIONS = {
    "Cycle Fade": {
        "id": AnimationId.CycleFade.value,
        "description": "Gradually fades through a cycle of colors in a smooth transition."
    },
    "Fade": {
        "id": AnimationId.Fade.value,
        "description": "Fades LEDs in and out through a specified set of colors."
    },
    "Blink": {
        "id": AnimationId.Blink.value,
        "description": "Alternates LEDs between colors in color palette in a blinking pattern."
    },
    "Chase": {
        "id": AnimationId.Chase.value,
        "description": "Creates a chasing light effect where a color moves across the LEDs."
    },
    "Twinkle Stars": {
        "id": AnimationId.TwinkleStars.value,
        "description": "Simulates a starry night with LEDs twinkling at random intervals."
    },
    "Candle Flicker": {
        "id": AnimationId.CandleFlicker.value,
        "description": "Mimics the natural flicker of a candle flame with subtle brightness variations."
    },
    "Bouncing": {
        "id": AnimationId.Bouncing.value,
        "description": "Creates a bouncing light effect as if a ball is moving across the LEDs."
    },
    "Twinkle": {
        "id": AnimationId.Twinkle.value,
        "description": "Randomly twinkles individual LEDs with subtle fades on and off."
    },
    "Twinkle Cycle": {
        "id": AnimationId.TwinkleCycle.value,
        "description": "Combines twinkling with a color cycling effect."
    },
    "Cover": {
        "id": AnimationId.Cover.value,
        "description": "Simulates a sweeping cover effect where LEDs turn on sequentially."
    },
}
